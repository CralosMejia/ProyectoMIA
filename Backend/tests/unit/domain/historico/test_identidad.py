import pytest

from app.domain.historico.identidad import identidad_de

pytestmark = pytest.mark.unit


def test_identidad_de_con_cedula_usa_la_cedula() -> None:
    assert identidad_de("1712345678", "ANA PEREZ") == "C:1712345678"


def test_identidad_de_sin_cedula_usa_el_nombre() -> None:
    assert identidad_de(None, "ANA PEREZ") == "N:ANA PEREZ"


def test_identidad_de_misma_cedula_con_nombres_distintos_da_la_misma_identidad() -> None:
    assert identidad_de("1712345678", "ANA PEREZ") == identidad_de("1712345678", "ANITA PEREZ")


def test_identidad_de_mismo_nombre_con_cedulas_distintas_da_identidades_distintas() -> None:
    assert identidad_de("1712345678", "ANA PEREZ") != identidad_de("0912345678", "ANA PEREZ")
