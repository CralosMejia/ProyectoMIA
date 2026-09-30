"""API de campanas: editar no activa, orden del listado y sugerencias por plan (R-009, R-010).

Complementa ``test_campanias_api.py``:
- una campana inactiva se puede editar pero sigue inactiva; ``activa`` en el cuerpo se
  rechaza: solo se reactiva con ``POST /campanias/{id}/activar`` (R-010, decision (a));
- ``GET /campanias`` ordena ``activa DESC, prioridad, lower(nombre)`` (decision (e));
- las sugerencias filtran tambien por plan y se ordenan por prioridad y nombre (decision (f)).

Aislamiento entre usuarios: NO APLICA (RT-12, sin login). Datos 100 % ficticios.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.integration.api import test_campanias_api as base
from tests.integration.api.contract_helpers import assert_validation_error
from tests.integration.api.test_campanias_api import CAMPANIAS_PATH, VALIDA, Campanias

# Fixtures reutilizadas de ``test_campanias_api.py`` (borran lo que crean).
campanias = base.campanias
prediccion_alto_mensual = base.prediccion_alto_mensual

pytestmark = pytest.mark.integration


def test_put_campania_inactiva_se_edita_y_sigue_inactiva(
    campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()
    contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/inactivar")

    response = contract_client.put(
        f"{CAMPANIAS_PATH}/{creada['id']}", json={**VALIDA, "nombre": "Editada inactiva"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["nombre"] == "Editada inactiva"
    assert response.json()["activa"] is False


def test_put_campania_con_activa_en_el_cuerpo_devuelve_400_y_no_reactiva(
    migrated_engine: Engine, campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()
    contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/inactivar")

    response = contract_client.put(
        f"{CAMPANIAS_PATH}/{creada['id']}", json={**VALIDA, "activa": True}
    )

    assert_validation_error(response)
    with migrated_engine.connect() as conexion:
        activa = conexion.execute(
            text("SELECT activa FROM campanias WHERE id = :id"), {"id": creada["id"]}
        ).scalar_one()
    assert activa is False


def test_campania_inactiva_solo_se_reactiva_con_la_ruta_activar(
    campanias: Campanias, contract_client: TestClient
) -> None:
    creada = campanias.crear()
    contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/inactivar")

    otra_ruta = contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/reactivar")
    activada = contract_client.post(f"{CAMPANIAS_PATH}/{creada['id']}/activar")

    assert otra_ruta.status_code in (404, 405)
    assert activada.status_code == 200, activada.text
    assert activada.json() == creada


def test_get_campanias_ordena_activas_primero_luego_prioridad_y_nombre_sin_mayusculas(
    campanias: Campanias, contract_client: TestClient
) -> None:
    inactiva = campanias.crear(nombre="Orden inactiva", prioridad=1)
    contract_client.post(f"{CAMPANIAS_PATH}/{inactiva['id']}/inactivar")
    zeta = campanias.crear(nombre="Orden Zeta", prioridad=998)
    alfa = campanias.crear(nombre="orden alfa", prioridad=998)
    ultima = campanias.crear(nombre="Orden ultima", prioridad=999)

    listado = contract_client.get(CAMPANIAS_PATH).json()

    propias = [c["id"] for c in listado if c["id"] in campanias.ids]
    assert propias == [alfa["id"], zeta["id"], ultima["id"], inactiva["id"]]
    activas = [c["activa"] for c in listado]
    assert activas == sorted(activas, reverse=True)


def test_sugeridas_excluye_campanias_de_otro_plan_o_nivel_y_ordena_por_prioridad_y_nombre(
    campanias: Campanias, contract_client: TestClient, prediccion_alto_mensual: int
) -> None:
    otro_plan = campanias.crear(nombre="Solo anual", niveles_riesgo=["ALTO"], planes=["ANUAL"])
    otro_nivel = campanias.crear(nombre="Solo bajo", niveles_riesgo=["BAJO"], planes=["MENSUAL"])
    beta = campanias.crear(nombre="beta sugerida", prioridad=1)
    alfa = campanias.crear(nombre="Alfa sugerida", prioridad=1)

    response = contract_client.get(
        f"/api/v1/predicciones/{prediccion_alto_mensual}/campanias-sugeridas"
    )

    assert response.status_code == 200, response.text
    sugeridas = response.json()
    ids = [c["id"] for c in sugeridas]
    assert otro_plan["id"] not in ids
    assert otro_nivel["id"] not in ids
    assert [i for i in ids if i in (alfa["id"], beta["id"])] == [alfa["id"], beta["id"]]
    assert all(c["activa"] for c in sugeridas)
    assert all("ALTO" in c["niveles_riesgo"] and "MENSUAL" in c["planes"] for c in sugeridas)
    prioridades = [c["prioridad"] for c in sugeridas]
    assert prioridades == sorted(prioridades)


def test_sugeridas_plan_diario_devuelve_lista_vacia(
    migrated_engine: Engine, contract_client: TestClient, prediccion_alto_mensual: int
) -> None:
    with migrated_engine.begin() as conexion:
        conexion.execute(
            text(
                "UPDATE membresias SET plan = 'DIARIO' WHERE id = "
                "(SELECT membresia_id FROM predicciones WHERE id = :p)"
            ),
            {"p": prediccion_alto_mensual},
        )

    response = contract_client.get(
        f"/api/v1/predicciones/{prediccion_alto_mensual}/campanias-sugeridas"
    )

    assert response.status_code == 200, response.text
    assert response.json() == []
