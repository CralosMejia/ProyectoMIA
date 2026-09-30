"""Router del modulo campanias: parametrizacion (CU-06) y sugerencias por socio (CU-07).

Solo HTTP: valida la entrada, delega en los casos de uso y traduce sus errores a codigos de
estado (``404`` si la campana o la prediccion no existen; ``400 validation_error`` si los
datos pasan el DTO pero no las reglas de la campana). No existe ``DELETE``: una campana se
inactiva, nunca se borra.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from fastapi.exceptions import RequestValidationError

from app.api.dependencies import (
    get_crear_campania,
    get_editar_campania,
    get_inactivar_campania,
    get_listar_campanias,
    get_sugerir_campanias,
)
from app.api.openapi import OpenApiResponses, error_responses, success_response
from app.application.campanias.dtos import CampaniaDTO, CampaniaEntradaDTO
from app.application.campanias.gestionar_campanias import (
    MENSAJE_CAMPANIA_NO_EXISTE,
    CampaniaNoExisteError,
    CrearCampania,
    EditarCampania,
    InactivarCampania,
    ListarCampanias,
)
from app.application.campanias.sugerir_campanias import (
    MENSAJE_PREDICCION_NO_EXISTE,
    PrediccionNoExisteError,
    SugerirCampanias,
)
from app.domain.campanias.campania import CampaniaInvalidaError

router = APIRouter(tags=["campanias"])

CampaniaId = Annotated[int, Path(ge=1, description="Identificador de la campana.")]
PrediccionId = Annotated[int, Path(ge=1, description="Identificador de la prediccion.")]

_TODOS_LOS_PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]
CAMPANIA_LLAMADA_EXAMPLE: dict[str, Any] = {
    "id": 1,
    "nombre": "Ejemplo: Llamada personal antes del vencimiento",
    "descripcion": "Llamar al socio antes de que venza su plan para recordarle sus avances y "
    "resolver dudas.",
    "activa": True,
    "niveles_riesgo": ["ALTO"],
    "planes": _TODOS_LOS_PLANES,
    "prioridad": 1,
    "es_ejemplo": True,
}
CAMPANIA_EXAMPLE: dict[str, Any] = {
    "id": 2,
    "nombre": "Ejemplo: Renovación anticipada",
    "descripcion": "Ofrecer renovar antes del vencimiento con el beneficio que Mtabolic defina.",
    "activa": True,
    "niveles_riesgo": ["ALTO", "MEDIO"],
    "planes": ["MENSUAL", "TRIMESTRAL"],
    "prioridad": 2,
    "es_ejemplo": True,
}
CAMPANIA_RECORDATORIO_EXAMPLE: dict[str, Any] = {
    "id": 3,
    "nombre": "Ejemplo: Recordatorio de renovación",
    "descripcion": "Enviar un recordatorio amable de la fecha de vencimiento.",
    "activa": True,
    "niveles_riesgo": ["MEDIO", "BAJO"],
    "planes": _TODOS_LOS_PLANES,
    "prioridad": 3,
    "es_ejemplo": True,
}
CAMPANIA_CREADA_EXAMPLE: dict[str, Any] = {
    "id": 4,
    "nombre": "Clase personalizada de regalo",
    "descripcion": "Una sesion con entrenador al renovar el plan.",
    "activa": True,
    "niveles_riesgo": ["ALTO", "MEDIO"],
    "planes": ["SEMESTRAL", "ANUAL"],
    "prioridad": 4,
    "es_ejemplo": False,
}
CAMPANIA_INACTIVA_EXAMPLE: dict[str, Any] = {**CAMPANIA_EXAMPLE, "activa": False}
CAMPANIAS_EXAMPLE = [
    CAMPANIA_LLAMADA_EXAMPLE,
    CAMPANIA_EXAMPLE,
    CAMPANIA_RECORDATORIO_EXAMPLE,
    CAMPANIA_CREADA_EXAMPLE,
]
SUGERIDAS_EXAMPLE = [CAMPANIA_LLAMADA_EXAMPLE, CAMPANIA_EXAMPLE]

CAMPANIA_REQUEST_EXAMPLES: dict[str, Any] = {
    "campania": {
        "summary": "Campana valida",
        "description": "Nombre y descripcion se recortan; niveles y planes repetidos se guardan "
        "una sola vez, en orden canonico. Prioridad 1..999 (1 es la mas prioritaria).",
        "value": {
            "nombre": "Clase personalizada de regalo",
            "descripcion": "Una sesion con entrenador al renovar el plan.",
            "niveles_riesgo": ["ALTO", "MEDIO"],
            "planes": ["SEMESTRAL", "ANUAL"],
            "prioridad": 4,
        },
    },
    "invalida": {
        "summary": "Datos invalidos (400)",
        "description": "Nombre vacio, sin niveles, plan DIARIO, prioridad fuera de 1..999 o un "
        "campo extra -> 400 validation_error; no se guarda nada.",
        "value": {"nombre": "   ", "niveles_riesgo": [], "planes": ["DIARIO"], "prioridad": 0},
    },
}

_BAD_ID = "El identificador no es valido."
_BAD_BODY = (
    "Datos invalidos: nombre vacio o de mas de 120 caracteres, descripcion de mas de 500, "
    "sin niveles o sin planes, plan DIARIO, prioridad fuera de 1..999, campo extra o "
    "identificador no valido."
)


def _con_mensaje(responses: OpenApiResponses, code: int, message: str) -> OpenApiResponses:
    """Sustituye el ejemplo generico de ``code`` por el mensaje real de la operacion."""
    ejemplo = responses[code]["content"]["application/json"]
    ejemplo["example"] = {"error": {**ejemplo["example"]["error"], "message": message}}
    return responses


def _errores_con_id(mensaje_404: str, descripcion_400: str) -> OpenApiResponses:
    return _con_mensaje(
        error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            descriptions={
                status.HTTP_400_BAD_REQUEST: descripcion_400,
                status.HTTP_404_NOT_FOUND: mensaje_404,
            },
        ),
        status.HTTP_404_NOT_FOUND,
        mensaje_404,
    )


def _no_existe(mensaje: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensaje)


def _entrada_invalida(exc: CampaniaInvalidaError) -> RequestValidationError:
    """Reglas de la campana que el DTO no cubre: mismo ``400 validation_error``."""
    return RequestValidationError(
        [{"loc": ("body",), "msg": str(exc), "type": "value_error", "input": None}]
    )


Entrada = Annotated[CampaniaEntradaDTO, Body(openapi_examples=CAMPANIA_REQUEST_EXAMPLES)]


@router.get(
    "/campanias",
    response_model=list[CampaniaDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Campanas no borradas: activas primero, luego por prioridad y nombre.",
            CAMPANIAS_EXAMPLE,
        ),
        **error_responses(status.HTTP_403_FORBIDDEN),
    },
    summary="Listar campanas",
)
def get_campanias(
    listar: Annotated[ListarCampanias, Depends(get_listar_campanias)],
) -> list[CampaniaDTO]:
    return listar.ejecutar()


@router.post(
    "/campanias",
    response_model=CampaniaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(
            status.HTTP_201_CREATED,
            "Campana creada (activa, no de ejemplo).",
            CAMPANIA_CREADA_EXAMPLE,
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            descriptions={status.HTTP_400_BAD_REQUEST: _BAD_BODY},
        ),
    },
    summary="Crear una campana",
)
def post_campania(
    body: Entrada, crear: Annotated[CrearCampania, Depends(get_crear_campania)]
) -> CampaniaDTO:
    try:
        return crear.ejecutar(body)
    except CampaniaInvalidaError as exc:
        raise _entrada_invalida(exc) from None


@router.put(
    "/campanias/{campania_id}",
    response_model=CampaniaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Campana actualizada; conserva su estado (activa/inactiva) y el indicador de ejemplo.",
            CAMPANIA_EXAMPLE,
        ),
        **_errores_con_id(MENSAJE_CAMPANIA_NO_EXISTE, _BAD_BODY),
    },
    summary="Editar una campana",
)
def put_campania(
    campania_id: CampaniaId,
    body: Entrada,
    editar: Annotated[EditarCampania, Depends(get_editar_campania)],
) -> CampaniaDTO:
    try:
        return editar.ejecutar(campania_id, body)
    except CampaniaInvalidaError as exc:
        raise _entrada_invalida(exc) from None
    except CampaniaNoExisteError:
        raise _no_existe(MENSAJE_CAMPANIA_NO_EXISTE) from None


@router.post(
    "/campanias/{campania_id}/inactivar",
    response_model=CampaniaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Campana inactivada (repetir devuelve la misma campana sin cambios). No se borra: "
            "las gestiones que ya la usan la conservan.",
            CAMPANIA_INACTIVA_EXAMPLE,
        ),
        **_errores_con_id(MENSAJE_CAMPANIA_NO_EXISTE, _BAD_ID),
    },
    summary="Inactivar una campana",
)
def post_inactivar_campania(
    campania_id: CampaniaId,
    inactivar: Annotated[InactivarCampania, Depends(get_inactivar_campania)],
) -> CampaniaDTO:
    try:
        return inactivar.ejecutar(campania_id)
    except CampaniaNoExisteError:
        raise _no_existe(MENSAJE_CAMPANIA_NO_EXISTE) from None


@router.get(
    "/predicciones/{prediccion_id}/campanias-sugeridas",
    response_model=list[CampaniaDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Campanas activas compatibles con el nivel de la prediccion y el plan del ciclo, "
            "por prioridad. Lista vacia si no hay ninguna o si el plan es DIARIO.",
            SUGERIDAS_EXAMPLE,
        ),
        **_errores_con_id(MENSAJE_PREDICCION_NO_EXISTE, _BAD_ID),
    },
    summary="Campanas sugeridas para un socio de la lista",
)
def get_campanias_sugeridas(
    prediccion_id: PrediccionId,
    sugerir: Annotated[SugerirCampanias, Depends(get_sugerir_campanias)],
) -> list[CampaniaDTO]:
    try:
        return sugerir.ejecutar(prediccion_id)
    except PrediccionNoExisteError:
        raise _no_existe(MENSAJE_PREDICCION_NO_EXISTE) from None
