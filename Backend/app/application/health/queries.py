"""Queries del modulo health."""

from app.application.health.dtos import HealthDTO
from app.application.health.ports import DatabaseProbe
from app.domain.common.clock import Clock
from app.domain.health.value_objects import ComponentStatus, HealthReport


class GetHealthQueryHandler:
    """Caso de uso: consultar el estado de salud del servicio."""

    def __init__(self, *, probe: DatabaseProbe, clock: Clock) -> None:
        self._probe = probe
        self._clock = clock

    def handle(self) -> HealthDTO:
        database = ComponentStatus.UP if self._probe.is_reachable() else ComponentStatus.DOWN
        report = HealthReport.create(database=database, checked_at=self._clock.now())
        return HealthDTO(
            status=report.status.value,
            database=report.database.value,
            checked_at=report.checked_at,
        )
