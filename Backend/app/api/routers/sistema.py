"""Router del modulo sistema: estado general para la pantalla de inicio (CU-03)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_consultar_estado_sistema
from app.api.openapi import OpenApiResponses, error_responses
from app.application.sistema.consultar_estado import ConsultarEstadoSistema
from app.application.sistema.dtos import EstadoSistemaDTO

router = APIRouter(prefix="/sistema", tags=["sistema"])

ESTADO_SISTEMA_EXAMPLE = {
    "estado": "LISTO",
    "migracion_historica": "COMPLETADA",
    "modelo_vigente": {
        "version": "v1",
        "fecha_entrenamiento": "2026-09-29T14:30:00Z",
        "ciclos_entrenamiento": 1564,
    },
    "ultima_carga_en": "2026-09-29T14:30:00Z",
    "proxima_fecha_reentrenamiento": "2027-03-29",
    "datos_mes_cargados": True,
}
ESTADO_SIN_DATOS_MES_EXAMPLE = {**ESTADO_SISTEMA_EXAMPLE, "datos_mes_cargados": False}
ESTADO_INICIALIZANDO_EXAMPLE = {
    "estado": "INICIALIZANDO",
    "migracion_historica": "EN_CURSO",
    "modelo_vigente": None,
    "ultima_carga_en": None,
    "proxima_fecha_reentrenamiento": None,
    "datos_mes_cargados": None,
}
ESTADO_FALTAN_DATOS_EXAMPLE = {
    "estado": "FALTAN_DATOS_HISTORICOS",
    "migracion_historica": "PENDIENTE",
    "modelo_vigente": None,
    "ultima_carga_en": None,
    "proxima_fecha_reentrenamiento": None,
    "datos_mes_cargados": None,
}

_ESTADO_RESPONSES: OpenApiResponses = {
    status.HTTP_200_OK: {
        "description": (
            "Estado actual del sistema: INICIALIZANDO mientras migra el historico, "
            "FALTAN_DATOS_HISTORICOS si no se pudieron migrar los libros, LISTO al terminar. "
            "``datos_mes_cargados``: si ya hay una carga de plantilla en el mes actual (fecha "
            "de Ecuador; la migracion historica no cuenta); nulo si el sistema no esta LISTO."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "listo": {"summary": "Sistema listo", "value": ESTADO_SISTEMA_EXAMPLE},
                    "sin_datos_del_mes": {
                        "summary": "Listo, sin datos cargados este mes",
                        "value": ESTADO_SIN_DATOS_MES_EXAMPLE,
                    },
                    "inicializando": {
                        "summary": "Migrando el historico",
                        "value": ESTADO_INICIALIZANDO_EXAMPLE,
                    },
                    "faltan_datos": {
                        "summary": "Faltan los datos historicos",
                        "value": ESTADO_FALTAN_DATOS_EXAMPLE,
                    },
                }
            }
        },
    }
}


@router.get(
    "/estado",
    response_model=EstadoSistemaDTO,
    status_code=status.HTTP_200_OK,
    responses={**_ESTADO_RESPONSES, **error_responses(status.HTTP_403_FORBIDDEN)},
    summary="Estado del sistema (inicializando, faltan datos historicos o listo)",
)
def get_estado_sistema(
    consulta: Annotated[ConsultarEstadoSistema, Depends(get_consultar_estado_sistema)],
) -> EstadoSistemaDTO:
    return consulta.ejecutar()
