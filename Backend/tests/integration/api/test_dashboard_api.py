"""``GET /dashboard`` contra PostgreSQL real (R-011 T17, CU-11, decision (c)).

Datos de ``sembrar_dashboard`` confirmados en ``app_db_test`` y borrados al terminar (las
campanas de ejemplo de ``0007`` se conservan). Reloj de la API fijo en 2026-09-30T15:00Z.
Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00). Datos 100 %
ficticios.
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.api.dependencies import get_clock
from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.persistence.test_migrations import modelo
from tests.integration.retencion_datos import (
    DatosDashboard,
    limpiar_retencion,
    sembrar_dashboard,
)

pytestmark = pytest.mark.integration

PATH = "/api/v1/dashboard"


class Reloj:
    def now(self) -> datetime:
        return datetime(2026, 9, 30, 15, 0, tzinfo=UTC)


@pytest.fixture
def base(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_retencion(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar_retencion(migrated_engine)


@pytest.fixture
def datos(base: Engine) -> DatosDashboard:
    with base.begin() as conexion:
        sembrados = sembrar_dashboard(conexion)
        modelo(
            conexion,
            version=1,
            vigente=True,
            fecha_entrenamiento=datetime(2026, 9, 1, 14, 30, tzinfo=UTC),
            ciclos_entrenamiento=1843,
            metadata_tecnica=json.dumps({"fecha_corte": "2026-08-31"}),
        )
        conexion.execute(
            text("UPDATE estado_sistema SET proxima_fecha_reentrenamiento = '2027-03-01'")
        )
    return sembrados


@pytest.fixture
def client(contract_app: FastAPI, contract_client: TestClient) -> Iterator[TestClient]:
    contract_app.dependency_overrides[get_clock] = Reloj
    try:
        yield contract_client
    finally:
        contract_app.dependency_overrides.pop(get_clock, None)


def test_get_dashboard_septiembre_devuelve_conteos_y_modelo(
    datos: DatosDashboard, client: TestClient
) -> None:
    respuesta = client.get(PATH, params={"mes": "2026-09"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["mes"] == "2026-09"
    assert cuerpo["embudo"] == {
        "asignadas": 21,
        "contactadas": 17,
        "ofrecidas": 11,
        "aceptadas": 7,
        "renovaron": 7,
    }
    assert cuerpo["por_campania"] == [
        {
            "campania_id": datos.campania_a,
            "nombre": "Zeta renovacion",
            "gestiones": 12,
            "contactados": 8,
            "renovaciones": 4,
            "gestiones_cerradas": 10,
            "tasa_renovacion": "0.40000000",
            "casos_insuficientes": False,
        },
        {
            "campania_id": datos.campania_b,
            "nombre": "alfa fidelizacion",
            "gestiones": 9,
            "contactados": 9,
            "renovaciones": 3,
            "gestiones_cerradas": 9,
            "tasa_renovacion": None,
            "casos_insuficientes": True,
        },
        {
            "campania_id": None,
            "nombre": "Sin campaña",
            "gestiones": 3,
            "contactados": 0,
            "renovaciones": 0,
            "gestiones_cerradas": 0,
            "tasa_renovacion": None,
            "casos_insuficientes": True,
        },
    ]
    estado = cuerpo["estado_modelo"]
    assert estado["version"] == "v1"
    assert estado["ciclos_entrenamiento"] == 1843
    assert estado["fecha_entrenamiento"].startswith("2026-09-01T14:30:00")
    assert estado["proxima_fecha_reentrenamiento"] == "2027-03-01"
    # Las membresias sembradas vencen el 2026-10-05: aun no son evaluables.
    assert estado["ciclos_nuevos_evaluables"] == 0


def test_get_dashboard_sin_mes_usa_el_mes_del_reloj(
    datos: DatosDashboard, client: TestClient
) -> None:
    cuerpo = client.get(PATH).json()

    assert cuerpo["mes"] == "2026-09"
    assert cuerpo["embudo"]["asignadas"] == 21


def test_get_dashboard_mes_sin_gestiones_devuelve_ceros(
    datos: DatosDashboard, client: TestClient
) -> None:
    cuerpo = client.get(PATH, params={"mes": "2026-08"}).json()

    assert cuerpo["embudo"] == {
        "asignadas": 0,
        "contactadas": 0,
        "ofrecidas": 0,
        "aceptadas": 0,
        "renovaron": 0,
    }
    assert cuerpo["por_campania"] == []
    assert cuerpo["estado_modelo"]["version"] == "v1"


def test_get_dashboard_sin_modelo_vigente_devuelve_estado_modelo_nulo(
    base: Engine, client: TestClient
) -> None:
    cuerpo = client.get(PATH, params={"mes": "2026-09"}).json()

    assert cuerpo["estado_modelo"] is None
    assert cuerpo["por_campania"] == []


@pytest.mark.parametrize("mes", ["2026-13", "sep"])
def test_get_dashboard_mes_invalido_devuelve_400(
    base: Engine, client: TestClient, mes: str
) -> None:
    assert_validation_error(client.get(PATH, params={"mes": mes}))


def test_openapi_dashboard_sin_501_y_con_fila_sin_campania(client: TestClient) -> None:
    op = client.get("/openapi.json").json()["paths"][PATH]["get"]

    assert "501" not in op["responses"]
    ejemplo = op["responses"]["200"]["content"]["application/json"]["example"]
    sin = ejemplo["por_campania"][-1]
    # FastAPI omite los nulos del ejemplo publicado.
    assert sin.get("campania_id") is None
    assert sin.get("tasa_renovacion") is None
    assert sin["casos_insuficientes"] is True
