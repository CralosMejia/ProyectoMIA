"""Router del modulo listas: lista priorizada, historial y su Excel (CU-04, CU-05, CU-12).

Solo HTTP: valida la entrada, delega en los casos de uso y traduce sus resultados a codigos
de estado (``409`` si el sistema no esta listo, ``404`` si la lista no existe). Una fecha
anterior a hoy (Ecuador) es ``FechaReferenciaPasadaError`` y la mapea a ``422`` el manejador
global de errores de dominio.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Response, status

from app.api.dependencies import get_consultar_listas, get_generar_lista
from app.api.openapi import XLSX_MEDIA_TYPE, error_responses, success_response
from app.application.listas.consultar_listas import ConsultarListas
from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO, ListaResumenDTO
from app.application.listas.generar_lista import (
    MENSAJE_FECHA_PASADA,
    MENSAJE_NO_LISTO,
    GenerarLista,
    SistemaNoListoError,
)

router = APIRouter(prefix="/listas", tags=["listas"])

ListaId = Annotated[int, Path(ge=1, description="Identificador de la lista priorizada.")]
Generador = Annotated[GenerarLista, Depends(get_generar_lista)]
Consultas = Annotated[ConsultarListas, Depends(get_consultar_listas)]

MENSAJE_LISTA_NO_EXISTE = "La lista no existe."
MENSAJE_SIN_LISTAS = "Aun no se ha generado ninguna lista."

LISTA_PRIORIZADA_EXAMPLE = {
    "id": 42,
    "nombre": "Campaña octubre",
    "modelo_version": "v1",
    "fecha_generacion": "2026-08-31",
    "creada_en": "2026-09-28T15:20:00Z",
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
            "cedula": "0912345678",
            "plan": "MENSUAL",
            "fecha_vencimiento": "2026-09-07",
            "dias_para_vencer": 7,
            "monto_cobrado": "40.00",
            "score": "0.81234567",
            "nivel_riesgo": "ALTO",
            "factores_principales": [
                "Ciclos previos: 0 (+0,08)",
                "Plan: MENSUAL (+0,05)",
                "Forma de pago: EFECTIVO (+0,02)",
            ],
            "dentro_top_k": True,
            "gestion_id": None,
            "gestion_estado": None,
            "campania_asignada": None,
        },
        {
            "prediccion_id": 1502,
            "prioridad": 2,
            "socio_nombre": "Carlos Andres Vera",
            "celular": None,
            "cedula": "1712345678",
            "plan": "TRIMESTRAL",
            "fecha_vencimiento": "2026-09-14",
            "dias_para_vencer": 14,
            "monto_cobrado": None,
            "score": "0.47000000",
            "nivel_riesgo": "MEDIO",
            "factores_principales": [],
            "dentro_top_k": True,
            "gestion_id": None,
            "gestion_estado": None,
            "campania_asignada": None,
        },
    ],
}

LISTAS_RESUMEN_EXAMPLE = [
    {
        "id": 43,
        "nombre": "Lista del 28 sep 2026",
        "fecha_generacion": "2026-09-28",
        "creada_en": "2026-09-28T16:05:00Z",
        "modelo_version": "v1",
        "horizonte_dias": 30,
        "top_k": 25,
        "total_items": 57,
    },
    {
        "id": 42,
        "nombre": "Campaña octubre",
        "fecha_generacion": "2026-08-31",
        "creada_en": "2026-09-28T15:20:00Z",
        "modelo_version": "v1",
        "horizonte_dias": 30,
        "top_k": 25,
        "total_items": 57,
    },
]


GENERAR_LISTA_REQUEST_EXAMPLES: dict[str, Any] = {
    "con_nombre": {
        "summary": "Lista con nombre",
        "description": "El nombre se recorta y se guarda tal cual (1..80 caracteres).",
        "value": {
            "nombre": "Campaña octubre",
            "fecha_referencia": "2026-09-29",
            "horizonte_dias": 30,
            "top_k": 25,
        },
    },
    "nombre_por_defecto": {
        "summary": "Sin nombre: nombre por defecto",
        "description": 'Sin nombre (o null) se guarda "Lista del <d> <mmm> <aaaa>" con la '
        'fecha de la lista, p. ej. "Lista del 29 sep 2026".',
        "value": {"horizonte_dias": 30, "top_k": 25},
    },
    "nombre_invalido": {
        "summary": "Nombre invalido (400)",
        "description": "Vacio tras recortar, mas de 80 caracteres o con caracteres de "
        "control -> 400 validation_error; no se guarda nada.",
        "value": {"nombre": "   "},
    },
}


def _con_mensaje(responses: dict[int | str, dict[str, Any]], code: int, message: str) -> None:
    """Sustituye el ejemplo generico de ``code`` por el mensaje real de la operacion."""
    ejemplo = responses[code]["content"]["application/json"]
    ejemplo["example"] = {"error": {**ejemplo["example"]["error"], "message": message}}


_POST_ERRORS = error_responses(
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_409_CONFLICT,
    status.HTTP_422_UNPROCESSABLE_CONTENT,
    descriptions={
        status.HTTP_400_BAD_REQUEST: "Horizonte fuera de 1..31, K menor que 1, fecha invalida "
        "o nombre invalido (vacio tras recortar, mas de 80 caracteres o con caracteres de "
        "control).",
        status.HTTP_409_CONFLICT: "El sistema no esta listo (migracion en curso o sin modelo).",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "La fecha de la lista es anterior a hoy.",
    },
)
_con_mensaje(_POST_ERRORS, status.HTTP_409_CONFLICT, MENSAJE_NO_LISTO)
_con_mensaje(_POST_ERRORS, status.HTTP_422_UNPROCESSABLE_CONTENT, MENSAJE_FECHA_PASADA)

_GET_ERRORS = error_responses(
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    descriptions={
        status.HTTP_404_NOT_FOUND: MENSAJE_LISTA_NO_EXISTE,
        status.HTTP_400_BAD_REQUEST: "El identificador de la lista no es valido.",
    },
)
_con_mensaje(_GET_ERRORS, status.HTTP_404_NOT_FOUND, MENSAJE_LISTA_NO_EXISTE)

_ULTIMA_ERRORS = error_responses(
    status.HTTP_403_FORBIDDEN,
    status.HTTP_404_NOT_FOUND,
    descriptions={status.HTTP_404_NOT_FOUND: MENSAJE_SIN_LISTAS},
)
_con_mensaje(_ULTIMA_ERRORS, status.HTTP_404_NOT_FOUND, MENSAJE_SIN_LISTAS)


def _no_existe(mensaje: str = MENSAJE_LISTA_NO_EXISTE) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensaje)


@router.post(
    "",
    response_model=ListaPriorizadaDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        **success_response(
            status.HTTP_201_CREATED, "Lista priorizada generada.", LISTA_PRIORIZADA_EXAMPLE
        ),
        **_POST_ERRORS,
    },
    summary="Generar la lista priorizada de no renovacion",
)
def post_lista(
    body: Annotated[GenerarListaDTO, Body(openapi_examples=GENERAR_LISTA_REQUEST_EXAMPLES)],
    generar: Generador,
) -> ListaPriorizadaDTO:
    try:
        return generar.ejecutar(body)
    except SistemaNoListoError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MENSAJE_NO_LISTO) from None


@router.get(
    "",
    response_model=list[ListaResumenDTO],
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Listas generadas, de la mas reciente a la mas antigua.",
            LISTAS_RESUMEN_EXAMPLE,
        ),
        **error_responses(status.HTTP_403_FORBIDDEN),
    },
    summary="Consultar el historial de listas generadas",
)
def get_listas(consultas: Consultas) -> list[ListaResumenDTO]:
    return consultas.listar()


# Declarada antes de ``/{lista_id}`` para que ``ultima`` no se interprete como id.
@router.get(
    "/ultima",
    response_model=ListaPriorizadaDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Ultima lista generada.", LISTA_PRIORIZADA_EXAMPLE),
        **_ULTIMA_ERRORS,
    },
    summary="Consultar la ultima lista priorizada",
)
def get_ultima_lista(consultas: Consultas) -> ListaPriorizadaDTO:
    lista = consultas.ultima()
    if lista is None:
        raise _no_existe(MENSAJE_SIN_LISTAS)
    return lista


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
def get_lista(lista_id: ListaId, consultas: Consultas) -> ListaPriorizadaDTO:
    lista = consultas.obtener(lista_id)
    if lista is None:
        raise _no_existe()
    return lista


@router.get(
    "/{lista_id}/excel",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Libro Excel con la lista priorizada (generado en memoria).",
            "content": {XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
            "headers": {
                "Content-Disposition": {
                    "description": "Nombre del archivo: id y fecha de la lista, sin datos "
                    "personales.",
                    "schema": {"type": "string"},
                    "example": 'attachment; filename="lista_42_2026-08-31.xlsx"',
                }
            },
        },
        **_GET_ERRORS,
    },
    summary="Descargar la lista priorizada en Excel",
)
def get_lista_excel(lista_id: ListaId, consultas: Consultas) -> Response:
    archivo = consultas.descargar_excel(lista_id)
    if archivo is None:
        raise _no_existe()
    return Response(
        content=archivo.contenido,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{archivo.nombre_archivo}"'},
    )
