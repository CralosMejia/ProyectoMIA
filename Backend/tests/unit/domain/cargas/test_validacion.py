"""Validacion por fila de la plantilla (CU-01, columnas A..N, RN-01.1 y RN-01.7).

Una prueba por regla. Datos sinteticos: nombres ficticios y cedulas generadas con modulo 10.
"""

from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from app.domain.cargas.fila import FilaPlantilla
from app.domain.cargas.validacion import ErrorFila, FilaValida, validar_fila
from app.domain.common.enums import EstadoRegistro, FormaPago, Plan
from tests.fixtures import esperado
from tests.fixtures import generar_fixtures as gen

pytestmark = pytest.mark.unit

CEDULA = gen.cedula_valida(41)
NOMBRE = "Rosa Ficticia Prueba"


def _fila(**cambios: object) -> FilaPlantilla:
    base = FilaPlantilla(
        fila=2,
        estado_registro="NUEVO",
        nombre=NOMBRE,
        cedula=CEDULA,
        celular="0980000001",
        correo="rosa.ficticia@example.com",
        plan="MENSUAL",
        fecha_inicio=date(2026, 9, 1),
        fecha_vencimiento=date(2026, 10, 1),
        forma_pago="EFECTIVO",
        numero_transaccion="TRX000001",
        monto_facturado=40,
        monto_cobrado=40,
        asistencias=12,
        observaciones=None,
    )
    return replace(base, **cambios)


def _valida(fila: FilaPlantilla) -> FilaValida:
    resultado = validar_fila(fila)
    assert isinstance(resultado, FilaValida), resultado
    return resultado


def _errores(fila: FilaPlantilla) -> tuple[ErrorFila, ...]:
    resultado = validar_fila(fila)
    assert isinstance(resultado, tuple), "se esperaban errores"
    return resultado


def _unico_error(fila: FilaPlantilla, columna: str) -> ErrorFila:
    errores = _errores(fila)
    assert [e.columna for e in errores] == [columna]
    assert errores[0].fila == fila.fila
    return errores[0]


# ------------------------------------------------------------------ fila correcta


def test_validar_fila_correcta_devuelve_fila_valida_con_valores_convertidos() -> None:
    valida = _valida(_fila())
    assert valida.fila == 2
    assert valida.estado_registro is EstadoRegistro.NUEVO
    assert valida.nombre_normalizado == "ROSA FICTICIA PRUEBA"
    assert valida.documento == CEDULA
    assert valida.plan is Plan.MENSUAL
    assert valida.forma_pago is FormaPago.EFECTIVO
    assert valida.fecha_inicio == date(2026, 9, 1)
    assert valida.fecha_vencimiento == date(2026, 10, 1)
    assert valida.monto_cobrado == Decimal("40")
    assert valida.asistencias == 12


def test_validar_fila_repr_no_expone_datos_personales() -> None:
    texto = repr(_valida(_fila()))
    assert CEDULA not in texto
    assert "ROSA" not in texto.upper()
    assert "0980000001" not in texto
    assert "example.com" not in texto


# ------------------------------------------------------------------ A · estado del registro


def test_validar_fila_estado_fuera_de_catalogo_error_en_a() -> None:
    _unico_error(_fila(estado_registro="PAUSA"), "A")


def test_validar_fila_estado_vacio_es_valido_sin_estado() -> None:
    assert _valida(_fila(estado_registro=None)).estado_registro is None


def test_validar_fila_estado_en_minusculas_con_espacios_es_valido() -> None:
    assert _valida(_fila(estado_registro=" renovacion ")).estado_registro is (
        EstadoRegistro.RENOVACION
    )


# ------------------------------------------------------------------ B · nombre


@pytest.mark.parametrize("nombre", [None, "", "   "], ids=["none", "vacio", "espacios"])
def test_validar_fila_nombre_vacio_error_en_b(nombre: object) -> None:
    _unico_error(_fila(nombre=nombre), "B")


def test_validar_fila_nombre_con_menos_de_5_letras_error_en_b() -> None:
    _unico_error(_fila(nombre="Al 12"), "B")


