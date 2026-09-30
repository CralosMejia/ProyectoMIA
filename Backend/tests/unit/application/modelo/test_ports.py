"""Contratos de los puertos del modelo predictivo (R-004 T2): Protocols, DTOs y aislamiento.

Sin login (RT-12): no hay propietario ni pruebas de aislamiento entre usuarios.
"""

import ast
import inspect
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.modelo import ports
from app.application.modelo.ports import (
    BloqueoMigracion,
    EstadoSistema,
    EstadoSistemaRepository,
    IntentoRepository,
    ModeloGuardado,
    ModeloRepository,
    NuevoIntento,
    NuevoModelo,
)
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)

pytestmark = pytest.mark.unit

INSTANTE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def nuevo_modelo(**cambios: object) -> NuevoModelo:
    base = NuevoModelo(
        version=1,
        fecha_entrenamiento=INSTANTE,
        ciclos_entrenamiento=100,
        periodo_desde=date(2023, 1, 1),
        periodo_hasta=date(2026, 8, 31),
        prevalencia=Decimal("0.35"),
        umbral_alto=Decimal("0.7"),
        umbral_medio=Decimal("0.4"),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=b"\x00\x01",
        metadata_tecnica={"n_estimators": 300},
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # construccion generica del test


def nuevo_intento(**cambios: object) -> NuevoIntento:
    base = NuevoIntento(
        fecha=INSTANTE,
        disparador=DisparadorReentrenamiento.INICIAL,
        resultado=ResultadoReentrenamiento.ENTRENADO,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # construccion generica del test


class ModeloRepositoryEnMemoria:
    def __init__(self) -> None:
        self.guardados: list[ModeloGuardado] = []

    def crear(self, modelo: NuevoModelo) -> int:
        nuevo_id = len(self.guardados) + 1
        self.guardados.append(
            ModeloGuardado(
                id=nuevo_id,
                version=modelo.version,
                fecha_entrenamiento=modelo.fecha_entrenamiento,
                ciclos_entrenamiento=modelo.ciclos_entrenamiento,
                periodo_desde=modelo.periodo_desde,
                periodo_hasta=modelo.periodo_hasta,
                prevalencia=modelo.prevalencia,
                umbral_alto=modelo.umbral_alto,
                umbral_medio=modelo.umbral_medio,
                porcentajes_umbral=modelo.porcentajes_umbral,
                artefacto=modelo.artefacto,
                metadata_tecnica=modelo.metadata_tecnica,
            )
        )
        return nuevo_id

    def obtener_vigente(self) -> ModeloGuardado | None:
        return self.guardados[-1] if self.guardados else None


class IntentoRepositoryEnMemoria:
    def __init__(self) -> None:
        self.intentos: list[NuevoIntento] = []

    def crear(self, intento: NuevoIntento) -> int:
        self.intentos.append(intento)
        return len(self.intentos)


class EstadoSistemaEnMemoria:
    def __init__(self) -> None:
        self.estado = EstadoSistema(EstadoMigracion.PENDIENTE, None)

    def obtener(self) -> EstadoSistema:
        return self.estado

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        self.estado = replace(self.estado, migracion_historica=estado)

    def fijar_proxima_fecha(self, fecha: date) -> None:
        self.estado = replace(self.estado, proxima_fecha_reentrenamiento=fecha)


class BloqueoEnMemoria:
    def __init__(self) -> None:
        self.tomado = False

    def intentar_adquirir(self) -> bool:
        if self.tomado:
            return False
        self.tomado = True
        return True

    def liberar(self) -> None:
        self.tomado = False


def test_ports_in_memory_doubles_satisfy_protocols() -> None:
    modelos: ModeloRepository = ModeloRepositoryEnMemoria()
    intentos: IntentoRepository = IntentoRepositoryEnMemoria()
    estado: EstadoSistemaRepository = EstadoSistemaEnMemoria()
    bloqueo: BloqueoMigracion = BloqueoEnMemoria()

    assert isinstance(modelos, ModeloRepository)
    assert isinstance(intentos, IntentoRepository)
    assert isinstance(estado, EstadoSistemaRepository)
    assert isinstance(bloqueo, BloqueoMigracion)


def test_ports_object_without_methods_is_not_a_port() -> None:
    assert not isinstance(object(), ModeloRepository)
    assert not isinstance(IntentoRepositoryEnMemoria(), ModeloRepository)
    assert not isinstance(IntentoRepositoryEnMemoria(), BloqueoMigracion)


def test_in_memory_doubles_follow_the_contract() -> None:
    modelos = ModeloRepositoryEnMemoria()
    assert modelos.obtener_vigente() is None
    modelos.crear(nuevo_modelo())
    modelos.crear(nuevo_modelo(version=2))
    vigente = modelos.obtener_vigente()
    assert vigente is not None
    assert vigente.version == 2

    estado = EstadoSistemaEnMemoria()
    estado.fijar_migracion(EstadoMigracion.EN_CURSO)
    estado.fijar_proxima_fecha(date(2027, 2, 28))
    assert estado.obtener() == EstadoSistema(EstadoMigracion.EN_CURSO, date(2027, 2, 28))

    bloqueo = BloqueoEnMemoria()
    assert bloqueo.intentar_adquirir() is True
    assert bloqueo.intentar_adquirir() is False
    bloqueo.liberar()
    assert bloqueo.intentar_adquirir() is True


def test_nuevo_modelo_umbral_alto_below_umbral_medio_raises_value_error() -> None:
    with pytest.raises(ValueError, match="umbral_alto"):
        nuevo_modelo(umbral_alto=Decimal("0.3"), umbral_medio=Decimal("0.4"))


def test_nuevo_modelo_equal_thresholds_are_accepted() -> None:
    modelo = nuevo_modelo(umbral_alto=Decimal("0.5"), umbral_medio=Decimal("0.5"))

    assert modelo.umbral_alto == modelo.umbral_medio


@pytest.mark.parametrize("campo", ["prevalencia", "umbral_alto", "umbral_medio"])
@pytest.mark.parametrize("valor", [Decimal("-0.01"), Decimal("1.01")])
def test_nuevo_modelo_probability_out_of_range_raises_value_error(
    campo: str, valor: Decimal
) -> None:
    cambios: dict[str, object] = {campo: valor}
    if campo == "umbral_alto":
        cambios["umbral_medio"] = Decimal("0")
    if campo == "umbral_medio":
        cambios["umbral_alto"] = Decimal("1")
    with pytest.raises(ValueError, match="entre 0 y 1"):
        nuevo_modelo(**cambios)


def test_nuevo_modelo_naive_fecha_raises_value_error() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        nuevo_modelo(fecha_entrenamiento=datetime(2026, 9, 1, 12, 0))  # noqa: DTZ001 - caso a probar


def test_nuevo_modelo_invalid_version_cycles_or_period_raise_value_error() -> None:
    with pytest.raises(ValueError, match="version"):
        nuevo_modelo(version=0)
    with pytest.raises(ValueError, match="ciclos_entrenamiento"):
        nuevo_modelo(ciclos_entrenamiento=-1)
    with pytest.raises(ValueError, match="periodo_hasta"):
        nuevo_modelo(periodo_desde=date(2026, 9, 1), periodo_hasta=date(2026, 8, 31))


def test_nuevo_modelo_keeps_decimal_values() -> None:
    modelo = nuevo_modelo()

    assert isinstance(modelo.prevalencia, Decimal)
    assert modelo.umbral_alto == Decimal("0.7")


def test_nuevo_intento_naive_fecha_raises_value_error() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        nuevo_intento(fecha=datetime(2026, 9, 1, 12, 0))  # noqa: DTZ001 - caso a probar


@pytest.mark.parametrize("campo", ["pr_auc_candidato", "pr_auc_vigente"])
def test_nuevo_intento_pr_auc_out_of_range_raises_value_error(campo: str) -> None:
    with pytest.raises(ValueError, match="entre 0 y 1"):
        nuevo_intento(**{campo: Decimal("1.5")})


def test_nuevo_intento_negative_new_cycles_raises_value_error() -> None:
    with pytest.raises(ValueError, match="ciclos_nuevos"):
        nuevo_intento(ciclos_nuevos=-1)


def test_nuevo_intento_defaults_are_empty() -> None:
    intento = nuevo_intento()

    assert intento.modelo_id is None
    assert intento.resultado is ResultadoReentrenamiento.ENTRENADO


@pytest.mark.parametrize(
    ("valor", "campo"),
    [
        (nuevo_modelo(), "version"),
        (nuevo_intento(), "motivo"),
        (EstadoSistema(EstadoMigracion.PENDIENTE, None), "migracion_historica"),
    ],
)
def test_dtos_are_frozen(valor: object, campo: str) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(valor, campo, "otro")


def test_ports_module_does_not_depend_on_infrastructure_or_data_libraries() -> None:
    arbol = ast.parse(inspect.getsource(ports))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module)

    assert not any(m.startswith(("sqlalchemy", "app.infrastructure")) for m in importados)
    assert not any(m.split(".")[0] in {"pandas", "numpy", "sklearn"} for m in importados)


def test_ports_docstring_states_no_commit_rollback_nor_delete() -> None:
    doc = inspect.getdoc(ports) or ""

    assert "commit" in doc
    assert "rollback" in doc
    assert "delete" in doc
    for puerto in (ModeloRepository, IntentoRepository, EstadoSistemaRepository):
        assert not any(nombre.startswith(("delete", "borrar")) for nombre in dir(puerto))
