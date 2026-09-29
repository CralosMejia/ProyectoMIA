import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import app
from app.domain.common.clock import Clock
from app.infrastructure.clock.system_clock import SystemClock

pytestmark = pytest.mark.unit


def test_now_returns_aware_datetime_in_utc() -> None:
    result = SystemClock().now()

    assert isinstance(result, datetime)
    assert result.tzinfo == UTC


def test_now_returns_current_instant() -> None:
    before = datetime.now(UTC)
    result = SystemClock().now()
    after = datetime.now(UTC)

    assert before - timedelta(seconds=1) <= result <= after + timedelta(seconds=1)


def test_system_clock_satisfies_clock_port() -> None:
    clock: Clock = SystemClock()

    assert clock.now().tzinfo == UTC


def test_system_clock_is_only_module_in_app_reading_system_time() -> None:
    app_root = Path(app.__file__).parent
    forbidden = ("datetime.now(", "datetime.utcnow(", "date.today(", "time.time(")
    offenders = [
        str(path.relative_to(app_root))
        for path in app_root.rglob("*.py")
        if path.name != "system_clock.py"
        and any(token in path.read_text(encoding="utf-8") for token in forbidden)
    ]

    assert offenders == []


def test_system_clock_consecutive_calls_are_monotonic_non_decreasing() -> None:
    clock = SystemClock()

    first = clock.now()
    second = clock.now()

    assert second >= first


def test_system_clock_module_is_only_caller_of_now_with_timezone_across_app() -> None:
    # Clock.now() sin argumentos es el puerto; now(<tz>) es leer la hora real del sistema.
    app_root = Path(app.__file__).parent
    system_now_call = re.compile(r"\.now\(\s*[^)\s]")
    callers = sorted(
        path.name
        for path in app_root.rglob("*.py")
        if system_now_call.search(path.read_text(encoding="utf-8"))
    )

    assert callers == ["system_clock.py"]
