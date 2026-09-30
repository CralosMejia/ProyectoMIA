"""API de gestiones contra PostgreSQL real en ``head`` (R-009 T12; CU-08, CU-10).

Reloj de la API fijo en 2026-09-29T15:00Z (10:00 en Ecuador). Cada prueba siembra una
membresia ficticia ``MENSUAL`` que vence el 2026-10-05 en dos listas (dos predicciones
``ALTO`` del mismo ciclo) y una campana propia; al terminar borra todo lo que creo. Las 3
campanas de ejemplo de ``0007`` no se modifican. Aislamiento entre usuarios: NO APLICA
(RT-12, sin login; acceso restringido por IP, CU-00). Datos 100 % ficticios.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.api.dependencies import get_clock
from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.persistence.test_migrations import insert, membresia, modelo, socio

pytestmark = pytest.mark.integration

GESTIONES_PATH = "/api/v1/gestiones"
AHORA = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
EJEMPLO_COMPATIBLE = "Ejemplo: Renovación anticipada"
CERRADA = "La gestion esta cerrada y no se puede modificar."
DUPLICADA = "El ciclo de membresia ya tiene una gestion."


class RelojApi:
    def now(self) -> datetime:
        return AHORA


@dataclass(frozen=True)
class Datos:
    membresia_id: int
    prediccion_1: int
    prediccion_2: int
    campania_propia: int
    campania_inactiva: int
    campania_ejemplo: int


def _lista(conexion: Any, version: int) -> int:
    return insert(
        conexion,
        "listas_priorizadas",
        {
            "modelo_id": modelo(conexion, version=version),
            "fecha_generacion": AHORA.date(),
            "horizonte_dias": 30,
            "top_k": 10,
            "creada_en": AHORA,
            "nombre": "Lista ficticia de gestiones",
        },
    )


def _prediccion(conexion: Any, lista_id: int, membresia_id: int) -> int:
    return insert(
        conexion,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "score": "0.81234567",
            "nivel_riesgo": "ALTO",
            "factores_principales": "[]",
            "prioridad": 3,
            "dentro_top_k": True,
        },
    )


def _campania(conexion: Any, nombre: str, *, activa: bool) -> int:
    return insert(
        conexion,
        "campanias",
        {
            "nombre": nombre,
            "activa": activa,
            "niveles_riesgo": ["ALTO"],
            "planes": ["MENSUAL"],
            "prioridad": 1,
            "es_ejemplo": False,
        },
    )


@pytest.fixture
def datos(migrated_engine: Engine) -> Iterator[Datos]:
    with migrated_engine.begin() as conexion:
        socio_id = socio(conexion, nombre="Socio Ficticio", nombre_normalizado="SOCIO FICTICIO")
        membresia_id = membresia(
            conexion, socio_id=socio_id, plan="MENSUAL", fecha_vencimiento="2026-10-05"
        )
        creados = Datos(
            membresia_id=membresia_id,
            prediccion_1=_prediccion(conexion, _lista(conexion, 8301), membresia_id),
            prediccion_2=_prediccion(conexion, _lista(conexion, 8302), membresia_id),
            campania_propia=_campania(conexion, "Campaña API ficticia", activa=True),
            campania_inactiva=_campania(conexion, "Campaña API inactiva", activa=False),
            campania_ejemplo=int(
                conexion.execute(
                    text("SELECT id FROM campanias WHERE es_ejemplo AND nombre = :n"),
                    {"n": EJEMPLO_COMPATIBLE},
                ).scalar_one()
            ),
        )
    try:
        yield creados
    finally:
        _borrar(migrated_engine, creados)


def _borrar(engine: Engine, d: Datos) -> None:
    with engine.begin() as conexion:
        m = {"m": d.membresia_id}
        fila = conexion.execute(
            text("SELECT socio_id, carga_id FROM membresias WHERE id = :m"), m
        ).one()
        listas = list(
            conexion.execute(
                text("SELECT lista_id FROM predicciones WHERE membresia_id = :m"), m
            ).scalars()
        )
        modelos = list(
            conexion.execute(
                text("SELECT modelo_id FROM listas_priorizadas WHERE id = ANY(:l)"), {"l": listas}
            ).scalars()
        )
        conexion.execute(text("DELETE FROM gestiones_retencion WHERE membresia_id = :m"), m)
        conexion.execute(text("DELETE FROM predicciones WHERE membresia_id = :m"), m)
        conexion.execute(text("DELETE FROM listas_priorizadas WHERE id = ANY(:l)"), {"l": listas})
        conexion.execute(text("DELETE FROM modelos WHERE id = ANY(:i)"), {"i": modelos})
        conexion.execute(
            text("DELETE FROM campanias WHERE id = ANY(:c) AND NOT es_ejemplo"),
            {"c": [d.campania_propia, d.campania_inactiva]},
        )
        conexion.execute(text("DELETE FROM membresias WHERE id = :m"), m)
        conexion.execute(text("DELETE FROM socios WHERE id = :s"), {"s": fila.socio_id})
        conexion.execute(text("DELETE FROM cargas WHERE id = :k"), {"k": fila.carga_id})


@pytest.fixture
def client(contract_app: FastAPI, contract_client: TestClient) -> Iterator[TestClient]:
    contract_app.dependency_overrides[get_clock] = RelojApi
    try:
        yield contract_client
    finally:
        contract_app.dependency_overrides.pop(get_clock, None)


def contar(engine: Engine, membresia_id: int) -> int:
    with engine.connect() as conexion:
        return int(
            conexion.execute(
                text("SELECT count(*) FROM gestiones_retencion WHERE membresia_id = :m"),
                {"m": membresia_id},
            ).scalar_one()
        )


def cuerpo_crear(prediccion_id: int, **cambios: Any) -> dict[str, Any]:
    return {
        "prediccion_id": prediccion_id,
        "campania_id": None,
        "fecha_seguimiento": "2026-10-30",
        "responsable": "Andrea",
        **cambios,
    }


def resultado(**cambios: Any) -> dict[str, Any]:
    return {
        "contactado": True,
        "campania_ofrecida": "SI",
        "campania_aceptada": "SI",
        "renovo_declarado": "PENDIENTE",
        "fecha_contacto": "2026-09-29",
        "observaciones": "Observacion ficticia.",
        "responsable": "Andrea",
        "fecha_seguimiento": "2026-10-27",
        **cambios,
    }


def assert_error(response: Any, status_code: int, code: str, message: str) -> None:
    assert response.status_code == status_code, response.text
    assert response.json() == {"error": {"code": code, "message": message}}


def crear(client: TestClient, datos: Datos, **cambios: Any) -> dict[str, Any]:
    """Crea la gestion de ``prediccion_1``; con la campana de ejemplo salvo que se indique otra.

    Desde R-010 una gestion sin campana nace cerrada: las pruebas del seguimiento y del
    resultado necesitan una gestion con campana.
    """
    cambios.setdefault("campania_id", datos.campania_ejemplo)
    response = client.post(GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1, **cambios))
    assert response.status_code == 201, response.text
    creada: dict[str, Any] = response.json()
    return creada


# ------------------------------------------------------------------ POST /gestiones
def test_post_con_campania_compatible_crea_pendiente_con_datos_de_la_prediccion(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    assert creada["estado"] == "PENDIENTE"
    assert creada["prediccion_id"] == datos.prediccion_1
    assert creada["campania_id"] == datos.campania_ejemplo
    assert creada["campania_nombre"] == EJEMPLO_COMPATIBLE
    assert creada["score"] == "0.81234567"
    assert creada["nivel_riesgo"] == "ALTO"
    assert creada["modelo_version"] == "v8301"
    assert creada["plan"] == "MENSUAL"
    assert creada["fecha_vencimiento"] == "2026-10-05"
    assert creada["fecha_seguimiento"] == "2026-10-30"
    assert creada["responsable"] == "Andrea"
    assert datetime.fromisoformat(creada["fecha_asignacion"]) == AHORA
    assert creada["fecha_cierre"] is None
    assert contar(migrated_engine, datos.membresia_id) == 1


def test_post_repetido_o_desde_otra_lista_del_mismo_ciclo_devuelve_409(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    crear(client, datos, campania_id=datos.campania_ejemplo)

    repetida = client.post(GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1))
    otra_lista = client.post(GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_2))

    assert_error(repetida, 409, "conflict", DUPLICADA)
    assert_error(otra_lista, 409, "conflict", DUPLICADA)
    assert contar(migrated_engine, datos.membresia_id) == 1


RESULTADO_NULO = (
    "contactado",
    "campania_ofrecida",
    "campania_aceptada",
    "renovo_declarado",
    "fecha_contacto",
    "observaciones",
    "responsable",
)


def fila_gestion(engine: Engine, gestion_id: int) -> dict[str, Any]:
    with engine.connect() as conexion:
        return dict(
            conexion.execute(
                text("SELECT * FROM gestiones_retencion WHERE id = :g"), {"g": gestion_id}
            )
            .mappings()
            .one()
        )


def test_post_sin_campania_crea_la_gestion_cerrada_sin_resultado(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    response = client.post(
        GESTIONES_PATH, json={"prediccion_id": datos.prediccion_1, "campania_id": None}
    )

    assert response.status_code == 201, response.text
    creada = response.json()
    assert creada["estado"] == "CERRADA"
    assert creada["campania_id"] is None
    assert creada["campania_nombre"] is None
    assert datetime.fromisoformat(creada["fecha_cierre"]) == AHORA
    assert datetime.fromisoformat(creada["fecha_asignacion"]) == AHORA
    assert {campo: creada[campo] for campo in RESULTADO_NULO} == dict.fromkeys(RESULTADO_NULO)
    fila = fila_gestion(migrated_engine, creada["id"])
    assert fila["estado"] == "CERRADA"
    assert fila["cerrada_en"] == AHORA
    assert fila["fecha_seguimiento"] == fila["fecha_asignacion"] == AHORA.date()
    assert {campo: fila[campo] for campo in RESULTADO_NULO} == dict.fromkeys(RESULTADO_NULO)
    assert fila["deleted_at"] is None
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == creada


def test_post_sin_campania_ignora_fecha_de_seguimiento_y_responsable(
    client: TestClient, datos: Datos
) -> None:
    # La fecha enviada esta fuera del rango [hoy, vencimiento + 30]: sin campana no se valida.
    creada = crear(
        client, datos, campania_id=None, fecha_seguimiento="2027-01-01", responsable="Andrea"
    )

    assert creada["estado"] == "CERRADA"
    assert creada["fecha_seguimiento"] == "2026-09-29"
    assert creada["responsable"] is None


def test_post_sin_campania_no_queda_entre_las_pendientes(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    """R-010 (h): las alertas del dia 6 cuentan solo ``PENDIENTE``."""
    crear(client, datos, campania_id=None)

    with migrated_engine.connect() as conexion:
        pendientes = conexion.execute(
            text(
                "SELECT count(*) FROM gestiones_retencion "
                "WHERE estado = 'PENDIENTE' AND membresia_id = :m"
            ),
            {"m": datos.membresia_id},
        ).scalar_one()
    assert pendientes == 0
    assert contar(migrated_engine, datos.membresia_id) == 1


def test_post_tras_gestion_sin_campania_devuelve_409_con_o_sin_campania(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    crear(client, datos, campania_id=None)

    sin_campania = client.post(
        GESTIONES_PATH, json={"prediccion_id": datos.prediccion_2, "campania_id": None}
    )
    con_campania = client.post(
        GESTIONES_PATH,
        json=cuerpo_crear(datos.prediccion_1, campania_id=datos.campania_ejemplo),
    )

    assert_error(sin_campania, 409, "conflict", DUPLICADA)
    assert_error(con_campania, 409, "conflict", DUPLICADA)
    assert contar(migrated_engine, datos.membresia_id) == 1


def test_put_resultado_sobre_gestion_sin_campania_devuelve_409_sin_cambios(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=None)
    antes = fila_gestion(migrated_engine, creada["id"])

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado",
        json=resultado(
            contactado=False,
            campania_ofrecida="NO_APLICA",
            campania_aceptada="NO_APLICA",
            fecha_contacto=None,
            renovo_declarado="NO",
        ),
    )

    assert_error(response, 409, "conflict", CERRADA)
    assert fila_gestion(migrated_engine, creada["id"]) == antes
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == creada


@pytest.mark.parametrize("fecha", ["2026-09-28", "2026-11-05"])
def test_post_fecha_fuera_de_rango_devuelve_422_con_el_rango(
    migrated_engine: Engine, client: TestClient, datos: Datos, fecha: str
) -> None:
    response = client.post(
        GESTIONES_PATH,
        json=cuerpo_crear(
            datos.prediccion_1, campania_id=datos.campania_ejemplo, fecha_seguimiento=fecha
        ),
    )

    assert_error(
        response,
        422,
        "domain_rule_violated",
        "La fecha de seguimiento debe estar entre 2026-09-29 y 2026-11-04.",
    )
    assert contar(migrated_engine, datos.membresia_id) == 0


def test_post_extremos_del_rango_son_validos(client: TestClient, datos: Datos) -> None:
    assert crear(client, datos, fecha_seguimiento="2026-11-04")["fecha_seguimiento"] == (
        "2026-11-04"
    )


def test_post_campania_inactiva_devuelve_422(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    response = client.post(
        GESTIONES_PATH,
        json=cuerpo_crear(datos.prediccion_1, campania_id=datos.campania_inactiva),
    )

    assert_error(
        response, 422, "domain_rule_violated", "La campana no esta activa o no aplica a este socio."
    )
    assert contar(migrated_engine, datos.membresia_id) == 0


def test_post_campania_inexistente_devuelve_404(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    response = client.post(
        GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1, campania_id=999_999)
    )

    assert_error(response, 404, "not_found", "La campana no existe.")
    assert contar(migrated_engine, datos.membresia_id) == 0


def test_post_prediccion_inexistente_devuelve_404(client: TestClient, datos: Datos) -> None:
    response = client.post(GESTIONES_PATH, json=cuerpo_crear(999_999))

    assert_error(response, 404, "not_found", "La prediccion no existe.")


@pytest.mark.parametrize("omitir", [True, False], ids=["sin-el-campo", "nula"])
def test_post_con_campania_y_sin_fecha_de_seguimiento_devuelve_400(
    migrated_engine: Engine, client: TestClient, datos: Datos, omitir: bool
) -> None:
    body = cuerpo_crear(
        datos.prediccion_1, campania_id=datos.campania_ejemplo, fecha_seguimiento=None
    )
    if omitir:
        del body["fecha_seguimiento"]

    assert_validation_error(client.post(GESTIONES_PATH, json=body))
    assert contar(migrated_engine, datos.membresia_id) == 0


# ------------------------------------------------------------------ GET /gestiones/{id}
def test_get_gestion_devuelve_la_gestion(client: TestClient, datos: Datos) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    response = client.get(f"{GESTIONES_PATH}/{creada['id']}")

    assert response.status_code == 200
    assert response.json() == creada


def test_get_gestion_conserva_el_nombre_tras_editar_e_inactivar_la_campania(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_propia)
    editada = client.put(
        f"/api/v1/campanias/{datos.campania_propia}",
        json={
            "nombre": "Nombre cambiado",
            "niveles_riesgo": ["ALTO"],
            "planes": ["MENSUAL"],
            "prioridad": 1,
        },
    )
    inactivada = client.post(f"/api/v1/campanias/{datos.campania_propia}/inactivar")
    assert (editada.status_code, inactivada.status_code) == (200, 200)

    response = client.get(f"{GESTIONES_PATH}/{creada['id']}")

    assert response.json()["campania_nombre"] == "Campaña API ficticia"


# ------------------------------------------------------------------ PUT /gestiones/{id}/resultado
def test_put_resultado_pendiente_sigue_pendiente_y_reprograma(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    response = client.put(f"{GESTIONES_PATH}/{creada['id']}/resultado", json=resultado())

    assert response.status_code == 200, response.text
    cuerpo = response.json()
    assert cuerpo["estado"] == "PENDIENTE"
    assert cuerpo["fecha_seguimiento"] == "2026-10-27"
    assert cuerpo["contactado"] is True
    assert cuerpo["campania_ofrecida"] == "SI"
    assert cuerpo["fecha_cierre"] is None


def test_put_resultado_renovo_no_cierra_y_otro_put_devuelve_409_sin_cambios(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)
    path = f"{GESTIONES_PATH}/{creada['id']}/resultado"

    cerrada = client.put(path, json=resultado(renovo_declarado="NO", campania_aceptada="NO"))

    assert cerrada.status_code == 200, cerrada.text
    assert cerrada.json()["estado"] == "CERRADA"
    assert datetime.fromisoformat(cerrada.json()["fecha_cierre"]) == AHORA
    assert cerrada.json()["fecha_seguimiento"] == "2026-10-30"

    otra = client.put(path, json=resultado(renovo_declarado="SI"))

    assert_error(otra, 409, "conflict", CERRADA)
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == cerrada.json()


def test_put_resultado_no_contactado_con_ofrecida_si_devuelve_422(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado",
        json=resultado(contactado=False, fecha_contacto=None),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "domain_rule_violated"
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == creada


def test_put_resultado_fecha_fuera_de_rango_devuelve_422(client: TestClient, datos: Datos) -> None:
    creada = crear(client, datos)

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado",
        json=resultado(fecha_seguimiento="2026-11-05"),
    )

    assert_error(
        response,
        422,
        "domain_rule_violated",
        "La fecha de seguimiento debe estar entre 2026-09-29 y 2026-11-04.",
    )


# ------------------------------------------------------------------ siguen en 501 (dia 6)
@pytest.mark.parametrize("path", ["/api/v1/alertas", f"{GESTIONES_PATH}?filtro=hoy"])
def test_alertas_y_filtro_siguen_en_501(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 501
