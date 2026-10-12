"""Manejadores globales de error: formato unico ``{"error": {"code", "message"}}``.

El detalle tecnico se registra en el servidor; al cliente solo llega un mensaje seguro,
sin tracebacks, SQL ni rutas del sistema.
"""

import json
import logging
from http import HTTPStatus
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.domain.common.exceptions import DomainError

logger = logging.getLogger(__name__)

VALIDATION_ERROR_MESSAGE = "La solicitud contiene datos invalidos o incompletos."
INTERNAL_ERROR_MESSAGE = "Ocurrio un error inesperado. Intentalo de nuevo mas tarde."
DOMAIN_ERROR_MESSAGE = "La operacion viola una regla de negocio."

PAYLOAD_TOO_LARGE_MESSAGE = "El archivo supera el tamano maximo permitido."
NOT_IMPLEMENTED_MESSAGE = "Esta funcion aun no esta disponible."

HTTP_ERRORS: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: ("bad_request", "La solicitud no es valida."),
    status.HTTP_401_UNAUTHORIZED: ("unauthorized", "Debes iniciar sesion para continuar."),
    status.HTTP_403_FORBIDDEN: ("forbidden", "El acceso no esta permitido desde este equipo."),
    status.HTTP_404_NOT_FOUND: ("not_found", "El recurso solicitado no existe."),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        "method_not_allowed",
        "El metodo HTTP no esta permitido para este recurso.",
    ),
    status.HTTP_409_CONFLICT: ("conflict", "La operacion entra en conflicto con el estado actual."),
    status.HTTP_413_CONTENT_TOO_LARGE: ("payload_too_large", PAYLOAD_TOO_LARGE_MESSAGE),
    status.HTTP_501_NOT_IMPLEMENTED: ("not_implemented", NOT_IMPLEMENTED_MESSAGE),
}


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    """Cuerpo del formato unico de error."""
    return {"error": {"code": code, "message": message}}


def _http_error_code_and_message(exc: StarletteHTTPException) -> tuple[str, str]:
    known = HTTP_ERRORS.get(exc.status_code)
    try:
        phrase = HTTPStatus(exc.status_code).phrase
    except ValueError:
        phrase = "Error"
    default_code = phrase.lower().replace(" ", "_").replace("-", "_")
    code, default_message = known if known else (default_code, phrase)
    # Un detalle explicito del codigo propio es un mensaje para el usuario; el de
    # Starlette por defecto (la frase HTTP en ingles) se sustituye por el nuestro.
    custom = isinstance(exc.detail, str) and exc.detail and exc.detail != phrase
    message = exc.detail if custom else default_message
    return code, message


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    code, message = _http_error_code_and_message(http_exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=error_body(code, message),
        headers=http_exc.headers,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    fields = [".".join(str(part) for part in err.get("loc", ())) for err in errors]
    logger.info("validacion de entrada fallida en %s: campos=%s", request.url.path, fields)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_body("validation_error", VALIDATION_ERROR_MESSAGE),
    )


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_body("domain_rule_violated", str(exc) or DOMAIN_ERROR_MESSAGE),
    )


def _registrar_no_controlado(metodo: str, ruta: str, exc: BaseException) -> None:
    # S6 (R-013): solo el tipo; el mensaje y la traza pueden llevar SQL con el DETAIL de
    # PostgreSQL (valores de socios) o rutas del sistema.
    logger.error("error no controlado en %s %s (%s)", metodo, ruta, type(exc).__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _registrar_no_controlado(request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body("internal_error", INTERNAL_ERROR_MESSAGE),
    )


_CUERPO_500 = json.dumps(error_body("internal_error", INTERNAL_ERROR_MESSAGE)).encode("utf-8")


class CapturaErroresNoControlados:
    """Middleware ASGI: convierte una excepcion no controlada en ``500`` sin re-lanzarla.

    El manejador de ``Exception`` de Starlette re-lanza la excepcion tras responder y el
    servidor (uvicorn) la registra con la traza completa; este middleware la detiene antes.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        iniciada = False

        async def enviar(mensaje: Message) -> None:
            nonlocal iniciada
            if mensaje["type"] == "http.response.start":
                iniciada = True
            await send(mensaje)

        try:
            await self._app(scope, receive, enviar)
        except Exception as exc:
            _registrar_no_controlado(scope.get("method", ""), scope.get("path", ""), exc)
            if iniciada:
                return  # la respuesta ya empezo: solo queda cerrar la conexion
            await send(
                {
                    "type": "http.response.start",
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(_CUERPO_500)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": _CUERPO_500})


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores globales en la aplicacion."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(DomainError, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
