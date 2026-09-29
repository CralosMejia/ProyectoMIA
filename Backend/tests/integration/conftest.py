"""Fixtures compartidas de las pruebas de integracion (PostgreSQL real, nunca SQLite).

Guarda: la base de ``TEST_DATABASE_URL`` debe llamarse ``*_test``. Las pruebas de
migracion ejecutan ``downgrade base``; contra la base de desarrollo la vaciarian.
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url

from app.infrastructure.persistence.database import create_database_engine

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"
TEST_DATABASE_SUFFIX = "_test"
MAINTENANCE_DATABASE = "postgres"
BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
_DATABASE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def _require_test_database_url() -> URL:
    """Devuelve la URL de la BD de pruebas o falla con un mensaje claro (nunca se salta)."""
    raw = os.environ.get(TEST_DATABASE_URL_ENV, "").strip()
    if not raw:
        pytest.fail(
            f"{TEST_DATABASE_URL_ENV} no esta definida: las pruebas de integracion requieren "
            "un PostgreSQL 16 real (p. ej. postgresql+psycopg://usuario:clave@127.0.0.1:55432/"
            "app_test). Exportala antes de ejecutar pytest.",
            pytrace=False,
        )
    return make_url(raw)


def _guard_test_database(url: URL) -> URL:
    """Aborta si la base no es de pruebas (nombre ``*_test``). Nunca muestra la URL."""
    name = url.database or ""
    if not name.endswith(TEST_DATABASE_SUFFIX) or not _DATABASE_NAME.match(name):
        pytest.fail(
            f"{TEST_DATABASE_URL_ENV} debe apuntar a una base cuyo nombre termine en "
            f"'{TEST_DATABASE_SUFFIX}' (minusculas, digitos y '_'): las pruebas de migracion "
            "la vacian y no pueden correr contra la base de desarrollo.",
            pytrace=False,
        )
    return url


def _ensure_database_exists(url: URL) -> None:
    """Crea la base de pruebas si no existe (conexion AUTOCOMMIT a ``postgres``)."""
    name = url.database
    assert name is not None
    admin = create_engine(
        url.set(database=MAINTENANCE_DATABASE),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
    )
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ).scalar()
            if not exists:
                quoted = conn.dialect.identifier_preparer.quote_identifier(name)
                conn.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    url = _guard_test_database(_require_test_database_url())
    _ensure_database_exists(url)
    return url


@pytest.fixture(scope="session")
def engine(test_database_url: URL) -> Iterator[Engine]:
    db_engine = create_database_engine(test_database_url.render_as_string(hide_password=False))
    try:
        yield db_engine
    finally:
        db_engine.dispose()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: URL) -> Iterator[Config]:
    """``Config`` de migraciones apuntando a la base de pruebas via ``DATABASE_URL``."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", test_database_url.render_as_string(hide_password=False))
        yield Config(str(ALEMBIC_INI))


@pytest.fixture(scope="session")
def migrated_engine(engine: Engine, alembic_config: Config) -> Iterator[Engine]:
    """Base en ``head`` durante la sesion; al terminar vuelve a ``base``."""
    command.upgrade(alembic_config, "head")
    try:
        yield engine
    finally:
        command.downgrade(alembic_config, "base")
