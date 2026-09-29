"""Value objects del modulo health."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Self

from app.domain.common.exceptions import DomainError


class ComponentStatus(StrEnum):
    """Estado de un componente del que depende el servicio."""

    UP = "up"
    DOWN = "down"


class OverallStatus(StrEnum):
    """Estado agregado del servicio."""

    OK = "ok"
    DEGRADED = "degraded"


class InvalidHealthReportError(DomainError):
    """El informe de salud viola una invariante."""


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Informe de salud inmutable del servicio."""

    status: OverallStatus
    database: ComponentStatus
    checked_at: datetime

    @classmethod
    def create(cls, *, database: ComponentStatus, checked_at: datetime) -> Self:
        if checked_at.tzinfo is None or checked_at.utcoffset() is None:
            raise InvalidHealthReportError("checked_at debe tener zona horaria (UTC aware)")
        status = OverallStatus.OK if database is ComponentStatus.UP else OverallStatus.DEGRADED
        return cls(status=status, database=database, checked_at=checked_at)
