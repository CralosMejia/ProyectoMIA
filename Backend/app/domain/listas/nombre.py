"""Nombre por defecto de una lista priorizada (R-008, decision (g)).

``"Lista del <d> <mmm> <aaaa>"`` con la fecha de la lista, dia sin cero y la tabla fija de
meses cortos en espanol (sin punto). No depende de ``locale`` ni del reloj: el mismo
formato lo reproducen la migracion ``0006`` y el frontend (``fechaCorta``).
"""

from datetime import date

MESES_CORTOS: tuple[str, ...] = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)
LONGITUD_MAXIMA_NOMBRE = 80


def nombre_por_defecto(fecha: date) -> str:
    """Nombre sugerido para la lista de ``fecha`` (``2026-09-29`` -> ``Lista del 29 sep 2026``)."""
    return f"Lista del {fecha.day} {MESES_CORTOS[fecha.month - 1]} {fecha.year}"
