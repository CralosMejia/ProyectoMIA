"""El dominio del historico solo usa la libreria estandar y el propio dominio (sin pandas)."""

import ast
import sys
from pathlib import Path

import pytest

import app.domain.historico as paquete

pytestmark = pytest.mark.unit

_DIRECTORIO = Path(paquete.__file__).parent
_MODULOS = sorted(_DIRECTORIO.glob("*.py"))


def _importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module)
    return nombres


def test_modulos_del_historico_existen() -> None:
    nombres = {ruta.stem for ruta in _MODULOS}
    assert {"conversiones", "normalizacion", "identidad", "registro", "ciclos"} <= nombres


@pytest.mark.parametrize("ruta", _MODULOS, ids=lambda ruta: ruta.stem)
def test_modulo_importa_solo_libreria_estandar_o_dominio(ruta: Path) -> None:
    ajenos = {
        modulo
        for modulo in _importados(ruta)
        if modulo.split(".")[0] not in sys.stdlib_module_names
        and not modulo.startswith("app.domain")
    }
    assert ajenos == set()
