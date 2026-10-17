"""Contrato de ``dashboard`` (CU-11) y comprobacion final del contrato completo.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.application.dashboard.dtos import DashboardDTO
from tests.integration.api.contract_helpers import (
    assert_operation_contract,
    assert_validation_error,
    json_example,
    operation,
)

pytestmark = pytest.mark.integration

DASHBOARD_PATH = "/api/v1/dashboard"

BUSINESS_OPERATIONS: set[tuple[str, str]] = {
    ("get", "/api/v1/sistema/estado"),
    ("post", "/api/v1/cargas/vista-previa"),
    ("post", "/api/v1/cargas"),
    ("post", "/api/v1/listas"),
    ("get", "/api/v1/listas"),
    ("get", "/api/v1/listas/ultima"),
    ("get", "/api/v1/listas/{lista_id}"),
    ("get", "/api/v1/listas/{lista_id}/excel"),
    ("get", "/api/v1/campanias"),
    ("post", "/api/v1/campanias"),
    ("put", "/api/v1/campanias/{campania_id}"),
    ("post", "/api/v1/campanias/{campania_id}/inactivar"),
    ("post", "/api/v1/campanias/{campania_id}/activar"),
    ("get", "/api/v1/predicciones/{prediccion_id}/campanias-sugeridas"),
    ("post", "/api/v1/gestiones"),
    ("get", "/api/v1/gestiones/{gestion_id}"),
    ("put", "/api/v1/gestiones/{gestion_id}/resultado"),
    ("get", "/api/v1/gestiones"),
    ("get", "/api/v1/alertas"),
    ("get", "/api/v1/dashboard"),
}
SUCCESS_CODES = {"200", "201"}
# El Excel es binario: su exito se documenta con el media type y el schema, sin ejemplo JSON.
BINARY_OPERATIONS = {("get", "/api/v1/listas/{lista_id}/excel")}
# Exito documentado con varios ejemplos (``examples``): un ejemplo por estado (R-004, T14).
# R-010: ``POST /gestiones`` documenta la gestion con campana (pendiente) y sin campana (cerrada).
# R-018: ``GET /dashboard`` documenta el piloto con lista y el mes sin lista (``SIN_DATOS``).
MULTI_EXAMPLE_OPERATIONS = {
    ("get", "/api/v1/sistema/estado"),
    ("post", "/api/v1/gestiones"),
    ("get", "/api/v1/dashboard"),
}
# Operaciones ya implementadas: dejan de declarar ``501`` (R-004: sistema y listas).
IMPLEMENTED_OPERATIONS = {
    ("get", "/api/v1/sistema/estado"),
    ("post", "/api/v1/cargas/vista-previa"),
    ("post", "/api/v1/cargas"),
    ("post", "/api/v1/listas"),
    ("get", "/api/v1/listas"),
    ("get", "/api/v1/listas/ultima"),
    ("get", "/api/v1/listas/{lista_id}"),
    ("get", "/api/v1/listas/{lista_id}/excel"),
    # R-009 T8: campanias y sugerencias.
    ("get", "/api/v1/campanias"),
    ("post", "/api/v1/campanias"),
    ("put", "/api/v1/campanias/{campania_id}"),
    ("post", "/api/v1/campanias/{campania_id}/inactivar"),
    ("post", "/api/v1/campanias/{campania_id}/activar"),  # R-010 T4
    ("get", "/api/v1/predicciones/{prediccion_id}/campanias-sugeridas"),
    # R-009 T12: gestiones.
    ("post", "/api/v1/gestiones"),
    ("get", "/api/v1/gestiones/{gestion_id}"),
    ("put", "/api/v1/gestiones/{gestion_id}/resultado"),
    # R-011 T4: alertas y filtro de pendientes.
    ("get", "/api/v1/gestiones"),
    ("get", "/api/v1/alertas"),
    # R-011 T17: dashboard.
    ("get", "/api/v1/dashboard"),
}


@pytest.mark.parametrize("params", [{}, {"mes": "2026-09"}, {"mes": "2026-12"}])
def test_get_dashboard_valid_or_absent_mes_returns_200(
    migrated_engine: Engine, contract_client: TestClient, params: dict[str, str]
) -> None:
    response = contract_client.get(DASHBOARD_PATH, params=params)

    assert response.status_code == 200
    DashboardDTO.model_validate(response.json())


@pytest.mark.parametrize("mes", ["2026-13", "abc", "2026-00", "2026-9", "2026-09-01", ""])
def test_get_dashboard_invalid_mes_returns_400(contract_client: TestClient, mes: str) -> None:
    assert_validation_error(contract_client.get(DASHBOARD_PATH, params={"mes": mes}))


def _ejemplos_200(spec: dict[str, Any]) -> dict[str, Any]:
    op = operation(spec, "get", DASHBOARD_PATH)
    media = op["responses"]["200"]["content"]["application/json"]
    return {nombre: ejemplo["value"] for nombre, ejemplo in media["examples"].items()}


def test_openapi_dashboard_declares_examples(openapi_spec: dict[str, Any]) -> None:
    assert_operation_contract(openapi_spec, "get", DASHBOARD_PATH, 200, (400, 403))
    ejemplos = _ejemplos_200(openapi_spec)

    assert set(ejemplos) == {"con_piloto", "piloto_sin_datos"}
    for ejemplo in ejemplos.values():
        DashboardDTO.model_validate(ejemplo)
    assert ejemplos["con_piloto"]["piloto"]["estado"] == "PARCIAL"
    assert ejemplos["piloto_sin_datos"]["piloto"]["estado"] == "SIN_DATOS"


# Campos publicados antes de R-018: el cambio es aditivo (solo se anade ``piloto``).
CAMPOS_ANTERIORES = {
    "DashboardDTO": {"mes", "embudo", "por_campania", "estado_modelo"},
    "EmbudoDTO": {"asignadas", "contactadas", "ofrecidas", "aceptadas", "renovaron"},
    "ResultadoCampaniaDTO": {
        "campania_id",
        "nombre",
        "gestiones",
        "contactados",
        "renovaciones",
        "gestiones_cerradas",
        "tasa_renovacion",
        "casos_insuficientes",
    },
    "EstadoModeloDTO": {
        "version",
        "fecha_entrenamiento",
        "ciclos_entrenamiento",
        "proxima_fecha_reentrenamiento",
        "ciclos_nuevos_evaluables",
    },
}


def test_openapi_dashboard_cambio_aditivo_conserva_los_campos_anteriores(
    openapi_spec: dict[str, Any],
) -> None:
    esquemas = openapi_spec["components"]["schemas"]

    for nombre, campos in CAMPOS_ANTERIORES.items():
        publicados = set(esquemas[nombre]["properties"])
        extra = {"piloto"} if nombre == "DashboardDTO" else set()
        assert publicados == campos | extra, nombre
    assert set(esquemas["DashboardDTO"]["required"]) >= {"mes", "embudo", "por_campania"}
    assert "piloto" in esquemas["DashboardDTO"]["required"]


def test_openapi_dashboard_piloto_publica_decimales_como_texto(
    openapi_spec: dict[str, Any],
) -> None:
    esquemas = openapi_spec["components"]["schemas"]

    for nombre, campo in (
        ("IndicadorProporcionDTO", "valor"),
        ("IndicadorDiasDTO", "valor"),
        ("IndicadorMontoDTO", "total"),
    ):
        tipos = {opcion.get("type") for opcion in esquemas[nombre]["properties"][campo]["anyOf"]}
        assert tipos == {"string", "null"}, nombre


def test_openapi_contains_exactly_the_20_business_operations_plus_health(
    openapi_spec: dict[str, Any],
) -> None:
    published = {
        (method, path)
        for path, item in openapi_spec["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }

    assert len(BUSINESS_OPERATIONS) == 20  # R-010: + POST /campanias/{id}/activar
    assert published == BUSINESS_OPERATIONS | {("get", "/api/v1/health")}


@pytest.mark.parametrize(("method", "path"), sorted(BUSINESS_OPERATIONS))
def test_openapi_business_operation_declares_success_and_501_examples(
    openapi_spec: dict[str, Any], method: str, path: str
) -> None:
    op = operation(openapi_spec, method, path)
    success = SUCCESS_CODES & set(op["responses"])
    assert len(success) == 1, f"{method.upper()} {path} debe declarar una respuesta de exito"
    if (method, path) in MULTI_EXAMPLE_OPERATIONS:
        media = op["responses"][success.pop()]["content"]["application/json"]
        assert media["examples"]
    elif (method, path) not in BINARY_OPERATIONS:
        assert json_example(op, int(success.pop())) is not None
    if (method, path) in IMPLEMENTED_OPERATIONS:
        assert "501" not in op["responses"]
    else:
        assert json_example(op, 501)["error"]["code"] == "not_implemented"


def test_dashboard_example_serializes_tasa_renovacion_as_string(
    openapi_spec: dict[str, Any],
) -> None:
    example = _ejemplos_200(openapi_spec)["con_piloto"]

    dumped = DashboardDTO.model_validate(example).model_dump(mode="json")
    tasas = [c["tasa_renovacion"] for c in dumped["por_campania"]]
    assert tasas
    assert all(t is None or isinstance(t, str) for t in tasas)
    assert any(isinstance(t, str) for t in tasas)
    assert dumped["piloto"]["precision_top25"]["valor"] == "0.60000000"
    assert dumped["piloto"]["monto_retenido"]["total"] == "312.50"
