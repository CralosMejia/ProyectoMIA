from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.historico.conversiones import (
    convertir_fecha,
    convertir_monto,
    normalizar_texto_encabezado,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- fecha


def test_convertir_fecha_datetime_devuelve_solo_la_fecha() -> None:
    celda = datetime(2025, 1, 6, 14, 30)  # noqa: DTZ001 - celda Excel sin zona
    assert convertir_fecha(celda) == date(2025, 1, 6)


def test_convertir_fecha_datetime_devuelve_tipo_date_puro() -> None:
    resultado = convertir_fecha(datetime(2025, 1, 6, 14, 30))  # noqa: DTZ001 - celda Excel sin zona
    assert type(resultado) is date


def test_convertir_fecha_date_devuelve_igual() -> None:
    assert convertir_fecha(date(2025, 1, 6)) == date(2025, 1, 6)


@pytest.mark.parametrize("serial", [45663, 45663.0, 45663.75])
def test_convertir_fecha_serial_excel_devuelve_fecha(serial: float) -> None:
    assert convertir_fecha(serial) == date(2025, 1, 6)


@pytest.mark.parametrize("serial", [19999, 60001, 19999.0])
def test_convertir_fecha_serial_fuera_de_rango_devuelve_none(serial: float) -> None:
    assert convertir_fecha(serial) is None


@pytest.mark.parametrize("serial", [20000, 60000])
def test_convertir_fecha_serial_en_los_bordes_se_convierte(serial: int) -> None:
    assert convertir_fecha(serial) is not None


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("06/01/2025", date(2025, 1, 6)),
        ("6/1/2025", date(2025, 1, 6)),
        (" 06-01-2025 ", date(2025, 1, 6)),
        ("2025-01-06", date(2025, 1, 6)),
        ("2025-01-06 00:00:00", date(2025, 1, 6)),
        ("12/25/2025", date(2025, 12, 25)),
    ],
)
def test_convertir_fecha_texto_devuelve_fecha_con_dia_primero(texto: str, esperado: date) -> None:
    assert convertir_fecha(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("06/01/25", date(2025, 1, 6)),
        ("2025/01/06", date(2025, 1, 6)),
        ("06.01.2025", date(2025, 1, 6)),
        ("06/01/2025 14:30", date(2025, 1, 6)),
        ("2025-01-06T08:15:00", date(2025, 1, 6)),
    ],
)
def test_convertir_fecha_texto_formatos_admitidos_devuelve_fecha(
    texto: str, esperado: date
) -> None:
    assert convertir_fecha(texto) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("15//03/2025", date(2025, 3, 15)),
        ("15///03/2025", date(2025, 3, 15)),
        ("15--03-2025", date(2025, 3, 15)),
        ("15/-03/2025", date(2025, 3, 15)),
        ("03//15/2025", date(2025, 3, 15)),
        ("2025//03/15", date(2025, 3, 15)),
    ],
)
def test_convertir_fecha_separador_repetido_tras_el_primer_componente_devuelve_fecha(
    texto: str, esperado: date
) -> None:
    # Como pd.to_datetime del notebook: tolera el separador repetido solo tras el 1.er campo.
    assert convertir_fecha(texto) == esperado


@pytest.mark.parametrize("texto", ["15/03//2025", "2025/03//15"])
def test_convertir_fecha_separador_repetido_tras_el_segundo_componente_devuelve_none(
    texto: str,
) -> None:
    assert convertir_fecha(texto) is None


def test_convertir_fecha_texto_ambiguo_prefiere_dia_primero() -> None:
    assert convertir_fecha("02/03/2025") == date(2025, 3, 2)


@pytest.mark.parametrize("texto", ["13/25/2025", "no es fecha", "31/02/2025"])
def test_convertir_fecha_texto_invalido_devuelve_none(texto: str) -> None:
    assert convertir_fecha(texto) is None


@pytest.mark.parametrize("valor", ["", "  ", None, float("nan")])
def test_convertir_fecha_vacio_devuelve_none(valor: object) -> None:
    assert convertir_fecha(valor) is None


@pytest.mark.parametrize("valor", [True, False])
def test_convertir_fecha_bool_devuelve_none(valor: bool) -> None:
    assert convertir_fecha(valor) is None


# ---------------------------------------------------------------- monto


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("39,50 USD", Decimal("39.50")),
        (25, Decimal("25")),
        (39.5, Decimal("39.5")),
        ("USD 1.200", Decimal("1.200")),
        ("-5", Decimal("-5")),
        (Decimal("12.30"), Decimal("12.30")),
    ],
)
def test_convertir_monto_valor_con_numero_devuelve_decimal(
    valor: object, esperado: Decimal
) -> None:
    resultado = convertir_monto(valor)
    assert isinstance(resultado, Decimal)
    assert resultado == esperado


def test_convertir_monto_float_no_arrastra_error_binario() -> None:
    assert convertir_monto(0.1) == Decimal("0.1")


@pytest.mark.parametrize(
    "valor", [25, 39.5, "39,50 USD", "-5", 0.1, 45663, "06/01/2025", None, "x"]
)
def test_convertir_monto_y_fecha_nunca_devuelven_float(valor: object) -> None:
    assert not isinstance(convertir_monto(valor), float)
    assert not isinstance(convertir_fecha(valor), float)


@pytest.mark.parametrize("valor", ["sin valor", None, "", float("nan"), True])
def test_convertir_monto_sin_numero_devuelve_none(valor: object) -> None:
    assert convertir_monto(valor) is None


# ---------------------------------------------------------------- encabezado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (" Cédula  ", "CEDULA"),
        ("Nombres   y apellidos", "NOMBRES Y APELLIDOS"),
        (None, ""),
        (float("nan"), ""),
    ],
)
def test_normalizar_texto_encabezado_devuelve_mayusculas_sin_tildes(
    valor: object, esperado: str
) -> None:
    assert normalizar_texto_encabezado(valor) == esperado
