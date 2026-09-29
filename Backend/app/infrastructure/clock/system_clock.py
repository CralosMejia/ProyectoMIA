"""Implementacion del puerto ``Clock`` con la hora real del sistema."""

from datetime import UTC, datetime


class SystemClock:
    """Reloj del sistema. Unico punto de la aplicacion que lee la hora real."""

    def now(self) -> datetime:
        """Devuelve la hora actual en UTC con zona horaria (aware)."""
        return datetime.now(UTC)
