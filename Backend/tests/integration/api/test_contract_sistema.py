"""Contrato de ``GET /api/v1/sistema/estado`` (CU-03, "Inicializando"), publicado en ``501``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.sistema.dtos import EstadoSistemaDTO
from tests.integration.api.contract_helpers import (
    assert_not_implemented,
    assert_operation_contract,
)

pytestmark = pytest.mark.integration

PATH = "/api/v1/sistema/estado"


def test_get_estado_sistema_returns_501_not_implemented(contract_client: TestClient) -> None:
    assert_not_implemented(contract_client.get(PATH))


def test_openapi_estado_sistema_declares_examples_and_schema(
    openapi_spec: dict[str, Any],
) -> None:
    op = assert_operation_contract(
        openapi_spec, "get", PATH, 200, (403, 501), success_type=EstadoSistemaDTO
    )

    schema = op["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/EstadoSistemaDTO")
    assert "EstadoSistemaDTO" in openapi_spec["components"]["schemas"]


def test_estado_sistema_dto_rejects_unknown_estado() -> None:
    with pytest.raises(ValueError, match="estado"):
        EstadoSistemaDTO.model_validate(
            {
                "estado": "OTRO",
                "migracion_historica": "COMPLETADA",
                "modelo_vigente": None,
                "ultima_carga_en": None,
                "proxima_fecha_reentrenamiento": None,
            }
        )


def test_openapi_estado_sistema_dto_declares_the_three_states(
    openapi_spec: dict[str, Any],
) -> None:
    rendered = str(openapi_spec["components"]["schemas"])

    for estado in ("INICIALIZANDO", "FALTAN_DATOS_HISTORICOS", "LISTO"):
        assert estado in rendered
