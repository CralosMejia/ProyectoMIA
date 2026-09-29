"""Puerto de reloj: unica fuente de fecha y hora para dominio y aplicacion."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Proveedor de la hora actual."""

    def now(self) -> datetime:
        """Devuelve la hora actual como ``datetime`` UTC con zona horaria (aware)."""
        ...
