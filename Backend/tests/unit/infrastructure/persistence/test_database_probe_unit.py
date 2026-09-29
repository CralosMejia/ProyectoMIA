"""Pruebas unitarias de SqlAlchemyDatabaseProbe con un doble de Engine (sin BD)."""

import logging
from types import TracebackType
from typing import Any, cast

import pytest
from sqlalchemy import Engine

from app.infrastructure.persistence.database_probe import SqlAlchemyDatabaseProbe

pytestmark = pytest.mark.unit

DRIVER_ERROR_WITH_DSN = "postgresql+psycopg://app:s3cr3t-pw@db.internal:5432/app"


class _FailingConnection:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def __enter__(self) -> "_FailingConnection":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def execute(self, statement: Any) -> None:
        raise self._error


class _EngineDouble:
    def __init__(
        self, *, connect_error: Exception | None = None, execute_error: Exception | None = None
    ) -> None:
        self._connect_error = connect_error
        self._execute_error = execute_error

    def connect(self) -> _FailingConnection:
        if self._connect_error is not None:
            raise self._connect_error
        assert self._execute_error is not None
        return _FailingConnection(self._execute_error)


def _probe(engine: _EngineDouble) -> SqlAlchemyDatabaseProbe:
    return SqlAlchemyDatabaseProbe(cast(Engine, engine))


@pytest.mark.parametrize(
    "error",
    [RuntimeError("boom"), OSError("connection refused"), TimeoutError("timeout")],
    ids=["runtime", "oserror", "timeout"],
)
def test_is_reachable_connect_raises_any_exception_returns_false(error: Exception) -> None:
    assert _probe(_EngineDouble(connect_error=error)).is_reachable() is False


def test_is_reachable_execute_raises_returns_false() -> None:
    engine = _EngineDouble(execute_error=RuntimeError("query failed"))

    assert _probe(engine).is_reachable() is False


def test_is_reachable_error_message_with_credentials_is_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = _EngineDouble(connect_error=RuntimeError(DRIVER_ERROR_WITH_DSN))

    with caplog.at_level(logging.DEBUG):
        result = _probe(engine).is_reachable()

    assert result is False
    assert caplog.records, "el fallo debe registrarse"
    assert "s3cr3t-pw" not in caplog.text
    assert "db.internal" not in caplog.text
    assert "postgresql" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
