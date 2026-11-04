"""Siembra de la grabacion (R-022/T9) contra un PostgreSQL real ``*_e2e``.

Necesita ``SEMBRAR_E2E_DATABASE_URL`` (base cuyo nombre termina en ``_e2e``, p. ej. un
PostgreSQL efimero sin volumen); sin ella la prueba de punta a punta se salta. La base se
deja en ``head`` desde cero (``downgrade base`` + ``upgrade head``): nunca la apuntes a una
base con datos que quieras conservar. Datos 100 % sinteticos (perfil ``grabacion``).
"""

import contextlib
import io
import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from scripts import generar_dataset_demo as generador
from scripts import sembrar_grabacion as siembra
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from app.application.dashboard.consultar_dashboard import ConsultarDashboard
from app.application.dashboard.dtos import DashboardDTO
from app.application.gestiones.consultar_alertas import ConsultarAlertas
from app.application.listas.consultar_listas import ConsultarListas
from app.application.sistema.migrar_historico import MigrarHistorico
from app.application.sistema.ports import RegistroMigracion, ResultadoMigracion
from app.domain.common.enums import NivelRiesgo
from app.domain.modelo.piloto import EstadoIndicador
from app.infrastructure.exportacion.excel_lista import ExcelListaOpenpyxl
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta
from app.infrastructure.ml.predictor_adoptado import PredictorAdoptado
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.repositories.dashboard import SqlAlchemyLectorDashboard
from app.infrastructure.persistence.repositories.seguimiento import SqlAlchemyLectorSeguimiento
from app.infrastructure.persistence.unit_of_work import (
    AbridorBloqueoMigracion,
    FabricaUnidadDeTrabajoSqlAlchemy,
)
from app.infrastructure.persistence.unit_of_work_listas import SqlAlchemyUnidadDeTrabajoListas

pytestmark = pytest.mark.integration

URL_ENV = "SEMBRAR_E2E_DATABASE_URL"
ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"
HOY = date(2026, 11, 3)
# 10:00 en Ecuador.
INSTANTE_HOY = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)
MESES_PASADOS = ("2026-07", "2026-08", "2026-09", "2026-10")


class RelojFijo:
    def __init__(self, instante: datetime) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


@dataclass(frozen=True, slots=True)
class BaseSembrada:
    engine: Engine
    carpeta: Path
    url: str
    salida: str


def _url() -> str:
    url = os.environ.get(URL_ENV, "").strip()
    if not url:
        pytest.skip(f"{URL_ENV} no definida (PostgreSQL efimero *_e2e)")
    if not (make_url(url).database or "").endswith("_e2e"):
        pytest.fail(f"{URL_ENV} debe apuntar a una base *_e2e", pytrace=False)
    return url


