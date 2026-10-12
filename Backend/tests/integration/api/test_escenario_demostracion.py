"""Escenario de demostracion de punta a punta (03 §21) con reloj simulado (R-013 T8).

Una sola prueba, en orden, contra la app real y el PostgreSQL de pruebas (``*_test``): el
reloj de la API (``get_clock``), el del comando ``reentrenar`` y el del planificador son el
mismo ``RelojAjustable``. Asi se ensayan CU-09 (alertas) y CU-02 (reentrenamiento y fecha
perdida ``OMITIDO``) sin reloj simulado en ejecucion (decision (c) de R-013).

Desviaciones respecto de 03 §21, resueltas aqui:

- Paso 4 ("lista con fecha 31-08-2026"): choca con ADR-006 (una fecha anterior a hoy ->
  ``422``). La prueba comprueba ese ``422`` y genera la lista con la fecha de hoy; la
  comparacion con el notebook al 31-08-2026 se hace con ``Backend/scripts/verificar_lista.py``
  (decision (h) de R-013).
- Paso 2 (acceso por IP, CU-00) lo cubre ``test_acceso_ip.py``; el paso 1 usa la migracion
  sintetica (libros de ``tests/fixtures/historico``), no los libros reales.
- Paso 10, caso v2: lo cubre ``test_cli_reentrenar.py`` (con datos suficientes).

Datos 100 % sinteticos. La base queda como se encontro (``limpiar_retencion`` al empezar y
al terminar: conserva las campanas de ejemplo de ``0007``). Aislamiento entre usuarios: NO
APLICA (sin login; acceso por IP, CU-00).
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL

from app.api.dependencies import get_clock
from app.application.sistema.ports import ResultadoMigracion
from app.cli import main as cli_main
from app.core.config import Settings
from app.main import create_app
from tests.fixtures.generar_fixtures import (
    DIR_PLANTILLAS,
    PLANTILLA_CEDULA_INVALIDA,
    PLANTILLA_VALIDA,
)
from tests.integration.retencion_datos import limpiar_retencion
from tests.integration.sistema.migracion_sintetica import migrar_sintetico

pytestmark = pytest.mark.integration

API = "/api/v1"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# 10:00 en Ecuador del dia siguiente a la migracion sintetica (2026-09-29).
INICIO = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
HOY = date(2026, 9, 30)
PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]


class RelojAjustable:
    """Reloj compartido por la API, el comando y el planificador; se adelanta en la prueba."""

    def __init__(self, instante: datetime) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante

    def adelantar(self, dias: int) -> None:
        self.instante += timedelta(days=dias)


@pytest.fixture
def base(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_retencion(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar_retencion(migrated_engine)


@pytest.fixture
def reloj() -> RelojAjustable:
    return RelojAjustable(INICIO)


@pytest.fixture
def cliente(
    contract_app: FastAPI, contract_client: TestClient, reloj: RelojAjustable
) -> Iterator[TestClient]:
    contract_app.dependency_overrides[get_clock] = lambda: reloj
    try:
        yield contract_client
    finally:
        contract_app.dependency_overrides.pop(get_clock, None)


def _archivo(nombre: str) -> dict[str, Any]:
    return {"archivo": (nombre, (DIR_PLANTILLAS / nombre).read_bytes(), XLSX)}


def _contar(engine: Engine, sql: str) -> int:
    """Conteo con SQL fijo de la prueba (sin parametros de usuario)."""
    with engine.connect() as conexion:
        return int(conexion.execute(text(sql)).scalar_one())


def _proxima_fecha(engine: Engine) -> date:
    with engine.connect() as conexion:
        valor = conexion.execute(
            text("SELECT proxima_fecha_reentrenamiento FROM estado_sistema WHERE id = 1")
        ).scalar_one()
    assert isinstance(valor, date)
    return valor


def _campania(cliente: TestClient, nombre: str, prioridad: int) -> dict[str, Any]:
    respuesta = cliente.post(
        f"{API}/campanias",
        json={
            "nombre": nombre,
            "descripcion": "Campana sintetica de la demostracion.",
            "niveles_riesgo": ["ALTO"],
            "planes": PLANES,
            "prioridad": prioridad,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    creada: dict[str, Any] = respuesta.json()
    return creada


def _arrancar_planificador(url: URL, reloj: RelojAjustable) -> None:
    """Arranca la app con el planificador y la apaga tras su primera revision."""
    settings = Settings(
        DATABASE_URL=SecretStr(url.render_as_string(hide_password=False)),
        APP_ENV="test",
        MIGRAR_HISTORICO_AL_ARRANCAR=False,
        REENTRENAMIENTO_AUTOMATICO=True,
    )
    with TestClient(create_app(settings, clock=reloj), client=("127.0.0.1", 50000)):
        pass


def test_escenario_demostracion_de_punta_a_punta_con_reloj_simulado(
    base: Engine,
    cliente: TestClient,
    reloj: RelojAjustable,
    test_database_url: URL,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 1. Historico sintetico migrado -> LISTO con el modelo v1 (CU-03).
    assert migrar_sintetico(base) is ResultadoMigracion.COMPLETADA
    estado = cliente.get(f"{API}/sistema/estado")
    assert estado.status_code == 200, estado.text
    assert estado.json()["estado"] == "LISTO"
    assert estado.json()["modelo_vigente"]["version"] == "v1"

    # 3. Plantilla con errores: vista previa con errores y confirmacion rechazada; corregida
    #    -> confirmada (CU-01).
    vista = cliente.post(f"{API}/cargas/vista-previa", files=_archivo(PLANTILLA_CEDULA_INVALIDA))
    assert vista.status_code == 200, vista.text
    assert vista.json()["puede_confirmar"] is False
    assert vista.json()["errores"]
    rechazada = cliente.post(f"{API}/cargas", files=_archivo(PLANTILLA_CEDULA_INVALIDA))
    assert rechazada.status_code == 422
    assert rechazada.json()["error"]["code"] == "domain_rule_violated"
    vista = cliente.post(f"{API}/cargas/vista-previa", files=_archivo(PLANTILLA_VALIDA))
    assert vista.json()["puede_confirmar"] is True
    confirmada = cliente.post(f"{API}/cargas", files=_archivo(PLANTILLA_VALIDA))
    assert confirmada.status_code == 201, confirmada.text

    # 4. Fecha pasada (31-08-2026) -> 422 por ADR-006; lista con la fecha de hoy (CU-04/05).
    pasada = cliente.post(
        f"{API}/listas",
        json={"fecha_referencia": "2026-08-31", "horizonte_dias": 31, "top_k": 25},
    )
    assert pasada.status_code == 422
    assert pasada.json()["error"]["code"] == "domain_rule_violated"
    respuesta = cliente.post(
        f"{API}/listas",
        json={"fecha_referencia": HOY.isoformat(), "horizonte_dias": 31, "top_k": 25},
    )
    assert respuesta.status_code == 201, respuesta.text
    lista = respuesta.json()
    assert lista["fecha_generacion"] == HOY.isoformat()
    assert lista["modelo_version"] == "v1"
    altos = [i for i in lista["items"] if i["nivel_riesgo"] == "ALTO"]
    assert altos, "la lista de hoy deberia tener al menos un socio ALTO"

    # 5. Excel (CU-12).
    excel = cliente.get(f"{API}/listas/{lista['id']}/excel")
    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith(XLSX)
    assert excel.content[:2] == b"PK"

    # 6. Dos campanas (CU-06), sugerencias de un socio ALTO (CU-07) y gestion con
    #    seguimiento hoy + 2 (CU-08).
    primera = _campania(cliente, "Demostracion renovacion anticipada", 1)
    segunda = _campania(cliente, "Demostracion clase de cortesia", 2)
    alto = altos[0]
    sugeridas = cliente.get(f"{API}/predicciones/{alto['prediccion_id']}/campanias-sugeridas")
    assert sugeridas.status_code == 200, sugeridas.text
    assert {primera["id"], segunda["id"]} <= {c["id"] for c in sugeridas.json()}
    seguimiento = HOY + timedelta(days=2)
    creada = cliente.post(
        f"{API}/gestiones",
        json={
            "prediccion_id": alto["prediccion_id"],
            "campania_id": primera["id"],
            "fecha_seguimiento": seguimiento.isoformat(),
            "responsable": "Responsable de la demostracion",
        },
    )
    assert creada.status_code == 201, creada.text
    gestion = creada.json()
    assert gestion["estado"] == "PENDIENTE"
    assert cliente.get(f"{API}/alertas").json() == {"vencidas": 0, "hoy": 0, "proximos_7_dias": 1}

    # 7. Reloj + 2 dias -> "para hoy"; + 1 dia mas -> "vencida" (CU-09).
    reloj.adelantar(2)
    alertas = cliente.get(f"{API}/alertas").json()
    assert (alertas["hoy"], alertas["vencidas"]) == (1, 0)
    para_hoy = cliente.get(f"{API}/gestiones", params={"filtro": "hoy"}).json()
    assert [g["id"] for g in para_hoy] == [gestion["id"]]
    reloj.adelantar(1)
    alertas = cliente.get(f"{API}/alertas").json()
    assert (alertas["hoy"], alertas["vencidas"]) == (0, 1)
    vencidas = cliente.get(f"{API}/gestiones", params={"filtro": "vencidas"}).json()
    assert [g["id"] for g in vencidas] == [gestion["id"]]

    # 8. Resultado "Renovo: Si" -> la gestion se cierra; sin alertas (CU-10).
    cierre = cliente.put(
        f"{API}/gestiones/{gestion['id']}/resultado",
        json={
            "contactado": True,
            "campania_ofrecida": "SI",
            "campania_aceptada": "SI",
            "renovo_declarado": "SI",
            "fecha_contacto": (HOY + timedelta(days=3)).isoformat(),
            "observaciones": None,
            "responsable": "Responsable de la demostracion",
            "fecha_seguimiento": None,
        },
    )
    assert cierre.status_code == 200, cierre.text
    assert cierre.json()["estado"] == "CERRADA"
    assert cliente.get(f"{API}/alertas").json() == {"vencidas": 0, "hoy": 0, "proximos_7_dias": 0}

    # 9. Dashboard del mes de creacion: embudo, tabla por campana y estado del modelo (CU-11).
    tablero = cliente.get(f"{API}/dashboard", params={"mes": HOY.strftime("%Y-%m")})
    assert tablero.status_code == 200, tablero.text
    cuerpo = tablero.json()
    assert cuerpo["embudo"]["asignadas"] == 1
    assert cuerpo["embudo"]["renovaron"] == 1
    fila = next(c for c in cuerpo["por_campania"] if c["campania_id"] == primera["id"])
    assert (fila["gestiones"], fila["renovaciones"]) == (1, 1)
    assert cuerpo["estado_modelo"]["version"] == "v1"

    # 10a. Reentrenamiento manual sin ciclos nuevos -> CRITERIOS_NO_CUMPLIDOS, un intento
    #      registrado y sin version nueva (CU-02).
    monkeypatch.setenv("DATABASE_URL", test_database_url.render_as_string(hide_password=False))
    capsys.readouterr()
    assert cli_main(["reentrenar"], clock=reloj) == 0
    assert "CRITERIOS_NO_CUMPLIDOS" in capsys.readouterr().out
    manuales = (
        "SELECT count(*) FROM intentos_reentrenamiento "
        "WHERE disparador = 'MANUAL' AND resultado = 'CRITERIOS_NO_CUMPLIDOS'"
    )
    assert _contar(base, manuales) == 1
    assert _contar(base, "SELECT count(*) FROM modelos") == 1

    # 10b. Planificador con el reloj 3 dias despues de la fecha programada -> un OMITIDO;
    #      un segundo arranque no anade otro (CU-02, fecha perdida).
    programada = _proxima_fecha(base)
    reloj.instante = datetime.combine(programada + timedelta(days=3), INICIO.timetz())
    omitidos = "SELECT count(*) FROM intentos_reentrenamiento WHERE resultado = 'OMITIDO'"
    _arrancar_planificador(test_database_url, reloj)
    assert _contar(base, omitidos) == 1
    assert _proxima_fecha(base) > programada
    _arrancar_planificador(test_database_url, reloj)
    assert _contar(base, omitidos) == 1
    assert _contar(base, "SELECT count(*) FROM modelos") == 1
