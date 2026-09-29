from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.domain.common.exceptions import DomainError
from app.domain.health.value_objects import (
    ComponentStatus,
    HealthReport,
    InvalidHealthReportError,
    OverallStatus,
)

pytestmark = pytest.mark.unit

CHECKED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_create_database_up_returns_ok() -> None:
    report = HealthReport.create(database=ComponentStatus.UP, checked_at=CHECKED_AT)

    assert report.status == OverallStatus.OK
    assert report.database == ComponentStatus.UP
    assert report.checked_at == CHECKED_AT


def test_create_database_down_returns_degraded() -> None:
    report = HealthReport.create(database=ComponentStatus.DOWN, checked_at=CHECKED_AT)

    assert report.status == OverallStatus.DEGRADED


def test_create_naive_datetime_raises_invalid_health_report_error() -> None:
    naive = datetime(2026, 1, 1, 12, 0)  # noqa: DTZ001 - naive a proposito

    with pytest.raises(InvalidHealthReportError):
        HealthReport.create(database=ComponentStatus.UP, checked_at=naive)


def test_invalid_health_report_error_is_domain_error() -> None:
    assert issubclass(InvalidHealthReportError, DomainError)


def test_health_report_is_immutable() -> None:
    report = HealthReport.create(database=ComponentStatus.UP, checked_at=CHECKED_AT)

    with pytest.raises(FrozenInstanceError):
        report.status = OverallStatus.DEGRADED  # type: ignore[misc]  # asignacion intencional para verificar frozen
