"""Datos sinteticos confirmados en ``app_db_test`` para las pruebas de API de listas.

Sustituye a la migracion sintetica de T12 (en curso por otro developer): siembra una carga,
30 socios con historial, un modelo v1 real (``RandomForestPredictor`` entrenado con filas
sinteticas) y el estado ``COMPLETADA``. Cada prueba trunca las tablas al empezar y al
terminar (la base se llama ``*_test``, lo garantiza ``test_database_url``).
Datos 100 % sinteticos: ningun nombre, celular ni correo real.

``fijar_reloj_api`` sobrescribe ``get_clock`` con un reloj fijo el 2026-08-31 (tambien en
Ecuador), para que esa fecha de referencia sea "hoy" y no una fecha pasada (R-005).
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_clock
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.application.modelo.ports import NuevoModelo
from app.domain.common.enums import (
    EstadoMigracion,
    FormaPago,
    OrigenMembresia,
    Plan,
    TipoCarga,
)
from app.domain.common.predictor import FeatureRow
from app.domain.modelo.variables import VARIABLES_CATEGORICAS, VARIABLES_NUMERICAS
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyCargaRepository,
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from app.infrastructure.persistence.repositories.modelo import (
    SqlAlchemyEstadoSistemaRepository,
    SqlAlchemyModeloRepository,
)

INSTANTE = datetime(2026, 8, 30, 15, 0, tzinfo=UTC)
FECHA = date(2026, 8, 31)
SOCIOS = 30
# socio 0 ya renovo y el ciclo en el horizonte del socio 1 es DIARIO -> 28 filas.
FILAS_ESPERADAS = SOCIOS - 2
_TABLAS = (
    "predicciones, listas_priorizadas, gestiones_retencion, membresias, socios, cargas, "
    "intentos_reentrenamiento, modelos"
)


RELOJ_API = datetime(2026, 8, 31, 15, 0, tzinfo=UTC)


class RelojFijo:
    def now(self) -> datetime:
        return INSTANTE


class RelojApi:
    """Reloj de la API en las pruebas: 2026-08-31 a las 10:00 en Ecuador."""

    def now(self) -> datetime:
        return RELOJ_API


def fijar_reloj_api(app: FastAPI) -> None:
    """Sobrescribe ``get_clock``; quitar otros overrides con ``pop``, no con ``clear``."""
    app.dependency_overrides[get_clock] = RelojApi


def limpiar(engine: Engine) -> None:
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {_TABLAS} RESTART IDENTITY CASCADE"))
        conexion.execute(
            text("UPDATE estado_sistema SET migracion_historica = :e"),
            {"e": EstadoMigracion.PENDIENTE.value},
        )


def _filas_entrenamiento() -> tuple[list[FeatureRow], list[int]]:
    filas: list[FeatureRow] = []
    etiquetas: list[int] = []
    for i in range(80):
        no_renueva = i % 3 == 0
        filas.append(
            {
                "ciclos_previos": 0 if no_renueva else 1 + i % 4,
                "antiguedad_dias": 5 * i,
                "duracion_modelo": 30,
                "monto_actual": Decimal(30 + i % 20),
                "monto_historico": Decimal(0 if no_renueva else 40 * (i % 5)),
                "dias_desde_ultima_membresia": None if no_renueva else 30,
                "plan": Plan.MENSUAL.value,
                "forma_pago": (FormaPago.EFECTIVO if i % 2 else FormaPago.TRANSFERENCIA).value,
                "mes_vencimiento": f"2026-{1 + i % 7:02d}",
                "inicio_aproximado": "False",
            }
        )
        etiquetas.append(int(no_renueva))
    return filas, etiquetas


def nuevo_modelo(version: int, alto: str = "0.60000000", medio: str = "0.40000000") -> NuevoModelo:
    filas, etiquetas = _filas_entrenamiento()
    entrenado = RandomForestPredictor().train(
        filas, etiquetas, VARIABLES_NUMERICAS, VARIABLES_CATEGORICAS
    )
    return NuevoModelo(
        version=version,
        fecha_entrenamiento=INSTANTE,
        ciclos_entrenamiento=len(filas),
        periodo_desde=date(2026, 1, 1),
        periodo_hasta=date(2026, 7, 31),
        prevalencia=Decimal(sum(etiquetas)) / len(etiquetas),
        umbral_alto=Decimal(alto),
        umbral_medio=Decimal(medio),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=entrenado.artefacto,
        metadata_tecnica={
            **entrenado.metadata_tecnica,
            "medianas_monto": {"por_plan": {"MENSUAL": "40.00"}, "general": "40.00"},
        },
    )


def sembrar(engine: Engine) -> None:
    reloj = RelojFijo()
    with Session(engine) as session, session.begin():
        carga_id = SqlAlchemyCargaRepository(session, reloj).crear(
            NuevaCarga(
                tipo=TipoCarga.MIGRACION_HISTORICA,
                fecha_carga=INSTANTE,
                nombre_archivo="Control Gym 2026 sintetico.xlsx",
                filas_leidas=2 * SOCIOS + 1,
                filas_guardadas=2 * SOCIOS + 1,
                filas_duplicadas=0,
                socios_enlazados=SOCIOS,
            )
        )
        socio_ids = SqlAlchemySocioRepository(session, reloj).insertar_en_bloque(
            [
                NuevoSocio(
                    cedula=f"{9200000000 + i:010d}",
                    nombre=f"Socio Sintetico {i:02d}",
                    nombre_normalizado=f"SOCIO SINTETICO {i:02d}",
                    celular=f"09{i:08d}",
                    correo=f"socio{i:02d}@ejemplo.test",
                )
                for i in range(SOCIOS)
            ]
        )
        membresias: list[NuevaMembresia] = []

        def agregar(i: int, inicio: date, vence: date, plan: Plan = Plan.MENSUAL) -> None:
            membresias.append(
                NuevaMembresia(
                    socio_id=socio_ids[i],
                    carga_id=carga_id,
                    plan=plan,
                    forma_pago=FormaPago.EFECTIVO if i % 2 else FormaPago.TRANSFERENCIA,
                    origen=OrigenMembresia.HISTORICO,
                    inicio_aproximado=False,
                    fecha_actividad=inicio,
                    fecha_inicio=inicio,
                    fecha_vencimiento=vence,
                    monto_cobrado=None if i == 5 else Decimal(30 + i),
                )
            )

        for i in range(SOCIOS):
            anterior = date(2026, 6, 1) + timedelta(days=i % 25)
            agregar(i, anterior, anterior + timedelta(days=30))  # historial
            if i == 1:
                agregar(i, date(2026, 9, 4), date(2026, 9, 5), Plan.DIARIO)
                continue
            inicio = date(2026, 8, 2) + timedelta(days=i % 25)
            agregar(i, inicio, inicio + timedelta(days=30))  # vence 09-01..09-25
        agregar(0, date(2026, 8, 28), date(2026, 11, 28), Plan.TRIMESTRAL)  # ya renovo
        SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(membresias)
        SqlAlchemyModeloRepository(session, reloj).crear(nuevo_modelo(1))
        SqlAlchemyEstadoSistemaRepository(session, reloj).fijar_migracion(
            EstadoMigracion.COMPLETADA
        )


def crear_modelo_vigente(engine: Engine, version: int) -> None:
    reloj = RelojFijo()
    with Session(engine) as session, session.begin():
        SqlAlchemyModeloRepository(session, reloj).crear(
            nuevo_modelo(version, alto="0.01000000", medio="0.00500000")
        )


@pytest.fixture
def base_limpia(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar(migrated_engine)


@pytest.fixture
def base_migrada(base_limpia: Engine) -> Engine:
    sembrar(base_limpia)
    return base_limpia
