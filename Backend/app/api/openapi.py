"""Piezas comunes del contrato OpenAPI: formato unico de error, ejemplos y ``501``.

Los routers declaran sus respuestas con estas funciones para que ``/openapi.json`` sea el
spec publico, con un ejemplo real por cada codigo de estado.
"""

from collections.abc import Mapping
from typing import Any, NoReturn

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.errors import (
    DOMAIN_ERROR_MESSAGE,
    HTTP_ERRORS,
    VALIDATION_ERROR_MESSAGE,
    error_body,
)

OpenApiResponses = dict[int | str, dict[str, Any]]

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ErrorDetailDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class ErrorResponseDTO(BaseModel):
    """Formato unico de error: ``{"error": {"code", "message"}}``."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetailDTO


_DESCRIPTIONS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Entrada invalida.",
    status.HTTP_403_FORBIDDEN: "Acceso no permitido desde este equipo.",
    status.HTTP_404_NOT_FOUND: "El recurso no existe.",
    status.HTTP_409_CONFLICT: "Conflicto con el estado actual del sistema.",
    status.HTTP_413_CONTENT_TOO_LARGE: "El archivo supera el tamano maximo permitido.",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "La operacion viola una regla de negocio.",
    status.HTTP_501_NOT_IMPLEMENTED: "La funcion aun no esta implementada.",
}

# Codigos cuyo ``code`` no sale del catalogo HTTP sino de un manejador especifico.
_SPECIAL_CODES: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: ("validation_error", VALIDATION_ERROR_MESSAGE),
    status.HTTP_422_UNPROCESSABLE_CONTENT: ("domain_rule_violated", DOMAIN_ERROR_MESSAGE),
}


def _error_code_and_message(status_code: int) -> tuple[str, str]:
    if status_code not in _DESCRIPTIONS:
        raise ValueError(f"codigo de error sin entrada en el catalogo OpenAPI: {status_code}")
    special = _SPECIAL_CODES.get(status_code)
    return special if special else HTTP_ERRORS[status_code]


def error_responses(
    *codes: int,
    descriptions: Mapping[int, str] | None = None,
) -> OpenApiResponses:
    """Entradas ``responses`` con el modelo de error y un ejemplo por codigo.

    ``descriptions`` sustituye la descripcion generica para explicar cuando ocurre el
    error en esa operacion concreta.
    """
    custom = descriptions or {}
    responses: OpenApiResponses = {}
    for status_code in codes:
        code, message = _error_code_and_message(status_code)
        responses[status_code] = {
            "model": ErrorResponseDTO,
            "description": custom.get(status_code, _DESCRIPTIONS[status_code]),
            "content": {"application/json": {"example": error_body(code, message)}},
        }
    return responses


def success_response(status_code: int, description: str, example: object) -> OpenApiResponses:
    """Entrada ``responses`` de la respuesta de exito con su ejemplo JSON."""
    return {
        status_code: {
            "description": description,
            "content": {"application/json": {"example": example}},
        }
    }


def raise_not_implemented() -> NoReturn:
    """Respuesta ``501`` en el formato unico (contrato publicado, logica pendiente)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED)
