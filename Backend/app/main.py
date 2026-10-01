"""Composition root: crea la aplicacion FastAPI.

No crea tablas ni ejecuta migraciones de esquema al arrancar: el esquema lo gestiona Alembic
como paso separado del despliegue. La unica migracion de datos al arrancar es CU-03
(ADR-004): si ``MIGRAR_HISTORICO_AL_ARRANCAR``, se lanza en un hilo en segundo plano para que
la API (``/health`` incluido) responda mientras tanto.

Si ``REENTRENAMIENTO_AUTOMATICO``, el planificador del reentrenamiento (CU-02) corre en otro
hilo daemon que se detiene al apagar la aplicacion.
"""

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import ArgumentError

from app.api.acceso_ip import FiltroAccesoIp
from app.api.dependencies import crear_migracion_historica, crear_reentrenamiento
from app.api.errors import register_exception_handlers
from app.api.routers import campanias, cargas, dashboard, gestiones, health, listas, sistema
from app.application.sistema.migrar_historico import MigrarHistorico
from app.application.sistema.ports import RegistroMigracion, ResultadoMigracion
from app.core.config import Settings
from app.domain.common.clock import Clock
from app.domain.common.predictor import PredictorModel
from app.infrastructure.clock.system_clock import SystemClock
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.planificador.reentrenamiento import PlanificadorReentrenamiento

logger = logging.getLogger(__name__)

API_V1_PREFIX = "/api/v1"
NOMBRE_HILO_MIGRACION = "migracion-historica"


def _load_settings() -> Settings:
    """Carga y valida la configuracion; falla rapido sin exponer valores en el log."""
    try:
        return Settings()  # valores desde variables de entorno
    except ValidationError as exc:
        # str(exc) nombra la variable y el tipo de error; hide_input_in_errors oculta el valor.
        logger.error("configuracion invalida: %s", str(exc))
        raise


def ejecutar_migracion_segura(migracion: MigrarHistorico, registro: RegistroMigracion) -> None:
    """Cuerpo del hilo: una excepcion se registra (solo su tipo) y no tumba el proceso."""
    try:
        migracion.ejecutar()
    except Exception as exc:
        # Sin traceback ni mensaje: podrian citar datos de los libros (RN-03.5).
        logger.error(
            "migracion historica: error inesperado en segundo plano (%s)", type(exc).__name__
        )
        registro.terminar(ResultadoMigracion.FALLIDA)


def lanzar_migracion_en_segundo_plano(
    migracion: MigrarHistorico, registro: RegistroMigracion
) -> threading.Thread:
    hilo = threading.Thread(
        target=ejecutar_migracion_segura,
        args=(migracion, registro),
        name=NOMBRE_HILO_MIGRACION,
        daemon=True,
    )
    hilo.start()
    return hilo


def create_app(
    settings: Settings | None = None,
    *,
    predictor: PredictorModel | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Construye la aplicacion. ``settings``, ``predictor`` y ``clock`` explicitos solo para
    pruebas (``clock`` lo usa el planificador del reentrenamiento)."""
    resolved = settings if settings is not None else _load_settings()
    registro_migracion = RegistroMigracion()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # El secreto solo se desenvuelve aqui, en el composition root.
        try:
            engine = create_database_engine(resolved.DATABASE_URL.get_secret_value())
        except (ArgumentError, ValueError):
            # La excepcion original incluye la URL (con contrasena): no se encadena.
            raise RuntimeError("DATABASE_URL invalida: revise su formato") from None
        app.state.engine = engine
        if resolved.MIGRAR_HISTORICO_AL_ARRANCAR:
            migracion = crear_migracion_historica(engine, resolved, registro_migracion, predictor)
            app.state.hilo_migracion = lanzar_migracion_en_segundo_plano(
                migracion, registro_migracion
            )
        planificador: PlanificadorReentrenamiento | None = None
        if resolved.REENTRENAMIENTO_AUTOMATICO:
            reloj = clock if clock is not None else SystemClock()
            planificador = PlanificadorReentrenamiento(
                crear_reentrenamiento(engine, resolved, predictor, reloj), reloj
            )
            planificador.iniciar()
        app.state.planificador_reentrenamiento = planificador
        try:
            yield
        finally:
            if planificador is not None:
                planificador.detener()
            engine.dispose()

    app = FastAPI(title="Backend API", debug=resolved.DEBUG, lifespan=lifespan)
    app.state.registro_migracion = registro_migracion
    register_exception_handlers(app)
    # CORS explicito por origen (Settings rechaza '*' y origenes mal formados).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # CU-00: el ultimo middleware anadido es el mas externo; asi el filtro de IP corre antes
    # que CORS y tambien cubre OPTIONS y /docs.
    app.add_middleware(FiltroAccesoIp, redes=resolved.IPS_PERMITIDAS)
    for router in (
        health.router,
        sistema.router,
        cargas.router,
        listas.router,
        campanias.router,
        gestiones.router,
        dashboard.router,
    ):
        app.include_router(router, prefix=API_V1_PREFIX)
    return app


_app: FastAPI | None = None


def __getattr__(name: str) -> FastAPI:
    """``app`` perezosa para ``uvicorn app.main:app``: importar el modulo no exige entorno."""
    global _app
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if _app is None:
        _app = create_app()
    return _app
