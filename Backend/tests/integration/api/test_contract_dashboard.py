"""Contrato de ``dashboard`` (CU-11) y comprobacion final del contrato completo.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.dashboard.dtos import DashboardDTO
from tests.integration.api.contract_helpers import (
    assert_not_implemented,
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
MULTI_EXAMPLE_OPERATIONS = {("get", "/api/v1/sistema/estado"), ("post", "/api/v1/gestiones")}
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
    # R-009 T12: gestiones (el filtro de pendientes y las alertas siguen en 501, dia 6).
    ("post", "/api/v1/gestiones"),
    ("get", "/api/v1/gestiones/{gestion_id}"),
    ("put", "/api/v1/gestiones/{gestion_id}/resultado"),
}


@pytest.mark.parametrize("params", [{}, {"mes": "2026-09"}, {"mes": "2026-12"}])
def test_get_dashboard_valid_or_absent_mes_returns_501(
    contract_client: TestClient, params: dict[str, str]
) -> None:
    assert_not_implemented(contract_client.get(DASHBOARD_PATH, params=params))


@pytest.mark.parametrize("mes", ["2026-13", "abc", "2026-00", "2026-9", "2026-09-01", ""])
def test_get_dashboard_invalid_mes_returns_400(contract_client: TestClient, mes: str) -> None:
    assert_validation_error(contract_client.get(DASHBOARD_PATH, params={"mes": mes}))


def test_openapi_dashboard_declares_examples(openapi_spec: dict[str, Any]) -> None:
    assert_operation_contract(
        openapi_spec, "get", DASHBOARD_PATH, 200, (400, 403, 501), DashboardDTO
    )


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
    example = json_example(operation(openapi_spec, "get", DASHBOARD_PATH), 200)

    dumped = DashboardDTO.model_validate(example).model_dump(mode="json")
    tasas = [c["tasa_renovacion"] for c in dumped["por_campania"]]
    assert tasas
    assert all(t is None or isinstance(t, str) for t in tasas)
    assert any(isinstance(t, str) for t in tasas)
