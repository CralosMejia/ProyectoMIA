"""S1 (R-013): ``Host`` y ``Origin`` con la app real contra PostgreSQL real.

Reproduce los vectores de la revision SEC-1: DNS rebinding (``Host`` ajeno) y CSRF con
peticiones "simples" desde otra pagina (``POST`` multipart o sin cuerpo con ``Origin`` ajeno).
Aislamiento entre usuarios: NO APLICA (RT-12, sin login; CU-00). Datos sinteticos.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL

from app.core.config import Settings
from app.main import create_app
from tests.fixtures.generar_fixtures import DIR_PLANTILLAS, PLANTILLA_VALIDA
from tests.integration.api.listas_datos import fijar_reloj_api

pytestmark = pytest.mark.integration

EVIL = "http://evil.example"
CARGAS = "/api/v1/cargas"
VISTA_PREVIA = "/api/v1/cargas/vista-previa"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CUERPO_403 = {
    "error": {"code": "forbidden", "message": "El acceso no esta permitido desde este equipo."}
}


def _archivo() -> dict[str, Any]:
    return {"archivo": ("plantilla.xlsx", (DIR_PLANTILLAS / PLANTILLA_VALIDA).read_bytes(), XLSX)}


def _cargas(engine: Engine) -> int:
    with engine.connect() as conexion:
        return int(conexion.execute(text("SELECT count(*) FROM cargas")).scalar_one())


@pytest.fixture
def app(test_database_url: URL, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Configuracion por defecto (sin ``testserver``): la que corre en Docker."""
    monkeypatch.delenv("HOSTS_PERMITIDOS", raising=False)
    settings = Settings(
        DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
        APP_ENV="test",
        CORS_ORIGINS=["http://localhost:5173"],
    )
    application = create_app(settings)
    fijar_reloj_api(application)
    return application


@pytest.fixture
def navegador(app: FastAPI, base_migrada: Engine) -> Iterator[TestClient]:
    """Como el frontend en Docker: nginx reenvia ``Host: localhost:8080``."""
    with TestClient(
        app,
        base_url="http://localhost:8080",
        client=("127.0.0.1", 50000),
        raise_server_exceptions=False,
    ) as cliente:
        yield cliente


def test_post_cargas_from_foreign_origin_returns_403_and_saves_nothing(
    navegador: TestClient, base_migrada: Engine
) -> None:
    antes = _cargas(base_migrada)

    respuesta = navegador.post(CARGAS, files=_archivo(), headers={"Origin": EVIL})

    assert respuesta.status_code == 403
    assert respuesta.json() == CUERPO_403
    assert "access-control-allow-origin" not in respuesta.headers
    assert _cargas(base_migrada) == antes


@pytest.mark.parametrize("accion", ["inactivar", "activar"])
def test_post_campania_action_without_body_from_foreign_origin_returns_403(
    navegador: TestClient, accion: str
) -> None:
    respuesta = navegador.post(f"/api/v1/campanias/1/{accion}", headers={"Origin": EVIL})

    assert respuesta.status_code == 403


def test_post_without_origin_but_cross_site_fetch_returns_403(navegador: TestClient) -> None:
    respuesta = navegador.post(
        VISTA_PREVIA, files=_archivo(), headers={"Sec-Fetch-Site": "cross-site"}
    )

    assert respuesta.status_code == 403


@pytest.mark.parametrize(
    "ruta", ["/api/v1/listas/ultima", "/api/v1/sistema/estado", "/api/v1/gestiones"]
)
def test_get_with_rebound_host_returns_400_not_data(navegador: TestClient, ruta: str) -> None:
    respuesta = navegador.get(ruta, headers={"Host": "atacante.tld:8080"})

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "bad_request"
    assert "atacante" not in respuesta.text


def test_get_with_local_hosts_passes(navegador: TestClient) -> None:
    for host in ("localhost:8080", "127.0.0.1:8081", "localhost:8081", "127.0.0.1:8000"):
        assert navegador.get("/api/v1/sistema/estado", headers={"Host": host}).status_code == 200


def test_post_vista_previa_same_origin_from_frontend_passes(navegador: TestClient) -> None:
    respuesta = navegador.post(
        VISTA_PREVIA, files=_archivo(), headers={"Origin": "http://localhost:8080"}
    )

    assert respuesta.status_code == 200


def test_post_vista_previa_same_origin_from_e2e_stack_passes(navegador: TestClient) -> None:
    respuesta = navegador.post(
        VISTA_PREVIA,
        files=_archivo(),
        headers={"Host": "localhost:8081", "Origin": "http://localhost:8081"},
    )

    assert respuesta.status_code == 200


def test_post_vista_previa_from_listed_cors_origin_passes(navegador: TestClient) -> None:
    respuesta = navegador.post(
        VISTA_PREVIA, files=_archivo(), headers={"Origin": "http://localhost:5173"}
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_from_docker_healthcheck_host_passes(app: FastAPI) -> None:
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 1)) as cliente:
        assert cliente.get("/api/v1/health").status_code == 200
