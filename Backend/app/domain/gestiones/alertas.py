"""Grupos de alerta de seguimiento por fecha (CU-09, decision (a) de R-011).

Solo cuentan las gestiones ``PENDIENTE`` no borradas (eso lo filtra quien consulta); aqui
solo se decide a que grupo pertenece una fecha de seguimiento respecto de ``hoy`` (fecha de
negocio en Ecuador, que calcula quien llama con ``hoy_en_negocio(clock.now())``):

- ``VENCIDAS``: ``fecha_seguimiento < hoy``.
- ``HOY``: ``fecha_seguimiento == hoy``.
- ``PROXIMAS``: ``hoy + 1 .. hoy + DIAS_PROXIMAS``, ambos incluidos.

Los tres rangos no se solapan: cada gestion cae como mucho en un grupo.
"""

from datetime import date, timedelta
from enum import StrEnum, unique

DIAS_PROXIMAS = 7
"""Ventana de "proximos dias" (fija, CU-09)."""


@unique
class GrupoAlerta(StrEnum):
    VENCIDAS = "vencidas"
    HOY = "hoy"
    PROXIMAS = "proximas"


def rango_de(grupo: GrupoAlerta, hoy: date) -> tuple[date | None, date]:
    """Rango ``[desde, hasta]`` (ambos incluidos) de fechas de seguimiento del grupo.

    ``desde`` es ``None`` cuando el rango no tiene limite inferior (vencidas).
    """
    if grupo is GrupoAlerta.VENCIDAS:
        return None, hoy - timedelta(days=1)
    if grupo is GrupoAlerta.HOY:
        return hoy, hoy
    return hoy + timedelta(days=1), hoy + timedelta(days=DIAS_PROXIMAS)
