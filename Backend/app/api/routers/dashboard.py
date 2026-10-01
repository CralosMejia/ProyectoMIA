"""Router del modulo dashboard: resultados de retencion del mes (CU-11, R-011 decision (c)).

Solo HTTP: valida ``mes`` (``YYYY-MM``; invalido -> ``400 validation_error``) y delega en
``ConsultarDashboard``. Aislamiento entre usuarios: NO APLICA (RT-12, sin login; CU-00).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_consultar_dashboard
from app.api.openapi import error_responses, success_response
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
}


@router.get(
    "",
    response_model=DashboardDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(
            status.HTTP_200_OK,
            "Dashboard del mes (por instante de asignacion en fecha de Ecuador). Embudo sobre "
            "las gestiones con campana; un resultado nulo nunca cuenta. ``gestiones_cerradas`` "
            "= cerradas con resultado (Renovo Si o No); ``tasa_renovacion`` (texto con 8 "
            "decimales) solo con 10 o mas, si no nula y ``casos_insuficientes``. La fila "
            "``Sin campaña`` va al final. ``estado_modelo`` nulo si no hay modelo vigente.",
            DASHBOARD_EXAMPLE,
        ),
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
