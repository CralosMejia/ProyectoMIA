"""Contrato de ``listas`` y su Excel (CU-04, CU-05, CU-12), publicados en ``501``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO
from tests.integration.api.contract_helpers import (
    assert_not_implemented,
    assert_operation_contract,
    assert_validation_error,
    operation,
    request_body_schema_name,
)

pytestmark = pytest.mark.integration

LISTAS_PATH = "/api/v1/listas"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_post_listas_valid_body_returns_501(contract_client: TestClient) -> None:
    body = {"fecha_referencia": "2026-09-28", "horizonte_dias": 30, "top_k": 25}

    assert_not_implemented(contract_client.post(LISTAS_PATH, json=body))


def test_post_listas_empty_body_uses_defaults_and_returns_501(
    contract_client: TestClient,
) -> None:
    assert_not_implemented(contract_client.post(LISTAS_PATH, json={}))


@pytest.mark.parametrize(
    "body",
    [{"top_k": 0}, {"horizonte_dias": 0}, {"horizonte_dias": 366}, {"fecha_referencia": "x"}],
)
def test_post_listas_invalid_body_returns_400(
    contract_client: TestClient, body: dict[str, Any]
) -> None:
    assert_validation_error(contract_client.post(LISTAS_PATH, json=body))


@pytest.mark.parametrize(
    "path", ["/api/v1/listas/ultima", "/api/v1/listas/42", "/api/v1/listas/42/excel"]
)
def test_get_listas_valid_path_returns_501(contract_client: TestClient, path: str) -> None:
    assert_not_implemented(contract_client.get(path))


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
        (400, 403, 409, 501),
        success_type=ListaPriorizadaDTO,
    )

    assert request_body_schema_name(op) == "GenerarListaDTO"
    schema = openapi_spec["components"]["schemas"]["GenerarListaDTO"]
    assert schema.get("examples")


@pytest.mark.parametrize("path", ["/api/v1/listas/ultima", "/api/v1/listas/{lista_id}"])
def test_openapi_get_lista_declares_examples(openapi_spec: dict[str, Any], path: str) -> None:
    assert_operation_contract(
        openapi_spec, "get", path, 200, (403, 404, 501), success_type=ListaPriorizadaDTO
    )


def test_openapi_excel_declares_xlsx_content(openapi_spec: dict[str, Any]) -> None:
    path = "/api/v1/listas/{lista_id}/excel"
    assert_operation_contract(openapi_spec, "get", path, 200, (400, 403, 404, 501))

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
