"""Comando ``python -m app.cli adoptar-modelo`` (R-015, T10) contra PostgreSQL real.

Escenario de ``reentrenamiento_datos`` (hoy = 2026-09-30, modelo v1 vigente) mas una cartera
de 12 ciclos ``MENSUAL`` que vencen en octubre de 2026 para poder generar listas. Se genera
una lista con v1 y una gestion; tras adoptar, lo anterior sigue igual (``modelo_id`` de v1) y
una lista nueva usa v2. Datos 100 % ficticios.
"""

from collections.abc import Iterator, Sequence
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.api.dependencies import get_clock
from app.application.historial.ports import NuevaMembresia, NuevoSocio
from app.cli import main
from app.core.config import Settings
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from app.infrastructure.persistence.unit_of_work_reentrenamiento import (
    AbridorBloqueoReentrenamiento,
)
from app.main import create_app
from tests.integration.reentrenamiento_datos import (
    HOY,
    Reloj,
    contar,
    limpiar_base,
    proxima_fecha,
    sembrar,
)

pytestmark = pytest.mark.integration

PROGRAMADA = date(2026, 12, 15)
LISTAS = "/api/v1/listas"
CUERPO_LISTA = {"fecha_referencia": HOY.isoformat(), "horizonte_dias": 30, "top_k": 25}
TABLAS_PREVIAS = ("listas_priorizadas", "predicciones", "gestiones_retencion")


class PredictorQueFalla:
    def train(self, *args: object, **kwargs: object) -> TrainedModel:
        raise RuntimeError("fallo del entrenamiento")

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        raise AssertionError("no se predice")


@pytest.fixture
def base(
    migrated_engine: Engine, test_database_url: URL, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Engine]:
    monkeypatch.setenv("DATABASE_URL", test_database_url.render_as_string(hide_password=False))
    monkeypatch.setenv("MIGRAR_HISTORICO_AL_ARRANCAR", "false")
    monkeypatch.setenv("REENTRENAMIENTO_AUTOMATICO", "false")
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


@pytest.fixture
def cliente(base: Engine, test_database_url: URL) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
            APP_ENV="test",
        )
    )
    app.dependency_overrides[get_clock] = Reloj
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
        yield c


def _sembrar_con_cartera(engine: Engine) -> None:
    sembrar(engine, programada=PROGRAMADA)
    carga_id = contar(engine, "SELECT min(id) FROM cargas")
    with Session(engine) as session, session.begin():
        # La cartera exige cedula (CU-04): socios propios con cedulas ficticias.
        socios = SqlAlchemySocioRepository(session, Reloj()).insertar_en_bloque(
            [
                NuevoSocio(
                    cedula=f"{9300000000 + i:010d}",
                    nombre=f"Socio Sintetico Cartera {i:02d}",
                    nombre_normalizado=f"SOCIO SINTETICO CARTERA {i:02d}",
                )
                for i in range(12)
            ]
        )
        SqlAlchemyMembresiaRepository(session, Reloj()).insertar_en_bloque(
            [
                NuevaMembresia(
                    socio_id=socio_id,
                    carga_id=carga_id,
                    plan=Plan.MENSUAL,
                    forma_pago=FormaPago.EFECTIVO,
                    origen=OrigenMembresia.PLANTILLA,
                    inicio_aproximado=False,
                    fecha_actividad=date(2026, 9, 5) + timedelta(days=i),
                    fecha_inicio=date(2026, 9, 5) + timedelta(days=i),
                    fecha_vencimiento=date(2026, 10, 5) + timedelta(days=i),
                    monto_cobrado=Decimal("30.00"),
                )
                for i, socio_id in enumerate(socios)
            ]
        )


def _filas(engine: Engine, sql: str) -> list[tuple[object, ...]]:
    """Filas con SQL fijo de la prueba (sin parametros de usuario)."""
    with engine.connect() as conexion:
        return [tuple(fila) for fila in conexion.execute(text(sql))]


def _instantanea(engine: Engine) -> dict[str, list[tuple[object, ...]]]:
    return {
        "listas": _filas(engine, "SELECT * FROM listas_priorizadas ORDER BY id"),
        "predicciones": _filas(engine, "SELECT * FROM predicciones ORDER BY id"),
        "gestiones": _filas(engine, "SELECT * FROM gestiones_retencion ORDER BY id"),
    }


