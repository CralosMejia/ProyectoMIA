"""Router del modulo cargas: vista previa y confirmacion de la plantilla (CU-01).

La confirmacion vuelve a validar el archivo en el servidor: no hay estado entre vista previa y
confirmacion. Mapeo de errores (decision (k) de R-007):

- archivo no ``.xlsx`` o danado, sin hoja ``Registros``, titulos distintos, formato antiguo,
  mas de 500 filas o sin el campo ``archivo`` -> ``400 validation_error``;
- mas de 5 MB -> ``413 payload_too_large``;
- migracion historica no ``COMPLETADA`` -> ``409 conflict``;
- confirmar con filas con error o sin filas nuevas -> ``422 domain_rule_violated`` (manejador
  global de ``DomainError``).

Del archivo se leen como maximo 5 MB + 1 byte; los mensajes nunca incluyen valores de celdas.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_confirmar_carga, get_previsualizar_carga
from app.api.errors import error_body
from app.api.openapi import error_responses, success_response
from app.application.cargas.dtos import CargaDTO, VistaPreviaCargaDTO
from app.application.cargas.procesar_carga import (
    MENSAJE_CON_ERRORES,
    MENSAJE_MIGRACION_NO_COMPLETADA,
    ConfirmarCarga,
    MigracionNoCompletadaError,
    PrevisualizarCarga,
)
from app.domain.cargas.errores import MENSAJES, MotivoPlantillaInvalida, PlantillaInvalidaError

router = APIRouter(prefix="/cargas", tags=["cargas"])

MAX_BYTES_PLANTILLA = 5 * 1024 * 1024
"""Tamano maximo de la plantilla (5 MB, decision (g))."""

MENSAJE_ARCHIVO_GRANDE = "El archivo supera el tamaño máximo permitido."

ArchivoPlantilla = Annotated[
    UploadFile, File(description="Plantilla oficial .xlsx; solo se lee la hoja Registros.")
]
Previsualizador = Annotated[PrevisualizarCarga, Depends(get_previsualizar_carga)]
Confirmador = Annotated[ConfirmarCarga, Depends(get_confirmar_carga)]

VISTA_PREVIA_EXAMPLE = {
    "filas_leidas": 120,
    "filas_validas": 117,
    "filas_con_error": 1,
    "filas_duplicadas": 2,
    "vencimiento_desde": "2026-10-01",
    "vencimiento_hasta": "2027-09-30",
    "errores": [
        {"fila": 14, "columna": "C", "motivo": "La cédula no tiene un dígito verificador válido."}
    ],
    "puede_confirmar": False,
}

CARGA_EXAMPLE = {
    "id": 8,
    "fecha_carga": "2026-09-29T15:10:00Z",
    "nombre_archivo": "plantilla-septiembre.xlsx",
    "filas_leidas": 120,
    "filas_guardadas": 118,
    "filas_duplicadas": 2,
    "socios_enlazados": 35,
    "avisos_enlace": [
        "Fila 22: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."
    ],
}

_ERROR_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: (
        "Archivo no .xlsx o dañado, sin hoja Registros, con titulos distintos, con el formato "
        "antiguo de hojas mensuales, con mas de 500 filas con datos o sin el campo archivo."
    ),
    status.HTTP_409_CONFLICT: MENSAJE_MIGRACION_NO_COMPLETADA,
    status.HTTP_413_CONTENT_TOO_LARGE: "El archivo supera 5 MB.",
    status.HTTP_422_UNPROCESSABLE_CONTENT: (
        "Hay filas con error o el archivo no tiene filas nuevas; no se puede confirmar."
    ),
}


def _con_mensaje(responses: dict[int | str, dict[str, Any]], code: int, message: str) -> None:
    """Sustituye el ejemplo generico de ``code`` por el mensaje real de la operacion."""
    ejemplo = responses[code]["content"]["application/json"]
    ejemplo["example"] = {"error": {**ejemplo["example"]["error"], "message": message}}


def _errores(*codes: int) -> dict[int | str, dict[str, Any]]:
    responses = error_responses(*codes, descriptions=_ERROR_DESCRIPTIONS)
    _con_mensaje(
        responses,
        status.HTTP_400_BAD_REQUEST,
        MENSAJES[MotivoPlantillaInvalida.SIN_REGISTROS],
    )
    _con_mensaje(responses, status.HTTP_409_CONFLICT, MENSAJE_MIGRACION_NO_COMPLETADA)
    _con_mensaje(responses, status.HTTP_413_CONTENT_TOO_LARGE, MENSAJE_ARCHIVO_GRANDE)
    if status.HTTP_422_UNPROCESSABLE_CONTENT in responses:
        _con_mensaje(responses, status.HTTP_422_UNPROCESSABLE_CONTENT, MENSAJE_CON_ERRORES)
    return responses


def _leer_acotado(archivo: UploadFile) -> bytes:
    """Lee como maximo 5 MB + 1 byte; si hay mas -> ``413``."""
    contenido = archivo.file.read(MAX_BYTES_PLANTILLA + 1)
    if len(contenido) > MAX_BYTES_PLANTILLA:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=MENSAJE_ARCHIVO_GRANDE
        )
    return contenido


def _plantilla_invalida(exc: PlantillaInvalidaError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_body("validation_error", str(exc)),
    )


def _migracion_no_completada() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail=MENSAJE_MIGRACION_NO_COMPLETADA
    )


@router.post(
    "/vista-previa",
    response_model=VistaPreviaCargaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Resultado de la validacion, sin guardar.", VISTA_PREVIA_EXAMPLE
        ),
        **_errores(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
            status.HTTP_413_CONTENT_TOO_LARGE,
        ),
    },
    summary="Validar una plantilla y ver la vista previa",
)
def post_vista_previa(
    archivo: ArchivoPlantilla, previsualizar: Previsualizador
) -> VistaPreviaCargaDTO | JSONResponse:
    contenido = _leer_acotado(archivo)
    try:
        return previsualizar.ejecutar(contenido)
    except PlantillaInvalidaError as exc:
        return _plantilla_invalida(exc)
    except MigracionNoCompletadaError:
        raise _migracion_no_completada() from None


@router.post(
    "",
    response_model=CargaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(status.HTTP_201_CREATED, "Carga guardada.", CARGA_EXAMPLE),
        **_errores(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_409_CONFLICT,
            status.HTTP_413_CONTENT_TOO_LARGE,
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        ),
    },
    summary="Confirmar y guardar una plantilla",
)
def post_carga(archivo: ArchivoPlantilla, confirmar: Confirmador) -> CargaDTO | JSONResponse:
    contenido = _leer_acotado(archivo)
    try:
        return confirmar.ejecutar(contenido, archivo.filename)
    except PlantillaInvalidaError as exc:
        return _plantilla_invalida(exc)
    except MigracionNoCompletadaError:
        raise _migracion_no_completada() from None
