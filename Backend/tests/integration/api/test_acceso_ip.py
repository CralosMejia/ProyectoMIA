"""CU-00: filtro de acceso por IP (T13) con la app real contra PostgreSQL real.

La IP del cliente se fija con ``TestClient(client=(ip, puerto))``: es la IP de la conexion,
la unica que mira el filtro.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.integration

LOCAL = ("127.0.0.1", 50000)
AJENA = ("10.0.0.5", 50000)
CUERPO_403 = {
    "error": {
        "code": "forbidden",
        "message": "El acceso no esta permitido desde este equipo.",
    }
}


def _app(url: URL, ips: str | None = None) -> FastAPI:
    extra: dict[str, object] = {} if ips is None else {"IPS_PERMITIDAS": ips}
    settings = Settings(
        DATABASE_URL=SecretStr(url.render_as_string(hide_password=False)),
        APP_ENV="test",
        **extra,  # type: ignore[arg-type]  # el validador convierte el texto en redes
    )
    return create_app(settings)


@pytest.fixture(autouse=True)
def _esquema(migrated_engine: Engine) -> None:
    """Base en ``head``: ``/sistema/estado`` lee ``estado_sistema``."""


@pytest.fixture
def app(test_database_url: URL) -> FastAPI:
    return _app(test_database_url)


@pytest.fixture
def ajeno(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, client=AJENA, raise_server_exceptions=False) as cliente:
        yield cliente


def test_ip_local_recibe_respuesta_normal(app: FastAPI) -> None:
    with TestClient(app, client=LOCAL) as cliente:
        respuesta = cliente.get("/api/v1/sistema/estado")

    assert respuesta.status_code == 200


def test_ip_no_autorizada_recibe_403_con_formato_unico_y_sin_detalles(
    ajeno: TestClient,
) -> None:
    respuesta = ajeno.get("/api/v1/sistema/estado")

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert set(respuesta.headers) == {"content-type", "content-length"}


def test_x_forwarded_for_autorizada_no_abre_el_acceso(ajeno: TestClient) -> None:
    for cabecera in ("X-Forwarded-For", "Forwarded", "X-Real-IP"):
        valor = "for=127.0.0.1" if cabecera == "Forwarded" else "127.0.0.1"
        respuesta = ajeno.get("/api/v1/sistema/estado", headers={cabecera: valor})
        assert respuesta.status_code == 403, cabecera


def test_health_desde_ip_no_autorizada_responde_normal(ajeno: TestClient) -> None:
    respuesta = ajeno.get("/api/v1/health")

    assert respuesta.status_code in (200, 503)
    assert respuesta.json() != CUERPO_403


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("GET", "/api/v1/health/x"),
        ("GET", "/api/v1/health/"),
        ("POST", "/api/v1/health"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
        ("OPTIONS", "/api/v1/sistema/estado"),
        ("GET", "/no-existe"),
    ],
)
def test_otras_rutas_y_metodos_desde_ip_no_autorizada_dan_403(
    ajeno: TestClient, metodo: str, ruta: str
) -> None:
    respuesta = ajeno.request(
        metodo,
        ruta,
        headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "GET"},
    )

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403


def test_rango_cidr_autoriza_una_ip_del_rango(test_database_url: URL) -> None:
    app = _app(test_database_url, "127.0.0.1, 172.30.0.0/24")

    with TestClient(app, client=("172.30.0.9", 50000)) as dentro:
        assert dentro.get("/api/v1/sistema/estado").status_code == 200
    with TestClient(app, client=("172.30.1.9", 50000)) as fuera:
        assert fuera.get("/api/v1/sistema/estado").status_code == 403


def test_cambiar_la_configuracion_y_crear_otra_app_cambia_el_resultado(
    test_database_url: URL,
) -> None:
    antes = _app(test_database_url)
    despues = _app(test_database_url, "10.0.0.5")

    with TestClient(antes, client=AJENA) as cliente:
        assert cliente.get("/api/v1/sistema/estado").status_code == 403
    with TestClient(despues, client=AJENA) as cliente:
        assert cliente.get("/api/v1/sistema/estado").status_code == 200
    with TestClient(despues, client=LOCAL) as cliente:
        assert cliente.get("/api/v1/sistema/estado").status_code == 403


def test_cliente_sin_ip_valida_recibe_403(app: FastAPI) -> None:
    with TestClient(app, raise_server_exceptions=False) as cliente:  # host "testclient"
        respuesta = cliente.get("/api/v1/sistema/estado")

    assert respuesta.status_code == 403
