"""La carga guardada alimenta la lista priorizada (R-007 T10, CU-01 -> CU-04).

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.

Con ``base_migrada`` la ultima carga es del 2026-08-30. Con el reloj 45 dias despues la lista
avisa de datos antiguos; tras confirmar una plantilla (libro construido en ``tmp_path``, con
cedulas ficticias y vencimientos dentro del horizonte) la advertencia desaparece y las
membresias nuevas entran en la cartera. Datos 100 % sinteticos.
"""

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.api.dependencies import get_clock
from tests.fixtures.generar_fixtures import cedula_valida, fila_plantilla, generar_plantilla
from tests.integration.api.listas_datos import INSTANTE

pytestmark = pytest.mark.integration

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
AHORA = INSTANTE + timedelta(days=45)  # 2026-10-14 15:00 UTC (10:00 en Ecuador)
HOY = date(2026, 10, 14)
FILAS_NUEVAS = 3


class RelojTardio:
    def now(self) -> datetime:
        return AHORA


@pytest.fixture
def cliente(contract_app: FastAPI, base_migrada: Engine) -> Iterator[TestClient]:
    contract_app.dependency_overrides[get_clock] = RelojTardio
    with TestClient(
        contract_app, client=("127.0.0.1", 50000), raise_server_exceptions=False
    ) as test_client:
        yield test_client


def _plantilla(tmp_path: Path) -> tuple[bytes, list[str]]:
    filas: list[list[object]] = []
    cedulas: list[str] = []
    for i in range(FILAS_NUEVAS):
        valores = fila_plantilla(0)  # plan MENSUAL
        cedula = cedula_valida(900 + i)
        inicio = HOY - timedelta(days=20 - i)
        valores[1] = f"Ficticio Cartera {chr(ord('A') + i)}"
        valores[2] = cedula
        valores[6] = inicio
        valores[7] = inicio + timedelta(days=30)  # vence 2026-10-24..26, dentro de 30 dias
        filas.append(valores)
        cedulas.append(cedula)
    ruta = generar_plantilla(filas, tmp_path / "plantilla-octubre.xlsx")
    return ruta.read_bytes(), cedulas


def test_saved_load_clears_old_data_warning_and_enters_portfolio(
    cliente: TestClient, tmp_path: Path
) -> None:
    contenido, cedulas = _plantilla(tmp_path)
    parametros = {"horizonte_dias": 30, "top_k": 100}

    antes = cliente.post("/api/v1/listas", json=parametros)
    carga = cliente.post(
        "/api/v1/cargas", files={"archivo": ("plantilla-octubre.xlsx", contenido, XLSX)}
    )
    despues = cliente.post("/api/v1/listas", json=parametros)

    assert antes.status_code == 201
    assert antes.json()["advertencia_datos_antiguos"] is True
    assert not set(cedulas) & {item["cedula"] for item in antes.json()["items"]}
    assert carga.status_code == 201
    assert carga.json()["filas_guardadas"] == FILAS_NUEVAS
    assert despues.status_code == 201
    assert despues.json()["advertencia_datos_antiguos"] is False
    assert set(cedulas) <= {item["cedula"] for item in despues.json()["items"]}
