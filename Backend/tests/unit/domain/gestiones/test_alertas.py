"""Grupos de alerta por fecha de seguimiento (R-011 T1, decision (a))."""

import ast
import inspect
import sys
from datetime import date, timedelta

import pytest

from app.domain.gestiones import alertas
from app.domain.gestiones.alertas import DIAS_PROXIMAS, GrupoAlerta, rango_de

pytestmark = pytest.mark.unit

HOY = date(2026, 9, 30)


@pytest.mark.parametrize(
    ("grupo", "esperado"),
    [
        (GrupoAlerta.VENCIDAS, (None, date(2026, 9, 29))),
        (GrupoAlerta.HOY, (date(2026, 9, 30), date(2026, 9, 30))),
        (GrupoAlerta.PROXIMAS, (date(2026, 10, 1), date(2026, 10, 7))),
    ],
)
def test_rango_de_grupo_devuelve_limites_incluidos(
    grupo: GrupoAlerta, esperado: tuple[date | None, date]
) -> None:
    assert rango_de(grupo, HOY) == esperado


def test_dias_proximas_es_siete() -> None:
    assert DIAS_PROXIMAS == 7


def test_rango_de_grupos_no_se_solapan_y_cubren_hasta_hoy_mas_siete() -> None:
    primero = HOY - timedelta(days=400)
    for desplazamiento in range((HOY + timedelta(days=10) - primero).days + 1):
        dia = primero + timedelta(days=desplazamiento)
        grupos = [
            grupo
            for grupo in GrupoAlerta
            if (rango_de(grupo, HOY)[0] or date.min) <= dia <= rango_de(grupo, HOY)[1]
        ]
        if dia <= HOY + timedelta(days=DIAS_PROXIMAS):
            assert len(grupos) == 1, dia
        else:
            assert grupos == [], dia


def test_grupo_alerta_valores_coinciden_con_el_filtro_de_la_api() -> None:
    assert [g.value for g in GrupoAlerta] == ["vencidas", "hoy", "proximas"]


def test_modulo_alertas_solo_usa_libreria_estandar() -> None:
    modulos: set[str] = set()
    for nodo in ast.walk(ast.parse(inspect.getsource(alertas))):
        if isinstance(nodo, ast.Import):
            modulos.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module.split(".")[0])

    assert modulos <= set(sys.stdlib_module_names)
