"""MigrarHistorico real: PostgreSQL de pruebas + libros sinteticos + RandomForestPredictor.

Cubre CU-03: migracion completa y atomica, fallo forzado del entrenamiento (rollback total),
dos migraciones simultaneas y segunda ejecucion sin cambios. Cada prueba parte de una base
vacia y la deja vacia (``limpiar_base`` solo actua sobre ``*_test``).

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso restringido por IP, CU-00).
"""

import threading
from collections.abc import Iterator, Sequence

import pytest
from sqlalchemy import Engine, text

from app.application.sistema.ports import ResultadoMigracion
from app.domain.common.predictor import FeatureRow, TrainedModel
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.persistence.repositories.modelo import PgBloqueoMigracion
from tests.fixtures import esperado
from tests.integration.sistema.migracion_sintetica import (
    CARPETA_LIBROS,
    crear_migracion,
    limpiar_base,
    migrar_sintetico,
)

pytestmark = pytest.mark.integration

TABLAS_CONTADAS = ("socios", "membresias", "cargas", "modelos", "intentos_reentrenamiento")


@pytest.fixture
def base_limpia(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar_base(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def conteos(engine: Engine) -> dict[str, int]:
    with engine.connect() as conexion:
        return {
            tabla: conexion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()  # noqa: S608 - nombre de tabla constante
            for tabla in TABLAS_CONTADAS
        }


def estado_migracion(engine: Engine) -> str:
    with engine.connect() as conexion:
        valor: str = conexion.execute(
            text("SELECT migracion_historica FROM estado_sistema WHERE id = 1")
        ).scalar_one()
        return valor


class PredictorQueFalla(RandomForestPredictor):
    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        raise RuntimeError("fallo forzado del entrenamiento")


class PredictorQueEspera(RandomForestPredictor):
    """Retiene el entrenamiento hasta que ``soltar`` se activa (o vence el plazo)."""

    def __init__(self, soltar: threading.Event) -> None:
        super().__init__()
        self._soltar = soltar

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        self._soltar.wait(timeout=30)
        return super().train(features, labels, numericas, categoricas, referencia)


def test_localizador_encuentra_los_libros_sinteticos_en_orden() -> None:
    rutas = LocalizadorLibrosCarpeta(CARPETA_LIBROS).rutas()

    assert [r.name for r in rutas] == [esperado.LIBRO_2025, esperado.LIBRO_2026]


def test_migrar_arranque_en_limpio_completa_con_los_conteos_esperados(
    base_limpia: Engine,
) -> None:
    resultado = migrar_sintetico(base_limpia)

    assert resultado is ResultadoMigracion.COMPLETADA
    assert estado_migracion(base_limpia) == "COMPLETADA"
    assert conteos(base_limpia) == {
        "socios": esperado.SOCIOS_DISTINTOS,
        "membresias": esperado.CON_IDENTIDAD,
        "cargas": 1,
        "modelos": 1,
        "intentos_reentrenamiento": 1,
    }
    with base_limpia.connect() as conexion:
        sin_actividad = conexion.execute(
            text("SELECT count(*) FROM membresias WHERE fecha_actividad IS NULL")
        ).scalar_one()
        modelo = conexion.execute(
            text(
                "SELECT version, vigente, length(artefacto) AS bytes, ciclos_entrenamiento, "
                "prevalencia FROM modelos"
            )
        ).one()
        intento = conexion.execute(
            text("SELECT disparador, resultado, modelo_id FROM intentos_reentrenamiento")
        ).one()
        proxima = conexion.execute(
            text("SELECT proxima_fecha_reentrenamiento FROM estado_sistema WHERE id = 1")
        ).scalar_one()
        carga = conexion.execute(
            text("SELECT tipo, filas_leidas, filas_guardadas, filas_duplicadas FROM cargas")
        ).one()
        origenes = conexion.execute(
            text("SELECT DISTINCT origen FROM membresias WHERE referencia_origen IS NOT NULL")
        ).scalars()
        assert list(origenes) == ["HISTORICO"]
    assert sin_actividad == 0
    assert modelo.version == 1
    assert modelo.vigente is True
    assert modelo.bytes > 0
    assert modelo.ciclos_entrenamiento == esperado.EVALUABLES
    assert modelo.prevalencia == esperado.PREVALENCIA
    assert (intento.disparador, intento.resultado) == ("INICIAL", "ENTRENADO")
    assert intento.modelo_id is not None
    assert proxima is not None
    assert tuple(carga) == ("MIGRACION_HISTORICA", esperado.FILAS_LEIDAS, 23, 0)


def test_migrar_fallo_forzado_revierte_todo_y_libera_el_bloqueo(base_limpia: Engine) -> None:
    resultado = crear_migracion(base_limpia, predictor=PredictorQueFalla()).ejecutar()

    assert resultado is ResultadoMigracion.FALLIDA
    assert conteos(base_limpia) == dict.fromkeys(TABLAS_CONTADAS, 0)
    assert estado_migracion(base_limpia) == "PENDIENTE"
    # Tras el fallo, otra conexion obtiene el bloqueo: se libero en el finally.
    with base_limpia.connect() as conexion:
        bloqueo = PgBloqueoMigracion(conexion.execution_options(isolation_level="AUTOCOMMIT"))
        try:
            assert bloqueo.intentar_adquirir() is True
        finally:
            bloqueo.liberar()


def test_migrar_dos_a_la_vez_solo_una_migra(base_limpia: Engine) -> None:
    soltar = threading.Event()
    salida = threading.Barrier(2)
    resultados: list[ResultadoMigracion] = []
    candado = threading.Lock()

    def correr() -> None:
        migracion = crear_migracion(base_limpia, predictor=PredictorQueEspera(soltar))
        salida.wait(timeout=10)
        try:
            resultado = migracion.ejecutar()
        finally:
            soltar.set()  # el que pierde el bloqueo suelta al que lo tiene
        with candado:
            resultados.append(resultado)

    hilos = [threading.Thread(target=correr) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)

    assert sorted(resultados) == sorted(
        [ResultadoMigracion.COMPLETADA, ResultadoMigracion.EN_OTRO_PROCESO]
    )
    assert conteos(base_limpia)["cargas"] == 1
    assert conteos(base_limpia)["modelos"] == 1


def test_migrar_segunda_ejecucion_no_cambia_ningun_conteo(base_limpia: Engine) -> None:
    assert migrar_sintetico(base_limpia) is ResultadoMigracion.COMPLETADA
    antes = conteos(base_limpia)

    resultado = migrar_sintetico(base_limpia)

    assert resultado is ResultadoMigracion.YA_MIGRADA
    assert conteos(base_limpia) == antes
    assert estado_migracion(base_limpia) == "COMPLETADA"
