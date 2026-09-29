"""Contrato de ``cargas`` (CU-01): vista previa y confirmacion, publicados en ``501``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.cargas.dtos import CargaDTO, VistaPreviaCargaDTO
from tests.integration.api.contract_helpers import (
    assert_not_implemented,
    assert_operation_contract,
    assert_validation_error,
)

pytestmark = pytest.mark.integration

VISTA_PREVIA_PATH = "/api/v1/cargas/vista-previa"
CARGAS_PATH = "/api/v1/cargas"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _archivo() -> dict[str, tuple[str, bytes, str]]:
    return {"archivo": ("plantilla.xlsx", b"PK\x03\x04contenido", XLSX)}


@pytest.mark.parametrize("path", [VISTA_PREVIA_PATH, CARGAS_PATH])
def test_post_carga_with_file_returns_501(contract_client: TestClient, path: str) -> None:
    assert_not_implemented(contract_client.post(path, files=_archivo()))


@pytest.mark.parametrize("path", [VISTA_PREVIA_PATH, CARGAS_PATH])
def test_post_carga_without_archivo_returns_400_validation_error(
    contract_client: TestClient, path: str
) -> None:
    response = contract_client.post(path, files={"otro": ("a.xlsx", b"x", XLSX)})

    assert_validation_error(response)


def test_openapi_vista_previa_declares_multipart_and_examples(
    openapi_spec: dict[str, Any],
) -> None:
    op = assert_operation_contract(
        openapi_spec,
        "post",
        VISTA_PREVIA_PATH,
        200,
        (400, 403, 409, 413, 501),
        success_type=VistaPreviaCargaDTO,
    )

    assert "multipart/form-data" in op["requestBody"]["content"]


def test_openapi_confirmar_carga_declares_multipart_and_examples(
    openapi_spec: dict[str, Any],
) -> None:
    op = assert_operation_contract(
        openapi_spec,
        "post",
        CARGAS_PATH,
        201,
        (400, 403, 409, 413, 422, 501),
        success_type=CargaDTO,
    )

    assert "multipart/form-data" in op["requestBody"]["content"]
