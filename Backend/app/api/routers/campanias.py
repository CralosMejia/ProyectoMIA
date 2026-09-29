"""Router del modulo campanias: parametrizacion (CU-06) y sugerencias por socio (CU-07).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma. No existe
``DELETE``: una campana se inactiva, nunca se borra.
"""

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.openapi import error_responses, raise_not_implemented, success_response
from app.application.campanias.dtos import CampaniaDTO, CampaniaEntradaDTO

router = APIRouter(tags=["campanias"])

CampaniaId = Annotated[int, Path(ge=1, description="Identificador de la campana.")]
PrediccionId = Annotated[int, Path(ge=1, description="Identificador de la prediccion.")]

CAMPANIA_EXAMPLE = {
    "id": 3,
    "nombre": "Renovacion anticipada",
    "descripcion": "10% de descuento si renueva antes del vencimiento.",
    "activa": True,
    "niveles_riesgo": ["ALTO", "MEDIO"],
    "planes": ["MENSUAL", "TRIMESTRAL"],
    "prioridad": 1,
    "es_ejemplo": True,
}
CAMPANIA_INACTIVA_EXAMPLE = {**CAMPANIA_EXAMPLE, "activa": False}
CAMPANIAS_EXAMPLE = [
    CAMPANIA_EXAMPLE,
    {
        "id": 4,
        "nombre": "Clase personalizada de regalo",
        "descripcion": "Una sesion con entrenador al renovar el plan.",
        "activa": True,
        "niveles_riesgo": ["BAJO"],
        "planes": ["SEMESTRAL", "ANUAL", "OTRO"],
        "prioridad": 2,
        "es_ejemplo": False,
    },
]

_BAD_ID = "El identificador no es valido."
_CAMPANIA_NO_EXISTE = "La campana no existe."


@router.get(
    "/campanias",
    response_model=list[CampaniaDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Campanas activas e inactivas por prioridad.", CAMPANIAS_EXAMPLE
        ),
        **error_responses(status.HTTP_403_FORBIDDEN, status.HTTP_501_NOT_IMPLEMENTED),
    },
    summary="Listar campanas",
)
def get_campanias() -> list[CampaniaDTO]:
    raise_not_implemented()


@router.post(
    "/campanias",
    response_model=CampaniaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(status.HTTP_201_CREATED, "Campana creada.", CAMPANIA_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_501_NOT_IMPLEMENTED
        ),
    },
    summary="Crear una campana",
)
def post_campania(body: CampaniaEntradaDTO) -> CampaniaDTO:
    raise_not_implemented()


@router.put(
    "/campanias/{campania_id}",
    response_model=CampaniaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Campana actualizada.", CAMPANIA_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={status.HTTP_404_NOT_FOUND: _CAMPANIA_NO_EXISTE},
        ),
    },
    summary="Editar una campana",
)
def put_campania(campania_id: CampaniaId, body: CampaniaEntradaDTO) -> CampaniaDTO:
    raise_not_implemented()


@router.post(
    "/campanias/{campania_id}/inactivar",
    response_model=CampaniaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Campana inactivada.", CAMPANIA_INACTIVA_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_400_BAD_REQUEST: _BAD_ID,
                status.HTTP_404_NOT_FOUND: _CAMPANIA_NO_EXISTE,
            },
        ),
    },
    summary="Inactivar una campana",
)
def post_inactivar_campania(campania_id: CampaniaId) -> CampaniaDTO:
    raise_not_implemented()


@router.get(
    "/predicciones/{prediccion_id}/campanias-sugeridas",
    response_model=list[CampaniaDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Campanas activas compatibles con el nivel y el plan del socio, por prioridad.",
            [CAMPANIA_EXAMPLE],
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_400_BAD_REQUEST: _BAD_ID,
                status.HTTP_404_NOT_FOUND: "La prediccion no existe.",
            },
        ),
    },
    summary="Campanas sugeridas para un socio de la lista",
)
def get_campanias_sugeridas(prediccion_id: PrediccionId) -> list[CampaniaDTO]:
    raise_not_implemented()
