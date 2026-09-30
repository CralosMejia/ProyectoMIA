"""Contrato OpenAPI de ``GET /api/v1/sistema/estado`` (CU-03); ya no responde ``501`` (T14).

El comportamiento real se prueba en ``test_sistema_api.py``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from pydantic import TypeAdapter

from app.application.sistema.dtos import EstadoSistemaDTO
from tests.integration.api.contract_helpers import assert_operation_contract

pytestmark = pytest.mark.integration

PATH = "/api/v1/sistema/estado"


def test_openapi_estado_sistema_declares_examples_and_schema(
    openapi_spec: dict[str, Any],
) -> None:
    op = assert_operation_contract(openapi_spec, "get", PATH, 200, (403,))

    assert "501" not in op["responses"]
    ejemplos = op["responses"]["200"]["content"]["application/json"]["examples"]
    estados = set()
    for ejemplo in ejemplos.values():
        dto = TypeAdapter(EstadoSistemaDTO).validate_python(ejemplo["value"])
        estados.add(dto.estado)
    assert estados == {"INICIALIZANDO", "FALTAN_DATOS_HISTORICOS", "LISTO"}
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