# ------------------------------------------------------------------ C · cedula


def test_validar_fila_cedula_con_verificador_incorrecto_error_en_c() -> None:
    invalida = CEDULA[:9] + str((int(CEDULA[9]) + 1) % 10)
    error = _unico_error(_fila(cedula=invalida), "C")
    assert error.motivo == "La cédula no tiene un dígito verificador válido."


def test_validar_fila_cedula_vacia_error_en_c() -> None:
    error = _unico_error(_fila(cedula=None), "C")
    assert error.motivo == "Falta la cédula."


def test_validar_fila_cedula_numerica_sin_cero_inicial_es_valida() -> None:
    # Inventada: verificador modulo 10 de 091234567 calculado a mano (suma 35 -> 5).
    assert _valida(_fila(cedula=912345675)).documento == "0912345675"


def test_validar_fila_pasaporte_con_observaciones_es_valido() -> None:
    valida = _valida(_fila(cedula="AB12345", observaciones="pasaporte colombiano"))
    assert valida.documento == "AB12345"


def test_validar_fila_alfanumerico_sin_pasaporte_error_en_c() -> None:
    _unico_error(_fila(cedula="AB12345"), "C")


# ------------------------------------------------------------------ E · correo


def test_validar_fila_correo_mal_formado_error_en_e() -> None:
    _unico_error(_fila(correo="rosa.ficticia@"), "E")


def test_validar_fila_correo_vacio_es_valido() -> None:
    assert _valida(_fila(correo=None)).correo is None


# ------------------------------------------------------------------ F · plan


def test_validar_fila_plan_fuera_de_catalogo_error_en_f() -> None:
    _unico_error(_fila(plan="SEMANAL"), "F")


def test_validar_fila_plan_vacio_error_en_f() -> None:
    _unico_error(_fila(plan=None), "F")


# ------------------------------------------------------------------ G · fecha de inicio


def test_validar_fila_inicio_vacio_error_en_g() -> None:
    _unico_error(_fila(fecha_inicio=None), "G")


def test_validar_fila_inicio_que_no_es_fecha_error_en_g() -> None:
    _unico_error(_fila(fecha_inicio="primero de septiembre"), "G")


@pytest.mark.parametrize("inicio", [date(2023, 12, 31), date(2036, 1, 1)], ids=str)
def test_validar_fila_inicio_fuera_de_rango_error_en_g(inicio: date) -> None:
    errores = _errores(_fila(fecha_inicio=inicio, fecha_vencimiento=None))
    assert "G" in [e.columna for e in errores]


def test_validar_fila_inicio_como_texto_iso_y_fecha_hora_es_valido() -> None:
    valida = _valida(
        _fila(
            fecha_inicio="2026-09-01",
            fecha_vencimiento=datetime.combine(date(2026, 10, 1), time(14, 30)),
        )
    )
    assert valida.fecha_inicio == date(2026, 9, 1)
    assert valida.fecha_vencimiento == date(2026, 10, 1)


# ------------------------------------------------------------------ H · fecha de vencimiento


def test_validar_fila_vencimiento_anterior_al_inicio_error_en_h() -> None:
    error = _unico_error(_fila(fecha_vencimiento=date(2026, 8, 22)), "H")
    assert error.motivo == "La fecha de vencimiento debe ser posterior a la de inicio."


def test_validar_fila_vencimiento_igual_al_inicio_error_en_h() -> None:
    _unico_error(_fila(fecha_vencimiento=date(2026, 9, 1)), "H")


def test_validar_fila_vencimiento_vacio_error_en_h() -> None:
    _unico_error(_fila(fecha_vencimiento=None), "H")


def test_validar_fila_duracion_menor_a_21_dias_error_en_h() -> None:
    _unico_error(_fila(fecha_vencimiento=date(2026, 9, 21)), "H")


def test_validar_fila_duracion_de_21_dias_es_valida() -> None:
    _valida(_fila(fecha_vencimiento=date(2026, 9, 22)))


