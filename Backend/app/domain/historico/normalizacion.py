"""Normalizacion de filas del historico (notebook MVP, secciones 3.6, 4.1, 4.2, 4.5 y 4.6).

Las reglas se copian tal cual del notebook y en el mismo orden; cualquier cambio altera
las cifras de reconciliacion de CU-03.
"""

import math
import re
import unicodedata

from app.domain.common.enums import FormaPago, Plan

_PALABRAS_DE_TOTALES = re.compile(r"TOTAL|SUBTOTAL|SUMA|MONTO")
_ENCABEZADOS_REPETIDOS = frozenset(
    {"STATUS", "NOMBRES Y APELLIDOS", "NOMBRES Y APELLIDOS DEL SOCIO"}
)
_MINIMO_DIGITOS_CEDULA = 9

FORMAS_PAGO_EN_CAMPO_PLAN = ("DATAFAST", "TRANSF", "EFECTIVO", "TARJETA", "DEPOSITO")
_UN_MES = re.compile(r"\b1\s*MES\b")


def _texto(valor: object) -> str:
    """``str`` del valor; ``None`` y ``NaN`` se tratan como vacio."""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    return str(valor)


def es_fila_util(nombre_crudo: object) -> bool:
    """Descarta filas vacias, de totales y encabezados repetidos (seccion 3.6)."""
    nombre = _texto(nombre_crudo).strip()
    if not nombre:
        return False
    nombre_mayuscula = nombre.upper()
    if _PALABRAS_DE_TOTALES.search(nombre_mayuscula):
        return False
    return nombre_mayuscula not in _ENCABEZADOS_REPETIDOS


def normalizar_nombre(texto: object) -> str:
    """MAYUSCULAS sin tildes, solo ``A-Z`` y espacios simples (seccion 4.1)."""
    limpio = unicodedata.normalize("NFKD", _texto(texto)).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^A-Z ]", " ", limpio.upper())
    return re.sub(r"\s+", " ", limpio).strip()


def normalizar_cedula(valor: object) -> str | None:
    """Solo digitos; ``None`` si quedan menos de 9 (seccion 4.2)."""
    digitos = re.sub(r"\D", "", _texto(valor))
    return digitos if len(digitos) >= _MINIMO_DIGITOS_CEDULA else None


def normalizar_plan(texto: object, duracion_dias: int | None) -> Plan:
    """Plan a partir del texto crudo y, si no basta, de la duracion observada (seccion 4.5)."""
    plan = _texto(texto).upper().strip()
    # Regla 1: el campo plan contenia una forma de pago.
    if any(pago in plan for pago in FORMAS_PAGO_EN_CAMPO_PLAN):
        plan = ""
    # Regla 2: palabras clave.
    if "DIARIO" in plan:
        return Plan.DIARIO
    if "ANUAL" in plan or "AÑO" in plan or "ANO" in plan:
        return Plan.ANUAL
    if "SEMESTR" in plan or "6 MES" in plan:
        return Plan.SEMESTRAL
    if any(x in plan for x in ("3 MES", "TRES MES", "TRIMEST")):
        return Plan.TRIMESTRAL
    if "MENSUAL" in plan or _UN_MES.search(plan) or "PLAN MES" in plan:
        return Plan.MENSUAL
    # Regla 3: duracion observada.
    if duracion_dias is not None:
        if 21 <= duracion_dias <= 45:
            return Plan.MENSUAL
        if 80 <= duracion_dias <= 130:
            return Plan.TRIMESTRAL
        if 160 <= duracion_dias <= 200:
            return Plan.SEMESTRAL
        if 330 <= duracion_dias <= 400:
            return Plan.ANUAL
    # Regla 4.
    return Plan.OTRO


def normalizar_forma_pago(texto: object) -> FormaPago:
    """Forma de pago a partir del texto crudo (seccion 4.6)."""
    forma = _texto(texto).upper()
    if not forma.strip():
        return FormaPago.SIN_DATO
    if "EFECT" in forma:
        return FormaPago.EFECTIVO
    if "DATAFAST" in forma or "TARJ" in forma:
        return FormaPago.TARJETA_DATAFAST
    if any(x in forma for x in ("TRANS", "PICH", "PROD", "DINERS", "INTER")):
        return FormaPago.TRANSFERENCIA
    return FormaPago.OTRO
