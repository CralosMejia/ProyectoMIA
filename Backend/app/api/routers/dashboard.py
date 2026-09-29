"""Router del modulo dashboard: resultados de retencion del mes (CU-11).

Contrato publicado; la logica responde ``501`` hasta su dia del cronograma.
"""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.openapi import error_responses, raise_not_implemented, success_response
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
            "nombre": "Sin campana",
            "gestiones": 3,
            "contactados": 2,
            "renovaciones": 1,
            "gestiones_cerradas": 2,
            "tasa_renovacion": None,
            "casos_insuficientes": True,
        },
    ],
    "estado_modelo": {
        "version": "v1",
        "fecha_entrenamiento": "2026-09-28T14:30:00Z",
        "ciclos_entrenamiento": 1843,
        "proxima_fecha_reentrenamiento": "2026-10-28",
        "ciclos_nuevos_evaluables": 57,
    },
}


@router.get(
    "",
    response_model=DashboardDTO,
    status_code=status.HTTP_200_OK,
    responses={
        **success_response(status.HTTP_200_OK, "Dashboard del mes.", DASHBOARD_EXAMPLE),
        **error_responses(
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_501_NOT_IMPLEMENTED,
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
            description="Mes YYYY-MM; si se omite, el mes actual segun el reloj del sistema.",
            examples=["2026-09"],
        ),
    ] = None,
) -> DashboardDTO:
    raise_not_implemented()
