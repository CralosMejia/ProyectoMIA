"""Contrato de ``gestiones`` y ``alertas`` (CU-08, CU-09, CU-10), publicados en ``501``.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.gestiones.dtos import (
    RESPUESTAS_ACEPTACION_DTO,
    RESPUESTAS_OFRECIMIENTO_DTO,
    RESPUESTAS_RENOVACION_DTO,
    AlertasDTO,
    GestionDTO,
    GestionResumenDTO,
)
from app.domain.common.enums import (
    RESPUESTAS_ACEPTACION,
    RESPUESTAS_OFRECIMIENTO,
    RESPUESTAS_RENOVACION,
)
from tests.integration.api.contract_helpers import (
    assert_not_implemented,
    assert_operation_contract,
    assert_validation_error,
    request_body_schema_name,
)

pytestmark = pytest.mark.integration

GESTIONES_PATH = "/api/v1/gestiones"
CREAR_BODY: dict[str, Any] = {
    "prediccion_id": 15,
    "campania_id": 3,
    "fecha_seguimiento": "2026-10-25",
    "responsable": "Andrea",
}
RESULTADO_BODY: dict[str, Any] = {
    "contactado": True,
    "campania_ofrecida": "SI",
    "campania_aceptada": "PENDIENTE",
    "renovo_declarado": "PENDIENTE",
    "fecha_contacto": "2026-10-20",
    "observaciones": "Pide que la llamen la proxima semana.",
    "responsable": "Andrea",
    "fecha_seguimiento": "2026-10-27",
}


def test_post_gestiones_valid_body_returns_501(contract_client: TestClient) -> None:
    assert_not_implemented(contract_client.post(GESTIONES_PATH, json=CREAR_BODY))


def test_post_gestiones_without_campania_returns_501(contract_client: TestClient) -> None:
    body = {"prediccion_id": 15, "fecha_seguimiento": "2026-10-25"}

    assert_not_implemented(contract_client.post(GESTIONES_PATH, json=body))


@pytest.mark.parametrize(
    "override",
    [
        {"prediccion_id": None},
        {"prediccion_id": 0},
        {"fecha_seguimiento": None},
        {"fecha_seguimiento": "25/10/2026"},
        {"responsable": "x" * 121},
    ],
)
def test_post_gestiones_invalid_body_returns_400(
    contract_client: TestClient, override: dict[str, Any]
) -> None:
    body = {**CREAR_BODY, **override}

    assert_validation_error(contract_client.post(GESTIONES_PATH, json=body))


def test_get_gestion_returns_501(contract_client: TestClient) -> None:
    assert_not_implemented(contract_client.get(f"{GESTIONES_PATH}/9"))


def test_get_gestion_invalid_id_returns_400(contract_client: TestClient) -> None:
    assert_validation_error(contract_client.get(f"{GESTIONES_PATH}/abc"))


def test_put_resultado_valid_body_returns_501(contract_client: TestClient) -> None:
    response = contract_client.put(f"{GESTIONES_PATH}/9/resultado", json=RESULTADO_BODY)

    assert_not_implemented(response)


@pytest.mark.parametrize(
    "override",
    [
        {"campania_ofrecida": "PENDIENTE"},
        {"campania_aceptada": "TALVEZ"},
        {"renovo_declarado": "NO_APLICA"},
        {"contactado": None},
        {"observaciones": "x" * 501},
    ],
)
def test_put_resultado_invalid_body_returns_400(
    contract_client: TestClient, override: dict[str, Any]
) -> None:
    body = {**RESULTADO_BODY, **override}

    response = contract_client.put(f"{GESTIONES_PATH}/9/resultado", json=body)

    assert_validation_error(response)


@pytest.mark.parametrize("filtro", ["vencidas", "hoy", "proximas"])
def test_get_gestiones_valid_filtro_returns_501(contract_client: TestClient, filtro: str) -> None:
    assert_not_implemented(contract_client.get(GESTIONES_PATH, params={"filtro": filtro}))


@pytest.mark.parametrize("params", [{"filtro": "todas"}, {"filtro": "HOY"}, {}])
def test_get_gestiones_invalid_filtro_returns_400(
    contract_client: TestClient, params: dict[str, str]
) -> None:
    assert_validation_error(contract_client.get(GESTIONES_PATH, params=params))


def test_get_alertas_returns_501(contract_client: TestClient) -> None:
    assert_not_implemented(contract_client.get("/api/v1/alertas"))


def test_respuestas_dto_match_domain_subsets() -> None:
    assert set(RESPUESTAS_OFRECIMIENTO_DTO) == RESPUESTAS_OFRECIMIENTO
    assert set(RESPUESTAS_ACEPTACION_DTO) == RESPUESTAS_ACEPTACION
    assert set(RESPUESTAS_RENOVACION_DTO) == RESPUESTAS_RENOVACION


def test_alertas_dto_rejects_negative_counters() -> None:
    with pytest.raises(ValueError, match="vencidas"):
        AlertasDTO(vencidas=-1, hoy=0, proximos_7_dias=0)


def test_openapi_gestiones_operations_declare_examples(openapi_spec: dict[str, Any]) -> None:
    crear = assert_operation_contract(
        openapi_spec, "post", GESTIONES_PATH, 201, (400, 403, 404, 409, 422, 501), GestionDTO
    )
    assert_operation_contract(
        openapi_spec, "get", "/api/v1/gestiones/{gestion_id}", 200, (400, 403, 404, 501), GestionDTO
    )
    resultado = assert_operation_contract(
        openapi_spec,
        "put",
        "/api/v1/gestiones/{gestion_id}/resultado",
        200,
        (400, 403, 404, 409, 422, 501),
        GestionDTO,
    )
    assert_operation_contract(
        openapi_spec, "get", GESTIONES_PATH, 200, (400, 403, 501), list[GestionResumenDTO]
    )
    assert_operation_contract(openapi_spec, "get", "/api/v1/alertas", 200, (403, 501), AlertasDTO)

    assert request_body_schema_name(crear) == "CrearGestionDTO"
    assert request_body_schema_name(resultado) == "RegistrarResultadoDTO"
    schemas = openapi_spec["components"]["schemas"]
    assert schemas["CrearGestionDTO"].get("examples")
    assert schemas["RegistrarResultadoDTO"].get("examples")


def test_post_gestiones_boundary_responsable_120_returns_501(
    contract_client: TestClient,
) -> None:
    body = {**CREAR_BODY, "responsable": "x" * 120}

    assert_not_implemented(contract_client.post(GESTIONES_PATH, json=body))


def test_put_resultado_boundary_observaciones_500_returns_501(
    contract_client: TestClient,
) -> None:
    body = {**RESULTADO_BODY, "observaciones": "x" * 500}

    response = contract_client.put(f"{GESTIONES_PATH}/9/resultado", json=body)

    assert_not_implemented(response)


def test_put_resultado_invalid_id_returns_400(contract_client: TestClient) -> None:
    response = contract_client.put(f"{GESTIONES_PATH}/abc/resultado", json=RESULTADO_BODY)

    assert_validation_error(response)
