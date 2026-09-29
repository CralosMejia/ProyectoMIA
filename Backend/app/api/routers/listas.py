"""Router del modulo listas: lista priorizada y su Excel (CU-04, CU-05, CU-12).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.api.openapi import (
    XLSX_MEDIA_TYPE,
    error_responses,
    raise_not_implemented,
    success_response,
)
from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO

router = APIRouter(prefix="/listas", tags=["listas"])

ListaId = Annotated[int, Path(ge=1, description="Identificador de la lista priorizada.")]

LISTA_PRIORIZADA_EXAMPLE = {
    "id": 42,
    "modelo_version": "v1",
    "fecha_generacion": "2026-09-28T15:20:00Z",
    "horizonte_dias": 30,
    "top_k": 25,
    "umbral_alto": "0.62000000",
    "umbral_medio": "0.35000000",
    "advertencia_datos_antiguos": False,
    "items": [
        {
            "prediccion_id": 1501,
            "prioridad": 1,
            "socio_nombre": "Maria Fernanda Lopez",
            "celular": "0991234567",
            "correo": "maria.lopez@example.com",
            "plan": "MENSUAL",
            "fecha_vencimiento": "2026-10-05",
            "dias_para_vencer": 7,
            "score": "0.81234567",
            "nivel_riesgo": "ALTO",
            "factores_principales": [
                "Pocas renovaciones previas",
                "Plan mensual",
                "Pago en efectivo",
            ],
            "dentro_top_k": True,
            "gestion_estado": None,
            "campania_asignada": None,
        },
        {
            "prediccion_id": 1502,
            "prioridad": 2,
            "socio_nombre": "Carlos Andres Vera",
            "celular": None,
            "correo": None,
            "plan": "TRIMESTRAL",
            "fecha_vencimiento": "2026-10-12",
            "dias_para_vencer": 14,
            "score": "0.47000000",
            "nivel_riesgo": "MEDIO",
            "factores_principales": ["Primer ciclo en el gimnasio"],
            "dentro_top_k": True,
            "gestion_estado": "PENDIENTE",
            "campania_asignada": "Renovacion anticipada",
        },
    ],
}

_NOT_FOUND = {status.HTTP_404_NOT_FOUND: "La lista no existe."}
_GET_ERRORS = error_responses(
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    status.HTTP_501_NOT_IMPLEMENTED,
    descriptions={
        **_NOT_FOUND,
        status.HTTP_400_BAD_REQUEST: "El identificador de la lista no es valido.",
    },
)


@router.post(
    "",
    response_model=ListaPriorizadaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(
            status.HTTP_201_CREATED, "Lista priorizada generada.", LISTA_PRIORIZADA_EXAMPLE
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={
                status.HTTP_409_CONFLICT: "El sistema no esta listo o no hay modelo vigente."
            },
        ),
    },
    summary="Generar la lista priorizada de no renovacion",
)
def post_lista(body: GenerarListaDTO) -> ListaPriorizadaDTO:
    raise_not_implemented()


# Declarada antes de ``/{lista_id}`` para que ``ultima`` no se interprete como id.
@router.get(
    "/ultima",
    response_model=ListaPriorizadaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Ultima lista generada.", LISTA_PRIORIZADA_EXAMPLE),
        **error_responses(
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions={status.HTTP_404_NOT_FOUND: "Aun no se ha generado ninguna lista."},
        ),
    },
    summary="Consultar la ultima lista priorizada",
)
def get_ultima_lista() -> ListaPriorizadaDTO:
    raise_not_implemented()


@router.get(
    "/{lista_id}",
    response_model=ListaPriorizadaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Lista priorizada.", LISTA_PRIORIZADA_EXAMPLE),
        **_GET_ERRORS,
    },
    summary="Consultar una lista priorizada",
)
def get_lista(lista_id: ListaId) -> ListaPriorizadaDTO:
    raise_not_implemented()


@router.get(
    "/{lista_id}/excel",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Libro Excel con la lista priorizada.",
            "content": {XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Content-Disposition": {
                    "description": "Nombre del archivo descargado.",
                    "schema": {"type": "string"},
                    "example": 'attachment; filename="lista-priorizada-42.xlsx"',
                }
            },
        },
        **_GET_ERRORS,
    },
    summary="Descargar la lista priorizada en Excel",
)
def get_lista_excel(lista_id: ListaId) -> Response:
    raise_not_implemented()
