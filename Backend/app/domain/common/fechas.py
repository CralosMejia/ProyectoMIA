"""Aritmetica de fechas del dominio (sin reloj: la fecha de partida la da quien llama)."""

import calendar
from datetime import date, datetime, timedelta, timezone

ZONA_NEGOCIO = timezone(timedelta(hours=-5))
"""Hora de Ecuador continental: UTC-5 fijo, sin horario de verano."""


def sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses de calendario; si el dia no existe en el mes destino, usa el ultimo del mes."""
    indice = fecha.year * 12 + (fecha.month - 1) + meses
    anio, mes = divmod(indice, 12)
    mes += 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


def hoy_en_negocio(instante: datetime) -> date:
    """Fecha de calendario de ``instante`` en la zona del negocio (Ecuador, UTC-5).

    ``instante`` debe tener zona horaria (normalmente ``clock.now()``); si no la tiene se
    lanza ``ValueError`` para no confundir una hora local con una UTC.
    """
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise ValueError("El instante debe tener zona horaria.")
    return instante.astimezone(ZONA_NEGOCIO).date()
