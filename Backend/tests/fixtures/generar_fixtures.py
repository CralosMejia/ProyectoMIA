"""Generador determinista de datos sintéticos para las pruebas (D2-OP-01).

Produce 7 archivos ``.xlsx``:

- ``historico/Control Gym 2025 sintetico.xlsx`` y ``historico/Control Gym 2026 sintetico.xlsx``:
  libros con la **estructura** de los históricos (hojas mensuales con espacios en el nombre,
  hojas auxiliares, encabezado en filas distintas, nombres de columna cambiantes, filas vacías,
  totales y encabezados repetidos).
- ``plantillas/plantilla_*.xlsx``: la plantilla oficial de CU-01 (hojas ``Instrucciones``,
  ``Registros``, ``Ejemplo`` y ``Catalogos``), una válida y cuatro con errores.

**Sin datos reales:** los nombres salen de ``NOMBRES_FICTICIOS``; las cédulas de los libros
usan el prefijo ``0999`` (tercer dígito 9: no corresponde a una persona natural) y las de las
plantillas se construyen con ``cedula_valida``. Nada se lee de ``plantillas/`` del repositorio.

Determinista: sin aleatoriedad; los metadatos del libro y las fechas de las entradas del zip
se fijan, así que dos ejecuciones producen los mismos bytes.

Uso (desde ``Backend/``): ``python tests/fixtures/generar_fixtures.py``. Los conteos que deben
obtener el lector y el procesamiento del histórico están en ``esperado.py``.
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet

DIRECTORIO = Path(__file__).resolve().parent
DIR_HISTORICO = DIRECTORIO / "historico"
DIR_PLANTILLAS = DIRECTORIO / "plantillas"

LIBRO_2025 = "Control Gym 2025 sintetico.xlsx"
LIBRO_2026 = "Control Gym 2026 sintetico.xlsx"
PLANTILLA_VALIDA = "plantilla_valida.xlsx"
PLANTILLA_CEDULA_INVALIDA = "plantilla_cedula_invalida.xlsx"
PLANTILLA_CATALOGO_INVALIDO = "plantilla_catalogo_invalido.xlsx"
PLANTILLA_FECHAS_INVALIDAS = "plantilla_fechas_invalidas.xlsx"
PLANTILLA_501_FILAS = "plantilla_501_filas.xlsx"

_FECHA_ZIP = (2026, 1, 1, 0, 0, 0)
_INSTANTE_FIJO = "2026-01-01T00:00:00Z"
_EPOCA_EXCEL = date(1899, 12, 30)

# Lista fija de nombres ficticios. Todo nombre de socio de los fixtures sale de aquí.
NOMBRES_FICTICIOS: tuple[str, ...] = (
    "Lucía Prueba Andrade",
    "LUCIA ANDRADE",
    "Mateo Prueba Castillo",
    "MATEO PRUEBA CASTILLO",
    "Camila Prueba Benitez",
    "Diego Prueba Salazar",
    "Sofia Prueba Guerrero",
    "Tomas Prueba Villacis",
    "Valentina Prueba Ortiz",
    "Joaquin Prueba Paredes",
    "Isabella Prueba Rivas",
    "Martin Prueba Cevallos",
    "Emilia Prueba Naranjo",
    "Samuel Prueba Ponce",
    "Renata Prueba Aguirre",
    "José Prueba Núñez",
    # Nombres con menos de 5 letras tras normalizar: registros sin identidad utilizable.
    "LUIS",
    "A-1",
    # Plantillas.
    "Ana Ficticia Rojas",
    "Bruno Ficticio Mena",
    "Carla Ficticia Vega",
    "Dario Ficticio Luna",
    "Elena Ficticia Soto",
    "Felipe Ficticio Paz",
)


# ------------------------------------------------------------------ utilidades


def serial_excel(fecha: date) -> int:
    """Número de serie de Excel (días desde 1899-12-30)."""
    return (fecha - _EPOCA_EXCEL).days


def cedula_valida(secuencia: int) -> str:
    """Cédula ecuatoriana sintética de 10 dígitos con dígito verificador válido (módulo 10)."""
    base = f"170{secuencia:06d}"
    total = 0
    for posicion, caracter in enumerate(base):
        producto = int(caracter) * (2 if posicion % 2 == 0 else 1)
        total += producto - 9 if producto > 9 else producto
    verificador = (10 - total % 10) % 10
    return f"{base}{verificador}"


def _con_hora(fecha: date) -> datetime:
    return datetime.combine(fecha, time(14, 30))


def _guardar_determinista(libro: Workbook, ruta: Path) -> None:
    """Guarda el libro con metadatos y fechas del zip fijos (mismos bytes en cada ejecución)."""
    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with (
        zipfile.ZipFile(buffer) as origen,
        zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as destino,
    ):
        for entrada in origen.infolist():
            datos = origen.read(entrada.filename)
            if entrada.filename == "docProps/core.xml":
                datos = re.sub(
                    rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*",
                    rb"\g<1>" + _INSTANTE_FIJO.encode(),
                    datos,
                )
            fija = zipfile.ZipInfo(entrada.filename, date_time=_FECHA_ZIP)
            fija.compress_type = zipfile.ZIP_DEFLATED
            fija.external_attr = 0o600 << 16
            destino.writestr(fija, datos)


def _libro_vacio() -> Workbook:
    libro = Workbook()
    libro.remove(libro.worksheets[0])
    libro.properties.creator = "generar_fixtures"
    libro.properties.lastModifiedBy = "generar_fixtures"
    return libro


def _escribir_fila(hoja: Worksheet, numero_fila: int, valores: Sequence[object]) -> None:
    for indice, valor in enumerate(valores):
        if valor is not None:
            hoja.cell(row=numero_fila, column=indice + 1, value=valor)


# ------------------------------------------------------------------ libros históricos

# Encabezados con la forma de los libros reales (solo títulos de columna).
ENCABEZADO_A: tuple[str | None, ...] = (
    None,
    "Nombres y apellidos del socio ",
    "Cédula",
    "Celular",
    "Correo",
    "Tipo de plan",
    "Fecha inscripción",
    "Fecha fin plan",
    "Tipo pago",
    "No transaccion",
    "Monto a facturar",
    "MONTO A COBRAR",
)
# "FECHA INSCRIP" no coincide con ningún alias del notebook: la hoja queda sin fecha de inicio.
ENCABEZADO_B: tuple[str | None, ...] = (
    None,
    "NOMBRES Y APELLIDOS",
    "CEDULA",
    "CELULAR",
    "CORREO",
    "TIPO DE PLAN",
    "FECHA INSCRIP",
    "FECHA FIN  PLAN",
    "TIPO PAGO",
    "No TRANSACCION",
    "MONTO FACTURAR",
    "MONTO A COBRAR",
)
ENCABEZADO_C: tuple[str | None, ...] = (
    None,
    "STATUS",
    "FACTURA",
    "NOMBRES Y APELLIDOS",
    "CEDULA",
    "CELULAR",
    "CORREO",
    "TIPO DE PLAN",
    "FECHA INICIO",
    "FECHA FIN",
    "TIPO PAGO",
    "No TRANSACCION",
    "No LOTE T/C",
    "MONTO FACTURAR",
    "MONTO A COBRAR",
    "NUTRIC",
)

_COLUMNAS_AB = {
    "nombre": 1,
    "cedula": 2,
    "celular": 3,
    "correo": 4,
    "plan": 5,
    "inicio": 6,
    "fin": 7,
    "pago": 8,
    "transaccion": 9,
    "facturar": 10,
    "monto": 11,
}
_COLUMNAS_C = {
    "status": 1,
    "factura": 2,
    "nombre": 3,
    "cedula": 4,
    "celular": 5,
    "correo": 6,
    "plan": 7,
    "inicio": 8,
    "fin": 9,
    "pago": 10,
    "transaccion": 11,
    "facturar": 13,
    "monto": 14,
}


@dataclass(frozen=True, slots=True)
class Formato:
    encabezado: tuple[str | None, ...]
    columnas: dict[str, int]


FORMATO_A = Formato(ENCABEZADO_A, _COLUMNAS_AB)
FORMATO_B = Formato(ENCABEZADO_B, _COLUMNAS_AB)
FORMATO_C = Formato(ENCABEZADO_C, _COLUMNAS_C)


@dataclass(frozen=True, slots=True)
class Membresia:
    nombre: str
    cedula: object
    plan: str
    inicio: object
    fin: object
    pago: str
    monto: object
    status: str | None = None


@dataclass(frozen=True, slots=True)
class Totales:
    """Fila de totales: etiqueta en la columna del nombre (o vacía) y la suma en el monto."""

    etiqueta: str | None
    monto: object


@dataclass(frozen=True, slots=True)
class EncabezadoRepetido:
    pass


@dataclass(frozen=True, slots=True)
class Vacia:
    pass


Fila = Membresia | Totales | EncabezadoRepetido | Vacia


@dataclass(frozen=True, slots=True)
class HojaMensual:
    nombre: str
    formato: Formato
    previas: tuple[tuple[object, ...], ...]  # filas antes del encabezado (índice 0-based = len)
    filas: tuple[Fila, ...]


@dataclass(frozen=True, slots=True)
class HojaAuxiliar:
    nombre: str
    filas: tuple[tuple[object, ...], ...]


Hoja = HojaMensual | HojaAuxiliar


@dataclass(frozen=True, slots=True)
class Libro:
    archivo: str
    hojas: tuple[Hoja, ...]


# Cédulas sintéticas de los libros (tercer dígito 9: no es de persona natural).
_CED_LUCIA = "0999000011"
_CED_MATEO = "0999000029"
_CED_TOMAS = "0999000053"
_CED_VALENTINA = "0999000061"
_CED_JOAQUIN = "0999000118"
_CED_MARTIN = "0999000037"
_CED_EMILIA = "0999000126"
_CED_SAMUEL = "0999000096"
_CED_RENATA = "0999000088"
_CED_SOFIA = 999000045  # numérica y de 9 dígitos, como una cédula que perdió el 0 inicial
_CED_CORTA = "12345"  # menos de 9 dígitos: identidad por nombre

_VALENTINA_FEB = Membresia(
    "Valentina Prueba Ortiz",
    _CED_VALENTINA,
    "MENSUAL",
    date(2025, 2, 10),
    date(2025, 3, 12),
    "EFECTIVO",
    35,
)

LIBROS: tuple[Libro, ...] = (
    Libro(
        LIBRO_2025,
        (
            HojaAuxiliar(
                "06 ene",
                (
                    ("REGISTRO DEL DIA",),
                    ("NOMBRE", "CEDULA", "VALOR"),
                    ("Tomas Prueba Villacis", _CED_TOMAS, 5),
                ),
            ),
            HojaMensual(
                "ENERO",
                FORMATO_A,
                ((), (None, "CONTROL GYM ENERO 2025 (SINTETICO)")),
                (
                    Membresia(
                        "Lucía Prueba Andrade",
                        _CED_LUCIA,
                        "MENSUAL",
                        _con_hora(date(2025, 1, 6)),
                        date(2025, 2, 5),
                        "Efectivo",
                        39.5,
                    ),
                    Membresia(
                        "Mateo Prueba Castillo",
                        "099900002-9",
                        "DATAFAST",
                        serial_excel(date(2025, 1, 6)),
                        serial_excel(date(2025, 2, 5)),
                        "Datafast",
                        "39,50 USD",
                    ),
                    Membresia(
                        "Camila Prueba Benitez",
                        None,
                        "PROMO 3 MESES",
                        "20/01/2025",
                        "20/04/2025",
                        "Transf Pichincha",
                        99,
                    ),
                    Vacia(),
                    Membresia(
                        "LUIS", "0999000100", "MENSUAL", date(2025, 1, 8), date(2025, 2, 7), "", 30
                    ),
                    Membresia(
                        "Martin Prueba Cevallos",
                        _CED_MARTIN,
                        "MENSUAL",
                        date(2024, 10, 31),
                        date(2024, 11, 30),
                        "EFECTIVO",
                        30,
                    ),
                    Membresia(
                        "Tomas Prueba Villacis",
                        _CED_TOMAS,
                        "PASE DIARIO",
                        date(2025, 1, 15),
                        date(2025, 1, 15),
                        "EFECTIVO",
                        5,
                    ),
                    EncabezadoRepetido(),
                    Membresia(
                        "Diego Prueba Salazar",
                        _CED_CORTA,
                        "1 MES",
                        date(2025, 1, 20),
                        date(2025, 2, 19),
                        "Produbanco",
                        40,
                    ),
                    Totales("TOTAL ENERO", 243.5),
                    Totales(None, 243.5),
                ),
            ),
            HojaMensual(
                "FEBRERO ",
                FORMATO_B,
                ((None, "CONTROL GYM FEBRERO"), (), (None, "Semana 1"), ()),
                (
                    Membresia(
                        "Sofia Prueba Guerrero",
                        _CED_SOFIA,
                        "MENSUAL 2X1",
                        date(2025, 2, 3),
                        date(2025, 3, 5),
                        "TARJ. DATAFAST",
                        "40 USD",
                    ),
                    _VALENTINA_FEB,
                    _VALENTINA_FEB,  # duplicado exacto: se conserva, como en el notebook
                    Membresia(
                        "A-1", None, "MENSUAL", date(2025, 2, 4), date(2025, 3, 6), "EFECTIVO", 30
                    ),
                    Membresia(
                        "Isabella Prueba Rivas",
                        None,
                        "TRIMESTRAL",
                        date(2025, 2, 12),
                        None,
                        "EFECTIVO",
                        95,
                    ),
                    Vacia(),
                    Totales("SUBTOTAL", 235),
                ),
            ),
            HojaMensual(
                " MARZO",
                FORMATO_C,
                (),
                (
                    Membresia(
                        "LUCIA ANDRADE",
                        _CED_LUCIA,
                        "MENSUAL",
                        date(2025, 3, 1),
                        date(2025, 3, 31),
                        "TRANSFERENCIA",
                        39.5,
                        "RENOVACION",
                    ),
                    Membresia(
                        "Valentina Prueba Ortiz",
                        _CED_VALENTINA,
                        "MENSUAL",
                        "15/03/2025",
                        serial_excel(date(2025, 4, 14)),
                        "Efectivo",
                        35,
                        "RENOVACION",
                    ),
                    Membresia(
                        "Renata Prueba Aguirre",
                        _CED_RENATA,
                        "MENSUAL",
                        date(2025, 3, 10),
                        date(2025, 4, 9),
                        "cheque",
                        -5,
                        "NUEVO",
                    ),
                    Membresia(
                        "Samuel Prueba Ponce",
                        _CED_SAMUEL,
                        "PROMO",
                        date(2025, 3, 3),
                        date(2025, 3, 18),
                        "EFECTIVO",
                        20,
                        "NUEVO",
                    ),
                    Membresia(
                        "José Prueba Núñez",
                        None,
                        "",
                        date(2025, 3, 20),
                        date(2025, 6, 28),
                        "",
                        None,
                        "NUEVO",
                    ),
                    Totales("TOTAL MARZO", 129.5),
                ),
            ),
            HojaMensual(
                "DICIEMBRE",
                FORMATO_C,
                ((None, "CONTROL GYM"), (), (None, "DICIEMBRE")),
                (
                    Membresia(
                        "Emilia Prueba Naranjo",
                        _CED_EMILIA,
                        "PLAN AÑO",
                        date(2025, 12, 5),
                        date(2026, 12, 4),
                        "DEPOSITO",
                        350,
                        "NUEVO",
                    ),
                    Membresia(
                        "MATEO PRUEBA CASTILLO",
                        _CED_MATEO,
                        "SEMESTRAL",
                        date(2025, 12, 15),
                        date(2026, 6, 13),
                        "TRANSFERENCIA",
                        190,
                        "REINGRESO",
                    ),
                    Membresia(
                        "Camila Prueba Benitez",
                        None,
                        "MENSUAL",
                        date(2025, 12, 20),
                        date(2026, 1, 19),
                        "EFECTIVO",
                        40,
                        "RENOVACION",
                    ),
                    Vacia(),
                    Totales("TOTAL", 580),
                ),
            ),
            HojaAuxiliar(
                "DIARIOS",
                (
                    ("PASES DIARIOS",),
                    ("NOMBRES Y APELLIDOS", "CEDULA", "VALOR"),
                    ("Tomas Prueba Villacis", _CED_TOMAS, 5),
                ),
            ),
            HojaAuxiliar("NOVEDADES ", (("NOVEDADES DEL MES",), ("Sin novedades",))),
        ),
    ),
    Libro(
        LIBRO_2026,
        (
            HojaMensual(
                "ENERO",
                FORMATO_C,
                ((), (), (None, "ENERO 2026")),
                (
                    Membresia(
                        "Camila Prueba Benitez",
                        None,
                        "ANUAL",
                        date(2026, 1, 25),
                        date(2027, 1, 24),
                        "Transferencia",
                        350,
                        "RENOVACION",
                    ),
                    EncabezadoRepetido(),
                    Totales("MONTO TOTAL", 350),
                ),
            ),
            HojaMensual(
                "JULIO",
                FORMATO_C,
                ((), (None, "JULIO 2026")),
                (
                    Membresia(
                        "Mateo Prueba Castillo",
                        _CED_MATEO,
                        "MENSUAL",
                        date(2026, 7, 1),
                        date(2026, 7, 31),
                        "TRANSFERENCIA",
                        40,
                        "RENOVACION",
                    ),
                    Membresia(
                        "Sofia Prueba Guerrero",
                        _CED_SOFIA,
                        "MENSUAL",
                        date(2026, 7, 2),
                        date(2026, 8, 1),
                        "EFECTIVO",
                        40,
                        "REINGRESO",
                    ),
                    Totales("TOTAL", 80),
                ),
            ),
            HojaMensual(
                "AGOSTO",
                FORMATO_C,
                ((), (), (None, "AGOSTO 2026")),
                (
                    # Caso del tutor: vence el 20 del último mes; T+30 queda fuera del corte.
                    Membresia(
                        "Joaquin Prueba Paredes",
                        _CED_JOAQUIN,
                        "MENSUAL",
                        date(2026, 7, 21),
                        date(2026, 8, 20),
                        "EFECTIVO",
                        40,
                        "NUEVO",
                    ),
                    Membresia(
                        "Sofia Prueba Guerrero",
                        _CED_SOFIA,
                        "MENSUAL",
                        date(2026, 8, 10),
                        date(2026, 9, 9),
                        "EFECTIVO",
                        40,
                        "RENOVACION",
                    ),
                    Vacia(),
                    Totales("TOTAL AGOSTO", 80),
                ),
            ),
            HojaAuxiliar("Hoja 40", ()),
            HojaAuxiliar("VENTAS", (("PRODUCTO", "CANTIDAD", "VALOR"), ("Agua", 3, 1.5))),
            HojaAuxiliar(
                "PENDIENTES",
                (("NOMBRE", "CEDULA", "PENDIENTE"), ("Emilia Prueba Naranjo", _CED_EMILIA, 10)),
            ),
        ),
    ),
)


def _valores_membresia(membresia: Membresia, formato: Formato, secuencia: int) -> list[object]:
    fila: list[object] = [None] * len(formato.encabezado)
    columnas = formato.columnas
    fila[columnas["nombre"]] = membresia.nombre
    fila[columnas["cedula"]] = membresia.cedula
    fila[columnas["celular"]] = f"0990{secuencia:06d}"
    fila[columnas["correo"]] = f"socio{secuencia:03d}@example.com"
    fila[columnas["plan"]] = membresia.plan
    fila[columnas["inicio"]] = membresia.inicio
    fila[columnas["fin"]] = membresia.fin
    fila[columnas["pago"]] = membresia.pago
    fila[columnas["transaccion"]] = f"TRX{secuencia:05d}"
    fila[columnas["facturar"]] = membresia.monto
    fila[columnas["monto"]] = membresia.monto
    if "status" in columnas:
        fila[columnas["status"]] = membresia.status
        fila[columnas["factura"]] = f"001-001-{secuencia:06d}"
    return fila


def _escribir_hoja_mensual(hoja: Worksheet, definicion: HojaMensual, secuencia: int) -> int:
    for indice, previa in enumerate(definicion.previas):
        _escribir_fila(hoja, indice + 1, previa)
    fila_encabezado = len(definicion.previas) + 1
    _escribir_fila(hoja, fila_encabezado, definicion.formato.encabezado)
    columnas = definicion.formato.columnas
    for desplazamiento, fila in enumerate(definicion.filas, start=1):
        numero = fila_encabezado + desplazamiento
        if isinstance(fila, Membresia):
            secuencia += 1
            _escribir_fila(hoja, numero, _valores_membresia(fila, definicion.formato, secuencia))
        elif isinstance(fila, Totales):
            valores: list[object] = [None] * len(definicion.formato.encabezado)
            valores[columnas["nombre"]] = fila.etiqueta
            valores[columnas["monto"]] = fila.monto
            _escribir_fila(hoja, numero, valores)
        elif isinstance(fila, EncabezadoRepetido):
            _escribir_fila(hoja, numero, definicion.formato.encabezado)
    return secuencia


def generar_libro(libro: Libro, destino: Path) -> Path:
    workbook = _libro_vacio()
    secuencia = 0
    for definicion in libro.hojas:
        hoja = workbook.create_sheet(definicion.nombre)
        if isinstance(definicion, HojaMensual):
            secuencia = _escribir_hoja_mensual(hoja, definicion, secuencia)
        else:
            for indice, valores in enumerate(definicion.filas):
                _escribir_fila(hoja, indice + 1, valores)
    ruta = destino / libro.archivo
    _guardar_determinista(workbook, ruta)
    return ruta


# ------------------------------------------------------------------ plantillas (CU-01)

TITULOS_REGISTROS: tuple[str, ...] = (
    "ESTADO DEL REGISTRO",
    "NOMBRES Y APELLIDOS",
    "CÉDULA",
    "CELULAR",
    "CORREO",
    "TIPO DE PLAN",
    "FECHA DE INICIO",
    "FECHA DE VENCIMIENTO",
    "FORMA DE PAGO",
    "N.º DE TRANSACCIÓN",
    "MONTO A FACTURAR (USD)",
    "MONTO COBRADO (USD)",
    "ASISTENCIAS EN EL PERÍODO",
    "OBSERVACIONES",
    "DURACIÓN (días)",
    "REVISIÓN AUTOMÁTICA",
)
PLANES = ("MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "DIARIO", "OTRO")
FORMAS_PAGO = ("EFECTIVO", "TRANSFERENCIA", "TARJETA_DATAFAST", "OTRO")
ESTADOS_REGISTRO = ("NUEVO", "RENOVACION", "CONGELAMIENTO", "REINGRESO", "BAJA")
_DURACION_PLAN = {
    "MENSUAL": 30,
    "TRIMESTRAL": 90,
    "SEMESTRAL": 180,
    "ANUAL": 365,
    "DIARIO": 1,
    "OTRO": 30,
}
_MONTO_PLAN = {
    "MENSUAL": 40.0,
    "TRIMESTRAL": 99.5,
    "SEMESTRAL": 190.0,
    "ANUAL": 350.0,
    "DIARIO": 5.0,
    "OTRO": 35.0,
}
_NOMBRES_PLANTILLA = NOMBRES_FICTICIOS[18:]
FILAS_PLANTILLA_VALIDA = 6
ULTIMA_FILA_FORMULAS = 501  # la plantilla oficial trae fórmulas en O y P hasta la fila 501

# Fila de Excel alterada en cada plantilla con errores.
FILA_CEDULA_INVALIDA = 3
FILA_CATALOGO_INVALIDO = 4
FILA_FECHAS_INVALIDAS = 5


def fila_plantilla(indice: int) -> list[object]:
    """Valores A-N de la fila ``indice`` (0-based) de una plantilla correcta."""
    plan = PLANES[indice % len(PLANES)]
    inicio = date(2026, 9, 1) + timedelta(days=indice % 28)
    fin = inicio + timedelta(days=_DURACION_PLAN[plan])
    monto = _MONTO_PLAN[plan]
    return [
        ESTADOS_REGISTRO[indice % len(ESTADOS_REGISTRO)],
        _NOMBRES_PLANTILLA[indice % len(_NOMBRES_PLANTILLA)],
        cedula_valida(indice + 1),
        f"0980{indice:06d}",
        f"plantilla{indice:03d}@example.com",
        plan,
        inicio,
        fin,
        FORMAS_PAGO[indice % len(FORMAS_PAGO)],
        f"TRX{indice:06d}",
        monto,
        monto,
        indice % 25,
        None,
    ]


def _formula_duracion(fila: int) -> str:
    return f'=IF(OR(G{fila}="",H{fila}=""),"",H{fila}-G{fila})'


def _formula_revision(fila: int) -> str:
    n = fila
    return (
        f'=IF(COUNTA(A{n}:N{n})=0,"",IF(B{n}="","Falta el nombre",'
        f'IF(C{n}="","Falta la cédula",IF(LEN(C{n})<>10,"La cédula debe tener 10 dígitos",'
        f'IF(F{n}="","Falta el tipo de plan",IF(G{n}="","Falta la fecha de inicio",'
        f'IF(H{n}="","Falta la fecha de vencimiento",'
        f'IF(O{n}<=0,"El vencimiento debe ser posterior al inicio",'
        f'IF(AND(F{n}<>"DIARIO",O{n}<21),"Duración muy corta: revisar fechas",'
        f'IF(O{n}>400,"Duración mayor a 400 días: revisar fechas",'
        f'IF(I{n}="","Falta la forma de pago",IF(L{n}="","Falta el monto cobrado","OK"))))))))))))'
    )


def _hoja_instrucciones(libro: Workbook) -> None:
    hoja = libro.create_sheet("Instrucciones")
    lineas = (
        None,
        "MTABOLIC · PLANTILLA OFICIAL DE CARGA DE DATOS",
        "Formato único para entregar la información de membresías (archivo sintético de prueba).",
        None,
        "¿Cómo se llena?",
        "Una membresía por fila en la hoja Registros, desde la fila 2.",
        "Use las listas de la hoja Catalogos para el plan, la forma de pago y el estado.",
    )
    for indice, linea in enumerate(lineas, start=1):
        if linea is not None:
            hoja.cell(row=indice, column=1, value=linea)


def _hoja_registros(libro: Workbook, filas: Sequence[Sequence[object]]) -> None:
    hoja = libro.create_sheet("Registros")
    _escribir_fila(hoja, 1, TITULOS_REGISTROS)
    hoja.freeze_panes = "A2"
    ultima = max(ULTIMA_FILA_FORMULAS, len(filas) + 1)
    for indice, valores in enumerate(filas):
        _escribir_fila(hoja, indice + 2, valores)
    for numero in range(2, ultima + 1):
        hoja.cell(row=numero, column=15, value=_formula_duracion(numero))
        hoja.cell(row=numero, column=16, value=_formula_revision(numero))
    validaciones = (
        DataValidation(type="list", formula1="Catalogos!$A$5:$A$10", sqref=f"F2:F{ultima}"),
        DataValidation(type="list", formula1="Catalogos!$A$14:$A$17", sqref=f"I2:I{ultima}"),
        DataValidation(type="list", formula1="Catalogos!$A$21:$A$25", sqref=f"A2:A{ultima}"),
        DataValidation(
            type="date",
            operator="between",
            formula1="DATE(2024,1,1)",
            formula2="DATE(2035,12,31)",
            sqref=f"G2:H{ultima}",
        ),
        DataValidation(
            type="decimal", operator="greaterThanOrEqual", formula1="0", sqref=f"K2:L{ultima}"
        ),
        DataValidation(
            type="whole", operator="between", formula1="0", formula2="400", sqref=f"M2:M{ultima}"
        ),
    )
    for validacion in validaciones:
        hoja.add_data_validation(validacion)


def _hoja_ejemplo(libro: Workbook) -> None:
    hoja = libro.create_sheet("Ejemplo")
    hoja.cell(row=1, column=1, value="EJEMPLO DE CÓMO SE VE UNA HOJA BIEN LLENADA")
    _escribir_fila(hoja, 3, TITULOS_REGISTROS[:14])
    for indice in range(3):
        _escribir_fila(hoja, indice + 4, fila_plantilla(indice))


def _hoja_catalogos(libro: Workbook) -> None:
    hoja = libro.create_sheet("Catalogos")
    hoja.cell(row=1, column=1, value="LISTAS PERMITIDAS")
    hoja.cell(row=2, column=1, value="Estos son los únicos valores que acepta el sistema.")
    bloques = ((4, "TIPO DE PLAN", PLANES), (13, "FORMA DE PAGO", FORMAS_PAGO))
    bloques += ((20, "ESTADO DEL REGISTRO", ESTADOS_REGISTRO),)
    for fila_titulo, titulo, valores in bloques:
        hoja.cell(row=fila_titulo, column=1, value=titulo)
        hoja.cell(row=fila_titulo, column=2, value="Cuándo se usa")
        for desplazamiento, valor in enumerate(valores, start=1):
            hoja.cell(row=fila_titulo + desplazamiento, column=1, value=valor)


def generar_plantilla(filas: Sequence[Sequence[object]], ruta: Path) -> Path:
    libro = _libro_vacio()
    _hoja_instrucciones(libro)
    _hoja_registros(libro, filas)
    _hoja_ejemplo(libro)
    _hoja_catalogos(libro)
    _guardar_determinista(libro, ruta)
    return ruta


def filas_plantillas() -> dict[str, list[list[object]]]:
    """Filas A-N de cada plantilla, por nombre de archivo."""
    validas = [fila_plantilla(i) for i in range(FILAS_PLANTILLA_VALIDA)]

    cedula = [list(f) for f in validas]
    original = str(cedula[FILA_CEDULA_INVALIDA - 2][2])
    cedula[FILA_CEDULA_INVALIDA - 2][2] = original[:9] + str((int(original[9]) + 1) % 10)

    catalogo = [list(f) for f in validas]
    catalogo[FILA_CATALOGO_INVALIDO - 2][5] = "SEMANAL"

    fechas = [list(f) for f in validas]
    fila = fechas[FILA_FECHAS_INVALIDAS - 2]
    inicio = fila[6]
    assert isinstance(inicio, date)
    fila[7] = inicio - timedelta(days=10)

    return {
        PLANTILLA_VALIDA: validas,
        PLANTILLA_CEDULA_INVALIDA: cedula,
        PLANTILLA_CATALOGO_INVALIDO: catalogo,
        PLANTILLA_FECHAS_INVALIDAS: fechas,
        PLANTILLA_501_FILAS: [fila_plantilla(i) for i in range(501)],
    }


# ------------------------------------------------------------------ punto de entrada


def generar(destino: Path = DIRECTORIO) -> list[Path]:
    """Genera los 7 archivos bajo ``destino/historico`` y ``destino/plantillas``."""
    rutas = [generar_libro(libro, destino / "historico") for libro in LIBROS]
    for archivo, filas in filas_plantillas().items():
        rutas.append(generar_plantilla(filas, destino / "plantillas" / archivo))
    return rutas


def main() -> int:
    for ruta in generar():
        print(ruta.relative_to(DIRECTORIO).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
