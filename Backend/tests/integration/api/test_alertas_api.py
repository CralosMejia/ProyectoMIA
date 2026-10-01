"""``GET /alertas`` y ``GET /gestiones?filtro=`` contra PostgreSQL real (R-011 T4, CU-09).

Datos de ``sembrar_seguimiento`` confirmados en ``app_db_test`` y borrados al terminar (las
campanas de ejemplo de ``0007`` se conservan). Reloj de la API fijo en 2026-09-30T15:00Z
(10:00 en Ecuador). Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso por IP,
CU-00). Datos 100 % ficticios.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.api.dependencies import get_clock
from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.retencion_datos import (
    DatosSeguimiento,
    limpiar_retencion,
    sembrar_seguimiento,
)

pytestmark = pytest.mark.integration

ALERTAS_PATH = "/api/v1/alertas"
GESTIONES_PATH = "/api/v1/gestiones"


class Reloj:
    instante = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return Reloj.instante


@pytest.fixture
def datos(migrated_engine: Engine) -> Iterator[DatosSeguimiento]:
    limpiar_retencion(migrated_engine)
    with migrated_engine.begin() as conexion:
        sembrados = sembrar_seguimiento(conexion)
    try:
        yield sembrados
    finally:
        limpiar_retencion(migrated_engine)


@pytest.fixture
def client(contract_app: FastAPI, contract_client: TestClient) -> Iterator[TestClient]:
    Reloj.instante = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
    contract_app.dependency_overrides[get_clock] = Reloj
    try:
        yield contract_client
    finally:
        contract_app.dependency_overrides.pop(get_clock, None)


def test_get_alertas_datos_conocidos_devuelve_conteos(
    datos: DatosSeguimiento, client: TestClient
) -> None:
    respuesta = client.get(ALERTAS_PATH)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"vencidas": 2, "hoy": 1, "proximos_7_dias": 2}


def test_get_gestiones_hoy_devuelve_la_fila_con_prediccion_id(
    datos: DatosSeguimiento, client: TestClient
) -> None:
    respuesta = client.get(GESTIONES_PATH, params={"filtro": "hoy"})

    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert len(filas) == 1
    assert filas[0] == {
        "id": datos.hoy,
        "prediccion_id": datos.hoy_prediccion,
        "socio_nombre": "Socio Ficticio",
        "celular": "0990000000",
        "plan": "MENSUAL",
        "fecha_vencimiento": "2026-10-05",
        "fecha_seguimiento": "2026-09-30",
        "nivel_riesgo": "ALTO",
        "campania_nombre": "Campaña congelada",
        "responsable": "Responsable ficticio",
        "estado": "PENDIENTE",
    }


@pytest.mark.parametrize(("filtro", "campo"), [("vencidas", "vencidas"), ("proximas", "proximas")])
def test_get_gestiones_otros_grupos_ordenados_por_fecha(
    datos: DatosSeguimiento, client: TestClient, filtro: str, campo: str
) -> None:
    filas = client.get(GESTIONES_PATH, params={"filtro": filtro}).json()

    assert [f["id"] for f in filas] == list(getattr(datos, campo))


@pytest.mark.parametrize("params", [{"filtro": "otro"}, {}])
def test_get_gestiones_filtro_invalido_o_ausente_devuelve_400(
    datos: DatosSeguimiento, client: TestClient, params: dict[str, str]
) -> None:
    assert_validation_error(client.get(GESTIONES_PATH, params=params))


def test_registrar_renovo_si_saca_la_gestion_de_hoy(
    datos: DatosSeguimiento, client: TestClient
) -> None:
    respuesta = client.put(
        f"{GESTIONES_PATH}/{datos.hoy}/resultado",
        json={
            "contactado": True,
            "campania_ofrecida": "SI",
            "campania_aceptada": "SI",
            "renovo_declarado": "SI",
            "fecha_contacto": "2026-09-30",
            "observaciones": None,
            "responsable": "Responsable ficticio",
            "fecha_seguimiento": None,
        },
    )
    assert respuesta.status_code == 200, respuesta.text

    assert client.get(ALERTAS_PATH).json() == {"vencidas": 2, "hoy": 0, "proximos_7_dias": 2}
    assert client.get(GESTIONES_PATH, params={"filtro": "hoy"}).json() == []


def test_reloj_al_dia_siguiente_mueve_la_de_hoy_a_vencidas(
    datos: DatosSeguimiento, client: TestClient
) -> None:
    Reloj.instante = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)

    # 10-01 pasa a hoy, 10-08 entra en proximas; cada gestion en un solo contador.
    assert client.get(ALERTAS_PATH).json() == {"vencidas": 3, "hoy": 1, "proximos_7_dias": 2}
    vencidas = client.get(GESTIONES_PATH, params={"filtro": "vencidas"}).json()
    assert [f["id"] for f in vencidas] == [*datos.vencidas, datos.hoy]


def test_reloj_noche_en_ecuador_sigue_siendo_hoy(
    datos: DatosSeguimiento, client: TestClient
) -> None:
    Reloj.instante = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    assert client.get(ALERTAS_PATH).json() == {"vencidas": 2, "hoy": 1, "proximos_7_dias": 2}
