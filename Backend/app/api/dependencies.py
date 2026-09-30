"""Composition root de la capa de presentacion.

Unico modulo de ``app.api`` que conoce ``app.infrastructure``: instancia las
implementaciones y las enlaza con los puertos de aplicacion via ``Depends``.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine

from app.application.health.ports import DatabaseProbe
from app.application.health.queries import GetHealthQueryHandler
from app.application.listas.consultar_listas import ConsultarListas
from app.application.listas.generar_lista import GenerarLista
from app.application.listas.ports import ExportadorLista, UnidadDeTrabajoListas
from app.application.sistema.consultar_estado import ConsultarEstadoSistema
from app.application.sistema.migrar_historico import MigrarHistorico
from app.application.sistema.ports import LectorEstadoSistema, RegistroMigracion
from app.core.config import Settings
from app.domain.common.clock import Clock
from app.domain.common.predictor import PredictorModel
from app.infrastructure.clock.system_clock import SystemClock
from app.infrastructure.exportacion.excel_lista import ExcelListaOpenpyxl
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.persistence.database_probe import SqlAlchemyDatabaseProbe
from app.infrastructure.persistence.repositories.sistema import SqlAlchemyLectorEstadoSistema
from app.infrastructure.persistence.unit_of_work import (
    AbridorBloqueoMigracion,
    FabricaUnidadDeTrabajoSqlAlchemy,
)
from app.infrastructure.persistence.unit_of_work_listas import SqlAlchemyUnidadDeTrabajoListas


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


# ---------------------------------------------------------------- listas (CU-04, CU-05, CU-12)


def get_predictor() -> PredictorModel:
    return RandomForestPredictor()


def get_unidad_de_trabajo_listas(
    engine: Annotated[Engine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> UnidadDeTrabajoListas:
    return SqlAlchemyUnidadDeTrabajoListas(engine, clock)


def get_exportador_lista() -> ExportadorLista:
    return ExcelListaOpenpyxl()


def get_generar_lista(
    uow: Annotated[UnidadDeTrabajoListas, Depends(get_unidad_de_trabajo_listas)],
    predictor: Annotated[PredictorModel, Depends(get_predictor)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> GenerarLista:
    return GenerarLista(uow, predictor, clock)


def get_consultar_listas(
    uow: Annotated[UnidadDeTrabajoListas, Depends(get_unidad_de_trabajo_listas)],
    exportador: Annotated[ExportadorLista, Depends(get_exportador_lista)],
) -> ConsultarListas:
    return ConsultarListas(uow, exportador)


# ---------------------------------------------------------------- sistema (CU-03)


def crear_migracion_historica(
    engine: Engine,
    settings: Settings,
    registro: RegistroMigracion,
    predictor: PredictorModel | None = None,
) -> MigrarHistorico:
    """Compone ``MigrarHistorico`` con la infraestructura real (lo lanza ``app.main``)."""
    clock = SystemClock()
    return MigrarHistorico(
        abrir_bloqueo=AbridorBloqueoMigracion(engine),
        unidad_de_trabajo=FabricaUnidadDeTrabajoSqlAlchemy(engine, clock),
        localizador=LocalizadorLibrosCarpeta(settings.HISTORICO_PATH),
        lector=LectorLibrosExcel(),
        predictor=predictor if predictor is not None else RandomForestPredictor(),
        clock=clock,
        registro=registro,
    )


def get_registro_migracion(request: Request) -> RegistroMigracion:
    """Resultado en memoria de la migracion de este proceso (creado en ``app.main``)."""
    registro: RegistroMigracion = request.app.state.registro_migracion
    return registro


def get_lector_estado_sistema(
    engine: Annotated[Engine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> LectorEstadoSistema:
    return SqlAlchemyLectorEstadoSistema(engine, clock)


def get_consultar_estado_sistema(
    lector: Annotated[LectorEstadoSistema, Depends(get_lector_estado_sistema)],
    registro: Annotated[RegistroMigracion, Depends(get_registro_migracion)],
) -> ConsultarEstadoSistema:
    return ConsultarEstadoSistema(lector, registro)
