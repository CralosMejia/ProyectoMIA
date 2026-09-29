"""Implementacion del puerto ``DatabaseProbe`` sobre un ``Engine`` de SQLAlchemy."""

import logging

from sqlalchemy import Engine, text

logger = logging.getLogger(__name__)

_PING_SQL = text("SELECT 1")


class SqlAlchemyDatabaseProbe:
    """Comprueba la conectividad ejecutando ``SELECT 1``. Nunca propaga excepciones."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_reachable(self) -> bool:
        """Devuelve ``True`` si la base responde; ``False`` ante cualquier error."""
        try:
            with self._engine.connect() as connection:
                connection.execute(_PING_SQL)
        except Exception as exc:
            # Solo el tipo de error: el mensaje del driver puede incluir host, puerto o usuario.
            logger.warning("database probe failed: %s", type(exc).__name__)
            return False
        return True
