"""API de gestiones: fronteras, concurrencia y datos personales (R-009 T9-T12, test-engineer).

Complementa ``test_gestiones_api.py`` con los criterios que alli no se cubren:
- plazo de seguimiento terminado -> ``422`` (decision (g));
- campana activa pero incompatible con el nivel del socio -> ``422`` (decision (g));
- "hoy" es el de Ecuador aunque en UTC ya sea el dia siguiente (decision (g));
- dos creaciones simultaneas del mismo ciclo: una ``201`` y otra ``409``, una sola fila;
- dos cierres simultaneos: esperan el ``FOR UPDATE``; uno ``200`` y el otro ``409`` (decision (h));
- cada regla de coherencia responde ``422`` con su propio mensaje y no guarda nada;
- ``GestionDTO`` tiene exactamente los campos del contrato;
- ni los logs ni los errores llevan nombre, cedula ni celular del socio.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
Datos 100 % ficticios.
"""

import logging
import threading
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.api.dependencies import get_clock
from tests.integration.api import test_gestiones_api as base
from tests.integration.api.test_gestiones_api import (
    CERRADA,
    DUPLICADA,
    GESTIONES_PATH,
    Datos,
    assert_error,
    contar,
    crear,
    cuerpo_crear,
    resultado,
)

# Fixtures reutilizadas de ``test_gestiones_api.py`` (misma siembra y mismo reloj fijo).
datos = base.datos
client = base.client

pytestmark = pytest.mark.integration

PLAZO_TERMINADO = "El plazo de seguimiento de este ciclo ya termino."
NO_APLICA = "La campana no esta activa o no aplica a este socio."
EJEMPLO_INCOMPATIBLE = "Ejemplo: Recordatorio de renovación"  # MEDIO, BAJO: no aplica a ALTO
CEDULA_FICTICIA = "1799999995"
CELULAR_FICTICIO = "0990000123"
CAMPOS_GESTION_DTO = {
    "id",
    "prediccion_id",
    "socio_nombre",
    "plan",
    "fecha_vencimiento",
    "modelo_version",
    "score",
    "nivel_riesgo",
    "campania_id",
    "campania_nombre",
    "estado",
    "fecha_asignacion",
    "fecha_seguimiento",
    "responsable",
    "contactado",
    "campania_ofrecida",
    "campania_aceptada",
    "renovo_declarado",
    "fecha_contacto",
    "observaciones",
    "fecha_cierre",
}


def _esperar_bloqueados(engine: Engine, cuantos: int, limite_s: float = 15.0) -> int:
    """Espera a que ``cuantos`` sesiones de la base de pruebas esperen un bloqueo."""
    fin = time.monotonic() + limite_s
    esperando = 0
    while time.monotonic() < fin:
        with engine.connect() as conexion:
            esperando = int(
                conexion.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    )
                ).scalar_one()
            )
        if esperando >= cuantos:
            return esperando
        time.sleep(0.05)
    return esperando


def _en_paralelo(
    engine: Engine, bloqueo_sql: str, parametros: dict[str, Any], peticion: Any
) -> tuple[int, list[httpx.Response]]:
    """Lanza dos peticiones mientras la prueba retiene un bloqueo de fila; luego lo suelta.

    Devuelve cuantas sesiones llegaron a esperar el bloqueo y las dos respuestas.
    """
    respuestas: list[httpx.Response] = []
    candado = threading.Lock()

    def ejecutar() -> None:
        response = peticion()
        with candado:
            respuestas.append(response)

    hilos = [threading.Thread(target=ejecutar, daemon=True) for _ in range(2)]
    with engine.connect() as retenedor, retenedor.begin():
        retenedor.execute(text(bloqueo_sql), parametros)
        for hilo in hilos:
            hilo.start()
        bloqueados = _esperar_bloqueados(engine, 2)
    for hilo in hilos:
        hilo.join(timeout=30)
    return bloqueados, respuestas


# ------------------------------------------------------------------ POST: fronteras
def test_post_plazo_de_seguimiento_terminado_devuelve_422(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    # vencimiento + 30 = 2026-09-28, anterior a hoy (2026-09-29).
    with migrated_engine.begin() as conexion:
        conexion.execute(
            text("UPDATE membresias SET fecha_vencimiento = '2026-08-29' WHERE id = :m"),
            {"m": datos.membresia_id},
        )

    response = client.post(
        GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1, fecha_seguimiento="2026-09-29")
    )

    assert_error(response, 422, "domain_rule_violated", PLAZO_TERMINADO)
    assert contar(migrated_engine, datos.membresia_id) == 0


