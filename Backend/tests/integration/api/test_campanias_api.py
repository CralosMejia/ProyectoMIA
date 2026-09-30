"""API de campanas y sugerencias contra PostgreSQL real en ``head`` (R-009 T8; CU-06, CU-07).

Cada prueba borra al terminar las campanas que creo (por id) y la prediccion ficticia que
sembro; las 3 campanas de ejemplo de ``0007`` no se modifican. Aislamiento entre usuarios:
NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00). Datos 100 % ficticios.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.persistence.test_migrations import insert, membresia, modelo

pytestmark = pytest.mark.integration

CAMPANIAS_PATH = "/api/v1/campanias"
INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
NOMBRES_EJEMPLO = [
    "Ejemplo: Llamada personal antes del vencimiento",
    "Ejemplo: Renovación anticipada",
    "Ejemplo: Recordatorio de renovación",
]
VALIDA: dict[str, Any] = {
    "nombre": "  Campana API  ",
    "descripcion": "Llamada de prueba.",
    "niveles_riesgo": ["MEDIO", "ALTO", "MEDIO"],
    "planes": ["TRIMESTRAL", "MENSUAL"],
    "prioridad": 5,
}


class Campanias:
    """Crea campanas por la API y recuerda sus ids para borrarlas al final."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.ids: list[int] = []

    def crear(self, **cambios: Any) -> dict[str, Any]:
        response = self.client.post(CAMPANIAS_PATH, json={**VALIDA, **cambios})
        assert response.status_code == 201, response.text
        cuerpo: dict[str, Any] = response.json()
        self.ids.append(int(cuerpo["id"]))
        return cuerpo


@pytest.fixture
def campanias(migrated_engine: Engine, contract_client: TestClient) -> Iterator[Campanias]:
    registro = Campanias(contract_client)
    try:
        yield registro
    finally:
        if registro.ids:
            with migrated_engine.begin() as conexion:
                conexion.execute(
                    text("DELETE FROM campanias WHERE id = ANY(:ids) AND NOT es_ejemplo"),
                    {"ids": registro.ids},
                )


def contar(engine: Engine) -> int:
    with engine.connect() as conexion:
        return int(conexion.execute(text("SELECT count(*) FROM campanias")).scalar_one())


@pytest.fixture
def prediccion_alto_mensual(migrated_engine: Engine) -> Iterator[int]:
    """Prediccion ficticia ``ALTO`` de una membresia ``MENSUAL`` (confirmada y borrada)."""
    with migrated_engine.begin() as conexion:
        membresia_id = membresia(conexion, plan="MENSUAL")
        modelo_id = modelo(conexion, version=8801)
        lista_id = insert(
            conexion,
            "listas_priorizadas",
            {
                "modelo_id": modelo_id,
                "fecha_generacion": INSTANTE.date(),
                "horizonte_dias": 30,
                "top_k": 10,
                "creada_en": INSTANTE,
                "nombre": "Lista ficticia de campanas",
            },
        )
        prediccion_id = insert(
            conexion,
            "predicciones",
            {
                "lista_id": lista_id,
                "membresia_id": membresia_id,
                "score": "0.8",
                "nivel_riesgo": "ALTO",
                "factores_principales": "[]",
                "prioridad": 1,
                "dentro_top_k": True,
            },
        )
        ids = (
            conexion.execute(
                text("SELECT socio_id, carga_id FROM membresias WHERE id = :id"),
                {"id": membresia_id},
            )
            .mappings()
            .one()
        )
    try:
        yield prediccion_id
    finally:
        with migrated_engine.begin() as conexion:
            for tabla, fila_id in (
                ("predicciones", prediccion_id),
                ("listas_priorizadas", lista_id),
                ("modelos", modelo_id),
                ("membresias", membresia_id),
                ("socios", ids["socio_id"]),
                ("cargas", ids["carga_id"]),
            ):
                conexion.execute(
                    text(f"DELETE FROM {tabla} WHERE id = :id"),  # noqa: S608 - nombres fijos
                    {"id": fila_id},
                )


# ------------------------------------------------------------------ GET /campanias
def test_get_campanias_devuelve_las_tres_de_ejemplo_por_prioridad(
    migrated_engine: Engine, contract_client: TestClient
) -> None:
    response = contract_client.get(CAMPANIAS_PATH)

    assert response.status_code == 200
    ejemplos = [c for c in response.json() if c["es_ejemplo"]]
    assert [c["nombre"] for c in ejemplos] == NOMBRES_EJEMPLO
    assert [c["prioridad"] for c in ejemplos] == [1, 2, 3]
    assert all(c["activa"] for c in ejemplos)


