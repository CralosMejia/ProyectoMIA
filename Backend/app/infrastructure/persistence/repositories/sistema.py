"""Lecturas ligeras para ``GET /sistema/estado`` (solo lectura; nunca carga el artefacto).

Cada metodo abre una ``Session`` corta de solo lectura. ``hay_carga_plantilla_entre`` responde
al aviso de "datos del mes" (D6-BE-06). El estado y la ultima carga reutilizan
los repositorios existentes; el resumen del modelo vigente solo selecciona sus columnas
ligeras (el artefacto puede pesar varios MB y el estado se consulta periodicamente).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import Engine, exists, select
from sqlalchemy.orm import Session

from app.application.modelo.ports import EstadoSistema
from app.application.sistema.ports import ResumenModelo
from app.domain.common.clock import Clock
from app.domain.common.enums import TipoCarga
from app.infrastructure.persistence.models.historial import Carga
from app.infrastructure.persistence.models.modelo import Modelo
from app.infrastructure.persistence.repositories.historial import SqlAlchemyCargaRepository
from app.infrastructure.persistence.repositories.modelo import SqlAlchemyEstadoSistemaRepository


class SqlAlchemyLectorEstadoSistema:
    """Implementa ``LectorEstadoSistema``."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._engine = engine
        self._clock = clock

    @contextmanager
    def _sesion(self) -> Iterator[Session]:
        with Session(self._engine) as session:
            try:
                yield session
            finally:
                session.rollback()

    def estado(self) -> EstadoSistema:
        with self._sesion() as session:
            return SqlAlchemyEstadoSistemaRepository(session, self._clock).obtener()

    def modelo_vigente(self) -> ResumenModelo | None:
        with self._sesion() as session:
            fila = session.execute(
                select(
                    Modelo.version, Modelo.fecha_entrenamiento, Modelo.ciclos_entrenamiento
                ).where(Modelo.vigente.is_(True))
            ).one_or_none()
        if fila is None:
            return None
        return ResumenModelo(
            version=fila.version,
            fecha_entrenamiento=fila.fecha_entrenamiento,
            ciclos_entrenamiento=fila.ciclos_entrenamiento,
        )

    def ultima_carga_en(self) -> datetime | None:
        with self._sesion() as session:
            return SqlAlchemyCargaRepository(session, self._clock).ultima_fecha_carga()

    def hay_carga_plantilla_entre(self, desde: datetime, hasta: datetime) -> bool:
        # Solo cargas mensuales (PLANTILLA) no borradas: la migracion historica no cuenta.
        with self._sesion() as session:
            return bool(
                session.scalar(
                    select(
                        exists().where(
                            Carga.tipo == TipoCarga.PLANTILLA.value,
                            Carga.deleted_at.is_(None),
                            Carga.fecha_carga >= desde,
                            Carga.fecha_carga < hasta,
                        )
                    )
                )
            )
