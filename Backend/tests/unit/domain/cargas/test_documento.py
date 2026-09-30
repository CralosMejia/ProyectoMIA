"""Cedula ecuatoriana (modulo 10) y excepcion de pasaporte de la columna C (CU-01).

Todas las cedulas son sinteticas: se generan aqui con el mismo algoritmo que
``tests/fixtures/generar_fixtures.cedula_valida`` (prefijo ``170`` y una secuencia inventada).
"""

import pytest

from app.domain.cargas.documento import cedula_valida, documento_valido, normalizar_documento

pytestmark = pytest.mark.unit


def cedula_valida_fixture(secuencia: int) -> str:
    """Cedula sintetica de 10 digitos con verificador modulo 10 (coeficientes 2, 1, 2, ...)."""
    base = f"170{secuencia:06d}"
    total = 0
    for posicion, caracter in enumerate(base):
        producto = int(caracter) * (2 if posicion % 2 == 0 else 1)
        total += producto - 9 if producto > 9 else producto
    return f"{base}{(10 - total % 10) % 10}"


def _con_verificador_mas_uno(cedula: str) -> str:
    return cedula[:9] + str((int(cedula[9]) + 1) % 10)


# ------------------------------------------------------------------ cedula_valida


def test_cedula_valida_generada_con_modulo_10_es_valida() -> None:
    assert cedula_valida(cedula_valida_fixture(1)) is True


@pytest.mark.parametrize("secuencia", [2, 17, 345, 999_999])
def test_cedula_valida_varias_secuencias_son_validas(secuencia: int) -> None:
    assert cedula_valida(cedula_valida_fixture(secuencia)) is True


def test_cedula_valida_verificador_mas_uno_es_invalida() -> None:
    assert cedula_valida(_con_verificador_mas_uno(cedula_valida_fixture(1))) is False


@pytest.mark.parametrize(
    "texto",
    [
        cedula_valida_fixture(1)[:9],  # 9 digitos
        cedula_valida_fixture(1) + "0",  # 11 digitos
        "17000000A1",  # letras
        "",  # vacio
        "170000001-9",  # separador
        "١٧٠٠٠٠٠٠١٩",  # digitos no ASCII
    ],
    ids=["9-digitos", "11-digitos", "letras", "vacio", "guion", "digitos-no-ascii"],
)
def test_cedula_valida_formato_incorrecto_es_invalida(texto: str) -> None:
    assert cedula_valida(texto) is False


def test_cedula_valida_verificador_cero_es_valida() -> None:
    # Busca una secuencia cuyo verificador sea 0 para cubrir el caso (10 - 0) % 10.
    cedula = next(c for c in (cedula_valida_fixture(s) for s in range(1, 100)) if c.endswith("0"))
    assert cedula_valida(cedula) is True


# ------------------------------------------------------------------ normalizar_documento


def test_normalizar_documento_celda_numerica_de_9_digitos_antepone_cero() -> None:
    assert normalizar_documento(912345678) == "0912345678"


def test_normalizar_documento_celda_numerica_flotante_entera_antepone_cero() -> None:
    assert normalizar_documento(912345678.0) == "0912345678"


def test_normalizar_documento_celda_numerica_de_10_digitos_se_conserva() -> None:
    assert normalizar_documento(1700000019) == "1700000019"


def test_normalizar_documento_texto_quita_espacios() -> None:
    assert normalizar_documento(" 1700000019 ") == "1700000019"


def test_normalizar_documento_texto_quita_espacios_intermedios() -> None:
    assert normalizar_documento("17000 00019") == "1700000019"


def test_normalizar_documento_texto_no_antepone_cero() -> None:
    assert normalizar_documento("912345678") == "912345678"


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_normalizar_documento_vacio_devuelve_cadena_vacia(valor: object) -> None:
    assert normalizar_documento(valor) == ""


# ------------------------------------------------------------------ documento_valido


def test_documento_valido_cedula_sin_observaciones_es_valido() -> None:
    assert documento_valido(cedula_valida_fixture(3), None) is True


def test_documento_valido_cedula_invalida_sin_pasaporte_es_invalido() -> None:
    assert documento_valido(_con_verificador_mas_uno(cedula_valida_fixture(3)), "") is False


def test_documento_valido_alfanumerico_con_pasaporte_es_valido() -> None:
    assert documento_valido("AB12345", "pasaporte colombiano") is True


def test_documento_valido_alfanumerico_con_pasaporte_en_mayusculas_es_valido() -> None:
    assert documento_valido("AB12345", "Socio extranjero, PASAPORTE vigente") is True


@pytest.mark.parametrize("observaciones", [None, "", "extranjero"])
def test_documento_valido_alfanumerico_sin_pasaporte_es_invalido(
    observaciones: str | None,
) -> None:
    assert documento_valido("AB12345", observaciones) is False


@pytest.mark.parametrize(
    "texto",
    ["AB1", "A" * 21, "AB-12345", ""],
    ids=["3-caracteres", "21-caracteres", "guion", "vacio"],
)
def test_documento_valido_pasaporte_con_formato_incorrecto_es_invalido(texto: str) -> None:
    assert documento_valido(texto, "PASAPORTE") is False


@pytest.mark.parametrize("texto", ["AB123", "A" * 20], ids=["5-caracteres", "20-caracteres"])
def test_documento_valido_pasaporte_en_los_limites_es_valido(texto: str) -> None:
    assert documento_valido(texto, "PASAPORTE") is True


def test_documento_valido_palabra_contenida_en_otra_no_cuenta_como_pasaporte() -> None:
    assert documento_valido("AB12345", "PASAPORTES") is False


# ---------------------------------------------------- interpretaciones (test-engineer)


@pytest.mark.parametrize(
    "observaciones",
    ["PASAPORTE", "Pasaporte: extranjero", "tiene (pasaporte) peruano"],
    ids=["sola", "con-dos-puntos", "entre-parentesis"],
)
def test_documento_valido_pasaporte_como_palabra_completa_activa_excepcion(
    observaciones: str,
) -> None:
    assert documento_valido("AB12345", observaciones) is True


@pytest.mark.parametrize("observaciones", ["NOPASAPORTE", "PASAPORTE1", "pasaportes"])
def test_documento_valido_pasaporte_dentro_de_otra_palabra_no_activa_excepcion(
    observaciones: str,
) -> None:
    assert documento_valido("AB12345", observaciones) is False


def test_documento_valido_cedula_valida_con_pasaporte_sigue_siendo_valida() -> None:
    assert documento_valido(cedula_valida_fixture(5), "PASAPORTE") is True


def test_normalizar_documento_celda_numerica_de_8_digitos_no_antepone_cero() -> None:
    assert normalizar_documento(12345678) == "12345678"


def test_normalizar_documento_booleano_devuelve_cadena_vacia() -> None:
    assert normalizar_documento(True) == ""
