"""``GET /dashboard`` contra PostgreSQL real (R-011 T17, CU-11, decision (c)).

Datos de ``sembrar_dashboard`` confirmados en ``app_db_test`` y borrados al terminar (las
campanas de ejemplo de ``0007`` se conservan). Reloj de la API fijo en 2026-09-30T15:00Z.
Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00). Datos 100 %
ficticios.
"""

import json
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text

from app.api.dependencies import get_clock
from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.persistence.test_migrations import carga, insert, membresia, modelo, socio
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


@pytest.mark.parametrize("mes", ["2026-13", "sep", "0000-01", "9999-12", "1899-12", "3000-01"])
def test_get_dashboard_mes_invalido_devuelve_400(
    base: Engine, client: TestClient, mes: str
) -> None:
    assert_validation_error(client.get(PATH, params={"mes": mes}))


def test_openapi_dashboard_sin_501_y_con_fila_sin_campania(client: TestClient) -> None:
    op = client.get("/openapi.json").json()["paths"][PATH]["get"]

    assert "501" not in op["responses"]
    ejemplo = op["responses"]["200"]["content"]["application/json"]["examples"]["con_piloto"]
    sin = ejemplo["value"]["por_campania"][-1]
    # FastAPI omite los nulos del ejemplo publicado.
    assert sin.get("campania_id") is None
    assert sin.get("tasa_renovacion") is None
    assert sin["casos_insuficientes"] is True


# ------------------------------------------------------------- indicadores del piloto (R-018)

NOMBRE_SOCIO = "Socia Ficticia Piloto"
CEDULA = "0999999999"
CELULAR = "0991112233"
CORREO = "socia.ficticia@example.invalid"


def _socio_ficticio(conexion: Connection, sufijo: str) -> int:
    return socio(
        conexion,
        nombre=f"{NOMBRE_SOCIO} {sufijo}",
        nombre_normalizado=f"{NOMBRE_SOCIO.upper()} {sufijo}",
        cedula=f"{CEDULA[:-1]}{sufijo}",
        celular=CELULAR,
        correo=CORREO,
    )


def _ciclo(conexion: Connection, socio_id: int, actividad: date, vence: date, **montos: str) -> int:
    return membresia(
        conexion,
        socio_id=socio_id,
        fecha_inicio=actividad,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        **montos,
    )


def _top(
    conexion: Connection,
    lista_id: int,
    membresia_id: int,
    socio_id: int,
    prioridad: int,
    fecha_contacto: date | None = None,
) -> None:
    prediccion_id = insert(
        conexion,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "socio_id": socio_id,
            "score": "0.90000000",
            "nivel_riesgo": "ALTO",
            "factores_principales": "[]",
            "prioridad": prioridad,
            "dentro_top_k": True,
        },
    )
    if fecha_contacto is not None:
        insert(
            conexion,
            "gestiones_retencion",
            {
                "prediccion_id": prediccion_id,
                "membresia_id": membresia_id,
                "fecha_asignacion": date(2026, 8, 1),
                "fecha_seguimiento": date(2026, 8, 1),
                "estado": "PENDIENTE",
                "contactado": True,
                "fecha_contacto": fecha_contacto,
            },
        )


