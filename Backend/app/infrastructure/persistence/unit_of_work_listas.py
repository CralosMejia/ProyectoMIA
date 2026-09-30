"""Unidad de trabajo SQLAlchemy de las listas priorizadas (CU-04, CU-05, CU-12).

Cada llamada abre una ``Session`` nueva con una sola transaccion; todos los repositorios
del contexto la comparten. Solo ``commit()`` confirma: salir del contexto sin confirmar, o
con una excepcion, revierte todo (la lista y sus predicciones se guardan juntas o nada).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.listas.ports import ContextoListas
from app.domain.common.clock import Clock
from app.infrastructure.persistence.repositories.historial import SqlAlchemyMembresiaRepository
from app.infrastructure.persistence.repositories.listas import (
    SqlAlchemyFechasCarga,
    SqlAlchemyListaRepository,
)
from app.infrastructure.persistence.repositories.modelo import (
    SqlAlchemyEstadoSistemaRepository,
    SqlAlchemyModeloRepository,
)


class _ContextoSqlAlchemy:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self.listas = SqlAlchemyListaRepository(session, clock)
        self.modelos = SqlAlchemyModeloRepository(session, clock)
        self.estado = SqlAlchemyEstadoSistemaRepository(session, clock)
        self.membresias = SqlAlchemyMembresiaRepository(session, clock)
        self.cargas = SqlAlchemyFechasCarga(session)

    def commit(self) -> None:
        self._session.commit()


class SqlAlchemyUnidadDeTrabajoListas:
    """Implementa ``UnidadDeTrabajoListas``."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._sesiones = sessionmaker(bind=engine, expire_on_commit=False)
        self._clock = clock

    @contextmanager
    def __call__(self) -> Iterator[ContextoListas]:
        with self._sesiones() as session:
            try:
                yield _ContextoSqlAlchemy(session, self._clock)
            finally:
                # Sin commit explicito no se confirma nada.
                session.rollback()
