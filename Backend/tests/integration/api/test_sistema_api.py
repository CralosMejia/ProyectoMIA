"""``GET /api/v1/sistema/estado`` real contra PostgreSQL de pruebas (T14).

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL

from app.application.sistema.ports import RegistroMigracion, ResultadoMigracion
from app.core.config import Settings
from app.main import create_app
from tests.fixtures import esperado
from tests.integration.sistema.migracion_sintetica import limpiar_base, migrar_sintetico

pytestmark = pytest.mark.integration

PATH = "/api/v1/sistema/estado"


@pytest.fixture
def base_limpia(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_base(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


@pytest.fixture
def app(test_database_url: URL, base_limpia: Engine) -> FastAPI:
    settings = Settings(
        DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
        APP_ENV="test",
        MIGRAR_HISTORICO_AL_ARRANCAR=False,
    )
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def registro(app: FastAPI) -> RegistroMigracion:
    valor: RegistroMigracion = app.state.registro_migracion
    return valor


def fijar_estado(engine: Engine, estado: str) -> None:
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE estado_sistema SET migracion_historica = :e WHERE id = 1"),
            {"e": estado},
        )


def test_get_estado_pendiente_sin_resultado_devuelve_inicializando(client: TestClient) -> None:
    respuesta = client.get(PATH)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "INICIALIZANDO",
        "migracion_historica": "PENDIENTE",
        "modelo_vigente": None,
        "ultima_carga_en": None,
        "proxima_fecha_reentrenamiento": None,
    }


def test_get_estado_en_curso_devuelve_inicializando(
    client: TestClient, base_limpia: Engine
) -> None:
    fijar_estado(base_limpia, "EN_CURSO")

    cuerpo = client.get(PATH).json()

    assert cuerpo["estado"] == "INICIALIZANDO"
    assert cuerpo["migracion_historica"] == "EN_CURSO"


def test_get_estado_hilo_en_curso_devuelve_inicializando(app: FastAPI, client: TestClient) -> None:
    registro(app).iniciar()

    assert client.get(PATH).json()["estado"] == "INICIALIZANDO"


@pytest.mark.parametrize("resultado", [ResultadoMigracion.FALTAN_DATOS, ResultadoMigracion.FALLIDA])
def test_get_estado_pendiente_con_fallo_devuelve_faltan_datos(
    app: FastAPI, client: TestClient, resultado: ResultadoMigracion
) -> None:
    registro(app).terminar(resultado)

    cuerpo = client.get(PATH).json()

    assert cuerpo["estado"] == "FALTAN_DATOS_HISTORICOS"
    assert cuerpo["migracion_historica"] == "PENDIENTE"


def test_get_estado_completada_devuelve_listo_con_modelo(
    client: TestClient, base_limpia: Engine
) -> None:
    assert migrar_sintetico(base_limpia) is ResultadoMigracion.COMPLETADA

    respuesta = client.get(PATH)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "LISTO"
    assert cuerpo["migracion_historica"] == "COMPLETADA"
    assert cuerpo["modelo_vigente"]["version"] == "v1"
    assert cuerpo["modelo_vigente"]["ciclos_entrenamiento"] == esperado.EVALUABLES
    assert cuerpo["modelo_vigente"]["fecha_entrenamiento"].startswith("2026-09-29T10:00:00")
    assert cuerpo["ultima_carga_en"].startswith("2026-09-29T10:00:00")
    assert cuerpo["proxima_fecha_reentrenamiento"] == "2027-03-29"
