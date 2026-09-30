"""Contratos de los puertos de cargas y de la fila de plantilla (R-007 T2).

Sin login (RT-12): no hay propietario ni pruebas de aislamiento entre usuarios.
"""

import ast
import inspect
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from types import ModuleType

import pytest

from app.application.cargas import ports
from app.application.cargas.ports import (
    ClaveMembresia,
    ConsultasCarga,
    ContextoCargas,
    EscrituraCarga,
    LectorPlantilla,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    UnidadDeTrabajoCargas,
)
from app.application.modelo.ports import EstadoSistema, EstadoSistemaRepository
from app.domain.cargas import fila as modulo_fila
from app.domain.cargas.enlace import ClaveMembresia as ClaveDominio
from app.domain.cargas.fila import COLUMNAS, FilaPlantilla, PlantillaLeida
from app.domain.common.enums import EstadoMigracion, Plan, TipoCarga

pytestmark = pytest.mark.unit

INICIO = date(2026, 9, 1)
FIN = date(2026, 10, 1)


class LectorEnMemoria:
    def __init__(self, plantilla: PlantillaLeida) -> None:
        self.plantilla = plantilla

    def leer(self, contenido: bytes) -> PlantillaLeida:
        return self.plantilla


class ConsultasEnMemoria:
    def __init__(self) -> None:
        self.cedulas: dict[str, int] = {}
        self.sin_cedula: dict[str, list[int]] = {}
        self.claves: set[ClaveMembresia] = set()

    def socios_por_cedulas(self, cedulas: Iterable[str]) -> dict[str, int]:
        return {c: self.cedulas[c] for c in cedulas if c in self.cedulas}

    def socios_sin_cedula_por_nombres(self, nombres: Iterable[str]) -> dict[str, list[int]]:
        return {n: self.sin_cedula[n] for n in nombres if n in self.sin_cedula}

    def claves_existentes(self, socio_ids: Iterable[int]) -> set[ClaveMembresia]:
        ids = set(socio_ids)
        return {c for c in self.claves if c.socio_id in ids}


class EscrituraEnMemoria:
    def __init__(self) -> None:
        self.socios: list[NuevoSocio] = []
        self.cedulas: dict[int, str] = {}
        self.membresias: list[NuevaMembresia] = []
        self.cargas: list[NuevaCarga] = []

    def crear_socios(self, socios: Sequence[NuevoSocio]) -> list[int]:
        inicio = len(self.socios) + 1
        self.socios.extend(socios)
        return list(range(inicio, inicio + len(socios)))

    def asignar_cedula(
        self, socio_id: int, cedula: str, celular: str | None, correo: str | None
    ) -> None:
        self.cedulas[socio_id] = cedula

    def insertar_membresias(self, membresias: Sequence[NuevaMembresia]) -> int:
        self.membresias.extend(membresias)
        return len(membresias)

    def crear_carga(self, carga: NuevaCarga) -> int:
        self.cargas.append(carga)
        return len(self.cargas)


class EstadoEnMemoria:
    def obtener(self) -> EstadoSistema:
        return EstadoSistema(EstadoMigracion.COMPLETADA, None)

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        raise AssertionError("la carga no cambia la migracion")

    def fijar_proxima_fecha(self, fecha: date) -> None:
        raise AssertionError("la carga no cambia el reentrenamiento")


class ContextoEnMemoria:
    def __init__(self) -> None:
        self._consultas = ConsultasEnMemoria()
        self._escritura = EscrituraEnMemoria()
        self._estado = EstadoEnMemoria()
        self.bloqueado = False
        self.commits = 0

    @property
    def consultas(self) -> ConsultasCarga:
        return self._consultas

    @property
    def escritura(self) -> EscrituraCarga:
        return self._escritura

    @property
    def estado(self) -> EstadoSistemaRepository:
        return self._estado

    def bloquear(self) -> None:
        self.bloqueado = True

    def commit(self) -> None:
        self.commits += 1


def abrir_unidad(contexto: ContextoEnMemoria) -> UnidadDeTrabajoCargas:
    @contextmanager
    def unidad() -> Iterator[ContextoCargas]:
        yield contexto

    return unidad


def test_in_memory_doubles_satisfy_protocols() -> None:
    contexto = ContextoEnMemoria()
    lector: LectorPlantilla = LectorEnMemoria(PlantillaLeida(()))
    consultas: ConsultasCarga = ConsultasEnMemoria()
    escritura: EscrituraCarga = EscrituraEnMemoria()
    ctx: ContextoCargas = contexto
    unidad: UnidadDeTrabajoCargas = abrir_unidad(contexto)

    assert isinstance(lector, LectorPlantilla)
    assert isinstance(consultas, ConsultasCarga)
    assert isinstance(escritura, EscrituraCarga)
    assert isinstance(ctx, ContextoCargas)
    assert isinstance(unidad, UnidadDeTrabajoCargas)


@pytest.mark.parametrize(
    "protocolo",
    [LectorPlantilla, ConsultasCarga, EscrituraCarga, ContextoCargas, UnidadDeTrabajoCargas],
)
def test_object_without_methods_does_not_satisfy_protocol(protocolo: type) -> None:
    assert not isinstance(object(), protocolo)


