"""Ayudas para migrar los libros sinteticos contra el PostgreSQL de pruebas.

Reutilizables por otras pruebas de integracion (p. ej. las de la API de listas, que parten de
una base migrada). ``limpiar_base`` solo actua sobre una base cuyo nombre termina en
``_test``; cualquier otra base aborta la prueba.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import Engine, text

from app.application.sistema.migrar_historico import MigrarHistorico
from app.application.sistema.ports import RegistroMigracion, ResultadoMigracion
from app.domain.common.predictor import PredictorModel
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.persistence.unit_of_work import (
    AbridorBloqueoMigracion,
    FabricaUnidadDeTrabajoSqlAlchemy,
)

CARPETA_LIBROS = Path(__file__).resolve().parents[2] / "fixtures" / "historico"
INSTANTE = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
TABLAS_DE_DATOS = (
    "predicciones",
    "listas_priorizadas",
    "gestiones_retencion",
    "membresias",
    "socios",
    "cargas",
    "intentos_reentrenamiento",
    "modelos",
)


class RelojFijo:
    def now(self) -> datetime:
        return INSTANTE


def limpiar_base(engine: Engine) -> None:
    """Vacia las tablas de datos y deja ``estado_sistema`` en ``PENDIENTE`` (solo ``*_test``)."""
    nombre = engine.url.database or ""
    if not nombre.endswith("_test"):
        pytest.fail("limpiar_base solo puede ejecutarse contra una base *_test", pytrace=False)
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {', '.join(TABLAS_DE_DATOS)} RESTART IDENTITY CASCADE"))
        conexion.execute(
            text(
                "UPDATE estado_sistema SET migracion_historica = 'PENDIENTE', "
                "proxima_fecha_reentrenamiento = NULL WHERE id = 1"
            )
        )


def crear_migracion(
    engine: Engine,
    *,
    predictor: PredictorModel | None = None,
    registro: RegistroMigracion | None = None,
    carpeta: Path = CARPETA_LIBROS,
) -> MigrarHistorico:
    """``MigrarHistorico`` con la infraestructura real y los libros sinteticos."""
    reloj = RelojFijo()
    return MigrarHistorico(
        abrir_bloqueo=AbridorBloqueoMigracion(engine),
        unidad_de_trabajo=FabricaUnidadDeTrabajoSqlAlchemy(engine, reloj),
        localizador=LocalizadorLibrosCarpeta(carpeta),
        lector=LectorLibrosExcel(),
        predictor=predictor if predictor is not None else RandomForestPredictor(),
        clock=reloj,
        registro=registro if registro is not None else RegistroMigracion(),
    )


def migrar_sintetico(engine: Engine) -> ResultadoMigracion:
    """Migra los libros sinteticos con el ``RandomForestPredictor`` real."""
    return crear_migracion(engine).ejecutar()
