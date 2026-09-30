"""Nombre por defecto de una lista (R-008 T6, decision (g))."""

from datetime import date

import pytest

from app.domain.listas.nombre import LONGITUD_MAXIMA_NOMBRE, MESES_CORTOS, nombre_por_defecto

pytestmark = pytest.mark.unit


def test_nombre_por_defecto_29_sep_2026_formato_corto() -> None:
    assert nombre_por_defecto(date(2026, 9, 29)) == "Lista del 29 sep 2026"


def test_nombre_por_defecto_dia_sin_cero_inicial() -> None:
    assert nombre_por_defecto(date(2027, 1, 5)) == "Lista del 5 ene 2027"


@pytest.mark.parametrize(
    ("mes", "corto"),
    [
        (1, "ene"),
        (2, "feb"),
        (3, "mar"),
        (4, "abr"),
        (5, "may"),
        (6, "jun"),
        (7, "jul"),
        (8, "ago"),
        (9, "sep"),
        (10, "oct"),
        (11, "nov"),
        (12, "dic"),
    ],
)
def test_nombre_por_defecto_cada_mes_usa_su_abreviatura(mes: int, corto: str) -> None:
    assert nombre_por_defecto(date(2026, mes, 1)) == f"Lista del 1 {corto} 2026"
    assert MESES_CORTOS[mes - 1] == corto


def test_nombre_por_defecto_nunca_supera_la_longitud_maxima() -> None:
    assert LONGITUD_MAXIMA_NOMBRE == 80
    assert len(nombre_por_defecto(date(9999, 12, 31))) <= LONGITUD_MAXIMA_NOMBRE


def test_nombre_module_uses_only_stdlib_without_locale_strftime_or_clock() -> None:
    import ast
    import inspect
    import sys

    import app.domain.listas.nombre as modulo

    fuente = inspect.getsource(modulo)
    arbol = ast.parse(fuente)
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])

    assert importados <= set(sys.stdlib_module_names)
    assert "locale" not in importados
    assert "strftime" not in fuente
    assert ".now(" not in fuente
    assert ".today(" not in fuente
