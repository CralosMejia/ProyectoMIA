"""Unidad de trabajo SQLAlchemy y bloqueo de la migracion sobre una conexion propia.

``SqlAlchemyUnidadDeTrabajo`` abre **una** ``Session`` con **una** transaccion
(``session.begin()``) al entrar en el ``with`` y construye los repositorios sobre ella. Solo
``commit()`` confirma; al salir sin ``commit`` o por una excepcion se hace ``rollback`` y la
sesion se cierra. Los repositorios nunca controlan la transaccion.

``abrir_bloqueo_migracion`` entrega un ``PgBloqueoMigracion`` sobre una conexion propia en
``AUTOCOMMIT`` (el bloqueo consultivo es de sesion, independiente de las transacciones). Al
salir, la conexion se invalida: la conexion fisica se cierra en lugar de volver al pool, de
modo que ningun bloqueo olvidado sobrevive (quien lo usa ya llama a ``liberar()``).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Self

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.modelo.ports import BloqueoMigracion
from app.domain.common.clock import Clock
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyCargaRepository,
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from app.infrastructure.persistence.repositories.modelo import (
    PgBloqueoMigracion,
    SqlAlchemyEstadoSistemaRepository,
    SqlAlchemyIntentoRepository,
    SqlAlchemyModeloRepository,
)


class SqlAlchemyUnidadDeTrabajo:
    """Implementa ``UnidadDeTrabajo`` sobre una ``Session`` y una transaccion."""

    def __init__(self, fabrica_sesiones: sessionmaker[Session], clock: Clock) -> None:
        self._fabrica = fabrica_sesiones
        self._clock = clock
        self._session: Session | None = None

    def __enter__(self) -> Self:
        session = self._fabrica()
        session.begin()
        self._session = session
        self.socios = SqlAlchemySocioRepository(session, self._clock)
        self.membresias = SqlAlchemyMembresiaRepository(session, self._clock)
        self.cargas = SqlAlchemyCargaRepository(session, self._clock)
        self.modelos = SqlAlchemyModeloRepository(session, self._clock)
        self.intentos = SqlAlchemyIntentoRepository(session, self._clock)
        self.estado = SqlAlchemyEstadoSistemaRepository(session, self._clock)
        return self

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("La unidad de trabajo no esta abierta.")
        self._session.commit()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._session
        self._session = None
        if session is None:
            return
        try:
            # Sin commit (o tras una excepcion) no queda nada; tras commit no hay nada que revertir.
            session.rollback()
        finally:
            session.close()


class FabricaUnidadDeTrabajoSqlAlchemy:
    """Implementa ``FabricaUnidadDeTrabajo``: una unidad (y transaccion) nueva por llamada."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._fabrica = sessionmaker(bind=engine, expire_on_commit=False)
        self._clock = clock

    def __call__(self) -> SqlAlchemyUnidadDeTrabajo:
        return SqlAlchemyUnidadDeTrabajo(self._fabrica, self._clock)


class AbridorBloqueoMigracion:
    """Implementa ``AbrirBloqueo`` con una conexion propia en ``AUTOCOMMIT``."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def __call__(self) -> Iterator[BloqueoMigracion]:
        conexion = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        try:
            yield PgBloqueoMigracion(conexion)
        finally:
            # Cierra la conexion fisica: un bloqueo de sesion no vuelve nunca al pool.
            conexion.invalidate()
            conexion.close()
