"""Factory del ``Engine`` de SQLAlchemy hacia PostgreSQL (driver ``psycopg`` 3).

No crea tablas ni ejecuta migraciones: el esquema lo gestiona Alembic como paso
separado del despliegue.
"""

from sqlalchemy import Engine, create_engine

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_CONNECT_TIMEOUT_SECONDS = 2
DEFAULT_POOL_TIMEOUT_SECONDS = 2


def create_database_engine(
    url: str,
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
    max_overflow: int = DEFAULT_MAX_OVERFLOW,
    connect_timeout_seconds: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    pool_timeout_seconds: float = DEFAULT_POOL_TIMEOUT_SECONDS,
) -> Engine:
    """Crea el ``Engine`` con pool explicito y ``pool_pre_ping``.

    ``url`` debe usar el driver ``postgresql+psycopg://``. ``connect_timeout`` corto
    para que una base caida se detecte rapido en lugar de bloquear el request, y
    ``pool_timeout`` corto para no bloquear el request (p. ej. el health check) con
    el pool agotado.
    """
    return create_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout_seconds,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": connect_timeout_seconds},
    )
