"""GET /api/v1/health contra PostgreSQL real.

Aislamiento entre usuarios: NO APLICA. El endpoint es publico, no requiere
autenticacion y no expone ni consulta datos de ningun usuario, por lo que la
prueba de "un usuario no accede a datos de otro" no tiene objeto aqui.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import URL

from app.api.dependencies import get_clock, get_database_probe
from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

HEALTH_PATH = "/api/v1/health"
FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)


class _FixedClock:
    def now(self) -> datetime:
        return FIXED_NOW


class _DownProbe:
    def is_reachable(self) -> bool:
        return False


@pytest.fixture
def app(test_database_url: URL) -> FastAPI:
    settings = Settings(
        DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
        APP_ENV="test",
    )
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, client=("127.0.0.1", 50000)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_health_database_up_returns_200_ok(client: TestClient) -> None:
    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    checked_at = datetime.fromisoformat(body["checked_at"])
    assert checked_at.utcoffset() is not None
    assert checked_at.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_get_health_with_overridden_clock_returns_fixed_checked_at(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_clock] = _FixedClock

    response = client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "up",
        "checked_at": "2026-01-01T00:00:00Z",
    }


def test_get_health_database_down_returns_503_degraded(app: FastAPI, client: TestClient) -> None:
    app.dependency_overrides[get_clock] = _FixedClock
    app.dependency_overrides[get_database_probe] = _DownProbe

    response = client.get(HEALTH_PATH)

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "down",
        "checked_at": "2026-01-01T00:00:00Z",
    }


def test_openapi_documents_health_with_model_200_503_and_examples(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    operation = spec["paths"][HEALTH_PATH]["get"]
    responses = operation["responses"]
    assert {"200", "503"} <= responses.keys()
    for code in ("200", "503"):
        content = responses[code]["content"]["application/json"]
        assert content["schema"] == {"$ref": "#/components/schemas/HealthDTO"}
        examples = content.get("examples") or {}
        assert examples, f"la respuesta {code} debe tener ejemplos"
        for example in examples.values():
            assert set(example["value"]) == {"status", "database", "checked_at"}
    assert operation.get("security") is None


def test_get_health_is_public_without_authorization_header(client: TestClient) -> None:
    response = client.get(HEALTH_PATH, headers={})

    assert response.status_code == 200


def _free_local_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
    return port


@pytest.fixture
def unreachable_client(test_database_url: URL) -> Iterator[TestClient]:
    unreachable = test_database_url.set(host="127.0.0.1", port=_free_local_port())
    settings = Settings(
        DATABASE_URL=SecretStr(unreachable.render_as_string(hide_password=False)),
        APP_ENV="test",
    )
    down_app = create_app(settings)
    with TestClient(down_app, client=("127.0.0.1", 50000)) as test_client:
        yield test_client


def test_get_health_real_database_unreachable_returns_503_without_leaking_connection(
    unreachable_client: TestClient, test_database_url: URL
) -> None:
    # Sin sobrescribir la sonda: la cadena real router -> handler -> probe detecta la caida.
    response = unreachable_client.get(HEALTH_PATH)

    assert response.status_code == 503
    body = response.json()
    assert set(body) == {"status", "database", "checked_at"}
    assert body["status"] == "degraded"
    assert body["database"] == "down"
    assert datetime.fromisoformat(body["checked_at"]).utcoffset() is not None
    has_password = bool(test_database_url.password)
    assert has_password, "la URL de pruebas debe tener contrasena para validar que no se filtra"
    leaked = str(test_database_url.password) in response.text or "postgresql" in response.text
    assert not leaked, "la respuesta 503 no debe exponer datos de conexion"


def test_get_health_database_up_checked_at_serialized_as_utc_z_suffix(
    client: TestClient,
) -> None:
    response = client.get(HEALTH_PATH)

    assert response.json()["checked_at"].endswith("Z")


def test_openapi_health_examples_match_status_of_each_response(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    responses = spec["paths"][HEALTH_PATH]["get"]["responses"]

    ok_values = [
        e["value"] for e in responses["200"]["content"]["application/json"]["examples"].values()
    ]
    down_values = [
        e["value"] for e in responses["503"]["content"]["application/json"]["examples"].values()
    ]
    assert all(v["status"] == "ok" and v["database"] == "up" for v in ok_values)
    assert all(v["status"] == "degraded" and v["database"] == "down" for v in down_values)


def test_openapi_health_dto_schema_declares_the_three_fields(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    schema = spec["components"]["schemas"]["HealthDTO"]
    assert set(schema["required"]) == {"status", "database", "checked_at"}
    assert set(schema["properties"]["status"]["enum"]) == {"ok", "degraded"}
    assert set(schema["properties"]["database"]["enum"]) == {"up", "down"}


def test_post_health_method_not_allowed_returns_405(client: TestClient) -> None:
    response = client.post(HEALTH_PATH, json={"status": "ok"})

    assert response.status_code == 405


def test_get_health_ignores_user_supplied_query_and_returns_same_contract(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_clock] = _FixedClock

    response = client.get(HEALTH_PATH, params={"user_id": "otro", "database": "down"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "up",
        "checked_at": "2026-01-01T00:00:00Z",
    }


def test_get_health_concurrent_requests_all_return_200(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: client.get(HEALTH_PATH).status_code, range(24)))

    assert codes == [200] * 24
