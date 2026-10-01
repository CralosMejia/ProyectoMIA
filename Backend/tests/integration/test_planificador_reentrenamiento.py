"""Planificador del reentrenamiento dentro del backend (CU-02, T10) contra PostgreSQL real.

El arranque de la aplicacion (``lifespan``) lanza el hilo; al salir de ``TestClient`` el
hilo termina despues de su primera revision, asi que los efectos ya estan en la base. Reloj
simulado (hoy = 2026-09-30 en Ecuador); datos sinteticos de ``reentrenamiento_datos``.
"""

import inspect
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.core.config import Settings
from app.domain.common.enums import ResultadoReentrenamiento
from app.infrastructure.planificador import reentrenamiento as modulo_planificador
from app.infrastructure.planificador.reentrenamiento import (
    NOMBRE_HILO,
    PlanificadorReentrenamiento,
)
from app.main import create_app
from tests.integration.reentrenamiento_datos import (
    HOY,
    Reloj,
    contar,
    limpiar_base,
    proxima_fecha,
    sembrar,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def base(migrated_engine: Engine) -> Iterator[Engine]:
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def _settings(url: URL, automatico: bool) -> Settings:
    return Settings(
        DATABASE_URL=SecretStr(url.render_as_string(hide_password=False)),
        APP_ENV="test",
        MIGRAR_HISTORICO_AL_ARRANCAR=False,
        REENTRENAMIENTO_AUTOMATICO=automatico,
    )


def _arrancar_y_apagar(url: URL, reloj: Reloj, automatico: bool = True) -> threading.Thread | None:
    app = create_app(_settings(url, automatico), clock=reloj)
    with TestClient(app, client=("127.0.0.1", 50000)):
        planificador = app.state.planificador_reentrenamiento
        hilo = planificador.hilo if planificador is not None else None
    return hilo


def _intentos(engine: Engine, resultado: str) -> int:
    consultas = {
        "OMITIDO": "SELECT count(*) FROM intentos_reentrenamiento WHERE resultado = 'OMITIDO'",
        "ENTRENADO": (
            "SELECT count(*) FROM intentos_reentrenamiento "
            "WHERE resultado = 'ENTRENADO' AND disparador = 'PROGRAMADO'"
        ),
    }
    return contar(engine, consultas[resultado])


def test_arranque_tres_dias_despues_registra_un_omitido_y_no_lo_repite(
    base: Engine, test_database_url: URL
) -> None:
    perdida = HOY - timedelta(days=3)
    sembrar(base, programada=perdida)

    _arrancar_y_apagar(test_database_url, Reloj())

    assert _intentos(base, "OMITIDO") == 1
    assert proxima_fecha(base) == date(2027, 3, 27)
    assert contar(base, "SELECT count(*) FROM modelos") == 1

    _arrancar_y_apagar(test_database_url, Reloj())

    assert _intentos(base, "OMITIDO") == 1
    assert proxima_fecha(base) == date(2027, 3, 27)


def test_arranque_en_la_fecha_programada_entrena_sin_intervencion(
    base: Engine, test_database_url: URL
) -> None:
    sembrar(base, programada=HOY)

    _arrancar_y_apagar(test_database_url, Reloj())

    assert _intentos(base, "ENTRENADO") == 1
    assert contar(base, "SELECT count(*) FROM modelos") == 2
    assert contar(base, "SELECT version FROM modelos WHERE vigente") == 2
    assert proxima_fecha(base) == date(2027, 3, 30)


def test_arranque_con_fecha_futura_no_escribe_nada(base: Engine, test_database_url: URL) -> None:
    sembrar(base, programada=date(2027, 3, 30))

    _arrancar_y_apagar(test_database_url, Reloj())

    assert contar(base, "SELECT count(*) FROM intentos_reentrenamiento") == 1  # el INICIAL
    assert contar(base, "SELECT count(*) FROM modelos") == 1
    assert proxima_fecha(base) == date(2027, 3, 30)


def test_reentrenamiento_automatico_false_no_lanza_el_hilo(
    base: Engine, test_database_url: URL
) -> None:
    sembrar(base, programada=HOY - timedelta(days=3))
    app = create_app(_settings(test_database_url, automatico=False), clock=Reloj())

    with TestClient(app, client=("127.0.0.1", 50000)):
        assert app.state.planificador_reentrenamiento is None
        assert NOMBRE_HILO not in {h.name for h in threading.enumerate()}

    assert contar(base, "SELECT count(*) FROM intentos_reentrenamiento") == 1


def test_al_apagar_la_app_el_hilo_termina(base: Engine, test_database_url: URL) -> None:
    sembrar(base, programada=date(2027, 3, 30))

    hilo = _arrancar_y_apagar(test_database_url, Reloj())

    assert hilo is not None
    assert hilo.daemon is True
    assert not hilo.is_alive()


# ---------------------------------------------------------------- vueltas del planificador


@dataclass
class ServicioDoble:
    respuestas: list[ResultadoReentrenamientoDTO | Exception]
    llamadas: int = 0
    vistos: list[int] = field(default_factory=list)

    def revisar_programado(self) -> ResultadoReentrenamientoDTO:
        self.llamadas += 1
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


NADA = ResultadoReentrenamientoDTO(resultado=None, motivo="Hoy no toca.")


def test_revisa_una_sola_vez_por_dia_de_negocio() -> None:
    reloj = Reloj(datetime(2026, 9, 30, 15, 0, tzinfo=UTC))
    servicio = ServicioDoble([NADA, NADA])
    planificador = PlanificadorReentrenamiento(servicio, reloj)

    planificador.revisar_si_cambio_el_dia()
    reloj.instante = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)  # aun 30-09 en Ecuador
    planificador.revisar_si_cambio_el_dia()
    assert servicio.llamadas == 1

    reloj.instante = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)  # ya 01-10
    planificador.revisar_si_cambio_el_dia()
    assert servicio.llamadas == 2


def test_error_o_bloqueo_ocupado_se_reintenta_en_la_siguiente_vuelta(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ocupado = ResultadoReentrenamientoDTO(resultado=None, motivo="x", en_curso=True)
    hecho = ResultadoReentrenamientoDTO(
        resultado=ResultadoReentrenamiento.OMITIDO, motivo="Se omitio."
    )
    servicio = ServicioDoble([RuntimeError("detalle con dato 1799999999"), ocupado, hecho])
    planificador = PlanificadorReentrenamiento(servicio, Reloj())

    for _ in range(4):
        planificador.revisar_si_cambio_el_dia()

    assert servicio.llamadas == 3
    assert "RuntimeError" in caplog.text
    assert "1799999999" not in caplog.text


def test_planificador_no_migra_ni_crea_tablas() -> None:
    fuente = inspect.getsource(modulo_planificador)

    for prohibido in ("create_all", "alembic", "ALTER", "datetime.now", "date.today"):
        assert prohibido not in fuente
