"""Datos sinteticos del reentrenamiento (CU-02) en ``app_db_test``: modelo v1 y membresias.

Escenario (hoy = 2026-09-30 en Ecuador):

- Modelo v1 vigente entrenado el 2026-03-01 con corte 2026-02-28 por ``RandomForestPredictor``
  con la senal **invertida** (aprende que los ``MENSUAL`` renuevan): sobre los datos nuevos
  puntua al reves, asi que un candidato bien entrenado no es peor y se entrena la v2.
- ``nuevas=True``: 200 socios con un ciclo cada uno vencido de febrero a agosto de 2026,
  registrados despues del entrenamiento de v1 -> 200 ciclos nuevos evaluables, 100 de cada
  clase. Los que no renuevan son ``MENSUAL``; los que renuevan son ``TRIMESTRAL`` con una
  membresia ``ANUAL`` 5 dias despues del vencimiento. Uno de cada tres socios tiene ademas
  un ciclo ``MENSUAL`` de 2025 (historial previo, no es un ciclo nuevo).
- ``nuevas=False``: solo 10 membresias de 2025 registradas antes de v1 (ningun ciclo nuevo).

Datos 100 % ficticios: "Socio Sintetico N", sin cedula, celular ni correo.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.application.modelo.ports import NuevoIntento, NuevoModelo
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    FormaPago,
    OrigenMembresia,
    Plan,
    ResultadoReentrenamiento,
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
    SqlAlchemyIntentoRepository,
    SqlAlchemyModeloRepository,
)
from tests.integration.sistema.migracion_sintetica import limpiar_base

BACKEND_DIR = Path(__file__).resolve().parents[2]
HOY = date(2026, 9, 30)
AHORA = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
ENTRENAMIENTO_V1 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
ANTES_DE_V1 = datetime(2026, 2, 28, 10, 0, tzinfo=UTC)
REGISTRO_NUEVAS = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
NO_RENUEVAN = 100
RENUEVAN = 100

__all__ = ["AHORA", "BACKEND_DIR", "HOY", "Reloj", "limpiar_base", "sembrar"]


class Reloj:
    """Reloj fijo configurable."""

    def __init__(self, instante: datetime = AHORA) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


def _filas_invertidas() -> tuple[list[FeatureRow], list[int]]:
    """Filas en las que los ``MENSUAL`` renuevan (0) y los ``TRIMESTRAL`` no (1)."""
    filas: list[FeatureRow] = []
    etiquetas: list[int] = []
    for i in range(80):
        mensual = i % 2 == 0
        filas.append(
            {
                "ciclos_previos": 0,
                "antiguedad_dias": 0,
                "duracion_modelo": 30 if mensual else 90,
                "monto_actual": Decimal("30.00"),
                "monto_historico": Decimal(0),
                "dias_desde_ultima_membresia": None if i % 4 == 0 else 30 + i % 7,
                "plan": (Plan.MENSUAL if mensual else Plan.TRIMESTRAL).value,
                "forma_pago": FormaPago.EFECTIVO.value,
                "mes_vencimiento": f"2025-{1 + i % 12:02d}",
                "inicio_aproximado": "False",
            }
        )
        etiquetas.append(0 if mensual else 1)
    return filas, etiquetas


def _modelo_v1() -> NuevoModelo:
    filas, etiquetas = _filas_invertidas()
    entrenado = RandomForestPredictor().train(
        filas, etiquetas, VARIABLES_NUMERICAS, VARIABLES_CATEGORICAS
    )
    return NuevoModelo(
        version=1,
        fecha_entrenamiento=ENTRENAMIENTO_V1,
        ciclos_entrenamiento=len(filas),
        periodo_desde=date(2025, 1, 1),
        periodo_hasta=date(2025, 12, 31),
        prevalencia=Decimal("0.5"),
        umbral_alto=Decimal("0.60000000"),
        umbral_medio=Decimal("0.40000000"),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=entrenado.artefacto,
        metadata_tecnica={
            **entrenado.metadata_tecnica,
            "fecha_corte": "2026-02-28",
            "medianas_monto": {"por_plan": {"MENSUAL": "30.00"}, "general": "30.00"},
        },
    )


def _membresia(
    socio_id: int, carga_id: int, plan: Plan, inicio: date, vence: date
) -> NuevaMembresia:
    return NuevaMembresia(
        socio_id=socio_id,
        carga_id=carga_id,
        plan=plan,
        forma_pago=FormaPago.EFECTIVO,
        origen=OrigenMembresia.PLANTILLA,
        inicio_aproximado=False,
        fecha_actividad=inicio,
        fecha_inicio=inicio,
        fecha_vencimiento=vence,
        monto_cobrado=Decimal("30.00"),
    )


def _membresias_nuevas(socio_ids: list[int], carga_id: int) -> list[NuevaMembresia]:
    resultado: list[NuevaMembresia] = []
    for i, socio_id in enumerate(socio_ids):
        if i % 3 == 0:  # historial previo de 2025 (ciclo antiguo, no nuevo)
            previo = date(2025, 6, 1 + i % 20)
            resultado.append(
                _membresia(socio_id, carga_id, Plan.MENSUAL, previo, previo + timedelta(days=30))
            )
        vence = date(2026, 2 + i % 7, 5 + i % 20)
        if i < NO_RENUEVAN:
            resultado.append(
                _membresia(socio_id, carga_id, Plan.MENSUAL, vence - timedelta(days=30), vence)
            )
        else:
            resultado.append(
                _membresia(socio_id, carga_id, Plan.TRIMESTRAL, vence - timedelta(days=90), vence)
            )
            renovacion = vence + timedelta(days=5)
            resultado.append(
                _membresia(
                    socio_id, carga_id, Plan.ANUAL, renovacion, renovacion + timedelta(days=365)
                )
            )
    return resultado


def _membresias_antiguas(socio_ids: list[int], carga_id: int) -> list[NuevaMembresia]:
    return [
        _membresia(socio_id, carga_id, Plan.MENSUAL, date(2025, 3, 1), date(2025, 3, 31))
        for socio_id in socio_ids
    ]


def sembrar(engine: Engine, *, programada: date | None, nuevas: bool = True) -> None:
    """Limpia la base ``*_test`` y siembra v1, sus membresias y el estado ``COMPLETADA``."""
    limpiar_base(engine)
    socios = NO_RENUEVAN + RENUEVAN if nuevas else 10
    registro = Reloj(REGISTRO_NUEVAS if nuevas else ANTES_DE_V1)
    with Session(engine) as session, session.begin():
        carga_id = SqlAlchemyCargaRepository(session, registro).crear(
            NuevaCarga(
                tipo=TipoCarga.PLANTILLA,
                fecha_carga=registro.instante,
                nombre_archivo="plantilla sintetica.xlsx",
                filas_leidas=socios,
                filas_guardadas=socios,
                filas_duplicadas=0,
                socios_enlazados=socios,
            )
        )
        socio_ids = SqlAlchemySocioRepository(session, registro).insertar_en_bloque(
            [
                NuevoSocio(
                    cedula=None,
                    nombre=f"Socio Sintetico {i:03d}",
                    nombre_normalizado=f"SOCIO SINTETICO {i:03d}",
                )
                for i in range(socios)
            ]
        )
        membresias = (
            _membresias_nuevas(socio_ids, carga_id)
            if nuevas
            else _membresias_antiguas(socio_ids, carga_id)
        )
        SqlAlchemyMembresiaRepository(session, registro).insertar_en_bloque(membresias)

        reloj_v1 = Reloj(ENTRENAMIENTO_V1)
        modelo_id = SqlAlchemyModeloRepository(session, reloj_v1).crear(_modelo_v1())
        SqlAlchemyIntentoRepository(session, reloj_v1).crear(
            NuevoIntento(
                fecha=ENTRENAMIENTO_V1,
                disparador=DisparadorReentrenamiento.INICIAL,
                resultado=ResultadoReentrenamiento.ENTRENADO,
                modelo_id=modelo_id,
            )
        )
        estado = SqlAlchemyEstadoSistemaRepository(session, reloj_v1)
        estado.fijar_migracion(EstadoMigracion.COMPLETADA)
        if programada is not None:
            estado.fijar_proxima_fecha(programada)


def contar(engine: Engine, sql: str) -> int:
    """Conteo con SQL fijo de la prueba (sin parametros de usuario)."""
    with engine.connect() as conexion:
        return int(conexion.execute(text(sql)).scalar_one())


def proxima_fecha(engine: Engine) -> date | None:
    with engine.connect() as conexion:
        valor: date | None = conexion.execute(
            text("SELECT proxima_fecha_reentrenamiento FROM estado_sistema WHERE id = 1")
        ).scalar_one()
        return valor