@pytest.fixture
def piloto(base: Engine) -> None:
    """Lista de agosto con 3 casos; corte de verificacion 2026-09-29 (ultima carga)."""
    with base.begin() as c:
        modelo_id = modelo(
            c,
            version=1,
            vigente=True,
            metadata_tecnica=json.dumps({"fecha_corte": "2026-08-31"}),
        )
        carga(c, fecha_carga=datetime(2026, 9, 29, 15, 0, tzinfo=UTC))
        lista_id = insert(
            c,
            "listas_priorizadas",
            {
                "modelo_id": modelo_id,
                "fecha_generacion": date(2026, 8, 1),
                "horizonte_dias": 30,
                "top_k": 25,
                "creada_en": datetime(2026, 8, 1, 15, 0, tzinfo=UTC),
                "nombre": "Lista agosto piloto",
            },
        )
        a, b, d = (_socio_ficticio(c, str(i)) for i in range(1, 4))
        renovo = _ciclo(c, a, date(2026, 7, 10), date(2026, 8, 10))
        _ciclo(c, a, date(2026, 8, 12), date(2026, 9, 12), monto_facturado="35.5000")
        no_renovo = _ciclo(c, b, date(2026, 7, 15), date(2026, 8, 15))
        sin_contacto = _ciclo(c, d, date(2026, 7, 20), date(2026, 8, 20))
        _ciclo(c, d, date(2026, 8, 25), date(2026, 9, 25), monto_cobrado="40.0000")
        _top(c, lista_id, renovo, a, 1, fecha_contacto=date(2026, 8, 5))
        _top(c, lista_id, no_renovo, b, 2, fecha_contacto=date(2026, 8, 15))
        _top(c, lista_id, sin_contacto, d, 3)


def test_get_dashboard_piloto_del_mes_calcula_indicadores(piloto: None, client: TestClient) -> None:
    respuesta = client.get(PATH, params={"mes": "2026-08"})

    assert respuesta.status_code == 200
    p = respuesta.json()["piloto"]
    assert p["estado"] == "COMPLETO"
    assert p["lista"]["nombre"] == "Lista agosto piloto"
    assert p["lista"]["fecha_generacion"] == "2026-08-01"
    assert p["corte_verificacion"] == "2026-09-29"
    assert (p["n_top"], p["sin_dato"]) == (3, 0)
    assert p["precision_top25"] == {
        "valor": "0.33333333",
        "numerador": 1,
        "denominador": 3,
        "n": 3,
        "pendientes": 0,
        "estado": "COMPLETO",
    }
    assert p["contactados_antes_vencimiento"]["valor"] == "0.33333333"
    assert p["dias_anticipacion"] == {"valor": "2.5", "n": 2, "estado": "COMPLETO"}
    assert p["tasa_renovacion_contactados"]["valor"] == "0.50000000"
    assert (
        p["tasa_renovacion_contactados"]["n"],
        p["tasa_renovacion_contactados"]["denominador"],
    ) == (2, 2)
    assert p["monto_retenido"] == {
        "total": "35.50",
        "renovaciones": 1,
        "renovaciones_sin_monto": 0,
        "n": 2,
        "pendientes": 0,
        "estado": "COMPLETO",
    }


def test_get_dashboard_piloto_mes_sin_lista_es_sin_datos(piloto: None, client: TestClient) -> None:
    respuesta = client.get(PATH, params={"mes": "2026-07"})

    assert respuesta.status_code == 200
    p = respuesta.json()["piloto"]
    assert p["estado"] == "SIN_DATOS"
    assert p["lista"] is None
    assert p["n_top"] == 0
    assert p["precision_top25"]["valor"] is None
    assert p["monto_retenido"]["total"] is None


def _claves_y_textos(valor: Any) -> Iterator[tuple[str | None, Any]]:
    if isinstance(valor, dict):
        for clave, hijo in valor.items():
            yield clave, hijo
            yield from _claves_y_textos(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from _claves_y_textos(hijo)


def test_get_dashboard_no_expone_datos_personales(piloto: None, client: TestClient) -> None:
    cuerpo = client.get(PATH, params={"mes": "2026-08"}).json()

    pares = list(_claves_y_textos(cuerpo))
    claves = {clave for clave, _ in pares}
    assert claves.isdisjoint({"cedula", "celular", "correo", "socio_id", "membresia_id"})
    textos = [v for _, v in pares if isinstance(v, str)]
    assert not any(NOMBRE_SOCIO in t or CELULAR in t or CORREO in t for t in textos)
    assert not any(t.startswith(CEDULA[:-1]) for t in textos)
