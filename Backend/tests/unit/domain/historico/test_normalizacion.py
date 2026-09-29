import pytest

from app.domain.common.enums import FormaPago, Plan
from app.domain.historico.normalizacion import (
    es_fila_util,
    normalizar_cedula,
    normalizar_forma_pago,
    normalizar_nombre,
    normalizar_plan,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- fila util


@pytest.mark.parametrize(
    "nombre",
    [
        "",
        None,
        "   ",
        "TOTAL ENERO",
        "subtotal",
        "SUMA",
        "MONTO",
        "STATUS",
        "NOMBRES Y APELLIDOS",
        " nombres y apellidos del socio ",
    ],
)
def test_es_fila_util_vacia_total_o_encabezado_devuelve_false(nombre: object) -> None:
    assert es_fila_util(nombre) is False


@pytest.mark.parametrize("nombre", ["Ana Pérez", "NOMBRES", "Luis Status Mora"])
def test_es_fila_util_nombre_de_socio_devuelve_true(nombre: str) -> None:
    assert es_fila_util(nombre) is True


# ---------------------------------------------------------------- nombre


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("  José  Núñez-2 ", "JOSE NUNEZ"),
        ("maría\tluisa", "MARIA LUISA"),
        (None, ""),
        ("A-1", "A"),
    ],
)
def test_normalizar_nombre_devuelve_mayusculas_solo_letras(crudo: object, esperado: str) -> None:
    assert normalizar_nombre(crudo) == esperado


# ---------------------------------------------------------------- cedula


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("171234567-8", "1712345678"),
        ("12345678", None),
        (123456789, "123456789"),
        (None, None),
        ("", None),
        ("sin cedula", None),
    ],
)
def test_normalizar_cedula_conserva_solo_digitos_si_hay_nueve_o_mas(
    crudo: object, esperado: str | None
) -> None:
    assert normalizar_cedula(crudo) == esperado


# ---------------------------------------------------------------- plan


@pytest.mark.parametrize(
    ("texto", "duracion", "esperado"),
    [
        ("PROMO 3 MESES", None, Plan.TRIMESTRAL),
        ("DATAFAST", 30, Plan.MENSUAL),
        ("TRANSFERENCIA ANUAL", None, Plan.OTRO),
        ("pase diario", None, Plan.DIARIO),
        ("PLAN AÑO", None, Plan.ANUAL),
        ("anual", None, Plan.ANUAL),
        ("6 meses", None, Plan.SEMESTRAL),
        ("semestral", None, Plan.SEMESTRAL),
        ("tres meses", None, Plan.TRIMESTRAL),
        ("1 MES", None, Plan.MENSUAL),
        ("1MES", None, Plan.MENSUAL),
        ("mensual", None, Plan.MENSUAL),
        ("PLAN MES", None, Plan.MENSUAL),
        ("", 100, Plan.TRIMESTRAL),
        ("", 170, Plan.SEMESTRAL),
        ("", 350, Plan.ANUAL),
        ("", 60, Plan.OTRO),
        ("", 21, Plan.MENSUAL),
        ("", 45, Plan.MENSUAL),
        ("", 20, Plan.OTRO),
        ("", 46, Plan.OTRO),
        ("", 80, Plan.TRIMESTRAL),
        ("", 130, Plan.TRIMESTRAL),
        ("", 160, Plan.SEMESTRAL),
        ("", 200, Plan.SEMESTRAL),
        ("", 330, Plan.ANUAL),
        ("", 400, Plan.ANUAL),
        ("", 401, Plan.OTRO),
        ("", None, Plan.OTRO),
        (None, 30, Plan.MENSUAL),
        ("promo especial", None, Plan.OTRO),
        # Igual que el notebook: "ANO" como subcadena ("VERANO") cuenta como anual.
        ("promo verano", None, Plan.ANUAL),
    ],
)
def test_normalizar_plan_aplica_reglas_del_notebook(
    texto: object, duracion: int | None, esperado: Plan
) -> None:
    resultado = normalizar_plan(texto, duracion)
    assert isinstance(resultado, Plan)
    assert resultado is esperado


def test_normalizar_plan_diario_tiene_prioridad_sobre_anual() -> None:
    assert normalizar_plan("DIARIO ANUAL", None) is Plan.DIARIO


# ---------------------------------------------------------------- forma de pago


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("", FormaPago.SIN_DATO),
        ("   ", FormaPago.SIN_DATO),
        (None, FormaPago.SIN_DATO),
        ("efectivo", FormaPago.EFECTIVO),
        ("TARJ. DATAFAST", FormaPago.TARJETA_DATAFAST),
        ("datafast", FormaPago.TARJETA_DATAFAST),
        ("Pichincha", FormaPago.TRANSFERENCIA),
        ("TRANSF", FormaPago.TRANSFERENCIA),
        ("Produbanco", FormaPago.TRANSFERENCIA),
        ("DINERS", FormaPago.TRANSFERENCIA),
        ("INTERNACIONAL", FormaPago.TRANSFERENCIA),
        ("cheque", FormaPago.OTRO),
    ],
)
def test_normalizar_forma_pago_aplica_reglas_del_notebook(
    texto: object, esperado: FormaPago
) -> None:
    assert normalizar_forma_pago(texto) is esperado


def test_normalizar_forma_pago_efectivo_antes_que_tarjeta() -> None:
    assert normalizar_forma_pago("EFECTIVO Y TARJETA") is FormaPago.EFECTIVO


def test_normalizar_forma_pago_tarjeta_antes_que_transferencia() -> None:
    assert normalizar_forma_pago("TARJETA DINERS") is FormaPago.TARJETA_DATAFAST