def test_post_ultimo_dia_del_plazo_se_acepta(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    # vencimiento + 30 = 2026-09-29 = hoy: el rango es un solo dia.
    with migrated_engine.begin() as conexion:
        conexion.execute(
            text("UPDATE membresias SET fecha_vencimiento = '2026-08-30' WHERE id = :m"),
            {"m": datos.membresia_id},
        )

    creada = crear(client, datos, fecha_seguimiento="2026-09-29")

    assert creada["fecha_seguimiento"] == "2026-09-29"


def test_post_campania_activa_de_otro_nivel_devuelve_422(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    with migrated_engine.connect() as conexion:
        incompatible = int(
            conexion.execute(
                text("SELECT id FROM campanias WHERE es_ejemplo AND nombre = :n"),
                {"n": EJEMPLO_INCOMPATIBLE},
            ).scalar_one()
        )

    response = client.post(
        GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1, campania_id=incompatible)
    )

    assert_error(response, 422, "domain_rule_violated", NO_APLICA)
    assert contar(migrated_engine, datos.membresia_id) == 0


class _RelojMadrugadaUtc:
    def now(self) -> datetime:
        return datetime(2026, 9, 30, 3, 0, tzinfo=UTC)  # 22:00 del 29 en Ecuador


def test_post_madrugada_utc_usa_hoy_de_ecuador(
    contract_app: FastAPI, client: TestClient, datos: Datos
) -> None:
    contract_app.dependency_overrides[get_clock] = _RelojMadrugadaUtc

    creada = crear(client, datos, fecha_seguimiento="2026-09-29")

    assert creada["fecha_seguimiento"] == "2026-09-29"


def test_post_devuelve_exactamente_los_campos_del_contrato(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    assert set(creada) == CAMPOS_GESTION_DTO


# ------------------------------------------------------------------ concurrencia
def test_post_dos_creaciones_simultaneas_del_mismo_ciclo_una_201_y_otra_409(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    predicciones = iter([datos.prediccion_1, datos.prediccion_2])
    candado = threading.Lock()

    def peticion() -> httpx.Response:
        with candado:
            prediccion_id = next(predicciones)
        return client.post(GESTIONES_PATH, json=cuerpo_crear(prediccion_id))

    # La prueba retiene la fila de la membresia: ambas creaciones pasan la comprobacion
    # previa (aun no hay gestion) y quedan en vuelo a la vez al insertar.
    bloqueados, respuestas = _en_paralelo(
        migrated_engine,
        "SELECT id FROM membresias WHERE id = :m FOR UPDATE",
        {"m": datos.membresia_id},
        peticion,
    )

    assert bloqueados == 2
    assert sorted(r.status_code for r in respuestas) == [201, 409], [r.text for r in respuestas]
    [rechazada] = [r for r in respuestas if r.status_code == 409]
    assert_error(rechazada, 409, "conflict", DUPLICADA)
    assert contar(migrated_engine, datos.membresia_id) == 1


def test_put_dos_cierres_simultaneos_esperan_el_bloqueo_uno_200_y_otro_409(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)
    path = f"{GESTIONES_PATH}/{creada['id']}/resultado"
    cuerpos = iter(
        [
            resultado(renovo_declarado="NO", campania_aceptada="NO"),
            resultado(renovo_declarado="SI", campania_aceptada="SI"),
        ]
    )
    candado = threading.Lock()

    def peticion() -> httpx.Response:
        with candado:
            cuerpo = next(cuerpos)
        return client.put(path, json=cuerpo)

    bloqueados, respuestas = _en_paralelo(
        migrated_engine,
        "SELECT id FROM gestiones_retencion WHERE id = :g FOR UPDATE",
        {"g": creada["id"]},
        peticion,
    )

    # Sin ``FOR UPDATE`` en la lectura previa, ninguna de las dos esperaria aqui.
    assert bloqueados == 2
    assert sorted(r.status_code for r in respuestas) == [200, 409], [r.text for r in respuestas]
    [ganadora] = [r for r in respuestas if r.status_code == 200]
    [rechazada] = [r for r in respuestas if r.status_code == 409]
    assert_error(rechazada, 409, "conflict", CERRADA)
    assert ganadora.json()["estado"] == "CERRADA"
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == ganadora.json()


# ------------------------------------------------------------------ PUT: coherencia y cierre
@pytest.mark.parametrize(
    ("con_campania", "cambios", "mensaje"),
    [
        (
            False,
            {"campania_ofrecida": "NO", "campania_aceptada": "NO_APLICA"},
            "Sin campana asignada, ¿Se ofrecio? y ¿Acepto? deben ser No aplica.",
        ),
        (
            True,
            {"campania_ofrecida": "NO", "campania_aceptada": "SI"},
            "Si no se ofrecio la campana, ¿Acepto? debe ser No aplica.",
        ),
        (
            True,
            {"campania_ofrecida": "SI", "campania_aceptada": "NO_APLICA"},
            "Si se ofrecio la campana, indique si la acepto (Si, No o Pendiente).",
        ),
        (
            True,
            {"fecha_contacto": None},
            "Si se contacto al socio, indique la fecha del contacto.",
        ),
        (
            True,
            {"fecha_contacto": "2026-09-30"},
            "La fecha del contacto debe estar entre la fecha de asignacion y hoy.",
        ),
        (
            True,
            {"fecha_contacto": "2026-09-28"},
            "La fecha del contacto debe estar entre la fecha de asignacion y hoy.",
        ),
        (
            True,
            {
                "contactado": False,
                "campania_ofrecida": "NO_APLICA",
                "campania_aceptada": "NO_APLICA",
            },
            "Si no se contacto al socio, no indique fecha del contacto.",
        ),
    ],
)
def test_put_resultado_incoherente_devuelve_422_con_el_mensaje_de_la_regla_sin_guardar(
    client: TestClient, datos: Datos, con_campania: bool, cambios: dict[str, Any], mensaje: str
) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo if con_campania else None)

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado",
        json=resultado(renovo_declarado="NO", **cambios),
    )

    assert_error(response, 422, "domain_rule_violated", mensaje)
    assert client.get(f"{GESTIONES_PATH}/{creada['id']}").json() == creada


def test_put_resultado_renovo_si_cierra_la_gestion(client: TestClient, datos: Datos) -> None:
    creada = crear(client, datos, campania_id=datos.campania_ejemplo)

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado", json=resultado(renovo_declarado="SI")
    )

    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "CERRADA"
    assert response.json()["renovo_declarado"] == "SI"
    assert response.json()["fecha_cierre"] is not None