def test_validar_fila_duracion_mayor_a_400_dias_error_en_h() -> None:
    _unico_error(_fila(plan="ANUAL", fecha_vencimiento=date(2027, 10, 7)), "H")


def test_validar_fila_diario_de_un_dia_es_valido() -> None:
    _valida(_fila(plan="DIARIO", fecha_vencimiento=date(2026, 9, 2)))


# ------------------------------------------------------------------ I · forma de pago


@pytest.mark.parametrize("forma", ["CHEQUE", "SIN_DATO", None], ids=str)
def test_validar_fila_forma_de_pago_fuera_de_catalogo_error_en_i(forma: object) -> None:
    _unico_error(_fila(forma_pago=forma), "I")


# ------------------------------------------------------------------ K · monto a facturar


def test_validar_fila_monto_facturado_negativo_error_en_k() -> None:
    _unico_error(_fila(monto_facturado=-1), "K")


def test_validar_fila_monto_facturado_con_3_decimales_error_en_k() -> None:
    _unico_error(_fila(monto_facturado=40.125), "K")


def test_validar_fila_monto_facturado_vacio_es_valido() -> None:
    assert _valida(_fila(monto_facturado=None)).monto_facturado is None


# ------------------------------------------------------------------ L · monto cobrado


@pytest.mark.parametrize("monto", [None, -5, "cuarenta"], ids=["vacio", "negativo", "texto"])
def test_validar_fila_monto_cobrado_invalido_error_en_l(monto: object) -> None:
    _unico_error(_fila(monto_cobrado=monto), "L")


@pytest.mark.parametrize(
    ("monto", "esperado_decimal"),
    [(40.5, Decimal("40.5")), ("40,50", Decimal("40.50")), ("99.5", Decimal("99.5")), (0, 0)],
    ids=["flotante", "coma", "punto", "cero"],
)
def test_validar_fila_monto_cobrado_se_convierte_a_decimal(
    monto: object, esperado_decimal: Decimal
) -> None:
    valida = _valida(_fila(monto_cobrado=monto))
    assert isinstance(valida.monto_cobrado, Decimal)
    assert valida.monto_cobrado == esperado_decimal


# ------------------------------------------------------------------ M · asistencias


@pytest.mark.parametrize("asistencias", [401, -1, 2.5], ids=str)
def test_validar_fila_asistencias_invalidas_error_en_m(asistencias: object) -> None:
    _unico_error(_fila(asistencias=asistencias), "M")


def test_validar_fila_asistencias_flotante_entera_se_convierte_a_entero() -> None:
    valida = _valida(_fila(asistencias=7.0))
    assert valida.asistencias == 7
    assert isinstance(valida.asistencias, int)


def test_validar_fila_asistencias_vacias_es_valido() -> None:
    assert _valida(_fila(asistencias=None)).asistencias is None


# ------------------------------------------------------------------ varios fallos y privacidad


def test_validar_fila_con_varios_fallos_devuelve_todos_sus_errores() -> None:
    errores = _errores(
        _fila(nombre="", cedula="123", plan="SEMANAL", forma_pago="CHEQUE", monto_cobrado=-1)
    )
    assert [e.columna for e in errores] == ["B", "C", "F", "I", "L"]


def test_validar_fila_ningun_motivo_incluye_el_valor_de_la_celda() -> None:
    invalida = CEDULA[:9] + str((int(CEDULA[9]) + 1) % 10)
    errores = _errores(
        _fila(
            estado_registro="PAUSAXYZ",
            nombre="Qwz",
            cedula=invalida,
            correo="correo-sin-arroba",
            plan="SEMANALXYZ",
            fecha_inicio="texto-fecha-xyz",
            forma_pago="CHEQUEXYZ",
            monto_facturado="-7.777",
            monto_cobrado="abcxyz",
            asistencias=987,
        )
    )
    valores = [invalida, "PAUSAXYZ", "QWZ", "correo-sin-arroba", "SEMANALXYZ"]
    valores += ["texto-fecha-xyz", "CHEQUEXYZ", "7.777", "abcxyz", "987"]
    for error in errores:
        for valor in valores:
            assert valor.upper() not in error.motivo.upper()


