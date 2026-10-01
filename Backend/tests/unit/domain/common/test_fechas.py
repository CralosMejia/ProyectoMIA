import ast
import inspect
import sys
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.domain.common import fechas
from app.domain.common.fechas import hoy_en_negocio, limites_mes_negocio, sumar_meses

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("fecha", "meses", "esperado"),
    [
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
        (date(2026, 9, 29), 6, date(2027, 3, 29)),
        (date(2027, 8, 31), 6, date(2028, 2, 29)),
        (date(2026, 1, 15), 0, date(2026, 1, 15)),
        (date(2026, 12, 31), 1, date(2027, 1, 31)),
        (date(2026, 3, 31), -1, date(2026, 2, 28)),
        (date(2026, 1, 31), 12, date(2027, 1, 31)),
    ],
)
def test_sumar_meses_ajusta_al_ultimo_dia_del_mes(fecha: date, meses: int, esperado: date) -> None:
    assert sumar_meses(fecha, meses) == esperado


@pytest.mark.parametrize(
    ("instante", "esperado"),
    [
        (datetime(2026, 9, 30, 3, 30, tzinfo=UTC), date(2026, 9, 29)),
        (datetime(2026, 9, 29, 5, 0, tzinfo=UTC), date(2026, 9, 29)),
        (datetime(2026, 9, 29, 4, 59, tzinfo=UTC), date(2026, 9, 28)),
    ],
)
def test_hoy_en_negocio_usa_la_hora_de_ecuador(instante: datetime, esperado: date) -> None:
    assert hoy_en_negocio(instante) == esperado


def test_hoy_en_negocio_con_otra_zona_convierte_a_ecuador() -> None:
    madrid_verano = timezone(timedelta(hours=2))

    assert hoy_en_negocio(datetime(2026, 9, 30, 6, 30, tzinfo=madrid_verano)) == date(2026, 9, 29)


def test_modulo_fechas_solo_usa_libreria_estandar_y_no_lee_el_reloj_del_sistema() -> None:
    fuente = inspect.getsource(fechas)
    modulos: set[str] = set()
    llamadas: set[str] = set()
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])
        elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            llamadas.add(nodo.func.attr)

    assert modulos <= set(sys.stdlib_module_names)
    assert llamadas.isdisjoint({"now", "today", "utcnow", "time"})


def test_hoy_en_negocio_sin_zona_horaria_lanza_value_error() -> None:
    with pytest.raises(ValueError):
        hoy_en_negocio(datetime(2026, 9, 29, 12, 0))  # noqa: DTZ001 - se prueba el rechazo


@pytest.mark.parametrize(
    ("anio", "mes", "esperado"),
    [
        (
            2026,
            9,
            (datetime(2026, 9, 1, 5, tzinfo=UTC), datetime(2026, 10, 1, 5, tzinfo=UTC)),
        ),
        (
            2026,
            12,
            (datetime(2026, 12, 1, 5, tzinfo=UTC), datetime(2027, 1, 1, 5, tzinfo=UTC)),
        ),
    ],
)
def test_limites_mes_negocio_devuelve_rango_utc_de_ecuador(
    anio: int, mes: int, esperado: tuple[datetime, datetime]
) -> None:
    assert limites_mes_negocio(anio, mes) == esperado
