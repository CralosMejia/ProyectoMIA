"""Puertos del modulo health (implementados en infrastructure)."""

from typing import Protocol


class DatabaseProbe(Protocol):
    """Sonda de conectividad con la base de datos."""

    def is_reachable(self) -> bool:
        """Indica si la base de datos responde. Nunca lanza: ante error devuelve ``False``."""
        ...
