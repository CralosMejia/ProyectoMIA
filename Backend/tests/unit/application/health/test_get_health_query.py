import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import app.application
from app.application.health.dtos import HealthDTO
from app.application.health.queries import GetHealthQueryHandler
from app.domain.health.value_objects import HealthReport, InvalidHealthReportError

pytestmark = pytest.mark.unit

FIXED_INSTANT = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


class FixedClock:
    """Doble del puerto Clock que devuelve siempre el mismo instante."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class StubDatabaseProbe:
    """Doble del puerto DatabaseProbe con respuesta fija."""

    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable
        self.calls = 0

    def is_reachable(self) -> bool:
        self.calls += 1
        return self._reachable


def _handle(*, reachable: bool) -> HealthDTO:
    handler = GetHealthQueryHandler(
        probe=StubDatabaseProbe(reachable=reachable), clock=FixedClock(FIXED_INSTANT)
    )
    return handler.handle()


def test_handle_probe_reachable_returns_ok_and_database_up() -> None:
    result = _handle(reachable=True)

    assert result == HealthDTO(status="ok", database="up", checked_at=FIXED_INSTANT)


def test_handle_probe_unreachable_returns_degraded_and_database_down() -> None:
    result = _handle(reachable=False)

    assert result.status == "degraded"
    assert result.database == "down"
    assert result.checked_at == FIXED_INSTANT


@pytest.mark.parametrize("reachable", [True, False])
def test_handle_any_probe_result_returns_dto_not_domain_entity(reachable: bool) -> None:
    result = _handle(reachable=reachable)

    assert type(result) is HealthDTO
    assert not isinstance(result, HealthReport)  # type: ignore[unreachable]  # mypy no admite subclase comun; se verifica en runtime


def test_handle_checked_at_comes_from_injected_clock() -> None:
    other_instant = datetime(2030, 6, 15, 8, 30, tzinfo=UTC)
    handler = GetHealthQueryHandler(
        probe=StubDatabaseProbe(reachable=True), clock=FixedClock(other_instant)
    )

    result = handler.handle()

    assert result.checked_at == other_instant


def test_handle_invoked_calls_probe_once() -> None:
    probe = StubDatabaseProbe(reachable=True)
    handler = GetHealthQueryHandler(probe=probe, clock=FixedClock(FIXED_INSTANT))

    handler.handle()

    assert probe.calls == 1


def test_handle_clock_returns_naive_datetime_raises_invalid_health_report_error() -> None:
    naive_instant = datetime(2026, 1, 1, 0, 0, 0)  # noqa: DTZ001 - naive a proposito
    handler = GetHealthQueryHandler(
        probe=StubDatabaseProbe(reachable=True), clock=FixedClock(naive_instant)
    )

    with pytest.raises(InvalidHealthReportError):
        handler.handle()


def test_handle_result_is_immutable_rejects_assignment() -> None:
    result = _handle(reachable=True)

    with pytest.raises(ValidationError):
        result.status = "degraded"  # type: ignore[misc]  # asignacion intencional para verificar frozen


def test_application_layer_source_has_no_system_clock_calls() -> None:
    application_dir = Path(app.application.__file__).parent
    forbidden = re.compile(r"datetime\.(now|utcnow|today)\(|date\.today\(|time\.time\(")

    offenders = [
        str(path)
        for path in application_dir.rglob("*.py")
        if forbidden.search(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []
