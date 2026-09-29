"""Router del modulo sistema: estado general para la pantalla de inicio (CU-03).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma.
"""

from fastapi import APIRouter, status

from app.api.openapi import error_responses, raise_not_implemented, success_response
from app.application.sistema.dtos import EstadoSistemaDTO

router = APIRouter(prefix="/sistema", tags=["sistema"])

ESTADO_SISTEMA_EXAMPLE = {
    "estado": "LISTO",
    "migracion_historica": "COMPLETADA",
    "modelo_vigente": {
        "version": "v1",
        "fecha_entrenamiento": "2026-09-28T14:30:00Z",
        "ciclos_entrenamiento": 1843,
    },
    "ultima_carga_en": "2026-09-27T16:05:00Z",
    "proxima_fecha_reentrenamiento": "2026-10-28",
}


@router.get(
    "/estado",
    response_model=EstadoSistemaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Estado actual del sistema.", ESTADO_SISTEMA_EXAMPLE
        ),
        **error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_501_NOT_IMPLEMENTED),
    },
    summary="Estado del sistema (inicializando, faltan datos historicos o listo)",
)
def get_estado_sistema() -> EstadoSistemaDTO:
    raise_not_implemented()
