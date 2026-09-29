"""Conversiones de valores crudos de celda (notebook MVP, secciones 3.1 y 3.3).

Reescritura en Python puro de ``normalizar_texto_encabezado``, ``convertir_fecha`` y
``convertir_numero``. El lector entrega valores crudos (``None`` en vez de ``NaN``); aqui
se tolera tambien un ``float('nan')`` por robustez. Los montos se devuelven como
``Decimal`` (el notebook usa ``float``): un ``float`` de celda pasa por ``str`` y nunca por
``Decimal(float)``.
"""

import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal

_EPOCA_EXCEL = date(1899, 12, 30)
_SERIAL_MINIMO = 20000
_SERIAL_MAXIMO = 60000

_HORA = r"(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?"
# Como ``pd.to_datetime`` del notebook, se tolera el separador repetido solo entre el primer y
# el segundo campo (``"15//03/2025"`` si; ``"15/03//2025"`` no).
_FECHA_ANIO_PRIMERO = re.compile(r"^(\d{4})[-/.]+(\d{1,2})[-/.](\d{1,2})" + _HORA + r"$")
_FECHA_DIA_PRIMERO = re.compile(r"^(\d{1,2})[-/.]+(\d{1,2})[-/.](\d{4}|\d{2})" + _HORA + r"$")
_NUMERO = re.compile(r"-?\d+(?:\.\d+)?")


def _es_vacio(valor: object) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _sin_tildes(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def normalizar_texto_encabezado(valor: object) -> str:
    """MAYUSCULAS, sin tildes y con espacios simples: ``" Cédula  "`` -> ``"CEDULA"``."""
    if _es_vacio(valor):
        return ""
    texto = _sin_tildes(str(valor).strip().upper())
    return re.sub(r"\s+", " ", texto)


def _crear_fecha(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _fecha_desde_texto(texto: str) -> date | None:
    coincidencia = _FECHA_ANIO_PRIMERO.match(texto)
    if coincidencia:
        anio, mes, dia = (int(g) for g in coincidencia.groups())
        return _crear_fecha(anio, mes, dia)
    coincidencia = _FECHA_DIA_PRIMERO.match(texto)
    if coincidencia:
        primero, segundo, anio_texto = coincidencia.groups()
        anio = int(anio_texto) + (2000 if len(anio_texto) == 2 else 0)
        # Primero dia/mes/anio (dayfirst=True); si no es valida, mes/dia/anio.
        return _crear_fecha(anio, int(segundo), int(primero)) or _crear_fecha(
            anio, int(primero), int(segundo)
        )
    return None


def convertir_fecha(valor: object) -> date | None:
    """Fecha sin hora a partir de un ``datetime``/``date``, un serial de Excel o un texto."""
    if _es_vacio(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if (
        isinstance(valor, int | float)
        and not isinstance(valor, bool)
        and _SERIAL_MINIMO <= valor <= _SERIAL_MAXIMO
    ):
        return _EPOCA_EXCEL + timedelta(days=math.floor(valor))
    texto = str(valor).strip()
    if not texto:
        return None
    return _fecha_desde_texto(texto)


def convertir_monto(valor: object) -> Decimal | None:
    """Primer numero del valor como ``Decimal``: ``"39,50 USD"`` -> ``Decimal("39.50")``.

    No filtra negativos: esa regla se aplica al construir el registro historico.
    """
    if _es_vacio(valor):
        return None
    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None
    if isinstance(valor, int) and not isinstance(valor, bool):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(str(valor)) if math.isfinite(valor) else None
    texto = str(valor).replace(",", ".")
    coincidencia = _NUMERO.search(texto)
    return Decimal(coincidencia.group(0)) if coincidencia else None
