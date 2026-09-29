"""Router del modulo cargas: vista previa y confirmacion de la plantilla (CU-01).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma. La confirmacion
vuelve a validar el archivo en el servidor: no hay estado entre vista previa y confirmacion.
"""

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.api.openapi import error_responses, raise_not_implemented, success_response
from app.application.cargas.dtos import CargaDTO, VistaPreviaCargaDTO

router = APIRouter(prefix="/cargas", tags=["cargas"])

ArchivoPlantilla = Annotated[
    UploadFile, File(description="Plantilla oficial .xlsx; solo se lee la hoja Registros.")
]

VISTA_PREVIA_EXAMPLE = {
    "filas_leidas": 120,
    "filas_validas": 117,
    "filas_con_error": 1,
    "filas_duplicadas": 2,
    "vencimiento_desde": "2026-10-01",
    "vencimiento_hasta": "2027-09-30",
    "errores": [
        {"fila": 14, "columna": "C", "motivo": "La cedula no tiene un digito verificador valido."}
    ],
    "puede_confirmar": False,
}

CARGA_EXAMPLE = {
    "id": 8,
    "fecha_carga": "2026-09-28T15:10:00Z",
    "nombre_archivo": "plantilla-septiembre.xlsx",
    "filas_leidas": 120,
    "filas_guardadas": 118,
    "filas_duplicadas": 2,
    "socios_enlazados": 35,
    "avisos_enlace": [
        "Fila 22: hay varios socios historicos con el mismo nombre; se creo un socio nuevo."
    ],
}

_ERROR_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: (
        "Archivo no .xlsx, sin hoja Registros, con titulos distintos, con mas de 500 filas "
        "con datos o sin el campo archivo."
    ),
    status.HTTP_409_CONFLICT: "La migracion del historico aun no se ha completado.",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Hay filas con error; no se puede confirmar.",
}


@router.post(
    "/vista-previa",
    response_model=VistaPreviaCargaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Resultado de la validacion, sin guardar.", VISTA_PREVIA_EXAMPLE
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
            status.HTTP_413_CONTENT_TOO_LARGE,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions=_ERROR_DESCRIPTIONS,
        ),
    },
    summary="Validar una plantilla y ver la vista previa",
)
def post_vista_previa(archivo: ArchivoPlantilla) -> VistaPreviaCargaDTO:
    raise_not_implemented()


@router.post(
    "",
    response_model=CargaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(status.HTTP_201_CREATED, "Carga guardada.", CARGA_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
            status.HTTP_413_CONTENT_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            status.HTTP_501_NOT_IMPLEMENTED,
            descriptions=_ERROR_DESCRIPTIONS,
        ),
    },
    summary="Confirmar y guardar una plantilla",
)
def post_carga(archivo: ArchivoPlantilla) -> CargaDTO:
    raise_not_implemented()
