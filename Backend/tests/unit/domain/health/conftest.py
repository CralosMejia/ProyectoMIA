from datetime import UTC, datetime

import pytest

from app.domain.common.clock import Clock


class FixedClock:
    """Doble del puerto Clock que devuelve siempre el mismo instante."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


@pytest.fixture
def checked_at() -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def fixed_clock(checked_at: datetime) -> Clock:
    return FixedClock(checked_at)