def _conteos(engine: Engine) -> dict[str, int]:
    tablas = (*TABLAS_PREVIAS, "modelos", "intentos_reentrenamiento", "membresias", "socios")
    return {t: contar(engine, f"SELECT count(*) FROM {t}") for t in tablas}  # noqa: S608 - lista blanca fija


def test_adoptar_modelo_pone_en_uso_v2_y_conserva_listas_predicciones_y_gestiones_de_v1(
    base: Engine,
    cliente: TestClient,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    _sembrar_con_cartera(base)
    lista_v1 = cliente.post(LISTAS, json=CUERPO_LISTA)
    assert lista_v1.status_code == 201, lista_v1.text
    assert lista_v1.json()["modelo_version"] == "v1"
    primer_item = lista_v1.json()["items"][0]
    gestion = cliente.post(
        "/api/v1/gestiones",
        json={"prediccion_id": primer_item["prediccion_id"], "campania_id": None},
    )
    assert gestion.status_code == 201, gestion.text
    antes = _instantanea(base)
    conteos_antes = _conteos(base)
    v1_id = contar(base, "SELECT id FROM modelos WHERE version = 1")
    assert {fila[0] for fila in _filas(base, "SELECT modelo_id FROM listas_priorizadas")} == {v1_id}

    codigo = main(["adoptar-modelo"], clock=Reloj())

    salida = capsys.readouterr()
    assert codigo == 0
    assert salida.out.strip() == "v2 en uso (Adopción del modelo M01)."
    textos = salida.out + salida.err + caplog.text
    assert "Socio Sintetico" not in textos
    assert "SOCIO SINTETICO" not in textos
    # Solo cambian modelos (+1) e intentos (+1); lo demas queda identico.
    assert _instantanea(base) == antes
    conteos_despues = _conteos(base)
    assert conteos_despues == {
        **conteos_antes,
        "modelos": conteos_antes["modelos"] + 1,
        "intentos_reentrenamiento": conteos_antes["intentos_reentrenamiento"] + 1,
    }
    assert contar(base, "SELECT version FROM modelos WHERE vigente") == 2
    assert contar(base, "SELECT count(*) FROM modelos WHERE version = 1 AND NOT vigente") == 1
    v2_id = contar(base, "SELECT id FROM modelos WHERE version = 2")
    intento = _filas(
        base,
        "SELECT disparador, resultado, motivo, modelo_id, fecha_programada "
        "FROM intentos_reentrenamiento ORDER BY id DESC LIMIT 1",
    )[0]
    assert intento == ("MANUAL", "ENTRENADO", "Adopción del modelo M01", v2_id, None)
    assert proxima_fecha(base) == PROGRAMADA
    # R-015 T11: etiqueta y entrena al corte de los datos (ultima carga por plantilla, el
    # 2026-09-01; el vigente tiene corte 2026-02-28), no a hoy (2026-09-30).
    corte_v2 = _filas(
        base, "SELECT metadata_tecnica->>'fecha_corte' FROM modelos WHERE version = 2"
    )
    assert corte_v2 == [("2026-09-01",)]

    # La lista de v1 sigue mostrando v1; una lista nueva usa v2.
    vieja = cliente.get(f"{LISTAS}/{lista_v1.json()['id']}")
    assert vieja.status_code == 200
    assert vieja.json()["modelo_version"] == "v1"
    nueva = cliente.post(LISTAS, json=CUERPO_LISTA)
    assert nueva.status_code == 201, nueva.text
    assert nueva.json()["modelo_version"] == "v2"
    ultima = _filas(base, "SELECT id, modelo_id FROM listas_priorizadas ORDER BY id DESC LIMIT 1")
    assert ultima == [(nueva.json()["id"], v2_id)]


def test_adoptar_modelo_dos_veces_crea_v3_vigente_y_conserva_v1_v2_y_lo_anterior(
    base: Engine, cliente: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    # R-015 T12: repetir el comando no es idempotente; crea la version siguiente (v3) y
    # conserva todas las anteriores sin tocar listas, predicciones ni gestiones previas.
    _sembrar_con_cartera(base)
    lista_v1 = cliente.post(LISTAS, json=CUERPO_LISTA)
    assert lista_v1.status_code == 201, lista_v1.text
    assert main(["adoptar-modelo"], clock=Reloj()) == 0
    lista_v2 = cliente.post(LISTAS, json=CUERPO_LISTA)
    assert lista_v2.status_code == 201, lista_v2.text
    antes = _instantanea(base)
    conteos_antes = _conteos(base)
    capsys.readouterr()

    codigo = main(["adoptar-modelo"], clock=Reloj())

    assert codigo == 0
    assert capsys.readouterr().out.strip() == "v3 en uso (Adopción del modelo M01)."
    assert _instantanea(base) == antes
    assert _conteos(base) == {
        **conteos_antes,
        "modelos": conteos_antes["modelos"] + 1,
        "intentos_reentrenamiento": conteos_antes["intentos_reentrenamiento"] + 1,
    }
    assert _filas(base, "SELECT version, vigente FROM modelos ORDER BY version") == [
        (1, False),
        (2, False),
        (3, True),
    ]
    assert proxima_fecha(base) == PROGRAMADA
    assert cliente.get(f"{LISTAS}/{lista_v1.json()['id']}").json()["modelo_version"] == "v1"
    assert cliente.get(f"{LISTAS}/{lista_v2.json()['id']}").json()["modelo_version"] == "v2"


def test_adoptar_modelo_lista_nueva_usa_cortes_fijos_070_y_050(
    base: Engine, cliente: TestClient
) -> None:
    # M01: niveles por cortes fijos (ALTO >= 0.70, MEDIO >= 0.50), no por percentiles.
    _sembrar_con_cartera(base)
    assert main(["adoptar-modelo"], clock=Reloj()) == 0

    nueva = cliente.post(LISTAS, json=CUERPO_LISTA)

    assert nueva.status_code == 201, nueva.text
    cuerpo = nueva.json()
    assert cuerpo["modelo_version"] == "v2"
    assert Decimal(cuerpo["umbral_alto"]) == Decimal("0.70")
    assert Decimal(cuerpo["umbral_medio"]) == Decimal("0.50")
    assert cuerpo["items"], "la cartera sintetica debe producir items"
    for item in cuerpo["items"]:
        score = Decimal(item["score"])
        esperado = (
            "ALTO" if score >= Decimal("0.70") else "MEDIO" if score >= Decimal("0.50") else "BAJO"
        )
        assert item["nivel_riesgo"] == esperado


def test_adoptar_modelo_si_el_entrenamiento_falla_sale_con_1_y_no_guarda_nada(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    _sembrar_con_cartera(base)
    conteos_antes = _conteos(base)

    codigo = main(["adoptar-modelo"], predictor=PredictorQueFalla(), clock=Reloj())

    salida = capsys.readouterr()
    assert codigo == 1
    assert "RuntimeError" in salida.out
    assert "fallo del entrenamiento" not in salida.out + salida.err
    assert _conteos(base) == conteos_antes
    assert contar(base, "SELECT version FROM modelos WHERE vigente") == 1


def test_adoptar_modelo_sistema_no_listo_sale_con_1(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    limpiar_base(base)

    codigo = main(["adoptar-modelo"], clock=Reloj())

    assert codigo == 1
    assert "El sistema aun no esta listo." in capsys.readouterr().out
    assert contar(base, "SELECT count(*) FROM modelos") == 0


def test_adoptar_modelo_con_el_bloqueo_tomado_sale_con_2(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    sembrar(base, programada=PROGRAMADA)

    with AbridorBloqueoReentrenamiento(base)() as bloqueo:
        assert bloqueo.intentar_adquirir() is True
        try:
            codigo = main(["adoptar-modelo"], clock=Reloj())
        finally:
            bloqueo.liberar()

    assert codigo == 2
    assert "Ya hay un reentrenamiento en curso." in capsys.readouterr().out
    assert contar(base, "SELECT count(*) FROM modelos") == 1
    assert contar(base, "SELECT count(*) FROM intentos_reentrenamiento") == 1
