"""Contrato de ``campanias`` y sugerencias (CU-06, CU-07), reales desde R-009 (T8).

El comportamiento con base de datos se prueba en ``test_campanias_api.py``; aqui quedan la
validacion de entrada (``400`` sin tocar la base) y el contrato OpenAPI.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.campanias.dtos import PLANES_CAMPANIA_DTO, CampaniaDTO
from app.domain.common.enums import PLANES_CAMPANIA
from tests.integration.api.contract_helpers import (
    assert_operation_contract,
    assert_validation_error,
    json_example,
    request_body_schema_name,
)

pytestmark = pytest.mark.integration

CAMPANIAS_PATH = "/api/v1/campanias"
VALID_BODY: dict[str, Any] = {
    "nombre": "Renovacion anticipada",
    "descripcion": "10% de descuento si renueva antes del vencimiento.",
    "niveles_riesgo": ["ALTO", "MEDIO"],
    "planes": ["MENSUAL", "TRIMESTRAL"],
    "prioridad": 1,
}


@pytest.mark.parametrize(
    "override",
    [
        {"planes": ["DIARIO"]},
        {"planes": []},
        {"planes": ["mensual"]},
        {"niveles_riesgo": []},
        {"niveles_riesgo": ["CRITICO"]},
        {"nombre": ""},
        {"nombre": "   "},
        {"nombre": "x" * 121},
        {"prioridad": 0},
        {"prioridad": 1000},
    ],
)
def test_post_campanias_invalid_body_returns_400(
    contract_client: TestClient, override: dict[str, Any]
) -> None:
    body = {**VALID_BODY, **override}

    assert_validation_error(contract_client.post(CAMPANIAS_PATH, json=body))


def test_put_campania_invalid_id_returns_400(contract_client: TestClient) -> None:
    assert_validation_error(contract_client.put(f"{CAMPANIAS_PATH}/abc", json=VALID_BODY))


@pytest.mark.parametrize("campania_id", ["abc", "0", "-1"])
def test_post_activar_campania_invalid_id_returns_400(
    contract_client: TestClient, campania_id: str
) -> None:
    assert_validation_error(contract_client.post(f"{CAMPANIAS_PATH}/{campania_id}/activar"))


def test_delete_campania_is_not_allowed(contract_client: TestClient) -> None:
    assert contract_client.delete(f"{CAMPANIAS_PATH}/7").status_code == 405


def test_planes_campania_dto_matches_domain_subset() -> None:
    assert set(PLANES_CAMPANIA_DTO) == PLANES_CAMPANIA


def test_openapi_campanias_operations_declare_examples(openapi_spec: dict[str, Any]) -> None:
    lista = list[CampaniaDTO]
    assert_operation_contract(openapi_spec, "get", CAMPANIAS_PATH, 200, (403,), lista)
    post = assert_operation_contract(
        openapi_spec, "post", CAMPANIAS_PATH, 201, (400, 403), CampaniaDTO
    )
    put = assert_operation_contract(
        openapi_spec,
        "put",
        "/api/v1/campanias/{campania_id}",
        200,
        (400, 403, 404),
        CampaniaDTO,
    )
    assert_operation_contract(
        openapi_spec,
        "post",
        "/api/v1/campanias/{campania_id}/inactivar",
        200,
        (400, 403, 404),
        CampaniaDTO,
    )
    activar = assert_operation_contract(
        openapi_spec,
        "post",
        "/api/v1/campanias/{campania_id}/activar",
        200,
        (400, 403, 404),
        CampaniaDTO,
    )
    assert json_example(activar, 200)["activa"] is True
    assert json_example(activar, 404)["error"]["message"] == "La campana no existe."
    assert "requestBody" not in activar
    assert_operation_contract(
        openapi_spec,
        "get",
        "/api/v1/predicciones/{prediccion_id}/campanias-sugeridas",
        200,
        (400, 403, 404),
        lista,
    )

    assert request_body_schema_name(post) == "CampaniaEntradaDTO"
    assert request_body_schema_name(put) == "CampaniaEntradaDTO"
    assert openapi_spec["components"]["schemas"]["CampaniaEntradaDTO"].get("examples")
    assert "delete" not in openapi_spec["paths"]["/api/v1/campanias/{campania_id}"]


def test_openapi_campania_planes_exclude_diario(openapi_spec: dict[str, Any]) -> None:
    assert "DIARIO" not in str(openapi_spec["components"]["schemas"]["CampaniaEntradaDTO"])


def test_put_campania_invalid_body_returns_400(contract_client: TestClient) -> None:
    body = {**VALID_BODY, "planes": ["DIARIO"]}

    assert_validation_error(contract_client.put(f"{CAMPANIAS_PATH}/7", json=body))


def test_openapi_campania_dto_planes_exclude_diario(openapi_spec: dict[str, Any]) -> None:
    assert "DIARIO" not in str(openapi_spec["components"]["schemas"]["CampaniaDTO"])