@pytest.fixture(scope="module")
def sembrada(tmp_path_factory: pytest.TempPathFactory) -> Iterator[BaseSembrada]:
    url = _url()
    carpeta = tmp_path_factory.mktemp("datos-grabacion")
    generador.main(
        ["--fecha-base", HOY.isoformat(), "--salida", str(carpeta), "--perfil", "grabacion"]
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        config = Config(str(ALEMBIC_INI))
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        engine = create_database_engine(url)
        reloj = RelojFijo(INSTANTE_HOY)
        migracion = MigrarHistorico(
            abrir_bloqueo=AbridorBloqueoMigracion(engine),
            unidad_de_trabajo=FabricaUnidadDeTrabajoSqlAlchemy(engine, reloj),
            localizador=LocalizadorLibrosCarpeta(carpeta),
            lector=LectorLibrosExcel(),
            predictor=PredictorAdoptado(),
            clock=reloj,
            registro=RegistroMigracion(),
        )
        assert migracion.ejecutar() is ResultadoMigracion.COMPLETADA
        capturada = _sembrar(carpeta)
        try:
            yield BaseSembrada(engine, carpeta, url, capturada)
        finally:
            engine.dispose()


def _sembrar(carpeta: Path) -> str:
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = siembra.main(["--datos", str(carpeta)], clock=RelojFijo(INSTANTE_HOY))
    assert codigo == 0, salida.getvalue()
    return salida.getvalue()


def _dashboard(engine: Engine, mes: str) -> DashboardDTO:
    return ConsultarDashboard(SqlAlchemyLectorDashboard(engine), RelojFijo(INSTANTE_HOY)).ejecutar(
        mes
    )


# ------------------------------------------------------------------ guardas (sin BD)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "no-es-una-url",
        "postgresql+psycopg://u:p@localhost:5432/app_db",
        "postgresql+psycopg://u:p@localhost:5432/app_db_test",
        "postgresql+psycopg://u:p@localhost:5432/app_e2e_copia",
    ],
)
def test_main_base_que_no_termina_en_e2e_sale_1_sin_conectarse(
    url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(
        siembra, "create_database_engine", lambda *_: pytest.fail("no debe conectarse")
    )
    assert siembra.main(["--datos", "."], clock=RelojFijo(INSTANTE_HOY)) == 1
    salida = capsys.readouterr().out
    assert "_e2e" in salida
    assert "u:p" not in salida


# ------------------------------------------------------------------ punta a punta


def test_meses_pasados_tienen_piloto_con_renovados_y_no_renovados(
    sembrada: BaseSembrada,
) -> None:
    for mes in ("2026-07", "2026-08"):
        piloto = _dashboard(sembrada.engine, mes).piloto
        assert piloto.estado is EstadoIndicador.COMPLETO, mes
        assert piloto.n_top == 25, mes
        tasa = piloto.tasa_renovacion_contactados
        assert tasa.n >= 12, mes
        # Credible: entre los contactados hay quien renovo y quien no.
        assert 0 < tasa.numerador < tasa.denominador, mes
        precision = piloto.precision_top25
        assert 0 < precision.numerador < precision.denominador, mes
        tramos = piloto.dias_anticipacion.tramos
        conteos = [
            tramos.quince_o_mas,
            tramos.de_ocho_a_catorce,
            tramos.de_uno_a_siete,
            tramos.mismo_dia_o_despues,
        ]
        assert sum(1 for c in conteos if c > 0) >= 3, mes
        assert sum(conteos) == piloto.dias_anticipacion.n, mes
    anterior = _dashboard(sembrada.engine, "2026-10").piloto
    assert anterior.estado in (EstadoIndicador.PARCIAL, EstadoIndicador.COMPLETO)


def test_embudo_de_cada_mes_pasado_es_coherente(sembrada: BaseSembrada) -> None:
    for mes in MESES_PASADOS:
        embudo = _dashboard(sembrada.engine, mes).embudo
        assert embudo.asignadas >= embudo.contactadas >= embudo.ofrecidas >= embudo.aceptadas
        assert embudo.aceptadas > 0, mes
        assert embudo.renovaron > 0, mes


def test_lista_de_hoy_tiene_nivel_alto_y_piloto_pendiente(sembrada: BaseSembrada) -> None:
    consultas = ConsultarListas(
        SqlAlchemyUnidadDeTrabajoListas(sembrada.engine, RelojFijo(INSTANTE_HOY)),
        ExcelListaOpenpyxl(),
    )
    ultima = consultas.ultima()
    assert ultima is not None
    assert ultima.fecha_generacion == HOY
    assert NivelRiesgo.ALTO in {item.nivel_riesgo for item in ultima.items}
    assert len(consultas.listar()) == len(MESES_PASADOS) + 1
    assert _dashboard(sembrada.engine, "2026-11").piloto.estado is EstadoIndicador.PENDIENTE


def test_siembra_no_deja_alertas(sembrada: BaseSembrada) -> None:
    alertas = ConsultarAlertas(
        SqlAlchemyLectorSeguimiento(sembrada.engine), RelojFijo(INSTANTE_HOY)
    ).ejecutar()
    assert (alertas.vencidas, alertas.hoy) == (0, 0)


def test_salida_solo_tiene_conteos(sembrada: BaseSembrada) -> None:
    assert "@example.com" not in sembrada.salida
    assert "0999" not in sembrada.salida
    assert sembrada.url not in sembrada.salida
    assert [linea.split(":")[0] for linea in sembrada.salida.splitlines()] == [
        *MESES_PASADOS,
        "2026-11",
    ]


def test_segunda_ejecucion_no_duplica(
    sembrada: BaseSembrada, monkeypatch: pytest.MonkeyPatch
) -> None:
    antes = {mes: _dashboard(sembrada.engine, mes).embudo for mes in MESES_PASADOS}
    monkeypatch.setenv("DATABASE_URL", sembrada.url)
    assert "ya estaba sembrado" in _sembrar(sembrada.carpeta)
    assert {mes: _dashboard(sembrada.engine, mes).embudo for mes in MESES_PASADOS} == antes
