"""Composition root: crea la aplicacion FastAPI.

No crea tablas ni ejecuta migraciones al arrancar: el esquema lo gestiona Alembic
como paso separado del despliegue.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import ArgumentError

from app.api.errors import register_exception_handlers
from app.api.routers import campanias, cargas, dashboard, gestiones, health, listas, sistema
from app.core.config import Settings
from app.infrastructure.persistence.database import create_database_engine

logger = logging.getLogger(__name__)

API_V1_PREFIX = "/api/v1"


def _load_settings() -> Settings:
    """Carga y valida la configuracion; falla rapido sin exponer valores en el log."""
    try:
        return Settings()  # valores desde variables de entorno
    except ValidationError as exc:
        # str(exc) nombra la variable y el tipo de error; hide_input_in_errors oculta el valor.
        logger.error("configuracion invalida: %s", str(exc))
        raise


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye la aplicacion. ``settings`` explicitas solo para pruebas."""
    resolved = settings if settings is not None else _load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # El secreto solo se desenvuelve aqui, en el composition root.
        try:
            engine = create_database_engine(resolved.DATABASE_URL.get_secret_value())
        except (ArgumentError, ValueError):
            # La excepcion original incluye la URL (con contrasena): no se encadena.
            raise RuntimeError("DATABASE_URL invalida: revise su formato") from None
        app.state.engine = engine
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Backend API", debug=resolved.DEBUG, lifespan=lifespan)
    register_exception_handlers(app)
    # CORS explicito por origen (Settings rechaza '*' y origenes mal formados).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.CORS_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
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
