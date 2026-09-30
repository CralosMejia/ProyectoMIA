"""Contrato de ``listas`` y su Excel (CU-04, CU-05, CU-12); el comportamiento, en
``test_listas_api.py`` y ``test_listas_excel_api.py``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO
from tests.integration.api.contract_helpers import (
    assert_operation_contract,
    assert_validation_error,
    operation,
    request_body_schema_name,
)

pytestmark = pytest.mark.integration

LISTAS_PATH = "/api/v1/listas"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.mark.parametrize(
    "body",
    [
        {"top_k": 0},
        {"horizonte_dias": 0},
        {"horizonte_dias": 32},
        {"horizonte_dias": 366},
        {"fecha_referencia": "x"},
    ],
)
def test_post_listas_invalid_body_returns_400(
    contract_client: TestClient, body: dict[str, Any]
) -> None:
    assert_validation_error(contract_client.post(LISTAS_PATH, json=body))


@pytest.mark.parametrize(
    "path", ["/api/v1/listas/abc", "/api/v1/listas/abc/excel", "/api/v1/listas/0"]
)
def test_get_listas_invalid_lista_id_returns_400(contract_client: TestClient, path: str) -> None:
    assert_validation_error(contract_client.get(path))


def test_generar_lista_dto_defaults() -> None:
    dto = GenerarListaDTO()

    assert dto.fecha_referencia is None
    assert dto.horizonte_dias == 30
    assert dto.top_k == 25


def test_openapi_post_listas_declares_body_and_examples(openapi_spec: dict[str, Any]) -> None:
    op = assert_operation_contract(
        openapi_spec,
        "post",
        LISTAS_PATH,
        201,
        (400, 403, 409, 422),
        success_type=ListaPriorizadaDTO,
    )

    assert request_body_schema_name(op) == "GenerarListaDTO"
    schema = openapi_spec["components"]["schemas"]["GenerarListaDTO"]
    assert schema.get("examples")
    assert schema["properties"]["horizonte_dias"]["maximum"] == 31
    assert op["responses"]["422"]["content"]["application/json"]["example"] == {
        "error": {
            "code": "domain_rule_violated",
            "message": "La fecha de la lista debe ser hoy o posterior.",
        }
    }


def test_openapi_prediccion_dto_has_cedula_and_no_correo(openapi_spec: dict[str, Any]) -> None:
    propiedades = openapi_spec["components"]["schemas"]["PrediccionDTO"]["properties"]

    assert "correo" not in propiedades
    assert "cedula" in propiedades


@pytest.mark.parametrize("path", ["/api/v1/listas/ultima", "/api/v1/listas/{lista_id}"])
def test_openapi_get_lista_declares_examples(openapi_spec: dict[str, Any], path: str) -> None:
    assert_operation_contract(
        openapi_spec, "get", path, 200, (403, 404), success_type=ListaPriorizadaDTO
    )


def test_openapi_excel_declares_xlsx_content(openapi_spec: dict[str, Any]) -> None:
    path = "/api/v1/listas/{lista_id}/excel"
    assert_operation_contract(openapi_spec, "get", path, 200, (400, 403, 404))

    content = operation(openapi_spec, "get", path)["responses"]["200"]["content"]
    assert XLSX in content
    assert content[XLSX]["schema"] == {"type": "string", "format": "binary"}


def test_lista_priorizada_example_serializes_score_as_string(
    openapi_spec: dict[str, Any],
) -> None:
    op = operation(openapi_spec, "get", "/api/v1/listas/ultima")
    example = op["responses"]["200"]["content"]["application/json"]["example"]

    dto = ListaPriorizadaDTO.model_validate(example)
    dumped = dto.model_dump(mode="json")
    assert isinstance(dumped["items"][0]["score"], str)
    assert isinstance(dumped["umbral_alto"], str)


def test_lista_priorizada_example_has_cedula_and_no_correo(openapi_spec: dict[str, Any]) -> None:
    op = operation(openapi_spec, "post", LISTAS_PATH)
    example = op["responses"]["201"]["content"]["application/json"]["example"]

    assert all("correo" not in item for item in example["items"])
    assert all(isinstance(item["cedula"], str) for item in example["items"])