# ------------------------------------------------------------------ fixtures sinteticos

_CAMPO_POR_COLUMNA = {
    "C": "cedula",
    "F": "tipo_plan",
    "G": "fecha_inicio",
    "H": "fecha_vencimiento",
}


@pytest.mark.parametrize(
    "archivo",
    [nombre for nombre in esperado.FILAS_CON_ERROR if nombre != esperado.PLANTILLA_501_FILAS],
)
def test_validar_fila_fixtures_coinciden_con_filas_con_error(archivo: str) -> None:
    filas = gen.filas_plantillas()[archivo]
    obtenido: dict[int, str] = {}
    for indice, valores in enumerate(filas):
        resultado = validar_fila(FilaPlantilla.desde_valores(indice + 2, valores))
        if isinstance(resultado, tuple):
            for error in resultado:
                obtenido[error.fila] = _CAMPO_POR_COLUMNA.get(error.columna, error.columna)
    assert obtenido == esperado.FILAS_CON_ERROR[archivo]


def test_validar_fila_fixture_501_filas_todas_validas() -> None:
    filas = gen.filas_plantillas()[esperado.PLANTILLA_501_FILAS]
    for indice, valores in enumerate(filas):
        assert isinstance(
            validar_fila(FilaPlantilla.desde_valores(indice + 2, valores)), FilaValida
        )


# ------------------------------------------ fronteras e interpretaciones (test-engineer)


@pytest.mark.parametrize("nombre", ["Ana Li", "A n a L i"], ids=["5-letras", "5-letras-separadas"])
def test_validar_fila_nombre_con_exactamente_5_letras_sin_contar_espacios_es_valido(
    nombre: str,
) -> None:
    _valida(_fila(nombre=nombre))


def test_validar_fila_nombre_de_4_letras_con_espacios_error_en_b() -> None:
    error = _unico_error(_fila(nombre="A n a L"), "B")
    assert error.motivo == "El nombre debe tener al menos 5 letras."


def test_validar_fila_cedula_sin_10_digitos_error_en_c_con_motivo_de_longitud() -> None:
    error = _unico_error(_fila(cedula="17000000191"), "C")
    assert error.motivo == "La cédula debe tener 10 dígitos."


def test_validar_fila_pasaporte_con_formato_incorrecto_error_en_c_con_motivo_de_pasaporte() -> None:
    error = _unico_error(_fila(cedula="A" * 21, observaciones="PASAPORTE"), "C")
    assert error.motivo == "El pasaporte debe tener de 5 a 20 letras o números."


def test_validar_fila_pasaporte_como_parte_de_otra_palabra_no_aplica_excepcion() -> None:
    _unico_error(_fila(cedula="AB12345", observaciones="NOPASAPORTE"), "C")


def test_validar_fila_cedula_texto_de_9_digitos_no_antepone_cero_error_en_c() -> None:
    # 912345675 como celda numerica es valida (se antepone 0); como texto no se corrige.
    error = _unico_error(_fila(cedula="912345675"), "C")
    assert error.motivo == "La cédula debe tener 10 dígitos."


@pytest.mark.parametrize("estado", list(EstadoRegistro), ids=str)
def test_validar_fila_estado_del_catalogo_es_valido(estado: EstadoRegistro) -> None:
    assert _valida(_fila(estado_registro=estado.value)).estado_registro is estado


@pytest.mark.parametrize("plan", [p for p in Plan if p is not Plan.DIARIO], ids=str)
def test_validar_fila_plan_del_catalogo_es_valido(plan: Plan) -> None:
    assert _valida(_fila(plan=plan.value.lower())).plan is plan


@pytest.mark.parametrize("forma", [f for f in FormaPago if f is not FormaPago.SIN_DATO], ids=str)
def test_validar_fila_forma_de_pago_del_catalogo_es_valida(forma: FormaPago) -> None:
    assert _valida(_fila(forma_pago=forma.value)).forma_pago is forma


