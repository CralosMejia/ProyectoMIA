"""Router del modulo gestiones: asignacion (CU-08), alertas (CU-09) y resultado (CU-10).

Solo HTTP: valida la entrada, delega en los casos de uso y traduce sus errores a codigos de
estado: ``404`` si la prediccion, la campana o la gestion no existen; ``409`` si el ciclo ya
tiene gestion o la gestion esta cerrada (una gestion sin campana nace cerrada, R-010); el
resto de reglas de dominio (fecha fuera de rango, plazo terminado, campana que no aplica,
resultado incoherente) -> ``422 domain_rule_violated`` por el manejador global.
``GET /alertas`` y ``GET /gestiones?filtro`` (CU-09, R-011 decision (a)) cuentan y listan solo
gestiones ``PENDIENTE`` no borradas segun la fecha de seguimiento y "hoy" en Ecuador; un
filtro ausente o fuera de la lista blanca -> ``400 validation_error``.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status

from app.api.dependencies import (
    get_consultar_alertas,
    get_consultar_gestion,
    get_crear_gestion,
    get_listar_gestiones_por_alerta,
    get_registrar_resultado,
)
from app.api.openapi import OpenApiResponses, error_responses, success_response
from app.application.campanias.gestionar_campanias import (
    MENSAJE_CAMPANIA_NO_EXISTE,
    CampaniaNoExisteError,
)
from app.application.campanias.sugerir_campanias import (
    MENSAJE_PREDICCION_NO_EXISTE,
    PrediccionNoExisteError,
)
from app.application.gestiones.consultar_alertas import ConsultarAlertas, ListarGestionesPorAlerta
from app.application.gestiones.consultar_gestion import ConsultarGestion
from app.application.gestiones.crear_gestion import CrearGestion
from app.application.gestiones.dtos import (
    AlertasDTO,
    CrearGestionDTO,
    FiltroGestiones,
    GestionDTO,
    GestionResumenDTO,
    RegistrarResultadoDTO,
)
from app.application.gestiones.registrar_resultado import (
    MENSAJE_GESTION_NO_EXISTE,
    GestionNoExisteError,
    RegistrarResultado,
)
from app.domain.gestiones.errores import (
    MENSAJE_GESTION_CERRADA,
    MENSAJE_GESTION_DUPLICADA,
    GestionCerradaError,
    GestionDuplicadaError,
)
from app.domain.gestiones.reglas import MENSAJE_NO_CONTACTADO

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
    "campania_id": 2,
    "campania_nombre": "Ejemplo: Renovación anticipada",
    "estado": "PENDIENTE",
    "fecha_asignacion": "2026-09-29T15:30:00Z",
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
GESTION_SIN_CAMPANIA_EXAMPLE = {
    **GESTION_EXAMPLE,
    "campania_id": None,
    "campania_nombre": None,
    "estado": "CERRADA",
    "fecha_seguimiento": "2026-09-29",
    "responsable": None,
    "fecha_cierre": "2026-09-29T15:30:00Z",
}
GESTIONES_RESUMEN_EXAMPLE = [
    {
        "id": 9,
        "prediccion_id": 1501,
        "socio_nombre": "Maria Fernanda Lopez",
        "celular": "0991234567",
        "plan": "MENSUAL",
        "fecha_vencimiento": "2026-10-05",
        "fecha_seguimiento": "2026-09-30",
        "nivel_riesgo": "ALTO",
        "campania_nombre": "Renovacion anticipada",
        "responsable": "Andrea",
        "estado": "PENDIENTE",
    }
]
ALERTAS_EXAMPLE = {"vencidas": 2, "hoy": 1, "proximos_7_dias": 5}

_BAD_ID = "El identificador de la gestion no es valido."
_MENSAJE_FECHA_FUERA = "La fecha de seguimiento debe estar entre 2026-09-29 y 2026-11-04."

CREAR_REQUEST_EXAMPLES: dict[str, Any] = {
    "con_campania": {
        "summary": "Con campana sugerida",
        "description": "La campana debe estar activa y aplicar al nivel y al plan del socio. "
        "Fecha de seguimiento obligatoria, entre hoy y el vencimiento + 30 dias.",
        "value": {
            "prediccion_id": 1501,
            "campania_id": 2,
            "fecha_seguimiento": "2026-10-30",
            "responsable": "Andrea",
        },
    },
    "sin_campania": {
        "summary": "No asignar campana",
        "description": "``campania_id`` nulo: la gestion nace cerrada, sin seguimiento ni "
        "resultado que registrar. ``fecha_seguimiento`` y ``responsable`` no se envian (si "
        "llegan, se ignoran) y no importa que el plazo de seguimiento haya terminado.",
        "value": {"prediccion_id": 1501, "campania_id": None},
    },
}
RESULTADO_REQUEST_EXAMPLES: dict[str, Any] = {
    "pendiente": {
        "summary": "Contactado, aun sin renovar",
        "description": "Renovo PENDIENTE: la gestion sigue abierta; ``fecha_seguimiento`` "
        "reprograma el seguimiento (nula = se conserva).",
        "value": {
            "contactado": True,
            "campania_ofrecida": "SI",
            "campania_aceptada": "SI",
            "renovo_declarado": "PENDIENTE",
            "fecha_contacto": "2026-09-29",
            "observaciones": "Acepta la propuesta; renovara la proxima semana.",
            "responsable": "Andrea",
            "fecha_seguimiento": "2026-10-27",
        },
    },
    "cerrar": {
        "summary": "Cerrar con Renovo No",
        "description": "Renovo SI o NO cierra la gestion; ya no se puede modificar.",
        "value": {
            "contactado": False,
            "campania_ofrecida": "NO_APLICA",
            "campania_aceptada": "NO_APLICA",
            "renovo_declarado": "NO",
            "fecha_contacto": None,
            "observaciones": None,
            "responsable": "Andrea",
            "fecha_seguimiento": None,
        },
    },
}


def _con_mensajes(responses: OpenApiResponses, mensajes: dict[int, str]) -> OpenApiResponses:
    """Sustituye el ejemplo generico de cada codigo por el mensaje real de la operacion."""
    for code, message in mensajes.items():
        ejemplo = responses[code]["content"]["application/json"]
        ejemplo["example"] = {"error": {**ejemplo["example"]["error"], "message": message}}
    return responses


def _error(codigo: int, mensaje: str) -> HTTPException:
    return HTTPException(status_code=codigo, detail=mensaje)


@router.post(
    "/gestiones",
    response_model=GestionDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Gestion creada: PENDIENTE con campana; CERRADA (con "
            "``fecha_cierre`` y resultado nulo) si no se asigna campana.",
            "content": {
                "application/json": {
                    "examples": {
                        "con_campania": {
                            "summary": "Con campana: pendiente de seguimiento",
                            "value": GESTION_EXAMPLE,
                        },
                        "sin_campania": {
                            "summary": "Sin campana: cerrada desde su creacion",
                            "value": GESTION_SIN_CAMPANIA_EXAMPLE,
                        },
                    }
                }
            },
        },
        **_con_mensajes(
            error_responses(
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_409_CONFLICT,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                descriptions={
                    status.HTTP_400_BAD_REQUEST: (
                        "Entrada invalida; incluye asignar campana sin fecha de seguimiento."
                    ),
                    status.HTTP_404_NOT_FOUND: "La prediccion o la campana no existen.",
                    status.HTTP_409_CONFLICT: MENSAJE_GESTION_DUPLICADA,
                    status.HTTP_422_UNPROCESSABLE_CONTENT: (
                        "Solo con campana: fecha de seguimiento fuera de [hoy, vencimiento + "
                        "30], plazo de seguimiento terminado o campana inactiva / que no "
                        "aplica al socio."
                    ),
                },
            ),
            {
                status.HTTP_404_NOT_FOUND: MENSAJE_PREDICCION_NO_EXISTE,
                status.HTTP_409_CONFLICT: MENSAJE_GESTION_DUPLICADA,
                status.HTTP_422_UNPROCESSABLE_CONTENT: _MENSAJE_FECHA_FUERA,
            },
        ),
    },
    summary="Asignar campana y crear el seguimiento",
)
def post_gestion(
    body: Annotated[CrearGestionDTO, Body(openapi_examples=CREAR_REQUEST_EXAMPLES)],
    crear: Annotated[CrearGestion, Depends(get_crear_gestion)],
) -> GestionDTO:
    try:
        return crear.ejecutar(body)
    except PrediccionNoExisteError:
        raise _error(status.HTTP_404_NOT_FOUND, MENSAJE_PREDICCION_NO_EXISTE) from None
    except CampaniaNoExisteError:
        raise _error(status.HTTP_404_NOT_FOUND, MENSAJE_CAMPANIA_NO_EXISTE) from None
    except GestionDuplicadaError:
        raise _error(status.HTTP_409_CONFLICT, MENSAJE_GESTION_DUPLICADA) from None


@router.get(
    "/gestiones",
    response_model=list[GestionResumenDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Gestiones PENDIENTE no borradas del grupo, ordenadas por fecha de seguimiento e "
            "id. ``vencidas``: seguimiento anterior a hoy; ``hoy``: igual a hoy; "
            "``proximas``: de manana a hoy + 7 dias (fecha de Ecuador).",
            GESTIONES_RESUMEN_EXAMPLE,
        ),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
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
    listar: Annotated[ListarGestionesPorAlerta, Depends(get_listar_gestiones_por_alerta)],
) -> list[GestionResumenDTO]:
    return listar.ejecutar(filtro)


@router.get(
    "/gestiones/{gestion_id}",
    response_model=GestionDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Gestion.", GESTION_EXAMPLE),
        **_con_mensajes(
            error_responses(
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
                descriptions={
                    status.HTTP_400_BAD_REQUEST: _BAD_ID,
                    status.HTTP_404_NOT_FOUND: MENSAJE_GESTION_NO_EXISTE,
                },
            ),
            {status.HTTP_404_NOT_FOUND: MENSAJE_GESTION_NO_EXISTE},
        ),
    },
    summary="Consultar una gestion",
)
def get_gestion(
    gestion_id: GestionId,
    consultar: Annotated[ConsultarGestion, Depends(get_consultar_gestion)],
) -> GestionDTO:
    try:
        return consultar.ejecutar(gestion_id)
    except GestionNoExisteError:
        raise _error(status.HTTP_404_NOT_FOUND, MENSAJE_GESTION_NO_EXISTE) from None


@router.put(
    "/gestiones/{gestion_id}/resultado",
    response_model=GestionDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK, "Resultado registrado.", GESTION_CON_RESULTADO_EXAMPLE
        ),
        **_con_mensajes(
            error_responses(
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_409_CONFLICT,
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                descriptions={
                    status.HTTP_404_NOT_FOUND: MENSAJE_GESTION_NO_EXISTE,
                    status.HTTP_409_CONFLICT: (
                        "La gestion esta cerrada: ya se registro Renovo Si o No, o se creo "
                        "sin campana (nace cerrada y no admite resultado)."
                    ),
                    status.HTTP_422_UNPROCESSABLE_CONTENT: (
                        "Respuestas incoherentes o fecha de seguimiento fuera de rango."
                    ),
                },
            ),
            {
                status.HTTP_404_NOT_FOUND: MENSAJE_GESTION_NO_EXISTE,
                status.HTTP_409_CONFLICT: MENSAJE_GESTION_CERRADA,
                status.HTTP_422_UNPROCESSABLE_CONTENT: MENSAJE_NO_CONTACTADO,
            },
        ),
    },
    summary="Registrar el resultado del seguimiento",
)
def put_resultado_gestion(
    gestion_id: GestionId,
    body: Annotated[RegistrarResultadoDTO, Body(openapi_examples=RESULTADO_REQUEST_EXAMPLES)],
    registrar: Annotated[RegistrarResultado, Depends(get_registrar_resultado)],
) -> GestionDTO:
    try:
        return registrar.ejecutar(gestion_id, body)
    except GestionNoExisteError:
        raise _error(status.HTTP_404_NOT_FOUND, MENSAJE_GESTION_NO_EXISTE) from None
    except GestionCerradaError:
        raise _error(status.HTTP_409_CONFLICT, MENSAJE_GESTION_CERRADA) from None


@router.get(
    "/alertas",
    response_model=AlertasDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Contadores de gestiones PENDIENTE no borradas por fecha de seguimiento (cada "
            "gestion cuenta en un solo grupo; las cerradas y las creadas sin campana no "
            "cuentan).",
            ALERTAS_EXAMPLE,
        ),
        **error_responses(status.HTTP_403_FORBIDDEN),
    },
    summary="Alertas de seguimiento",
)
def get_alertas(
    consultar: Annotated[ConsultarAlertas, Depends(get_consultar_alertas)],
) -> AlertasDTO:
    return consultar.ejecutar()
