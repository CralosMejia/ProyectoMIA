"""Router del modulo health: estado de salud del servicio (endpoint publico)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_health_query_handler
from app.application.health.dtos import HealthDTO
from app.application.health.queries import GetHealthQueryHandler

router = APIRouter(prefix="/health", tags=["health"])

_OK_EXAMPLE = {"status": "ok", "database": "up", "checked_at": "2026-01-01T00:00:00Z"}
_DEGRADED_EXAMPLE = {
    "status": "degraded",
    "database": "down",
    "checked_at": "2026-01-01T00:00:00Z",
}

_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "El servicio y la base de datos responden.",
        "content": {
            "application/json": {
                "examples": {"ok": {"summary": "Servicio sano", "value": _OK_EXAMPLE}},
            },
        },
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": HealthDTO,
        "description": "La base de datos no responde: servicio degradado.",
        "content": {
            "application/json": {
                "examples": {
                    "degraded": {"summary": "Base de datos caida", "value": _DEGRADED_EXAMPLE},
                },
            },
        },
    },
}


# ``def`` (no ``async``): la sonda de base de datos es bloqueante y FastAPI la ejecuta
# en el threadpool.
@router.get(
    "",
    response_model=HealthDTO,
    status_code=status.HTTP_200_OK,
    responses=_RESPONSES,
    summary="Estado de salud del servicio",
)
def get_health(
    response: Response,
    handler: Annotated[GetHealthQueryHandler, Depends(get_health_query_handler)],
) -> HealthDTO:
    health = handler.handle()
    if health.database == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health