@pytest.mark.parametrize(
    ("inicio", "vencimiento"),
    [(date(2024, 1, 1), date(2024, 2, 1)), (date(2035, 11, 30), date(2035, 12, 31))],
    ids=["minimo", "maximo"],
)
def test_validar_fila_fechas_en_los_limites_del_rango_son_validas(
    inicio: date, vencimiento: date
) -> None:
    _valida(_fila(fecha_inicio=inicio, fecha_vencimiento=vencimiento))


def test_validar_fila_vencimiento_posterior_a_2035_error_en_h() -> None:
    _unico_error(_fila(fecha_inicio=date(2035, 12, 1), fecha_vencimiento=date(2036, 1, 1)), "H")


@pytest.mark.parametrize("texto", ["01/09/2026", "2026-02-30", "2026-9-1"], ids=str)
def test_validar_fila_inicio_texto_no_iso_o_imposible_error_en_g(texto: str) -> None:
    _unico_error(_fila(fecha_inicio=texto), "G")


def test_validar_fila_inicio_numerico_error_en_g() -> None:
    _unico_error(_fila(fecha_inicio=46000), "G")


def test_validar_fila_duracion_de_400_dias_es_valida() -> None:
    _valida(_fila(plan="ANUAL", fecha_vencimiento=date(2027, 10, 6)))


def test_validar_fila_diario_de_mas_de_400_dias_error_en_h() -> None:
    _unico_error(_fila(plan="DIARIO", fecha_vencimiento=date(2027, 10, 7)), "H")


def test_validar_fila_duracion_corta_con_plan_desconocido_solo_error_en_f() -> None:
    # < 21 dias solo se juzga con un plan conocido; aqui el unico fallo es el plan.
    _unico_error(_fila(plan="SEMANAL", fecha_vencimiento=date(2026, 9, 8)), "F")


def test_validar_fila_duracion_mayor_a_400_con_plan_desconocido_error_en_f_y_h() -> None:
    errores = _errores(_fila(plan="SEMANAL", fecha_vencimiento=date(2027, 10, 7)))
    assert [e.columna for e in errores] == ["F", "H"]


def test_validar_fila_vencimiento_anterior_con_plan_vacio_error_en_f_y_h() -> None:
    errores = _errores(_fila(plan=None, fecha_vencimiento=date(2026, 8, 1)))
    assert [e.columna for e in errores] == ["F", "H"]


@pytest.mark.parametrize(
    "monto", ["1.234,50", "1,234.50", "40,125", "40.125", "1e3", "40 USD", True], ids=str
)
def test_validar_fila_monto_cobrado_con_formato_invalido_error_en_l(monto: object) -> None:
    _unico_error(_fila(monto_cobrado=monto), "L")


def test_validar_fila_monto_facturado_con_coma_y_punto_error_en_k() -> None:
    _unico_error(_fila(monto_facturado="1.234,50"), "K")


@pytest.mark.parametrize(
    ("monto", "esperado_decimal"),
    [("40.12", Decimal("40.12")), (" 15 ", Decimal("15")), (Decimal("7.10"), Decimal("7.1"))],
    ids=["2-decimales", "espacios", "decimal"],
)
def test_validar_fila_monto_facturado_valido_se_convierte_a_decimal(
    monto: object, esperado_decimal: Decimal
) -> None:
    valida = _valida(_fila(monto_facturado=monto))
    assert isinstance(valida.monto_facturado, Decimal)
    assert valida.monto_facturado == esperado_decimal


@pytest.mark.parametrize(("asistencias", "entero"), [(0, 0), (400, 400), ("7.0", 7)], ids=str)
def test_validar_fila_asistencias_en_los_limites_son_validas(
    asistencias: object, entero: int
) -> None:
    assert _valida(_fila(asistencias=asistencias)).asistencias == entero


def test_validar_fila_asistencias_texto_no_numerico_error_en_m() -> None:
    _unico_error(_fila(asistencias="doce"), "M")