# ------------------------------------------------------------------ POST /campanias
def test_post_campania_valida_devuelve_201_normalizada_y_aparece_en_get(
    campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()

    assert creada["nombre"] == "Campana API"
    assert creada["niveles_riesgo"] == ["ALTO", "MEDIO"]
    assert creada["planes"] == ["MENSUAL", "TRIMESTRAL"]
    assert creada["activa"] is True
    assert creada["es_ejemplo"] is False
    listado = contract_client.get(CAMPANIAS_PATH).json()
    assert creada in listado


@pytest.mark.parametrize(
    "cambios",
    [
        {"nombre": "   "},
        {"niveles_riesgo": []},
        {"planes": ["DIARIO"]},
        {"prioridad": 0},
        {"prioridad": 1000},
        {"extra": "no permitido"},
    ],
    ids=["nombre-espacios", "sin-niveles", "plan-diario", "prioridad-0", "prioridad-1000", "extra"],
)
def test_post_campania_invalida_devuelve_400_sin_guardar(
    migrated_engine: Engine, contract_client: TestClient, cambios: dict[str, Any]
) -> None:
    antes = contar(migrated_engine)

    response = contract_client.post(CAMPANIAS_PATH, json={**VALIDA, **cambios})

    assert_validation_error(response)
    assert contar(migrated_engine) == antes


# ------------------------------------------------------------------ PUT /campanias/{id}
def test_put_campania_devuelve_200_con_los_datos_nuevos(
    campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()
    nuevos = {**VALIDA, "nombre": "Editada", "niveles_riesgo": ["BAJO"], "prioridad": 9}

    response = contract_client.put(f"{CAMPANIAS_PATH}/{creada['id']}", json=nuevos)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["id"] == creada["id"]
    assert cuerpo["nombre"] == "Editada"
    assert cuerpo["niveles_riesgo"] == ["BAJO"]
    assert cuerpo["prioridad"] == 9
    assert cuerpo["activa"] is True
    assert cuerpo["es_ejemplo"] is False


def test_put_campania_inexistente_devuelve_404(
    migrated_engine: Engine, contract_client: TestClient
) -> None:
    response = contract_client.put(f"{CAMPANIAS_PATH}/999999", json=VALIDA)

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "La campana no existe."}}


def test_put_campania_id_cero_devuelve_400(contract_client: TestClient) -> None:
    assert_validation_error(contract_client.put(f"{CAMPANIAS_PATH}/0", json=VALIDA))


# ------------------------------------------------------------------ POST /campanias/{id}/inactivar
def test_inactivar_devuelve_200_idempotente_y_no_borra_la_fila(
    migrated_engine: Engine, campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()
    antes = contar(migrated_engine)

    primera = contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/inactivar")
    segunda = contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/inactivar")

    assert primera.status_code == 200
    assert primera.json() == {**creada, "activa": False}
    assert segunda.status_code == 200
    assert segunda.json() == primera.json()
    assert contar(migrated_engine) == antes
    with migrated_engine.connect() as conexion:
        deleted_at = conexion.execute(
            text("SELECT deleted_at FROM campanias WHERE id = :id"), {"id": creada["id"]}
        ).scalar_one()
    assert deleted_at is None


def test_inactivar_inexistente_devuelve_404(
    migrated_engine: Engine, contract_client: TestClient
) -> None:
    response = contract_client.post(f"{CAMPANIAS_PATH}/999999/inactivar")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "La campana no existe."


# ------------------------------------------------------------------ sugerencias (CU-07)
def test_sugeridas_devuelve_compatibles_activas_por_prioridad_y_excluye_inactivadas(
    campanias: Campanias, contract_client: TestClient, prediccion_alto_mensual: int
) -> None:
    compatible = campanias.crear(nombre="Campana API compatible", prioridad=5)
    campanias.crear(nombre="Campana API solo bajo", niveles_riesgo=["BAJO"], prioridad=1)
    campanias.crear(nombre="Campana API solo anual", planes=["ANUAL"], prioridad=1)
    ruta = f"/api/v1/predicciones/{prediccion_alto_mensual}/campanias-sugeridas"

    response = contract_client.get(ruta)

    assert response.status_code == 200
    assert [c["nombre"] for c in response.json()] == [
        "Ejemplo: Llamada personal antes del vencimiento",
        "Ejemplo: Renovación anticipada",
        "Campana API compatible",
    ]

    contract_client.post(f"{CAMPANIAS_PATH}/{compatible['id']}/inactivar")

    nombres = [c["nombre"] for c in contract_client.get(ruta).json()]
    assert "Campana API compatible" not in nombres


def test_sugeridas_prediccion_inexistente_devuelve_404(
    migrated_engine: Engine, contract_client: TestClient
) -> None:
    response = contract_client.get("/api/v1/predicciones/999999/campanias-sugeridas")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "La prediccion no existe."}
    }


# ------------------------------------------------------------------ OpenAPI
def test_openapi_campanias_sin_501_y_prioridad_maxima_999(openapi_spec: dict[str, Any]) -> None:
    rutas = [
        ("get", "/api/v1/campanias"),
        ("post", "/api/v1/campanias"),
        ("put", "/api/v1/campanias/{campania_id}"),
        ("post", "/api/v1/campanias/{campania_id}/inactivar"),
        ("get", "/api/v1/predicciones/{prediccion_id}/campanias-sugeridas"),
    ]
    for metodo, ruta in rutas:
        assert "501" not in openapi_spec["paths"][ruta][metodo]["responses"], (metodo, ruta)

    prioridad = openapi_spec["components"]["schemas"]["CampaniaEntradaDTO"]["properties"][
        "prioridad"
    ]
    assert prioridad["maximum"] == 999
    assert prioridad["minimum"] == 1


def test_openapi_post_y_put_declaran_ejemplos_de_request(openapi_spec: dict[str, Any]) -> None:
    for metodo, ruta in (("post", "/api/v1/campanias"), ("put", "/api/v1/campanias/{campania_id}")):
        cuerpo = openapi_spec["paths"][ruta][metodo]["requestBody"]["content"]["application/json"]
        assert cuerpo["examples"], (metodo, ruta)
