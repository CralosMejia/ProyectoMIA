"""Limpieza del historico: filas crudas -> registros. Nombres y cedulas son inventados."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.common.enums import FormaPago, Plan
from app.domain.historico.registro import FilaCruda, RegistroHistorico, limpiar

pytestmark = pytest.mark.unit

MES_ENERO = date(2025, 1, 1)


def fila(numero: int = 5, **celdas: object) -> FilaCruda:
    valores: dict[str, object] = {
        "nombre": "Ana Ficticia Perez",
        "cedula": "171234567-8",
        "plan": "MENSUAL",
        "fecha_inicio": datetime(2025, 1, 6),  # noqa: DTZ001 - celda Excel sin zona
        "fecha_fin": datetime(2025, 2, 5),  # noqa: DTZ001 - celda Excel sin zona
        "forma_pago": " efectivo ",
        "monto_cobrado": "39,50",
    }
    valores.update(celdas)
    return FilaCruda(anio=2025, hoja="ENERO", fila=numero, mes_hoja=MES_ENERO, **valores)


def unico(filas: list[FilaCruda]) -> RegistroHistorico:
    resultado = limpiar(filas)
    assert len(resultado.registros) == 1
    return resultado.registros[0]


# ---------------------------------------------------------------- conteos


def test_limpiar_fila_no_util_cuenta_en_descartadas() -> None:
    resultado = limpiar([fila(nombre="TOTAL ENERO"), fila(nombre=None), fila()])

    assert resultado.filas_leidas == 3
    assert resultado.descartadas_no_utiles == 2
    assert resultado.utiles == 1
    assert len(resultado.registros) == 1


@pytest.mark.parametrize("nombre", ["A-1", "LUIS", "Jo é"])
def test_limpiar_nombre_normalizado_corto_cuenta_sin_identidad(nombre: str) -> None:
    resultado = limpiar([fila(nombre=nombre), fila()])

    assert resultado.utiles == 2
    assert resultado.sin_identidad == 1
    assert resultado.con_identidad == 1
    assert len(resultado.registros) == 1


def test_limpiar_nombre_normalizado_de_cinco_caracteres_tiene_identidad() -> None:
    resultado = limpiar([fila(nombre="Lucas")])

    assert resultado.sin_identidad == 0
    assert resultado.con_identidad == 1


def test_limpiar_nombre_de_cinco_caracteres_con_espacio_tiene_identidad() -> None:
    # Fiel al notebook (4.1): se cuenta la longitud del nombre normalizado, espacios incluidos.
    resultado = limpiar([fila(nombre="Ana B", cedula=None)])

    assert resultado.sin_identidad == 0
    assert resultado.registros[0].identidad == "N:ANA B"


def test_limpiar_fila_sin_identidad_no_cuenta_como_no_util() -> None:
    resultado = limpiar([fila(nombre="LUIS")])

    assert resultado.descartadas_no_utiles == 0
    assert resultado.utiles == 1
    assert resultado.sin_identidad == 1
    assert resultado.registros == ()


def test_limpiar_acepta_un_iterable_de_una_sola_pasada() -> None:
    resultado = limpiar(fila(numero) for numero in range(3))

    assert resultado.filas_leidas == 3
    assert resultado.con_identidad == 3


def test_limpiar_conteos_de_identidad_y_socios() -> None:
    filas = [
        fila(1, nombre="Ana Ficticia", cedula="1712345678"),
        fila(2, nombre="Anita Ficticia", cedula="171234567-8"),
        fila(3, nombre="Bruno Inventado", cedula=None),
        fila(4, nombre="Bruno  Inventado", cedula="123"),
        fila(5, nombre="Carla Imaginaria", cedula=None, fecha_inicio=None),
    ]

    resultado = limpiar(filas)

    assert resultado.con_identidad == 5
    assert resultado.socios_distintos == 3
    assert resultado.por_cedula == 2
    assert resultado.por_nombre == 3
    assert resultado.inicio_aproximado == 1


def test_limpiar_sin_filas_devuelve_ceros() -> None:
    resultado = limpiar([])

    assert resultado.filas_leidas == 0
    assert resultado.utiles == 0
    assert resultado.socios_distintos == 0
    assert resultado.registros == ()


# ---------------------------------------------------------------- registro


def test_limpiar_construye_registro_normalizado() -> None:
    registro = unico([fila(7)])

    assert registro.identidad == "C:1712345678"
    assert registro.cedula == "1712345678"
    assert registro.nombre == "Ana Ficticia Perez"
    assert registro.nombre_normalizado == "ANA FICTICIA PEREZ"
    assert registro.plan is Plan.MENSUAL
    assert registro.plan_original == "MENSUAL"
    assert registro.forma_pago is FormaPago.EFECTIVO
    assert registro.forma_pago_original == "efectivo"
    assert registro.fecha_inicio == date(2025, 1, 6)
    assert registro.fecha_vencimiento == date(2025, 2, 5)
    assert registro.duracion_dias == 30
    assert registro.monto_cobrado == Decimal("39.50")
    assert registro.referencia == (2025, "ENERO", 7)


def test_limpiar_sin_cedula_valida_identifica_por_nombre() -> None:
    registro = unico([fila(nombre="  Ana  Ficticia ", cedula="12345678")])

    assert registro.cedula is None
    assert registro.identidad == "N:ANA FICTICIA"


def test_limpiar_sin_fecha_inicio_usa_el_mes_de_la_hoja() -> None:
    registro = unico([fila(fecha_inicio=None)])

    assert registro.fecha_inicio is None
    assert registro.inicio_aproximado is True
    assert registro.fecha_actividad == MES_ENERO
    assert registro.duracion_dias is None


def test_limpiar_con_fecha_inicio_la_usa_como_actividad() -> None:
    registro = unico([fila()])

    assert registro.inicio_aproximado is False
    assert registro.fecha_actividad == date(2025, 1, 6)


def test_limpiar_sin_vencimiento_duracion_es_none() -> None:
    registro = unico([fila(fecha_fin=None)])

    assert registro.fecha_vencimiento is None
    assert registro.duracion_dias is None


def test_limpiar_plan_se_normaliza_con_la_duracion() -> None:
    registro = unico([fila(plan="DATAFAST", fecha_inicio="06/01/2025", fecha_fin="06/04/2025")])

    assert registro.duracion_dias == 90
    assert registro.plan is Plan.TRIMESTRAL
    assert registro.plan_original == "DATAFAST"


@pytest.mark.parametrize("vacio", [None, "", "   "])
def test_limpiar_textos_originales_vacios_quedan_none(vacio: object) -> None:
    registro = unico([fila(plan=vacio, forma_pago=vacio)])

    assert registro.plan_original is None
    assert registro.forma_pago_original is None
    assert registro.forma_pago is FormaPago.SIN_DATO


def test_limpiar_monto_negativo_queda_none_y_cuenta_como_invalido() -> None:
    resultado = limpiar([fila(1, monto_cobrado="-5"), fila(2, monto_cobrado=None), fila(3)])

    assert resultado.registros[0].monto_cobrado is None
    assert resultado.registros[1].monto_cobrado is None
    assert resultado.registros[2].monto_cobrado == Decimal("39.50")
    assert resultado.montos_invalidos == 1


@pytest.mark.parametrize("negativo", [-5, -0.5, Decimal("-1.00"), "USD -20"])
def test_limpiar_monto_negativo_de_cualquier_tipo_queda_none(negativo: object) -> None:
    resultado = limpiar([fila(monto_cobrado=negativo)])

    assert resultado.registros[0].monto_cobrado is None
    assert resultado.montos_invalidos == 1


def test_limpiar_monto_float_de_celda_queda_decimal() -> None:
    registro = unico([fila(monto_cobrado=39.5)])

    assert isinstance(registro.monto_cobrado, Decimal)
    assert registro.monto_cobrado == Decimal("39.5")


def test_limpiar_monto_cero_es_valido() -> None:
    resultado = limpiar([fila(monto_cobrado=0)])

    assert resultado.registros[0].monto_cobrado == Decimal("0")
    assert resultado.montos_invalidos == 0


def test_limpiar_conserva_duplicados_exactos() -> None:
    resultado = limpiar([fila(), fila()])

    assert len(resultado.registros) == 2
    assert resultado.socios_distintos == 1


def test_registro_es_inmutable() -> None:
    registro = unico([fila()])

    with pytest.raises(FrozenInstanceError):
        registro.plan = Plan.ANUAL  # type: ignore[misc]  # se prueba que es inmutable


# ---------------------------------------------------------------- datos personales


def test_resultado_limpieza_repr_no_contiene_datos_personales() -> None:
    resultado = limpiar(
        [fila(nombre="Zoe Inventada Quintero", cedula="0999888777", celular="0987654321")]
    )

    for texto in (repr(resultado), str(resultado)):
        assert "ZOE" not in texto.upper()
        assert "QUINTERO" not in texto.upper()
        assert "0999888777" not in texto


def test_registro_y_fila_repr_no_contienen_datos_personales() -> None:
    cruda = fila(
        nombre="Zoe Inventada Quintero",
        cedula="0999888777",
        celular="0987654321",
        correo="zoe@ejemplo.invalid",
    )
    registro = unico([cruda])

    for texto in (repr(cruda), repr(registro)):
        assert "QUINTERO" not in texto.upper()
        assert "0999888777" not in texto
        assert "0987654321" not in texto
        assert "ejemplo.invalid" not in texto
