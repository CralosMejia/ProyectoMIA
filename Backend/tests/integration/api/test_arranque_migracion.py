"""Lanzamiento de la migracion historica en segundo plano al arrancar (T13, ADR-004).

App real contra PostgreSQL de pruebas con los libros sinteticos. Nombres inventados.
Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

import logging
import threading
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from app.application.sistema.ports import RegistroMigracion, ResultadoMigracion
from app.core.config import Settings
from app.domain.common.predictor import FeatureRow, TrainedModel
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.main import NOMBRE_HILO_MIGRACION, create_app, ejecutar_migracion_segura
from tests.integration.sistema.migracion_sintetica import CARPETA_LIBROS, limpiar_base

pytestmark = pytest.mark.integration

NOMBRE_SECRETO = "Nombre Ficticio Secreto"
ESTADO = "/api/v1/sistema/estado"
HEALTH = "/api/v1/health"


class PredictorRetenido(RandomForestPredictor):
    """Retiene el entrenamiento hasta que ``soltar`` se activa."""

    def __init__(self, soltar: threading.Event) -> None:
        super().__init__()
        self._soltar = soltar

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        self._soltar.wait(timeout=60)
        return super().train(features, labels, numericas, categoricas, referencia)


class PredictorConDatoPersonal(RandomForestPredictor):
    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        raise RuntimeError(f"fallo con {NOMBRE_SECRETO}")


@pytest.fixture
def base_limpia(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_base(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def settings(url: URL, migrar: bool, carpeta: Path = CARPETA_LIBROS) -> Settings:
    return Settings(
        DATABASE_URL=SecretStr(url.render_as_string(hide_password=False)),
        APP_ENV="test",
        MIGRAR_HISTORICO_AL_ARRANCAR=migrar,
        HISTORICO_PATH=carpeta,
    )


def esperar_estado(client: TestClient, esperado: str, plazo: float = 60) -> dict[str, object]:
    limite = time.monotonic() + plazo
    while True:
        cuerpo: dict[str, object] = client.get(ESTADO).json()
        if cuerpo["estado"] == esperado or time.monotonic() > limite:
            return cuerpo
        time.sleep(0.2)


def hilos_de_migracion() -> list[threading.Thread]:
    return [h for h in threading.enumerate() if h.name == NOMBRE_HILO_MIGRACION]


def test_arranque_health_responde_mientras_migra_y_termina_listo(
    test_database_url: URL, base_limpia: Engine
) -> None:
    soltar = threading.Event()
    app = create_app(settings(test_database_url, True), predictor=PredictorRetenido(soltar))

    try:
        with TestClient(app, client=("127.0.0.1", 50000)) as client:
            inicio = time.monotonic()
            health = client.get(HEALTH)
            assert health.status_code == 200
            assert time.monotonic() - inicio < 2
            assert client.get(ESTADO).json()["estado"] == "INICIALIZANDO"

            soltar.set()
            cuerpo = esperar_estado(client, "LISTO")
            assert cuerpo["estado"] == "LISTO"
            assert cuerpo["migracion_historica"] == "COMPLETADA"
            app.state.hilo_migracion.join(timeout=30)
    finally:
        soltar.set()


def test_arranque_sin_migrar_no_lanza_ningun_hilo(
    test_database_url: URL, base_limpia: Engine
) -> None:
    app = create_app(settings(test_database_url, False))

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert not hasattr(app.state, "hilo_migracion")
        assert hilos_de_migracion() == []
        assert client.get(ESTADO).json()["estado"] == "INICIALIZANDO"
    registro: RegistroMigracion = app.state.registro_migracion
    assert registro.resultado is None


def test_arranque_sin_libros_devuelve_faltan_datos(
    test_database_url: URL, base_limpia: Engine, tmp_path: Path
) -> None:
    app = create_app(settings(test_database_url, True, carpeta=tmp_path))

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        app.state.hilo_migracion.join(timeout=30)
        cuerpo = client.get(ESTADO).json()

    assert cuerpo["estado"] == "FALTAN_DATOS_HISTORICOS"
    assert cuerpo["migracion_historica"] == "PENDIENTE"


def test_arranque_fallo_en_el_hilo_se_registra_sin_datos_personales(
    test_database_url: URL, base_limpia: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(settings(test_database_url, True), predictor=PredictorConDatoPersonal())

    with caplog.at_level(logging.INFO), TestClient(app, client=("127.0.0.1", 50000)) as client:
        app.state.hilo_migracion.join(timeout=60)
        assert client.get(HEALTH).status_code == 200
        cuerpo = client.get(ESTADO).json()

    assert cuerpo["estado"] == "FALTAN_DATOS_HISTORICOS"
    assert "RuntimeError" in caplog.text
    assert NOMBRE_SECRETO not in caplog.text


def test_ejecutar_migracion_segura_captura_y_registra_la_excepcion(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class MigracionQueExplota:
        def ejecutar(self) -> ResultadoMigracion:
            raise ValueError(f"dato {NOMBRE_SECRETO}")

    registro = RegistroMigracion()
    with caplog.at_level(logging.ERROR):
        ejecutar_migracion_segura(MigracionQueExplota(), registro)  # type: ignore[arg-type]  # doble estructural

    assert registro.resultado is ResultadoMigracion.FALLIDA
    assert "ValueError" in caplog.text
    assert NOMBRE_SECRETO not in caplog.text
