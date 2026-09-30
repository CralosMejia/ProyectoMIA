"""Contratos de los puertos del historial (T6): Protocols, DTOs de escritura y aislamiento."""

import ast
import inspect
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.historial import ports
from app.application.historial.ports import (
    CargaRepository,
    LectorHistorico,
    LibroLeido,
    LibrosLeidos,
    MembresiaParaPrediccion,
    MembresiaRepository,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    ReferenciaOrigen,
    SocioRepository,
)
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan, TipoCarga
from app.domain.historico.registro import FilaCruda

INSTANTE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def nueva_carga(**cambios: object) -> NuevaCarga:
    datos: dict[str, object] = {
        "tipo": TipoCarga.MIGRACION_HISTORICA,
        "fecha_carga": INSTANTE,
        "nombre_archivo": "Control Gym 2025 sintetico.xlsx",
        "filas_leidas": 10,
        "filas_guardadas": 8,
        "filas_duplicadas": 0,
        "socios_enlazados": 5,
    }
    datos.update(cambios)
    return NuevaCarga(**datos)  # type: ignore[arg-type]  # construccion generica del test


def nueva_membresia(socio_id: int = 1, carga_id: int = 1) -> NuevaMembresia:
    return NuevaMembresia(
        socio_id=socio_id,
        carga_id=carga_id,
        plan=Plan.MENSUAL,
        forma_pago=FormaPago.EFECTIVO,
        origen=OrigenMembresia.HISTORICO,
        inicio_aproximado=False,
        fecha_actividad=date(2025, 1, 6),
        fecha_inicio=date(2025, 1, 6),
        fecha_vencimiento=date(2025, 2, 5),
        monto_cobrado=Decimal("39.50"),
        referencia_origen=ReferenciaOrigen(anio=2025, hoja="ENERO", fila=7),
    )


class LectorEnMemoria:
    def __init__(self, filas: Sequence[FilaCruda]) -> None:
        self._filas = filas

    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        libros = tuple(
            LibroLeido(nombre=r.name, anio=2025, hojas_incluidas=("ENERO",), hojas_omitidas=())
            for r in rutas
        )
        return LibrosLeidos(filas=tuple(self._filas), libros=libros)


class SocioRepositoryEnMemoria:
    def __init__(self) -> None:
        self.socios: list[NuevoSocio] = []

    def insertar_en_bloque(self, socios: Sequence[NuevoSocio]) -> list[int]:
        inicio = len(self.socios) + 1
        self.socios.extend(socios)
        return list(range(inicio, inicio + len(socios)))


class MembresiaRepositoryEnMemoria:
    def __init__(self) -> None:
        self.membresias: list[NuevaMembresia] = []

    def insertar_en_bloque(self, membresias: Sequence[NuevaMembresia]) -> int:
        self.membresias.extend(membresias)
        return len(membresias)

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        return [
            MembresiaParaPrediccion(
                membresia_id=i,
                socio_id=m.socio_id,
                plan=m.plan,
                forma_pago=m.forma_pago,
                fecha_inicio=m.fecha_inicio,
                fecha_vencimiento=m.fecha_vencimiento,
                fecha_actividad=m.fecha_actividad,
                monto_cobrado=m.monto_cobrado,
                inicio_aproximado=m.inicio_aproximado,
                socio_con_cedula=True,
            )
            for i, m in enumerate(self.membresias, start=1)
        ]


class CargaRepositoryEnMemoria:
    def __init__(self) -> None:
        self.cargas: list[NuevaCarga] = []

    def crear(self, carga: NuevaCarga) -> int:
        self.cargas.append(carga)
        return len(self.cargas)

    def ultima_fecha_carga(self) -> datetime | None:
        return max((c.fecha_carga for c in self.cargas), default=None)

    def hay_migracion_o_membresias(self) -> bool:
        return any(c.tipo is TipoCarga.MIGRACION_HISTORICA for c in self.cargas)


def test_ports_in_memory_doubles_satisfy_protocols() -> None:
    lector: LectorHistorico = LectorEnMemoria([])
    socios: SocioRepository = SocioRepositoryEnMemoria()
    membresias: MembresiaRepository = MembresiaRepositoryEnMemoria()
    cargas: CargaRepository = CargaRepositoryEnMemoria()

    assert isinstance(lector, LectorHistorico)
    assert isinstance(socios, SocioRepository)
    assert isinstance(membresias, MembresiaRepository)
    assert isinstance(cargas, CargaRepository)


def test_ports_object_without_method_is_not_a_repository() -> None:
    assert not isinstance(object(), SocioRepository)
    assert not isinstance(CargaRepositoryEnMemoria(), SocioRepository)


def test_leer_in_memory_double_returns_rows_and_sheets_per_book() -> None:
    fila = FilaCruda(anio=2025, hoja="ENERO", fila=7, mes_hoja=date(2025, 1, 1))
    lector: LectorHistorico = LectorEnMemoria([fila])

    leidos = lector.leer([Path("Control Gym 2025 sintetico.xlsx")])

    assert list(leidos.filas) == [fila]
    assert leidos.libros[0].nombre == "Control Gym 2025 sintetico.xlsx"
    assert leidos.libros[0].hojas_incluidas == ("ENERO",)


