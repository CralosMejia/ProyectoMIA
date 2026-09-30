"""Documento de identidad de la columna C de la plantilla (CU-01, decision (e) de R-007).

Cedula ecuatoriana: 10 digitos con verificador modulo 10 (coeficientes 2, 1, 2, ... sobre los
9 primeros), sin reglas de provincia. Excepcion: si Observaciones contiene la palabra
``PASAPORTE`` (sin distinguir mayusculas) se acepta un documento de 5 a 20 caracteres
``[A-Za-z0-9]``.
"""

import re

_CEDULA = re.compile(r"[0-9]{10}")
_PASAPORTE = re.compile(r"[A-Za-z0-9]{5,20}")
_PALABRA_PASAPORTE = re.compile(r"\bPASAPORTE\b", re.IGNORECASE)
_ESPACIOS = re.compile(r"\s+")
_DIGITOS_CEDULA_SIN_CERO = 9


def normalizar_documento(valor: object) -> str:
    """Texto del documento tal como se valida.

    Texto: se quitan los espacios. Numero (Excel pierde el cero inicial): ``str(int)`` y, si
    quedan 9 digitos, se antepone ``0``. ``None`` o vacio: ``""``.
    """
    if valor is None or isinstance(valor, bool):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    if isinstance(valor, int):
        texto = str(valor)
        return "0" + texto if len(texto) == _DIGITOS_CEDULA_SIN_CERO else texto
    return _ESPACIOS.sub("", str(valor))


def cedula_valida(texto: str) -> bool:
    """``True`` si son 10 digitos y el ultimo es el verificador modulo 10 de los 9 primeros."""
    if not _CEDULA.fullmatch(texto):
        return False
    total = 0
    for posicion, caracter in enumerate(texto[:9]):
        producto = int(caracter) * (2 if posicion % 2 == 0 else 1)
        total += producto - 9 if producto > 9 else producto
    return (10 - total % 10) % 10 == int(texto[9])


def es_pasaporte(observaciones: str | None) -> bool:
    """``True`` si Observaciones contiene la palabra ``PASAPORTE``."""
    return bool(observaciones) and _PALABRA_PASAPORTE.search(observaciones or "") is not None


def documento_valido(texto: str, observaciones: str | None) -> bool:
    """Cedula valida o, con ``PASAPORTE`` en Observaciones, documento alfanumerico 5..20."""
    if es_pasaporte(observaciones):
        return _PASAPORTE.fullmatch(texto) is not None
    return cedula_valida(texto)
