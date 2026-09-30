"""Contrato de ``cargas`` (CU-01): vista previa y confirmacion (R-007 T10, sin ``501``).

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.cargas.dtos import CargaDTO, VistaPreviaCargaDTO
from tests.integration.api.contract_helpers import (
    assert_operation_contract,
    assert_validation_error,
    json_example,
)

pytestmark = pytest.mark.integration

VISTA_PREVIA_PATH = "/api/v1/cargas/vista-previa"
CARGAS_PATH = "/api/v1/cargas"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MENSAJE_409 = "La migracion del historico aun no se ha completado."
MENSAJE_413 = "El archivo supera el tamaño máximo permitido."
MENSAJE_422 = "Hay filas con error; corrija el archivo y vuelva a subirlo."


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
        (400, 403, 409, 413),
        success_type=VistaPreviaCargaDTO,
    )

    assert "multipart/form-data" in op["requestBody"]["content"]
    assert "501" not in op["responses"]
    assert json_example(op, 400)["error"]["code"] == "validation_error"
    assert json_example(op, 409) == {"error": {"code": "conflict", "message": MENSAJE_409}}
    assert json_example(op, 413) == {"error": {"code": "payload_too_large", "message": MENSAJE_413}}


def test_openapi_confirmar_carga_declares_multipart_and_examples(
    openapi_spec: dict[str, Any],
) -> None:
    op = assert_operation_contract(
        openapi_spec,
        "post",
        CARGAS_PATH,
        201,
        (400, 403, 409, 413, 422),
        success_type=CargaDTO,
    )

    assert "multipart/form-data" in op["requestBody"]["content"]
    assert "501" not in op["responses"]
    assert json_example(op, 409)["error"]["message"] == MENSAJE_409
    assert json_example(op, 413)["error"]["message"] == MENSAJE_413
    assert json_example(op, 422) == {
        "error": {"code": "domain_rule_violated", "message": MENSAJE_422}
    }