def test_put_resultado_sin_campania_no_contactado_cierra_con_no_aplica(
    client: TestClient, datos: Datos
) -> None:
    creada = crear(client, datos)

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

    assert response.status_code == 200, response.text
    assert response.json()["estado"] == "CERRADA"
    assert response.json()["contactado"] is False


def test_put_resultado_no_modifica_la_membresia(
    migrated_engine: Engine, client: TestClient, datos: Datos
) -> None:
    consulta = text("SELECT updated_at, fecha_vencimiento, plan FROM membresias WHERE id = :m")
    creada = crear(client, datos)
    with migrated_engine.connect() as conexion:
        antes = conexion.execute(consulta, {"m": datos.membresia_id}).one()

    response = client.put(
        f"{GESTIONES_PATH}/{creada['id']}/resultado",
        json=resultado(
            campania_ofrecida="NO_APLICA", campania_aceptada="NO_APLICA", renovo_declarado="SI"
        ),
    )

    assert response.status_code == 200, response.text
    with migrated_engine.connect() as conexion:
        assert conexion.execute(consulta, {"m": datos.membresia_id}).one() == antes


# ------------------------------------------------------------------ datos personales
def test_gestiones_no_exponen_datos_personales_en_logs_ni_en_errores(
    migrated_engine: Engine,
    client: TestClient,
    datos: Datos,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with migrated_engine.begin() as conexion:
        conexion.execute(
            text(
                "UPDATE socios SET cedula = :cedula, celular = :celular "
                "WHERE id = (SELECT socio_id FROM membresias WHERE id = :m)"
            ),
            {"cedula": CEDULA_FICTICIA, "celular": CELULAR_FICTICIO, "m": datos.membresia_id},
        )
    personales = ["Socio Ficticio", CEDULA_FICTICIA, CELULAR_FICTICIO]

    with caplog.at_level(logging.DEBUG):
        fuera = client.post(
            GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_1, fecha_seguimiento="2026-09-28")
        )
        inactiva = client.post(
            GESTIONES_PATH,
            json=cuerpo_crear(datos.prediccion_1, campania_id=datos.campania_inactiva),
        )
        creada = client.post(
            GESTIONES_PATH,
            json=cuerpo_crear(datos.prediccion_1, campania_id=datos.campania_ejemplo),
        )
        duplicada = client.post(GESTIONES_PATH, json=cuerpo_crear(datos.prediccion_2))
        path = f"{GESTIONES_PATH}/{creada.json()['id']}"
        sugeridas = client.get(f"/api/v1/predicciones/{datos.prediccion_1}/campanias-sugeridas")
        leida = client.get(path)
        incoherente = client.put(
            f"{path}/resultado", json=resultado(contactado=False, fecha_contacto=None)
        )
        cerrada = client.put(
            f"{path}/resultado", json=resultado(renovo_declarado="NO", campania_aceptada="NO")
        )
        tras_cierre = client.put(f"{path}/resultado", json=resultado())

    respuestas = [
        fuera,
        inactiva,
        creada,
        duplicada,
        sugeridas,
        leida,
        incoherente,
        cerrada,
        tras_cierre,
    ]
    assert [r.status_code for r in respuestas] == [422, 422, 201, 409, 200, 200, 422, 200, 409]
    errores = "".join(r.text for r in (fuera, inactiva, duplicada, incoherente, tras_cierre))
    assert [valor for valor in personales if valor in caplog.text] == []
    assert [valor for valor in personales if valor in errores + sugeridas.text] == []
