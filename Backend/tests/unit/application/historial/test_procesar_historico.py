"""Caso de uso ProcesarHistorico con un lector doble (sin pandas, sin base de datos)."""

import inspect
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.historial.ports import LibroLeido, LibrosLeidos
from app.application.historial.procesar_historico import (
    InformeHistorico,
    ProcesarHistorico,
)
from app.domain.common.enums import EstadoCiclo
from app.domain.historico.ciclos import MotivoCiclo, SinMesesDisponiblesError
from app.domain.historico.errores import HojaSinEncabezadoError
from app.domain.historico.registro import FilaCruda

pytestmark = pytest.mark.unit

MES = date(2026, 8, 1)
NOMBRES = ("Ana Perez Lopez", "Carlos Mena Ruiz", "Diana Soto Vera", "LUIS")
CEDULAS = ("1712345678", "0999000011")


def _celda(anio: int, mes: int, dia: int) -> datetime:
    return datetime(anio, mes, dia)  # noqa: DTZ001 - celda Excel sin zona


def _fila(fila: int, **campos: object) -> FilaCruda:
    return FilaCruda(anio=2026, hoja="AGOSTO", fila=fila, mes_hoja=MES, **campos)  # type: ignore[arg-type]  # campos opcionales de la fila


FILAS = (
    _fila(2, nombre=None, cedula=None),  # no util
    _fila(3, nombre="LUIS", cedula="1700000001"),  # sin identidad (< 5 letras)
    _fila(  # evaluable (vence 07-01, T+30 = 07-31 <= corte); renueva con la fila 5
        4,
        nombre=NOMBRES[0],
        cedula=CEDULAS[0],
        celular="0991234567",
        correo="ana@example.com",
        plan="1 MES",
        fecha_inicio=_celda(2026, 6, 1),
        fecha_fin=_celda(2026, 7, 1),
        monto_cobrado="39,50 USD",
    ),
    _fila(  # pendiente: vence 08-20, T+30 > corte (caso del tutor)
        5,
        nombre=NOMBRES[0],
        cedula=CEDULAS[0],
        plan="1 MES",
        fecha_inicio=_celda(2026, 7, 5),
        fecha_fin="20/08/2026",
        monto_cobrado=-5,
    ),
    _fila(  # evaluable sin cedula; no renueva
        6,
        nombre=NOMBRES[1],
        plan="1 MES",
        fecha_inicio=_celda(2026, 1, 1),
        fecha_fin=_celda(2026, 2, 1),
    ),
    _fila(7, nombre=NOMBRES[2], cedula=CEDULAS[1], plan="1 MES"),  # excluido: sin vencimiento
)


class LectorDoble:
    def __init__(self, filas: Sequence[FilaCruda]) -> None:
        self.filas = filas
        self.rutas: list[Sequence[Path]] = []

    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        self.rutas.append(rutas)
        libro = LibroLeido("Control Gym 2026.xlsx", 2026, ("AGOSTO",), ("VENTAS", "DIARIOS"))
        return LibrosLeidos(filas=tuple(self.filas), libros=(libro,))


@pytest.fixture
def informe() -> InformeHistorico:
    return ProcesarHistorico(LectorDoble(FILAS)).ejecutar([Path("x.xlsx")]).informe


def test_ejecutar_pasa_las_rutas_al_lector() -> None:
    lector = LectorDoble(FILAS)
    rutas = [Path("a.xlsx"), Path("b.xlsx")]
    ProcesarHistorico(lector).ejecutar(rutas)
    assert lector.rutas == [rutas]


def test_ejecutar_seis_filas_conteos_de_limpieza_exactos(informe: InformeHistorico) -> None:
    assert informe.libros == 1
    assert informe.hojas_incluidas == 1
    assert informe.hojas_omitidas == 2
    assert informe.filas_leidas == 6
    assert informe.descartadas_no_utiles == 1
    assert informe.utiles == 5
    assert informe.sin_identidad == 1
    assert informe.con_identidad == 4
    assert informe.socios_distintos == 3
    assert informe.socios_por_cedula == 2
    assert informe.socios_por_nombre == 1
    assert informe.registros_por_cedula == 3
    assert informe.registros_por_nombre == 1
    assert informe.inicio_aproximado == 1
    assert informe.montos_invalidos == 1


def test_ejecutar_seis_filas_ciclos_por_estado_y_motivo(informe: InformeHistorico) -> None:
    assert informe.fecha_corte == date(2026, 8, 31)
    assert informe.ciclos_por_estado == {"EVALUABLE": 2, "PENDIENTE": 1, "EXCLUIDO": 1}
    assert informe.ciclos_por_motivo == {
        "SIN_VENCIMIENTO": 1,
        "FECHA_FUERA_DE_RANGO": 0,
        "VENCIMIENTO_POSTERIOR_AL_CORTE": 0,
        "PASE_DIARIO": 0,
        "DURACION_IMPLAUSIBLE": 0,
        "VENTANA_INCOMPLETA": 1,
        "EVALUABLE": 2,
    }
    assert sum(informe.ciclos_por_estado.values()) == informe.con_identidad


def test_ejecutar_seis_filas_etiqueta_y_prevalencia_decimal(informe: InformeHistorico) -> None:
    assert informe.evaluables == 2
    assert informe.no_renovo == 1
    assert informe.renovo == 1
    assert informe.prevalencia == Decimal("0.5")
    assert isinstance(informe.prevalencia, Decimal)
    assert informe.rango_vencimientos == (date(2026, 2, 1), date(2026, 8, 20))
    assert informe.rango_vencimientos_evaluables == (date(2026, 2, 1), date(2026, 7, 1))


