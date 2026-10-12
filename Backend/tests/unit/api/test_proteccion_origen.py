"""S1 (R-013): filtro de ``Host`` (DNS rebinding) y de ``Origin`` (CSRF) sin base de datos.

Se monta sobre una app Starlette minima; las pruebas con la app real estan en
``tests/integration/api/test_proteccion_origen_api.py``.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from app.api.proteccion_origen import FiltroHostYOrigen

pytestmark = pytest.mark.unit

HOSTS = ("localhost", "127.0.0.1", "testserver")
ORIGENES = ("http://localhost:5173",)
CUERPO_403 = {
    "error": {"code": "forbidden", "message": "El acceso no esta permitido desde este equipo."}
}


async def _ok(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


@pytest.fixture
def cliente() -> TestClient:
    app = Starlette(routes=[Route("/r", _ok, methods=["GET", "HEAD", "OPTIONS", "POST", "PUT"])])
    protegida = FiltroHostYOrigen(app, hosts=HOSTS, origenes=ORIGENES)
    return TestClient(protegida, base_url="http://localhost:8080")


def test_get_with_allowed_host_and_port_passes(cliente: TestClient) -> None:
    assert cliente.get("/r").status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8080", "localhost.evil", ""])
def test_get_with_unlisted_host_returns_400_unique_format(cliente: TestClient, host: str) -> None:
    respuesta = cliente.get("/r", headers={"Host": host})

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "bad_request"
    assert host == "" or host not in respuesta.text


def test_host_comparison_is_case_insensitive(cliente: TestClient) -> None:
    assert cliente.get("/r", headers={"Host": "LOCALHOST:8080"}).status_code == 200


def test_post_from_foreign_origin_returns_403_unique_format(cliente: TestClient) -> None:
    respuesta = cliente.post("/r", headers={"Origin": "http://evil.example"})

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


@pytest.mark.parametrize("origen", ["null", "http://localhost:9999", "https://localhost:8080"])
def test_post_from_other_origin_on_same_machine_returns_403(
    cliente: TestClient, origen: str
) -> None:
    assert cliente.post("/r", headers={"Origin": origen}).status_code == 403


def test_post_same_origin_as_host_passes(cliente: TestClient) -> None:
    respuesta = cliente.post("/r", headers={"Origin": "http://localhost:8080"})

    assert respuesta.status_code == 200


def test_post_from_listed_cors_origin_passes(cliente: TestClient) -> None:
    assert cliente.post("/r", headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_post_without_origin_nor_fetch_metadata_passes(cliente: TestClient) -> None:
    assert cliente.post("/r").status_code == 200


def test_post_without_origin_and_cross_site_fetch_returns_403(cliente: TestClient) -> None:
    respuesta = cliente.post("/r", headers={"Sec-Fetch-Site": "cross-site"})

    assert respuesta.status_code == 403


def test_put_from_foreign_origin_returns_403(cliente: TestClient) -> None:
    assert cliente.put("/r", headers={"Origin": "http://evil.example"}).status_code == 403


@pytest.mark.parametrize("metodo", ["GET", "HEAD", "OPTIONS"])
def test_safe_methods_from_foreign_origin_are_not_blocked(cliente: TestClient, metodo: str) -> None:
    respuesta = cliente.request(metodo, "/r", headers={"Origin": "http://evil.example"})

    assert respuesta.status_code == 200
