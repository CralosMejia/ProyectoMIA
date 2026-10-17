"""Router del modulo dashboard: resultados de retencion del mes (CU-11, R-011 decision (c)).

Solo HTTP: valida ``mes`` (``YYYY-MM``; invalido -> ``400 validation_error``) y delega en
``ConsultarDashboard``. Aislamiento entre usuarios: NO APLICA (RT-12, sin login; CU-00).
R-018 (M04): bloque aditivo ``piloto`` con los indicadores del top 25 de la lista del mes; sin
datos personales ni ids de socio.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_consultar_dashboard
from app.api.openapi import OpenApiResponses, error_responses
from app.application.dashboard.consultar_dashboard import ConsultarDashboard
from app.application.dashboard.dtos import MES_PATTERN, DashboardDTO

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DASHBOARD_EXAMPLE = {
    "mes": "2026-09",
    "embudo": {
        "asignadas": 40,
        "contactadas": 32,
        "ofrecidas": 25,
        "aceptadas": 12,
        "renovaron": 10,
    },
    "por_campania": [
        {
            "campania_id": 3,
            "nombre": "Renovacion anticipada",
            "gestiones": 22,
            "contactados": 19,
            "renovaciones": 8,
            "gestiones_cerradas": 16,
            "tasa_renovacion": "0.50000000",
            "casos_insuficientes": False,
        },
        {
            "campania_id": None,
            "nombre": "Sin campaña",
            "gestiones": 3,
            "contactados": 0,
            "renovaciones": 0,
            "gestiones_cerradas": 0,
            "tasa_renovacion": None,
            "casos_insuficientes": True,
        },
    ],
    "estado_modelo": {
        "version": "v1",
        "fecha_entrenamiento": "2026-09-28T14:30:00Z",
        "ciclos_entrenamiento": 1843,
        "proxima_fecha_reentrenamiento": "2027-03-28",
        "ciclos_nuevos_evaluables": 57,
    },
    "piloto": {
        "estado": "PARCIAL",
        "lista": {"id": 12, "nombre": "Lista septiembre", "fecha_generacion": "2026-09-01"},
        "corte_verificacion": "2026-10-28",
        "n_top": 25,
        "sin_dato": 0,
        "precision_top25": {
            "valor": "0.60000000",
            "numerador": 12,
            "denominador": 20,
            "n": 25,
            "pendientes": 5,
            "estado": "PARCIAL",
        },
        "contactados_antes_vencimiento": {
            "valor": "0.72000000",
            "numerador": 18,
            "denominador": 25,
            "n": 25,
            "pendientes": 0,
            "estado": "COMPLETO",
        },
        "dias_anticipacion": {"valor": "4.5", "n": 19, "estado": "COMPLETO"},
        "tasa_renovacion_contactados": {
            "valor": "0.41176471",
            "numerador": 7,
            "denominador": 17,
            "n": 21,
            "pendientes": 4,
            "estado": "PARCIAL",
        },
        "monto_retenido": {
            "total": "312.50",
            "renovaciones": 7,
            "renovaciones_sin_monto": 1,
            "n": 17,
            "pendientes": 4,
            "estado": "PARCIAL",
        },
    },
}

_PROPORCION_SIN_DATOS = {
    "valor": None,
    "numerador": 0,
    "denominador": 0,
    "n": 0,
    "pendientes": 0,
    "estado": "SIN_DATOS",
}

DASHBOARD_PILOTO_SIN_DATOS_EXAMPLE = {
    **DASHBOARD_EXAMPLE,
    "piloto": {
        "estado": "SIN_DATOS",
        "lista": None,
        "corte_verificacion": None,
        "n_top": 0,
        "sin_dato": 0,
        "precision_top25": _PROPORCION_SIN_DATOS,
        "contactados_antes_vencimiento": _PROPORCION_SIN_DATOS,
        "dias_anticipacion": {"valor": None, "n": 0, "estado": "SIN_DATOS"},
        "tasa_renovacion_contactados": _PROPORCION_SIN_DATOS,
        "monto_retenido": {
            "total": None,
            "renovaciones": 0,
            "renovaciones_sin_monto": 0,
            "n": 0,
            "pendientes": 0,
            "estado": "SIN_DATOS",
        },
    },
}

_DASHBOARD_RESPONSES: OpenApiResponses = {
    status.HTTP_200_OK: {
        "description": (
            "Dashboard del mes (por instante de asignacion en fecha de Ecuador). Embudo sobre "
            "las gestiones con campana; un resultado nulo nunca cuenta. ``gestiones_cerradas`` "
            "= cerradas con resultado (Renovo Si o No); ``tasa_renovacion`` (texto con 8 "
            "decimales) solo con 10 o mas, si no nula y ``casos_insuficientes``. La fila "
            "``Sin campaña`` va al final. ``estado_modelo`` nulo si no hay modelo vigente. "
            "``piloto``: indicadores observados (no causales) del top 25 (prioridad <= 25) de "
            "la ultima lista generada en el mes, verificados 30 dias despues del vencimiento "
            "con ``corte_verificacion`` (ultimo dia con datos); proporciones como texto con 8 "
            "decimales, ``dias_anticipacion`` con 1 y ``monto_retenido.total`` con 2; estados "
            "COMPLETO, PARCIAL, PENDIENTE o SIN_DATOS (mes sin lista), siempre con su ``n``."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "con_piloto": {
                        "summary": "Mes con lista: piloto parcialmente verificado",
                        "value": DASHBOARD_EXAMPLE,
                    },
                    "piloto_sin_datos": {
                        "summary": "Mes sin lista: piloto sin datos",
                        "value": DASHBOARD_PILOTO_SIN_DATOS_EXAMPLE,
                    },
                }
            }
        },
    }
}


@router.get(
    "",
    response_model=DashboardDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **_DASHBOARD_RESPONSES,
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            descriptions={status.HTTP_400_BAD_REQUEST: "El mes no tiene el formato YYYY-MM."},
        ),
    },
    summary="Dashboard de retencion del mes",
)
def get_dashboard(
    mes: Annotated[
        str | None,
        Query(
            pattern=MES_PATTERN,
            description="Mes YYYY-MM; si se omite, el mes actual (fecha de Ecuador).",
            examples=["2026-09"],
        ),
    ] = None,
    *,
    consultar: Annotated[ConsultarDashboard, Depends(get_consultar_dashboard)],
) -> DashboardDTO:
    return consultar.ejecutar(mes)
