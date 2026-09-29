import logging
import socket
import time
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from app.application.health.ports import DatabaseProbe
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.database_probe import SqlAlchemyDatabaseProbe

pytestmark = pytest.mark.integration

MAX_UNREACHABLE_SECONDS = 5.0
MAX_POOL_TIMEOUT_SECONDS = 2


def _free_local_port() -> int:
    """Puerto de 127.0.0.1 sin servicio escuchando."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
    return port


@pytest.fixture
def unreachable_url(test_database_url: URL) -> URL:
    return test_database_url.set(host="127.0.0.1", port=_free_local_port())


@pytest.fixture
def unreachable_engine(unreachable_url: URL) -> Iterator[Engine]:
    db_engine = create_database_engine(unreachable_url.render_as_string(hide_password=False))
    try:
        yield db_engine
    finally:
        db_engine.dispose()


def test_is_reachable_returns_true_when_database_is_up(engine: Engine) -> None:
    probe = SqlAlchemyDatabaseProbe(engine)

    assert probe.is_reachable() is True


def test_is_reachable_returns_false_quickly_when_database_is_down(
    unreachable_engine: Engine,
) -> None:
    probe = SqlAlchemyDatabaseProbe(unreachable_engine)

    started = time.monotonic()
    result = probe.is_reachable()
    elapsed = time.monotonic() - started

    assert result is False
    assert elapsed < MAX_UNREACHABLE_SECONDS


def test_is_reachable_logs_failure_without_url_or_credentials(
    unreachable_engine: Engine,
    unreachable_url: URL,
    caplog: pytest.LogCaptureFixture,
) -> None:
    probe = SqlAlchemyDatabaseProbe(unreachable_engine)

    with caplog.at_level(logging.DEBUG):
        probe.is_reachable()

    assert caplog.records, "el fallo de conectividad debe quedar registrado en el log"
    logged = caplog.text
    # Aserciones booleanas con mensaje fijo: si fallan, pytest no debe imprimir el secreto.
    has_password = bool(unreachable_url.password)
    assert has_password, "la URL de pruebas debe tener contrasena para validar que no se filtra"
    leaks = {
        "contrasena": str(unreachable_url.password) in logged,
        "url completa": unreachable_url.render_as_string(hide_password=False) in logged,
        "url enmascarada": unreachable_url.render_as_string(hide_password=True) in logged,
        "esquema postgresql": "postgresql" in logged,
        "usuario@": f"{unreachable_url.username}@" in logged,
        "puerto": str(unreachable_url.port) in logged,
    }
    leaked = [name for name, found in leaks.items() if found]
    assert not leaked, f"el log filtra datos de conexion: {leaked}"


def test_probe_satisfies_database_probe_port(engine: Engine) -> None:
    probe: DatabaseProbe = SqlAlchemyDatabaseProbe(engine)

    assert callable(probe.is_reachable)


def test_engine_uses_psycopg_driver_and_pre_ping(engine: Engine) -> None:
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    assert engine.pool._pre_ping is True


def test_create_database_engine_uses_short_pool_timeout_by_default(engine: Engine) -> None:
    # Con el pool agotado, el health check no debe quedar bloqueado los 30 s por defecto.
    assert engine.pool.timeout() <= MAX_POOL_TIMEOUT_SECONDS  # type: ignore[attr-defined]


def test_is_reachable_executes_select_1_against_database(engine: Engine) -> None:
    from sqlalchemy import event

    statements: list[str] = []

    def _capture(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _capture)
    try:
        assert SqlAlchemyDatabaseProbe(engine).is_reachable() is True
    finally:
        event.remove(engine, "before_cursor_execute", _capture)

    assert "SELECT 1" in [s.strip() for s in statements]


def test_is_reachable_concurrent_calls_on_same_engine_all_return_true(engine: Engine) -> None:
    from concurrent.futures import ThreadPoolExecutor

    probe = SqlAlchemyDatabaseProbe(engine)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: probe.is_reachable(), range(32)))

    assert results == [True] * 32


def test_is_reachable_unreachable_does_not_raise_on_repeated_calls(
    unreachable_engine: Engine,
) -> None:
    probe = SqlAlchemyDatabaseProbe(unreachable_engine)

    assert [probe.is_reachable() for _ in range(2)] == [False, False]
