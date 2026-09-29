"""Router del modulo gestiones: asignacion (CU-08), alertas (CU-09) y resultado (CU-10).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.openapi import error_responses, raise_not_implemented, success_response
from app.application.gestiones.dtos import (
    AlertasDTO,
    CrearGestionDTO,
    FiltroGestiones,
    GestionDTO,
    GestionResumenDTO,
    RegistrarResultadoDTO,
)

router = APIRouter(tags=["gestiones"])

GestionId = Annotated[int, Path(ge=1, description="Identificador de la gestion.")]

GESTION_EXAMPLE = {
    "id": 9,
    "prediccion_id": 1501,
    "socio_nombre": "Maria Fernanda Lopez",
    "plan": "MENSUAL",
    "fecha_vencimiento": "2026-10-05",
    "modelo_version": "v1",
    "score": "0.81234567",
    "nivel_riesgo": "ALTO",
    "campania_id": 3,
    "campania_nombre": "Renovacion anticipada",
    "estado": "PENDIENTE",
    "fecha_asignacion": "2026-09-28T15:30:00Z",
    "fecha_seguimiento": "2026-10-30",
    "responsable": "Andrea",
    "contactado": None,
    "campania_ofrecida": None,
    "campania_aceptada": None,
    "renovo_declarado": None,
    "fecha_contacto": None,
    "observaciones": None,
    "fecha_cierre": None,
}
GESTION_CON_RESULTADO_EXAMPLE = {
    **GESTION_EXAMPLE,
    "contactado": True,
    "campania_ofrecida": "SI",
    "campania_aceptada": "SI",
    "renovo_declarado": "PENDIENTE",
    "fecha_contacto": "2026-10-20",
    "observaciones": "Acepta el descuento; renovara la proxima semana.",
    "fecha_seguimiento": "2026-10-27",
}
GESTIONES_RESUMEN_EXAMPLE = [
    {
        "id": 9,
        "socio_nombre": "Maria Fernanda Lopez",
        "celular": "0991234567",
        "plan": "MENSUAL",
        "fecha_vencimiento": "2026-10-05",
        "fecha_seguimiento": "2026-09-28",
        "nivel_riesgo": "ALTO",
        "campania_nombre": "Renovacion anticipada",
        "responsable": "Andrea",
        "estado": "PENDIENTE",
    }
]
ALERTAS_EXAMPLE = {"vencidas": 2, "hoy": 1, "proximos_7_dias": 5}

_BAD_ID = "El identificador de la gestion no es valido."
_GESTION_NO_EXISTE = "La gestion no existe."


@router.post(
    "/gestiones",
    response_model=GestionDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(status.HTTP_201_CREATED, "Gestion creada.", GESTION_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_409_CONFLICT,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_404_NOT_FOUND: "La prediccion o la campana no existen.",
                status.HTTP_409_CONFLICT: "El ciclo de membresia ya tiene una gestion.",
                status.HTTP_422_UNPROCESSABLE_CONTENT: (
                    "La fecha de seguimiento esta fuera del rango de hoy al vencimiento + 30 dias."
                ),
            },
        ),
    },
    summary="Asignar campana y crear el seguimiento",
)
def post_gestion(body: CrearGestionDTO) -> GestionDTO:
    raise_not_implemented()


@router.get(
    "/gestiones",
    response_model=list[GestionResumenDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Gestiones pendientes del grupo.", GESTIONES_RESUMEN_EXAMPLE
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={status.HTTP_400_BAD_REQUEST: "Filtro ausente o no permitido."},
        ),
    },
    summary="Listar gestiones pendientes por grupo de alerta",
)
def get_gestiones(
    filtro: Annotated[
        FiltroGestiones,
        Query(description="Grupo de alerta: vencidas, hoy o proximas (7 dias)."),
    ],
) -> list[GestionResumenDTO]:
    raise_not_implemented()


@router.get(
    "/gestiones/{gestion_id}",
    response_model=GestionDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Gestion.", GESTION_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_400_BAD_REQUEST: _BAD_ID,
                status.HTTP_404_NOT_FOUND: _GESTION_NO_EXISTE,
            },
        ),
    },
    summary="Consultar una gestion",
)
def get_gestion(gestion_id: GestionId) -> GestionDTO:
    raise_not_implemented()


@router.put(
    "/gestiones/{gestion_id}/resultado",
    response_model=GestionDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Resultado registrado.", GESTION_CON_RESULTADO_EXAMPLE
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_409_CONFLICT,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_404_NOT_FOUND: _GESTION_NO_EXISTE,
                status.HTTP_409_CONFLICT: "La gestion esta cerrada y no se puede modificar.",
                status.HTTP_422_UNPROCESSABLE_CONTENT: (
                    "Respuestas incoherentes o fecha de seguimiento fuera de rango."
                ),
            },
        ),
    },
    summary="Registrar el resultado del seguimiento",
)
def put_resultado_gestion(gestion_id: GestionId, body: RegistrarResultadoDTO) -> GestionDTO:
    raise_not_implemented()


@router.get(
    "/alertas",
    response_model=AlertasDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Contadores de gestiones pendientes.", ALERTAS_EXAMPLE
        ),
        **error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_501_NOT_IMPLEMENTED),
    },
    summary="Alertas de seguimiento",
)
def get_alertas() -> AlertasDTO:
    raise_not_implemented()
