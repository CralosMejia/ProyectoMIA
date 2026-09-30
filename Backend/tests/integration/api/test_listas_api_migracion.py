"""API de listas sobre la migracion sintetica real de T12 (CU-03 -> CU-04) y contrato del frontend.

La base se prepara con ``MigrarHistorico`` real (libros de ``tests/fixtures/historico`` +
``RandomForestPredictor``), no con datos sembrados. El contrato comprobado es el de
``.harness/contrato_listas.md``.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

import re
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from app.application.historial.ports import NuevaMembresia, NuevoSocio
from app.application.sistema.ports import ResultadoMigracion
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan
from app.infrastructure.persistence.models.historial import Carga
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from tests.integration.api.listas_datos import (
    RelojApi,
    crear_modelo_vigente,
    fijar_reloj_api,
)
from tests.integration.sistema.migracion_sintetica import limpiar_base, migrar_sintetico

pytestmark = pytest.mark.integration

LISTAS = "/api/v1/listas"
BODY = {"fecha_referencia": "2026-08-31", "horizonte_dias": 31, "top_k": 3}
DECIMAL = re.compile(r"^-?\d+(\.\d+)?$")
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CAMPOS_LISTA = {
    "id",
    "nombre",
    "modelo_version",
    "fecha_generacion",
    "creada_en",
    "horizonte_dias",
    "top_k",
    "umbral_alto",
    "umbral_medio",
    "advertencia_datos_antiguos",
    "items",
}
CAMPOS_ITEM = {
    "prediccion_id",
    "prioridad",
    "socio_nombre",
    "celular",
    "cedula",
    "plan",
    "fecha_vencimiento",
    "dias_para_vencer",
    "monto_cobrado",
    "score",
    "nivel_riesgo",
    "factores_principales",
    "dentro_top_k",
    "gestion_id",
    "gestion_estado",
    "campania_asignada",
}
CAMPOS_RESUMEN = {
    "id",
    "nombre",
    "fecha_generacion",
    "creada_en",
    "modelo_version",
    "horizonte_dias",
    "top_k",
    "total_items",
}


@pytest.fixture(autouse=True)
def _reloj_fijo(contract_app: FastAPI) -> None:
    """La API ve 2026-08-31 como hoy (reloj fijo en lugar del del sistema)."""
    fijar_reloj_api(contract_app)


@pytest.fixture
def base_migrada_t12(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_base(migrated_engine)
    try:
        assert migrar_sintetico(migrated_engine) is ResultadoMigracion.COMPLETADA
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def _fijar_estado(engine: Engine, estado: str) -> None:
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE estado_sistema SET migracion_historica = :e WHERE id = 1"), {"e": estado}
        )


def _es_decimal(valor: Any) -> bool:
    return isinstance(valor, str) and DECIMAL.match(valor) is not None


def test_post_listas_after_synthetic_migration_returns_201_with_frontend_contract(
    contract_client: TestClient, base_migrada_t12: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json=BODY)

    assert respuesta.status_code == 201
    lista = respuesta.json()
    assert set(lista) == CAMPOS_LISTA
    assert isinstance(lista["id"], int)
    assert lista["modelo_version"] == "v1"
    assert lista["fecha_generacion"] == "2026-08-31"
    assert datetime.fromisoformat(lista["creada_en"]).tzinfo is not None
    assert (lista["horizonte_dias"], lista["top_k"]) == (31, 3)
    assert _es_decimal(lista["umbral_alto"])
    assert _es_decimal(lista["umbral_medio"])
    assert Decimal(lista["umbral_alto"]) >= Decimal(lista["umbral_medio"])
    assert isinstance(lista["advertencia_datos_antiguos"], bool)

    items = lista["items"]
    assert items, "la cartera sintetica a 31 dias no deberia estar vacia"
    for item in items:
        assert set(item) == CAMPOS_ITEM
        assert isinstance(item["prediccion_id"], int)
        assert isinstance(item["socio_nombre"], str)
        assert item["celular"] is None or isinstance(item["celular"], str)
        assert isinstance(item["cedula"], str)
        assert item["plan"] != "DIARIO"
        assert FECHA.match(item["fecha_vencimiento"])
        assert isinstance(item["dias_para_vencer"], int)
        assert (date.fromisoformat(item["fecha_vencimiento"]) - date(2026, 8, 31)).days == item[
            "dias_para_vencer"
        ]
        assert 0 <= item["dias_para_vencer"] <= 31
        assert item["monto_cobrado"] is None or _es_decimal(item["monto_cobrado"])
        assert _es_decimal(item["score"])
        assert item["nivel_riesgo"] in {"ALTO", "MEDIO", "BAJO"}
        assert isinstance(item["factores_principales"], list)
        assert all(isinstance(f, str) for f in item["factores_principales"])
        assert isinstance(item["dentro_top_k"], bool)
        assert item["gestion_id"] is None
        assert item["gestion_estado"] is None
        assert item["campania_asignada"] is None
    assert [i["prioridad"] for i in items] == list(range(1, len(items) + 1))
    scores = [Decimal(i["score"]) for i in items]
    assert scores == sorted(scores, reverse=True)
    assert sum(i["dentro_top_k"] for i in items) == min(3, len(items))
    assert all(i["dentro_top_k"] for i in items[: min(3, len(items))])
    # una fila por socio: el id de prediccion y el par (nombre, celular) no se repiten
    assert len({i["prediccion_id"] for i in items}) == len(items)
    assert len({(i["socio_nombre"], i["celular"]) for i in items}) == len(items)


def test_get_listas_after_synthetic_migration_returns_summary_contract(
    contract_client: TestClient, base_migrada_t12: Engine
) -> None:
    creada = contract_client.post(LISTAS, json=BODY).json()

    resumenes = contract_client.get(LISTAS).json()

    assert len(resumenes) == 1
    assert set(resumenes[0]) == CAMPOS_RESUMEN
    assert resumenes[0]["id"] == creada["id"]
    assert resumenes[0]["total_items"] == len(creada["items"])
    assert resumenes[0]["modelo_version"] == "v1"


def test_get_lista_by_id_after_new_current_model_keeps_original_levels_and_version(
    contract_client: TestClient, base_migrada_t12: Engine
) -> None:
    creada = contract_client.post(LISTAS, json=BODY).json()

    crear_modelo_vigente(base_migrada_t12, version=2)
    por_id = contract_client.get(f"{LISTAS}/{creada['id']}")
    ultima = contract_client.get(f"{LISTAS}/ultima")

    assert por_id.status_code == 200
    assert por_id.json() == creada
    assert ultima.json() == creada


@pytest.mark.parametrize("estado", ["PENDIENTE", "EN_CURSO"])
def test_post_listas_with_migration_not_completed_returns_409_and_saves_nothing(
    contract_client: TestClient, base_migrada_t12: Engine, estado: str
) -> None:
    _fijar_estado(base_migrada_t12, estado)
    try:
        respuesta = contract_client.post(LISTAS, json=BODY)
    finally:
        _fijar_estado(base_migrada_t12, "COMPLETADA")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "error": {
            "code": "conflict",
            "message": "El sistema se esta inicializando; intente de nuevo en unos minutos.",
        }
    }
    with base_migrada_t12.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM listas_priorizadas")).scalar_one() == 0


@pytest.mark.parametrize(
    "cambio",
    [
        {"horizonte_dias": -1},
        {"top_k": -1},
        {"horizonte_dias": "treinta"},
        {"fecha_referencia": "2026-02-30"},
    ],
)
def test_post_listas_invalid_boundary_values_returns_400(
    contract_client: TestClient, base_migrada_t12: Engine, cambio: dict[str, Any]
) -> None:
    respuesta = contract_client.post(LISTAS, json={**BODY, **cambio})

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "validation_error"


def _insertar_socio_sin_cedula(engine: Engine) -> None:
    """Socio sin cedula con una membresia que vence dentro de los proximos 31 dias."""
    reloj = RelojApi()
    with Session(engine) as session, session.begin():
        carga_id = session.scalars(select(Carga.id).order_by(Carga.id).limit(1)).one()
        (socio_id,) = SqlAlchemySocioRepository(session, reloj).insertar_en_bloque(
            [
                NuevoSocio(
                    cedula=None,
                    nombre="Socio Sin Cedula Sintetico",
                    nombre_normalizado="SOCIO SIN CEDULA SINTETICO",
                    celular="0999999999",
                )
            ]
        )
        SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
            [
                NuevaMembresia(
                    socio_id=socio_id,
                    carga_id=carga_id,
                    plan=Plan.MENSUAL,
                    forma_pago=FormaPago.EFECTIVO,
                    origen=OrigenMembresia.HISTORICO,
                    inicio_aproximado=False,
                    fecha_actividad=date(2026, 8, 20),
                    fecha_inicio=date(2026, 8, 20),
                    fecha_vencimiento=date(2026, 9, 20),
                    monto_cobrado=Decimal("40.00"),
                )
            ]
        )


def test_post_listas_excludes_socio_without_cedula(
    contract_client: TestClient, base_migrada_t12: Engine
) -> None:
    _insertar_socio_sin_cedula(base_migrada_t12)

    respuesta = contract_client.post(LISTAS, json={**BODY, "top_k": 25})

    assert respuesta.status_code == 201
    items = respuesta.json()["items"]
    assert items
    assert all(i["socio_nombre"] != "Socio Sin Cedula Sintetico" for i in items)
    assert all(i["cedula"] is not None for i in items)
    assert all("correo" not in i for i in items)
