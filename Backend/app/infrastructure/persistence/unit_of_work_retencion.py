"""Unidad de trabajo SQLAlchemy de retencion: campanas, sugerencias y gestiones
(CU-06, CU-07, CU-08, CU-10).

Mismo patron que ``unit_of_work_listas``: cada llamada abre una ``Session`` nueva con una
sola transaccion que comparten todos los repositorios del contexto. Solo ``commit()``
confirma; salir del contexto sin confirmar, o con una excepcion, revierte todo.

La violacion del indice unico ``ux_gestiones_retencion_membresia_id`` (dos gestiones para el
mismo ciclo, p. ej. por una carrera entre dos peticiones) se traduce a
``GestionDuplicadaError`` (RN-08.1 -> 409).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.common.clock import Clock
from app.domain.gestiones.errores import GestionDuplicadaError
from app.infrastructure.persistence.repositories.campanias import (
    SqlAlchemyCampaniaRepository,
    SqlAlchemyPerfilPrediccion,
)
from app.infrastructure.persistence.repositories.gestiones import (
    SqlAlchemyGestionRepository,
    es_gestion_duplicada,
)


class _ContextoRetencion:
    """Implementa ``ContextoCampanias`` y ``ContextoGestiones`` sobre una ``Session``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self.campanias = SqlAlchemyCampaniaRepository(session, clock)
        self.perfiles = SqlAlchemyPerfilPrediccion(session)
        self.gestiones = SqlAlchemyGestionRepository(session, clock)

    def commit(self) -> None:
        self._session.commit()


class SqlAlchemyUnidadDeTrabajoRetencion:
    """Implementa ``UnidadDeTrabajoCampanias`` y ``UnidadDeTrabajoGestiones``."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self._sesiones = sessionmaker(bind=engine, expire_on_commit=False)
        self._clock = clock

    @contextmanager
    def __call__(self) -> Iterator[_ContextoRetencion]:
        with self._sesiones() as session:
            try:
                yield _ContextoRetencion(session, self._clock)
            except IntegrityError as error:
                if es_gestion_duplicada(error):
                    raise GestionDuplicadaError() from error
                raise
            finally:
                # Sin commit explicito no se confirma nada.
                session.rollback()
