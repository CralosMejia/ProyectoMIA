"""Fixtures compartidas de las pruebas de integracion (PostgreSQL real, nunca SQLite)."""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import URL, make_url

from app.infrastructure.persistence.database import create_database_engine

TEST_DATABASE_URL_ENV = "TEST_DATABASE_URL"


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


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    return _require_test_database_url()


@pytest.fixture(scope="session")
def engine(test_database_url: URL) -> Iterator[Engine]:
    db_engine = create_database_engine(test_database_url.render_as_string(hide_password=False))
    try:
        yield db_engine
    finally:
        db_engine.dispose()
