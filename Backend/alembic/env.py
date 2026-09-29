"""Entorno de migraciones.

La URL sale solo de la variable de entorno ``DATABASE_URL`` (nunca de ``alembic.ini``).
Si falta, el proceso termina con un mensaje que nombra la variable sin mostrar valores.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.engine import create_engine

from app.infrastructure.persistence.models import Base

DATABASE_URL_ENV = "DATABASE_URL"
DATABASE_URL_SCHEME = "postgresql+psycopg://"

target_metadata = Base.metadata

if context.config.config_file_name is not None:
    # Sin desactivar los loggers ya creados (p. ej. al invocarse desde pytest).
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def _database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV, "").strip()
    if not url:
        raise SystemExit(
            f"{DATABASE_URL_ENV} no esta definida: exportala con la URL de PostgreSQL "
            f"({DATABASE_URL_SCHEME}...) antes de ejecutar las migraciones."
        )
    if not url.startswith(DATABASE_URL_SCHEME):
        raise SystemExit(f"{DATABASE_URL_ENV} debe usar el esquema {DATABASE_URL_SCHEME}")
    return url


def run_migrations_offline() -> None:
    """Genera SQL (``--sql``) sin conectarse."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        compare_type=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_database_url(), poolclass=pool.NullPool, hide_parameters=True)
    try:
        with engine.connect() as connection:
            _run_with_connection(connection)
    finally:
        engine.dispose()


def _run_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
