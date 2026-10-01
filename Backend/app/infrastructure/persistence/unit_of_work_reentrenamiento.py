"""Unidad de trabajo SQLAlchemy del reentrenamiento (CU-02) y su bloqueo consultivo.

Cada llamada abre una ``Session`` nueva con una sola transaccion; los repositorios del
contexto la comparten. Solo ``commit()`` confirma: salir del contexto sin confirmar, o con una
excepcion, revierte todo (el modelo nuevo, su intento y la proxima fecha van juntos o nada).

``AbridorBloqueoReentrenamiento`` entrega un ``PgBloqueoReentrenamiento`` sobre una conexion
propia en ``AUTOCOMMIT``; al salir la conexion fisica se cierra (mismo patron que el de la
migracion), de modo que ningun bloqueo olvidado vuelve al pool.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.modelo.ports import BloqueoReentrenamiento, ContextoReentrenamiento
from app.domain.common.clock import Clock
from app.infrastructure.persistence.repositories.historial import SqlAlchemyMembresiaRepository
from app.infrastructure.persistence.repositories.modelo import (
    PgBloqueoReentrenamiento,
    SqlAlchemyEstadoSistemaRepository,
    SqlAlchemyIntentoRepository,
    SqlAlchemyModeloRepository,
)


class _ContextoSqlAlchemy:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self.membresias = SqlAlchemyMembresiaRepository(session, clock)
        self.modelos = SqlAlchemyModeloRepository(session, clock)
        self.intentos = SqlAlchemyIntentoRepository(session, clock)
        self.estado = SqlAlchemyEstadoSistemaRepository(session, clock)

    def commit(self) -> None:
        self._session.commit()


class SqlAlchemyUnidadDeTrabajoReentrenamiento:
    """Implementa ``UnidadDeTrabajoReentrenamiento``."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._sesiones = sessionmaker(bind=engine, expire_on_commit=False)
        self._clock = clock

    @contextmanager
    def __call__(self) -> Iterator[ContextoReentrenamiento]:
        with self._sesiones() as session:
            try:
                yield _ContextoSqlAlchemy(session, self._clock)
            finally:
                # Sin commit explicito no se confirma nada.
                session.rollback()


class AbridorBloqueoReentrenamiento:
    """Implementa ``AbrirBloqueoReentrenamiento`` con una conexion propia en ``AUTOCOMMIT``."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def __call__(self) -> Iterator[BloqueoReentrenamiento]:
        conexion = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        try:
            yield PgBloqueoReentrenamiento(conexion)
        finally:
            # Cierra la conexion fisica: un bloqueo de sesion no vuelve nunca al pool.
            conexion.invalidate()
            conexion.close()
