"""Conteos esperados de los fixtures sintéticos (generados por ``generar_fixtures.py``).

Fuente de verdad para T9 (lector), T10 (procesamiento) y T11 (verificación) sobre los libros
sintéticos, y para el lector de la plantilla (D4-BE-01). Las cifras se calcularon aplicando las
reglas del notebook (secciones 2.4 a 5.5) a estos libros; ``test_fixtures_sinteticos.py`` las
vuelve a calcular desde los archivos.

Sin datos personales: solo nombres de archivo, nombres de hoja, números de fila y conteos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

# ------------------------------------------------------------------ libros históricos

LIBRO_2025 = "Control Gym 2025 sintetico.xlsx"
LIBRO_2026 = "Control Gym 2026 sintetico.xlsx"
ANIO_POR_LIBRO: dict[str, int] = {LIBRO_2025: 2025, LIBRO_2026: 2026}

# Nombres exactos (con sus espacios), en el orden del libro.
HOJAS_INCLUIDAS: dict[str, tuple[str, ...]] = {
    LIBRO_2025: ("ENERO", "FEBRERO ", " MARZO", "DICIEMBRE"),
    LIBRO_2026: ("ENERO", "JULIO", "AGOSTO"),
}
HOJAS_OMITIDAS: dict[str, tuple[str, ...]] = {
    LIBRO_2025: ("06 ene", "DIARIOS", "NOVEDADES "),
    LIBRO_2026: ("Hoja 40", "VENTAS", "PENDIENTES"),
}

# Fila del encabezado (0-based, como ``encontrar_fila_encabezado`` del notebook).
FILA_ENCABEZADO: dict[tuple[int, str], int] = {
    (2025, "ENERO"): 2,
    (2025, "FEBRERO "): 4,
    (2025, " MARZO"): 0,
    (2025, "DICIEMBRE"): 3,
    (2026, "ENERO"): 3,
    (2026, "JULIO"): 2,
    (2026, "AGOSTO"): 3,
}

# Filas leídas por hoja: desde la fila siguiente al encabezado hasta la última con datos
# (incluye vacías intermedias, totales y encabezados repetidos).
FILAS_LEIDAS_POR_HOJA: dict[tuple[int, str], int] = {
    (2025, "ENERO"): 11,
    (2025, "FEBRERO "): 7,
    (2025, " MARZO"): 6,
    (2025, "DICIEMBRE"): 5,
    (2026, "ENERO"): 3,
    (2026, "JULIO"): 3,
    (2026, "AGOSTO"): 4,
}

# Hojas sin la columna de fecha de inicio reconocible ("FECHA INSCRIP" no es un alias).
HOJAS_SIN_FECHA_INICIO: tuple[tuple[int, str], ...] = ((2025, "FEBRERO "),)

# ------------------------------------------------------------------ limpieza e identidad (T4)

FILAS_LEIDAS = 39
DESCARTADAS_NO_UTILES = 14  # vacías, totales, sin nombre y encabezados repetidos
UTILES = 25
SIN_IDENTIDAD = 2  # nombre normalizado de menos de 5 letras
CON_IDENTIDAD = 23
SOCIOS_DISTINTOS = 14
SOCIOS_POR_CEDULA = 10
SOCIOS_POR_NOMBRE = 4
REGISTROS_POR_CEDULA = 17
REGISTROS_POR_NOMBRE = 6
INICIO_APROXIMADO = 4
MONTOS_INVALIDOS = 1  # monto negativo: se guarda como None (desviación documentada en T4)
DUPLICADOS_EXACTOS = 2  # filas que participan en un duplicado exacto; ambas se conservan

# ------------------------------------------------------------------ ciclos y etiqueta (T5, T10)

FECHA_CORTE = date(2026, 8, 31)

CICLOS_POR_ESTADO: dict[str, int] = {"EVALUABLE": 15, "PENDIENTE": 1, "EXCLUIDO": 7}
CICLOS_POR_MOTIVO: dict[str, int] = {
    "SIN_VENCIMIENTO": 1,
    "FECHA_FUERA_DE_RANGO": 1,
    "VENCIMIENTO_POSTERIOR_AL_CORTE": 3,
    "PASE_DIARIO": 1,
    "DURACION_IMPLAUSIBLE": 1,
    "VENTANA_INCOMPLETA": 1,
    "EVALUABLE": 15,
}
EVALUABLES = 15
NO_RENOVO = 9
RENOVO = 6
PREVALENCIA = Decimal("0.6")  # NO_RENOVO / EVALUABLES, exacta

# Rango de vencimientos de los registros con identidad y fecha de vencimiento.
RANGO_VENCIMIENTOS: tuple[date, date] = (date(2024, 11, 30), date(2027, 1, 24))
# Rango de vencimientos de los ciclos evaluables.
RANGO_VENCIMIENTOS_EVALUABLES: tuple[date, date] = (date(2025, 2, 5), date(2026, 8, 1))

# Caso del tutor: vence el 2026-08-20 (T+30 = 2026-09-19 > corte) -> PENDIENTE.
CASO_TUTOR: dict[str, object] = {
    "anio": 2026,
    "hoja": "AGOSTO",
    "fila": 5,
    "fecha_vencimiento": date(2026, 8, 20),
    "estado": "PENDIENTE",
    "motivo": "VENTANA_INCOMPLETA",
}

# Referencias (anio, hoja, fila) con resultado conocido, para pruebas puntuales.
RENOVACIONES: tuple[tuple[int, str, int], ...] = (
    (2025, "ENERO", 4),  # renueva dentro de T..T+30 en " MARZO" (misma cédula, otro nombre)
    (2025, "FEBRERO ", 7),  # duplicado exacto: ambos renuevan con la misma fila de " MARZO"
    (2025, "FEBRERO ", 8),
    (2025, "DICIEMBRE", 6),  # renueva en JULIO 2026
    (2025, "DICIEMBRE", 7),  # socio sin cédula; renueva en ENERO 2026 (entre libros)
    (2026, "JULIO", 5),  # T+30 = corte (límite inclusivo); renueva en AGOSTO
)

# ------------------------------------------------------------------ plantillas (CU-01)

PLANTILLA_VALIDA = "plantilla_valida.xlsx"
PLANTILLA_CEDULA_INVALIDA = "plantilla_cedula_invalida.xlsx"
PLANTILLA_CATALOGO_INVALIDO = "plantilla_catalogo_invalido.xlsx"
PLANTILLA_FECHAS_INVALIDAS = "plantilla_fechas_invalidas.xlsx"
PLANTILLA_501_FILAS = "plantilla_501_filas.xlsx"

HOJAS_PLANTILLA: tuple[str, ...] = ("Instrucciones", "Registros", "Ejemplo", "Catalogos")

# Filas con datos en A-N de la hoja Registros (O y P traen fórmulas en todas las filas,
# como la plantilla oficial, y no cuentan como datos).
FILAS_CON_DATOS: dict[str, int] = {
    PLANTILLA_VALIDA: 6,
    PLANTILLA_CEDULA_INVALIDA: 6,
    PLANTILLA_CATALOGO_INVALIDO: 6,
    PLANTILLA_FECHAS_INVALIDAS: 6,
    PLANTILLA_501_FILAS: 501,
}

# Fila de Excel con error -> campo que falla. Vacío = todas las filas son correctas.
FILAS_CON_ERROR: dict[str, dict[int, str]] = {
    PLANTILLA_VALIDA: {},
    PLANTILLA_CEDULA_INVALIDA: {3: "cedula"},  # dígito verificador incorrecto
    PLANTILLA_CATALOGO_INVALIDO: {4: "tipo_plan"},  # plan SEMANAL
    PLANTILLA_FECHAS_INVALIDAS: {5: "fecha_vencimiento"},  # vencimiento anterior al inicio
    PLANTILLA_501_FILAS: {},  # se rechaza el archivo completo por superar 500 filas
}