def test_ejecutar_devuelve_registros_ciclos_y_corte() -> None:
    resultado = ProcesarHistorico(LectorDoble(FILAS)).ejecutar([])
    assert resultado.fecha_corte == date(2026, 8, 31)
    assert len(resultado.registros) == 4
    assert [c.registro for c in resultado.ciclos] == list(resultado.registros)
    por_fila = {c.registro.referencia[2]: c for c in resultado.ciclos}
    assert por_fila[4].no_renovo is False and por_fila[4].fecha_renovacion == date(2026, 7, 5)
    assert (por_fila[5].estado, por_fila[5].motivo) == (
        EstadoCiclo.PENDIENTE,
        MotivoCiclo.VENTANA_INCOMPLETA,
    )
    assert por_fila[6].no_renovo is True


def test_ejecutar_sin_evaluables_prevalencia_none() -> None:
    informe = ProcesarHistorico(LectorDoble(FILAS[5:])).ejecutar([]).informe
    assert informe.evaluables == 0
    assert informe.prevalencia is None
    assert informe.rango_vencimientos is None
    assert informe.rango_vencimientos_evaluables is None


def test_ejecutar_sin_filas_lanza_error_de_dominio() -> None:
    with pytest.raises(SinMesesDisponiblesError):
        ProcesarHistorico(LectorDoble(())).ejecutar([])


def _valores_planos(valor: object) -> list[object]:
    if isinstance(valor, dict):
        return [x for v in valor.values() for x in _valores_planos(v)]
    if isinstance(valor, list | tuple):
        return [x for v in valor for x in _valores_planos(v)]
    return [valor]


def test_a_dict_solo_numeros_fechas_y_claves_fijas(informe: InformeHistorico) -> None:
    datos = informe.a_dict()
    assert set(datos) == {
        "libros",
        "hojas_incluidas",
        "hojas_omitidas",
        "filas_leidas",
        "descartadas_no_utiles",
        "utiles",
        "sin_identidad",
        "con_identidad",
        "socios_distintos",
        "socios_por_cedula",
        "socios_por_nombre",
        "registros_por_cedula",
        "registros_por_nombre",
        "inicio_aproximado",
        "montos_invalidos",
        "fecha_corte",
        "ciclos_por_estado",
        "ciclos_por_motivo",
        "evaluables",
        "no_renovo",
        "renovo",
        "prevalencia",
        "rango_vencimientos",
        "rango_vencimientos_evaluables",
    }
    assert set(datos["ciclos_por_estado"]) == {e.value for e in EstadoCiclo}  # type: ignore[arg-type]  # valor anidado del dict
    assert set(datos["ciclos_por_motivo"]) == {m.value for m in MotivoCiclo}  # type: ignore[arg-type]  # valor anidado del dict
    for valor in _valores_planos(datos):
        assert valor is None or isinstance(valor, int | Decimal | date)
        assert not isinstance(valor, bool | float | str)


def test_informe_y_resultado_no_exponen_datos_personales() -> None:
    resultado = ProcesarHistorico(LectorDoble(FILAS)).ejecutar([])
    personales = (*NOMBRES, *CEDULAS, "ana@example.com", "0991234567", "ANA PEREZ LOPEZ")
    textos = (
        repr(resultado),
        str(resultado),
        repr(resultado.informe),
        str(resultado.informe.a_dict()),
    )
    for texto in textos:
        assert not any(dato in texto for dato in personales)


# ------------------------------------------------------------------ casos limite (test-engineer)


class LectorQueFalla:
    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        raise HojaSinEncabezadoError("Control Gym 2026.xlsx", "AGOSTO")


def test_ejecutar_error_del_lector_se_propaga_sin_resultado() -> None:
    with pytest.raises(HojaSinEncabezadoError) as error:
        ProcesarHistorico(LectorQueFalla()).ejecutar([Path("x.xlsx")])
    assert (error.value.libro, error.value.hoja) == ("Control Gym 2026.xlsx", "AGOSTO")


def test_init_solo_recibe_el_lector_sin_repositorios() -> None:
    parametros = list(inspect.signature(ProcesarHistorico.__init__).parameters)
    assert parametros == ["self", "lector"]
    modulo = inspect.getmodule(ProcesarHistorico)
    assert modulo is not None
    importados = {
        getattr(v, "__module__", "") or getattr(v, "__name__", "") for v in vars(modulo).values()
    }
    assert not any("sqlalchemy" in m or "infrastructure" in m for m in importados)


def test_ejecutar_dos_veces_con_el_mismo_lector_da_el_mismo_informe() -> None:
    caso = ProcesarHistorico(LectorDoble(FILAS))
    assert caso.ejecutar([]).informe == caso.ejecutar([]).informe


def test_ejecutar_solo_filas_no_utiles_cuenta_y_no_crea_ciclos() -> None:
    filas = (_fila(2), _fila(3, nombre="TOTAL", cedula=None), _fila(4, nombre="LUIS"))
    resultado = ProcesarHistorico(LectorDoble(filas)).ejecutar([])
    informe = resultado.informe
    assert informe.filas_leidas == 3
    assert informe.con_identidad == 0
    assert resultado.ciclos == ()
    assert sum(informe.ciclos_por_estado.values()) == 0
    assert informe.prevalencia is None