def test_insertar_en_bloque_in_memory_double_returns_ids_in_input_order() -> None:
    repo = SocioRepositoryEnMemoria()
    socios = [
        NuevoSocio(cedula=None, nombre="Socio Uno", nombre_normalizado="SOCIO UNO"),
        NuevoSocio(cedula="0000000002", nombre="Socio Dos", nombre_normalizado="SOCIO DOS"),
    ]

    assert repo.insertar_en_bloque(socios) == [1, 2]


def test_nueva_carga_naive_fecha_carga_raises_value_error() -> None:
    with pytest.raises(ValueError, match="zona horaria"):
        nueva_carga(fecha_carga=datetime(2026, 9, 1, 12, 0))  # noqa: DTZ001 - caso a probar


def test_nueva_carga_aware_fecha_carga_is_accepted() -> None:
    carga = nueva_carga()

    assert carga.fecha_carga == INSTANTE
    assert carga.tipo is TipoCarga.MIGRACION_HISTORICA


def test_nueva_carga_aware_non_utc_fecha_carga_is_accepted() -> None:
    quito = timezone(timedelta(hours=-5))
    carga = nueva_carga(fecha_carga=datetime(2026, 9, 1, 7, 0, tzinfo=quito))

    assert carga.fecha_carga == INSTANTE  # 07:00-05:00 es el mismo instante que 12:00 UTC


def test_nueva_membresia_socio_id_is_required() -> None:
    campos = {c.name: c for c in NuevaMembresia.__dataclass_fields__.values()}
    assert "socio_id" in campos
    assert campos["socio_id"].type in (int, "int")
    with pytest.raises(TypeError):
        NuevaMembresia(  # type: ignore[call-arg]  # falta socio_id a proposito
            carga_id=1,
            plan=Plan.MENSUAL,
            forma_pago=FormaPago.EFECTIVO,
            origen=OrigenMembresia.HISTORICO,
            inicio_aproximado=False,
            fecha_actividad=date(2025, 1, 6),
        )


def test_nueva_membresia_fecha_actividad_is_required() -> None:
    campos = {c.name: c for c in NuevaMembresia.__dataclass_fields__.values()}
    assert campos["fecha_actividad"].type in (date, "date")
    with pytest.raises(TypeError):
        NuevaMembresia(  # type: ignore[call-arg]  # falta fecha_actividad a proposito
            socio_id=1,
            carga_id=1,
            plan=Plan.MENSUAL,
            forma_pago=FormaPago.EFECTIVO,
            origen=OrigenMembresia.HISTORICO,
            inicio_aproximado=False,
        )


def test_read_methods_in_memory_doubles_follow_the_contract() -> None:
    membresias = MembresiaRepositoryEnMemoria()
    membresias.insertar_en_bloque([nueva_membresia()])
    cargas = CargaRepositoryEnMemoria()
    assert cargas.ultima_fecha_carga() is None
    assert cargas.hay_migracion_o_membresias() is False
    cargas.crear(nueva_carga())

    (leida,) = membresias.listar_para_prediccion()
    assert leida.fecha_actividad == date(2025, 1, 6)
    assert isinstance(leida.monto_cobrado, Decimal)
    assert cargas.ultima_fecha_carga() == INSTANTE
    assert cargas.hay_migracion_o_membresias() is True


def test_nueva_membresia_keeps_decimal_amount_and_reference() -> None:
    membresia = nueva_membresia()

    assert membresia.monto_cobrado == Decimal("39.50")
    assert isinstance(membresia.monto_cobrado, Decimal)
    assert membresia.referencia_origen == ReferenciaOrigen(anio=2025, hoja="ENERO", fila=7)
    assert membresia.estado_registro is None


@pytest.mark.parametrize(
    ("valor", "campo"),
    [
        (nueva_carga(), "nombre_archivo"),
        (nueva_membresia(), "socio_id"),
        (NuevoSocio(cedula=None, nombre="Socio", nombre_normalizado="SOCIO"), "nombre"),
    ],
)
def test_write_dtos_are_frozen(valor: object, campo: str) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(valor, campo, "otro")


def test_ports_module_does_not_depend_on_sessions_engines_or_orm() -> None:
    arbol = ast.parse(inspect.getsource(ports))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module)

    assert not any(m.startswith(("sqlalchemy", "app.infrastructure")) for m in importados)
    assert not any(m.split(".")[0] in {"pandas", "numpy", "sklearn"} for m in importados)


def test_ports_docstring_states_caller_owns_the_transaction() -> None:
    doc = inspect.getdoc(ports) or ""

    assert "commit" in doc
    assert "rollback" in doc


def test_membresia_para_prediccion_socio_con_cedula_is_required() -> None:
    campos = {
        "membresia_id": 1,
        "socio_id": 1,
        "plan": Plan.MENSUAL,
        "forma_pago": FormaPago.EFECTIVO,
        "fecha_inicio": date(2026, 9, 1),
        "fecha_vencimiento": date(2026, 10, 1),
        "fecha_actividad": date(2026, 9, 1),
        "monto_cobrado": Decimal("40"),
        "inicio_aproximado": False,
    }

    with pytest.raises(TypeError, match="socio_con_cedula"):
        ports.MembresiaParaPrediccion(**campos)  # type: ignore[arg-type]  # se prueba el campo obligatorio
    assert ports.MembresiaParaPrediccion(**campos, socio_con_cedula=False).socio_con_cedula is False  # type: ignore[arg-type]  # campos heterogeneos