def test_unit_of_work_double_yields_shared_context() -> None:
    contexto = ContextoEnMemoria()
    unidad = abrir_unidad(contexto)

    with unidad() as ctx:
        ctx.bloquear()
        ids = ctx.escritura.crear_socios([NuevoSocio(None, "Socio Sintetico", "SOCIO SINTETICO")])
        ctx.escritura.crear_carga(
            NuevaCarga(
                tipo=TipoCarga.PLANTILLA,
                fecha_carga=datetime(2026, 9, 29, 15, 0, tzinfo=UTC),
                nombre_archivo="plantilla.xlsx",
                filas_leidas=1,
                filas_guardadas=1,
                filas_duplicadas=0,
                socios_enlazados=0,
            )
        )
        ctx.commit()
        estado = ctx.estado.obtener()

    assert ids == [1]
    assert contexto.bloqueado
    assert contexto.commits == 1
    assert estado.migracion_historica is EstadoMigracion.COMPLETADA


def test_clave_membresia_is_frozen_and_hashable() -> None:
    clave = ClaveMembresia(1, INICIO, FIN, Plan.MENSUAL)

    assert clave == ClaveMembresia(1, INICIO, FIN, Plan.MENSUAL)
    assert len({clave, ClaveMembresia(1, INICIO, FIN, Plan.MENSUAL)}) == 1
    with pytest.raises(FrozenInstanceError):
        clave.socio_id = 2  # type: ignore[misc]  # se comprueba que es inmutable


def test_clave_membresia_is_the_domain_type() -> None:
    assert ClaveMembresia is ClaveDominio


def test_consultas_double_filters_keys_by_socio() -> None:
    consultas = ConsultasEnMemoria()
    consultas.claves = {
        ClaveMembresia(1, INICIO, FIN, Plan.MENSUAL),
        ClaveMembresia(2, INICIO, FIN, Plan.MENSUAL),
    }

    assert consultas.claves_existentes([1]) == {ClaveMembresia(1, INICIO, FIN, Plan.MENSUAL)}


@pytest.mark.parametrize("numero", [1, 0, -3])
def test_fila_plantilla_below_row_2_raises_value_error(numero: int) -> None:
    with pytest.raises(ValueError, match="fila"):
        FilaPlantilla(numero)


def test_fila_plantilla_from_values_maps_columns_a_to_n_in_order() -> None:
    valores: list[object] = [f"v{i}" for i in range(14)]

    fila = FilaPlantilla.desde_valores(7, valores)

    assert fila.fila == 7
    assert [fila.valor(letra) for letra, _ in COLUMNAS] == valores
    assert fila.estado_registro == "v0"
    assert fila.observaciones == "v13"
    assert [letra for letra, _ in COLUMNAS] == list("ABCDEFGHIJKLMN")


def test_fila_plantilla_from_short_values_fills_with_none() -> None:
    fila = FilaPlantilla.desde_valores(2, ["NUEVO", "Socio Sintetico"])

    assert fila.nombre == "Socio Sintetico"
    assert fila.cedula is None
    assert fila.observaciones is None


def test_fila_plantilla_more_than_14_values_raises_value_error() -> None:
    with pytest.raises(ValueError, match="14"):
        FilaPlantilla.desde_valores(2, [None] * 15)


def test_fila_plantilla_unknown_column_raises_value_error() -> None:
    with pytest.raises(ValueError, match="columna"):
        FilaPlantilla(2).valor("O")


def test_fila_plantilla_repr_hides_personal_data() -> None:
    fila = FilaPlantilla.desde_valores(
        2, [None, "Nombre Ficticio", "1700000019", "0980000000", "x@example.com"]
    )

    texto = repr(fila)
    for dato in ("Nombre Ficticio", "1700000019", "0980000000", "x@example.com"):
        assert dato not in texto


def test_plantilla_leida_is_frozen() -> None:
    plantilla = PlantillaLeida((FilaPlantilla(2),))

    with pytest.raises(FrozenInstanceError):
        plantilla.filas = ()  # type: ignore[misc]  # se comprueba que es inmutable


def _modulos_importados(modulo: ModuleType) -> set[str]:
    arbol = ast.parse(inspect.getsource(modulo))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module)
    return importados


@pytest.mark.parametrize("modulo", [ports, modulo_fila])
def test_modules_do_not_depend_on_infrastructure_or_data_libraries(modulo: ModuleType) -> None:
    importados = _modulos_importados(modulo)

    assert not any(m.startswith("app.infrastructure") for m in importados)
    prohibidos = {"pandas", "numpy", "sklearn", "openpyxl", "sqlalchemy"}
    assert not any(m.split(".")[0] in prohibidos for m in importados)


def test_ports_docstring_states_no_commit_rollback_nor_delete() -> None:
    doc = inspect.getdoc(ports) or ""

    assert "commit" in doc
    assert "rollback" in doc
    assert "delete" in doc
    for protocolo in (ConsultasCarga, EscrituraCarga):
        assert not any(n.startswith(("delete", "borrar")) for n in dir(protocolo))
