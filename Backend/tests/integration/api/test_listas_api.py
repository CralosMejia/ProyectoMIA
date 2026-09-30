"""API de listas (CU-04, CU-05) contra PostgreSQL real con datos sinteticos confirmados.

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.api.dependencies import get_clock, get_predictor
from app.application.listas.generar_lista import MENSAJE_FECHA_PASADA
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from tests.integration.api.contract_helpers import assert_operation_contract, json_example
from tests.integration.api.listas_datos import FILAS_ESPERADAS, fijar_reloj_api

pytestmark = pytest.mark.integration

LISTAS = "/api/v1/listas"
BODY = {"fecha_referencia": "2026-08-31", "horizonte_dias": 30, "top_k": 25}
CONFLICTO = {
    "error": {
        "code": "conflict",
        "message": "El sistema se esta inicializando; intente de nuevo en unos minutos.",
    }
}
FECHA_PASADA = {"error": {"code": "domain_rule_violated", "message": MENSAJE_FECHA_PASADA}}


@pytest.fixture(autouse=True)
def _reloj_fijo(contract_app: FastAPI) -> None:
    """La API ve 2026-08-31 como hoy (reloj fijo en lugar del del sistema)."""
    fijar_reloj_api(contract_app)


class PredictorQueFalla:
    def train(self, *args: object, **kwargs: object) -> TrainedModel:
        raise AssertionError("no se entrena")

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        raise RuntimeError("fallo del modelo")


def contar(engine: Engine, tabla: str) -> int:
    assert tabla in {"listas_priorizadas", "predicciones"}
    with engine.connect() as conexion:
        return int(conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())  # noqa: S608 - lista blanca


def test_post_listas_returns_201_sorted_items_with_decimal_strings(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json=BODY)

    assert respuesta.status_code == 201
    lista = respuesta.json()
    assert lista["modelo_version"] == "v1"
    assert lista["fecha_generacion"] == "2026-08-31"
    assert datetime.fromisoformat(lista["creada_en"]).tzinfo is not None
    assert (lista["horizonte_dias"], lista["top_k"]) == (30, 25)
    assert lista["umbral_alto"] == "0.60000000"
    assert lista["umbral_medio"] == "0.40000000"
    assert lista["advertencia_datos_antiguos"] is False
    items = lista["items"]
    assert len(items) == FILAS_ESPERADAS
    assert [i["prioridad"] for i in items] == list(range(1, FILAS_ESPERADAS + 1))
    assert all(isinstance(i["score"], str) for i in items)
    scores = [Decimal(i["score"]) for i in items]
    assert scores == sorted(scores, reverse=True)
    assert sum(i["dentro_top_k"] for i in items) == 25
    nombres = {i["socio_nombre"] for i in items}
    assert len(nombres) == FILAS_ESPERADAS  # una fila por socio
    assert "Socio Sintetico 00" not in nombres  # ya renovo
    assert "Socio Sintetico 01" not in nombres  # solo DIARIO en el horizonte
    assert all(i["plan"] != "DIARIO" for i in items)
    assert set(items[0]) == {
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
        "gestion_estado",
        "campania_asignada",
    }
    assert all("correo" not in i for i in items)
    assert all(isinstance(i["cedula"], str) for i in items)
    montos = [i["monto_cobrado"] for i in items]
    assert None in montos  # el socio 5 no tiene monto
    assert all(m is None or isinstance(m, str) for m in montos)
    assert all(i["nivel_riesgo"] in {"ALTO", "MEDIO", "BAJO"} for i in items)
    assert contar(base_migrada, "listas_priorizadas") == 1
    assert contar(base_migrada, "predicciones") == FILAS_ESPERADAS


@pytest.mark.parametrize("cambio", [{"horizonte_dias": 0}, {"horizonte_dias": 32}, {"top_k": 0}])
def test_post_listas_invalid_parameters_returns_400(
    contract_client: TestClient, base_migrada: Engine, cambio: dict[str, Any]
) -> None:
    respuesta = contract_client.post(LISTAS, json={**BODY, **cambio})

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "validation_error"


def test_post_listas_migration_not_completed_returns_409(
    contract_client: TestClient, base_limpia: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json=BODY)

    assert respuesta.status_code == 409
    assert respuesta.json() == CONFLICTO


def test_post_listas_model_failure_saves_nothing(
    contract_app: FastAPI, contract_client: TestClient, base_migrada: Engine
) -> None:
    contract_app.dependency_overrides[get_predictor] = PredictorQueFalla
    try:
        respuesta = contract_client.post(LISTAS, json=BODY)
    finally:
        contract_app.dependency_overrides.pop(get_predictor, None)

    assert respuesta.status_code == 500
    assert contar(base_migrada, "listas_priorizadas") == 0
    assert contar(base_migrada, "predicciones") == 0


def test_get_listas_returns_summaries_most_recent_first(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    assert contract_client.get(LISTAS).json() == []
    primera = contract_client.post(LISTAS, json=BODY).json()
    segunda = contract_client.post(LISTAS, json={**BODY, "top_k": 10}).json()

    respuesta = contract_client.get(LISTAS)

    assert respuesta.status_code == 200
    resumenes = respuesta.json()
    assert [r["id"] for r in resumenes] == [segunda["id"], primera["id"]]
    assert resumenes[0] == {
        "id": segunda["id"],
        "nombre": "Lista del 31 ago 2026",
        "fecha_generacion": "2026-08-31",
        "creada_en": segunda["creada_en"],
        "modelo_version": "v1",
        "horizonte_dias": 30,
        "top_k": 10,
        "total_items": FILAS_ESPERADAS,
    }


def test_get_ultima_and_by_id_return_the_saved_list(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    assert contract_client.get(f"{LISTAS}/ultima").status_code == 404
    creada = contract_client.post(LISTAS, json=BODY).json()

    ultima = contract_client.get(f"{LISTAS}/ultima")
    por_id = contract_client.get(f"{LISTAS}/{creada['id']}")

    assert ultima.status_code == 200
    assert por_id.status_code == 200
    assert ultima.json() == creada
    assert por_id.json() == creada


@pytest.mark.parametrize(("ruta", "codigo"), [("/999999", 404), ("/abc", 400), ("/0", 400)])
def test_get_lista_unknown_or_invalid_id(
    contract_client: TestClient, base_limpia: Engine, ruta: str, codigo: int
) -> None:
    respuesta = contract_client.get(f"{LISTAS}{ruta}")

    assert respuesta.status_code == codigo
    assert set(respuesta.json()) == {"error"}


def test_openapi_documents_every_listas_operation_with_examples(
    openapi_spec: dict[str, Any],
) -> None:
    assert_operation_contract(openapi_spec, "post", LISTAS, 201, (400, 403, 409, 422))
    assert_operation_contract(openapi_spec, "get", LISTAS, 200, (403,))
    assert_operation_contract(openapi_spec, "get", f"{LISTAS}/ultima", 200, (403, 404))
    assert_operation_contract(openapi_spec, "get", f"{LISTAS}/{{lista_id}}", 200, (400, 403, 404))
    post = openapi_spec["paths"][LISTAS]["post"]
    assert json_example(post, 409) == CONFLICTO
    assert json_example(post, 422) == FECHA_PASADA
    assert "1..31" in post["responses"]["400"]["description"]
    prediccion = openapi_spec["components"]["schemas"]["PrediccionDTO"]["properties"]
    assert "correo" not in prediccion
    assert "cedula" in prediccion
    assert "501" not in post["responses"]


def test_post_listas_past_date_returns_422_and_saves_nothing(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json={**BODY, "fecha_referencia": "2026-08-30"})

    assert respuesta.status_code == 422
    assert respuesta.json() == FECHA_PASADA
    assert contar(base_migrada, "listas_priorizadas") == 0


def test_post_listas_horizon_31_returns_201(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json={**BODY, "horizonte_dias": 31})

    assert respuesta.status_code == 201
    assert respuesta.json()["horizonte_dias"] == 31


def test_post_listas_without_date_uses_clock_today(
    contract_client: TestClient, base_migrada: Engine
) -> None:
    respuesta = contract_client.post(LISTAS, json={"horizonte_dias": 30, "top_k": 25})

    assert respuesta.status_code == 201
    assert respuesta.json()["fecha_generacion"] == "2026-08-31"


# ------------------------------------------------------------------ R-008 T10: nombre de la lista
RELOJ_29_SEP = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)


class Reloj29Sep:
    def now(self) -> datetime:
        return RELOJ_29_SEP


@pytest.fixture
def reloj_29_sep(contract_app: FastAPI) -> None:
    contract_app.dependency_overrides[get_clock] = Reloj29Sep


def test_post_listas_without_name_returns_default_name_everywhere(
    contract_client: TestClient, base_migrada: Engine, reloj_29_sep: None
) -> None:
    respuesta = contract_client.post(LISTAS, json={})

    assert respuesta.status_code == 201
    creada = respuesta.json()
    assert creada["nombre"] == "Lista del 29 sep 2026"
    assert contract_client.get(f"{LISTAS}/{creada['id']}").json()["nombre"] == creada["nombre"]
    assert contract_client.get(f"{LISTAS}/ultima").json()["nombre"] == creada["nombre"]
    assert [r["nombre"] for r in contract_client.get(LISTAS).json()] == [creada["nombre"]]


def test_post_listas_with_name_saves_it_stripped(
    contract_client: TestClient, base_migrada: Engine, reloj_29_sep: None
) -> None:
    respuesta = contract_client.post(LISTAS, json={"nombre": "  Campaña octubre  "})

    assert respuesta.status_code == 201
    creada = respuesta.json()
    assert creada["nombre"] == "Campaña octubre"
    assert contract_client.get(f"{LISTAS}/{creada['id']}").json()["nombre"] == "Campaña octubre"
    assert contract_client.get(f"{LISTAS}/ultima").json()["nombre"] == "Campaña octubre"
    assert [r["nombre"] for r in contract_client.get(LISTAS).json()] == ["Campaña octubre"]


@pytest.mark.parametrize(
    "nombre",
    ["   ", "a" * 81, "a\u0007b", 5],
    ids=["solo-espacios", "81-caracteres", "caracter-de-control", "no-texto"],
)
def test_post_listas_invalid_name_returns_400_and_saves_nothing(
    contract_client: TestClient, base_migrada: Engine, reloj_29_sep: None, nombre: object
) -> None:
    antes = contar(base_migrada, "listas_priorizadas")

    respuesta = contract_client.post(LISTAS, json={"nombre": nombre})

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "validation_error"
    assert set(respuesta.json()) == {"error"}
    assert contar(base_migrada, "listas_priorizadas") == antes


def test_openapi_documents_nombre_in_request_and_responses(
    openapi_spec: dict[str, Any],
) -> None:
    schemas = openapi_spec["components"]["schemas"]
    generar = schemas["GenerarListaDTO"]
    assert "nombre" not in generar.get("required", [])
    variantes = generar["properties"]["nombre"]["anyOf"]
    texto = next(v for v in variantes if v.get("type") == "string")
    assert texto["maxLength"] == 80
    assert texto["minLength"] == 1
    assert {"type": "null"} in variantes
    assert generar["examples"][0]["nombre"] == "Campaña octubre"
    for dto in ("ListaPriorizadaDTO", "ListaResumenDTO"):
        assert "nombre" in schemas[dto]["required"]
        assert schemas[dto]["properties"]["nombre"]["maxLength"] == 80
    post = openapi_spec["paths"][LISTAS]["post"]
    ejemplos = post["requestBody"]["content"]["application/json"]["examples"]
    assert ejemplos["con_nombre"]["value"]["nombre"] == "Campaña octubre"
    assert ejemplos["nombre_invalido"]["value"] == {"nombre": "   "}
    assert "nombre" in post["responses"]["400"]["description"]
    assert json_example(post, 201)["nombre"] == "Campaña octubre"
    resumen = openapi_spec["paths"][LISTAS]["get"]["responses"]["200"]["content"]
    assert all("nombre" in r for r in resumen["application/json"]["example"])
