import ast
import sys
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

import pytest

from app.domain.common.clock import Clock
from app.domain.common.exceptions import DomainError
from app.domain.health.value_objects import (
    ComponentStatus,
    HealthReport,
    InvalidHealthReportError,
    OverallStatus,
)

pytestmark = pytest.mark.unit

DOMAIN_DIR = Path(__file__).resolve().parents[4] / "app" / "domain"


class _TzWithoutOffset(tzinfo):
    """tzinfo presente pero sin offset: el datetime sigue siendo naive."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


@pytest.mark.parametrize(
    ("database", "expected"),
    [
        (ComponentStatus.UP, OverallStatus.OK),
        (ComponentStatus.DOWN, OverallStatus.DEGRADED),
    ],
)
def test_create_with_clock_now_derives_status_from_database(
    fixed_clock: Clock, database: ComponentStatus, expected: OverallStatus
) -> None:
    report = HealthReport.create(database=database, checked_at=fixed_clock.now())

    assert report.status == expected
    assert report.checked_at == fixed_clock.now()


def test_create_naive_datetime_is_catchable_as_domain_error() -> None:
    naive = datetime(2026, 1, 1, 12, 0)  # noqa: DTZ001 - naive a proposito

    with pytest.raises(DomainError):
        HealthReport.create(database=ComponentStatus.DOWN, checked_at=naive)


def test_create_tzinfo_without_utcoffset_raises_invalid_health_report_error() -> None:
    pseudo_aware = datetime(2026, 1, 1, 12, 0, tzinfo=_TzWithoutOffset())

    with pytest.raises(InvalidHealthReportError):
        HealthReport.create(database=ComponentStatus.UP, checked_at=pseudo_aware)


@pytest.mark.parametrize("field", ["status", "database", "checked_at"])
def test_setattr_any_field_raises_frozen_instance_error(checked_at: datetime, field: str) -> None:
    report = HealthReport.create(database=ComponentStatus.UP, checked_at=checked_at)

    with pytest.raises(FrozenInstanceError):
        setattr(report, field, None)


def test_health_report_uses_slots_has_no_instance_dict(checked_at: datetime) -> None:
    report = HealthReport.create(database=ComponentStatus.UP, checked_at=checked_at)

    assert not hasattr(report, "__dict__")
    assert set(HealthReport.__slots__) == {"status", "database", "checked_at"}


def test_health_report_equal_inputs_are_equal_and_hashable(checked_at: datetime) -> None:
    a = HealthReport.create(database=ComponentStatus.UP, checked_at=checked_at)
    b = HealthReport.create(database=ComponentStatus.UP, checked_at=checked_at)

    assert a == b
    assert hash(a) == hash(b)


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
    return modules


def test_domain_modules_import_only_stdlib_or_domain() -> None:
    files = list(DOMAIN_DIR.rglob("*.py"))
    assert files, f"no se encontraron modulos en {DOMAIN_DIR}"

    offenders = {
        f"{path.relative_to(DOMAIN_DIR)}: {module}"
        for path in files
        for module in _top_level_imports(path)
        if not module.startswith("app.domain")
        and module.split(".")[0] not in sys.stdlib_module_names
    }

    assert offenders == set()
