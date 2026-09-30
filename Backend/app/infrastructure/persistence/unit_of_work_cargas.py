"""Unidad de trabajo SQLAlchemy de la carga por plantilla (CU-01).

Cada llamada abre una ``Session`` nueva con una sola transaccion; consultas, escritura y
estado la comparten. Solo ``commit()`` confirma: salir del contexto sin confirmar, o con una
excepcion, revierte todo (socios, cedulas, membresias y carga se guardan juntos o nada).

``bloquear()`` toma ``pg_advisory_xact_lock`` con una clave fija de cargas (decision (j) de
R-007): se libera solo al terminar la transaccion (``commit`` o ``rollback``), asi dos
confirmaciones nunca revalidan duplicados ni escriben a la vez.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.cargas.ports import ContextoCargas
from app.domain.common.clock import Clock
from app.infrastructure.persistence.repositories.cargas import (
    SqlAlchemyConsultasCarga,
    SqlAlchemyEscrituraCarga,
)
from app.infrastructure.persistence.repositories.modelo import SqlAlchemyEstadoSistemaRepository

CLAVE_BLOQUEO_CARGAS = 7_310_004
"""Clave del bloqueo consultivo de cargas (distinta de ``CLAVE_BLOQUEO_MIGRACION``)."""


class _ContextoSqlAlchemy:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self.consultas = SqlAlchemyConsultasCarga(session, clock)
        self.escritura = SqlAlchemyEscrituraCarga(session, clock)
        self.estado = SqlAlchemyEstadoSistemaRepository(session, clock)

    def bloquear(self) -> None:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": CLAVE_BLOQUEO_CARGAS}
        )

    def commit(self) -> None:
        self._session.commit()


class SqlAlchemyUnidadDeTrabajoCargas:
    """Implementa ``UnidadDeTrabajoCargas``."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._sesiones = sessionmaker(bind=engine, expire_on_commit=False)
        self._clock = clock

    @contextmanager
    def __call__(self) -> Iterator[ContextoCargas]:
        with self._sesiones() as session:
            try:
                yield _ContextoSqlAlchemy(session, self._clock)
            finally:
                # Sin commit explicito no se confirma nada (y se libera el bloqueo).
                session.rollback()
