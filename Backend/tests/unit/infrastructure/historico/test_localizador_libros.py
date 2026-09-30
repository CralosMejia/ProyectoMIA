"""Localizador de libros historicos sobre una carpeta temporal (sin datos reales)."""

from pathlib import Path

import pytest

from app.application.sistema.ports import LocalizadorLibros
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta

pytestmark = pytest.mark.unit


def test_rutas_devuelve_xlsx_en_orden_alfabetico_ignorando_temporales(tmp_path: Path) -> None:
    nombres = (
        "Control Gym B 2026.xlsx",
        "Control Gym A 2025.XLSX",
        "~$Control Gym B 2026.xlsx",
        "Control Gym notas.txt",
        "Control Gym C.xls",
    )
    for nombre in nombres:
        (tmp_path / nombre).write_bytes(b"")
    (tmp_path / "Control Gym sub.xlsx").mkdir()

    rutas = LocalizadorLibrosCarpeta(tmp_path).rutas()

    assert [r.name for r in rutas] == ["Control Gym A 2025.XLSX", "Control Gym B 2026.xlsx"]


def test_rutas_ignora_xlsx_que_no_son_libros_control_gym(tmp_path: Path) -> None:
    nombres = (
        "Libro CONTROL de gym 2024.xlsx",
        "Plantilla_Carga_Datos_Ficticia.xlsx",
        "Control 2025.xlsx",
        "Gym 2025.xlsx",
    )
    for nombre in nombres:
        (tmp_path / nombre).write_bytes(b"")

    rutas = LocalizadorLibrosCarpeta(tmp_path).rutas()

    assert [r.name for r in rutas] == ["Libro CONTROL de gym 2024.xlsx"]


def test_rutas_carpeta_vacia_devuelve_lista_vacia(tmp_path: Path) -> None:
    assert LocalizadorLibrosCarpeta(tmp_path).rutas() == []


def test_rutas_carpeta_inexistente_devuelve_lista_vacia(tmp_path: Path) -> None:
    assert LocalizadorLibrosCarpeta(tmp_path / "no-existe").rutas() == []


def test_localizador_cumple_el_puerto(tmp_path: Path) -> None:
    assert isinstance(LocalizadorLibrosCarpeta(tmp_path), LocalizadorLibros)
