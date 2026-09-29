"""Composition root de la capa de presentacion.

Unico modulo de ``app.api`` que conoce ``app.infrastructure``: instancia las
implementaciones y las enlaza con los puertos de aplicacion via ``Depends``.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine

from app.application.health.ports import DatabaseProbe
from app.application.health.queries import GetHealthQueryHandler
from app.domain.common.clock import Clock
from app.infrastructure.clock.system_clock import SystemClock
from app.infrastructure.persistence.database_probe import SqlAlchemyDatabaseProbe


def get_engine(request: Request) -> Engine:
    """``Engine`` creado en el arranque de la aplicacion (ver ``app.main``)."""
    engine: Engine = request.app.state.engine
    return engine


def get_clock() -> Clock:
    return SystemClock()


def get_database_probe(engine: Annotated[Engine, Depends(get_engine)]) -> DatabaseProbe:
    return SqlAlchemyDatabaseProbe(engine)


def get_health_query_handler(
    probe: Annotated[DatabaseProbe, Depends(get_database_probe)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GetHealthQueryHandler:
    return GetHealthQueryHandler(probe=probe, clock=clock)
