"""Persistencia del reentrenamiento (CU-02, T9) contra PostgreSQL real.

Unidad de trabajo: el modelo nuevo, los intentos y la proxima fecha solo persisten con
``commit``. Bloqueo consultivo propio, independiente del de la migracion. Las membresias para
entrenar excluyen las borradas logicamente. Cada prueba limpia la base al empezar y al
terminar (solo ``*_test``).
"""

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, select, text, update
from sqlalchemy.orm import Session

from app.application.modelo.ports import (
    BloqueoReentrenamiento,
    LectorMembresiasEntrenamiento,
    NuevoIntento,
    NuevoModelo,
)
from app.domain.common.enums import DisparadorReentrenamiento, ResultadoReentrenamiento
from app.infrastructure.persistence.models.historial import Membresia
from app.infrastructure.persistence.models.modelo import IntentoReentrenamiento, Modelo
from app.infrastructure.persistence.repositories.modelo import (
    CLAVE_BLOQUEO_MIGRACION,
    CLAVE_BLOQUEO_REENTRENAMIENTO,
    PgBloqueoMigracion,
)
from app.infrastructure.persistence.unit_of_work_reentrenamiento import (
    AbridorBloqueoReentrenamiento,
    SqlAlchemyUnidadDeTrabajoReentrenamiento,
)
from tests.integration.reentrenamiento_datos import AHORA, Reloj, contar, limpiar_base, sembrar

pytestmark = pytest.mark.integration


@pytest.fixture
def base(migrated_engine: Engine) -> Iterator[Engine]:
    sembrar(migrated_engine, programada=date(2026, 9, 30))
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def _intento(resultado: ResultadoReentrenamiento, **campos: object) -> NuevoIntento:
    base = NuevoIntento(
        fecha=AHORA, disparador=DisparadorReentrenamiento.PROGRAMADO, resultado=resultado
    )
    return replace(base, **campos)  # type: ignore[arg-type]  # construccion generica del test


def _modelo_v2(vigente_metadata: dict[str, object], artefacto: bytes) -> NuevoModelo:
    return NuevoModelo(
        version=2,
        fecha_entrenamiento=AHORA,
        ciclos_entrenamiento=200,
        periodo_desde=date(2026, 2, 5),
        periodo_hasta=date(2026, 8, 24),
        prevalencia=Decimal("0.5"),
        umbral_alto=Decimal("0.7"),
        umbral_medio=Decimal("0.4"),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=artefacto,
        metadata_tecnica={**vigente_metadata, "fecha_corte": "2026-09-30"},
    )


def test_intentos_de_cada_resultado_se_guardan_y_cumplen_los_check(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoReentrenamiento(base, Reloj())

    with uow() as contexto:
        vigente = contexto.modelos.obtener_vigente()
        assert vigente is not None
        contexto.intentos.crear(
            _intento(
                ResultadoReentrenamiento.OMITIDO,
                fecha_programada=date(2026, 9, 27),
                motivo="La fecha programada paso.",
            )
        )
        contexto.intentos.crear(
            _intento(
                ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS,
                motivo="Hay 3 ciclos nuevos evaluables.",
                ciclos_nuevos=3,
            )
        )
        contexto.intentos.crear(
            _intento(
                ResultadoReentrenamiento.NO_SUPERA_VIGENTE,
                pr_auc_candidato=Decimal("0.41234567"),
                pr_auc_vigente=Decimal("0.51234567"),
            )
        )
        modelo_id = contexto.modelos.crear(
            _modelo_v2(dict(vigente.metadata_tecnica), vigente.artefacto)
        )
        contexto.intentos.crear(
            _intento(
                ResultadoReentrenamiento.ENTRENADO,
                disparador=DisparadorReentrenamiento.MANUAL,
                modelo_id=modelo_id,
                pr_auc_candidato=Decimal("0.9"),
                pr_auc_vigente=Decimal("0.5"),
            )
        )
        contexto.estado.fijar_proxima_fecha(date(2027, 3, 30))
        contexto.commit()

    with Session(base) as session:
        filas = session.scalars(
            select(IntentoReentrenamiento).order_by(IntentoReentrenamiento.id)
        ).all()
        por_resultado = {f.resultado: f for f in filas}
    assert por_resultado["OMITIDO"].fecha_programada == date(2026, 9, 27)
    assert por_resultado["CRITERIOS_NO_CUMPLIDOS"].motivo == "Hay 3 ciclos nuevos evaluables."
    no_supera = por_resultado["NO_SUPERA_VIGENTE"]
    assert (no_supera.pr_auc_candidato, no_supera.pr_auc_vigente) == (
        Decimal("0.41234567"),
        Decimal("0.51234567"),
    )
    entrenado = [f for f in filas if f.resultado == "ENTRENADO" and f.disparador == "MANUAL"]
    assert entrenado[0].modelo_id == modelo_id
    with uow() as contexto:
        assert contexto.estado.obtener().proxima_fecha_reentrenamiento == date(2027, 3, 30)


def test_guardar_v2_desmarca_v1_y_la_conserva(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoReentrenamiento(base, Reloj())

    with uow() as contexto:
        vigente = contexto.modelos.obtener_vigente()
        assert vigente is not None
        contexto.modelos.crear(_modelo_v2(dict(vigente.metadata_tecnica), b"v2"))
        contexto.commit()

    with Session(base) as session:
        modelos = session.execute(
            select(Modelo.version, Modelo.vigente).order_by(Modelo.version)
        ).all()
    assert [tuple(m) for m in modelos] == [(1, False), (2, True)]


def test_sin_commit_no_persiste_nada(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoReentrenamiento(base, Reloj())
    intentos_antes = contar(base, "SELECT count(*) FROM intentos_reentrenamiento")

    with uow() as contexto:
        vigente = contexto.modelos.obtener_vigente()
        assert vigente is not None
        contexto.modelos.crear(_modelo_v2(dict(vigente.metadata_tecnica), b"v2"))
        contexto.intentos.crear(_intento(ResultadoReentrenamiento.FALLIDO, motivo="x"))
        contexto.estado.fijar_proxima_fecha(date(2030, 1, 1))

    assert contar(base, "SELECT count(*) FROM modelos") == 1
    assert contar(base, "SELECT count(*) FROM intentos_reentrenamiento") == intentos_antes
    with uow() as contexto:
        assert contexto.estado.obtener().proxima_fecha_reentrenamiento == date(2026, 9, 30)


def test_bloqueo_de_reentrenamiento_segunda_sesion_no_lo_obtiene_y_migracion_sigue_libre(
    migrated_engine: Engine,
) -> None:
    abridor = AbridorBloqueoReentrenamiento(migrated_engine)
    assert CLAVE_BLOQUEO_REENTRENAMIENTO != CLAVE_BLOQUEO_MIGRACION

    with abridor() as primero, abridor() as segundo:
        assert isinstance(primero, BloqueoReentrenamiento)
        assert primero.intentar_adquirir() is True
        try:
            assert segundo.intentar_adquirir() is False
            with migrated_engine.connect() as conexion:
                migracion = PgBloqueoMigracion(
                    conexion.execution_options(isolation_level="AUTOCOMMIT")
                )
                assert migracion.intentar_adquirir() is True
                migracion.liberar()
        finally:
            primero.liberar()
        assert segundo.intentar_adquirir() is True
        segundo.liberar()


def test_listar_para_entrenamiento_excluye_borradas_y_trae_registrada_en(base: Engine) -> None:
    total = contar(base, "SELECT count(*) FROM membresias")
    with Session(base) as session, session.begin():
        borrada = session.scalars(select(Membresia.id).order_by(Membresia.id).limit(1)).one()
        session.execute(
            update(Membresia)
            .where(Membresia.id == borrada)
            .values(deleted_at=datetime(2026, 9, 2, tzinfo=UTC))
        )

    with SqlAlchemyUnidadDeTrabajoReentrenamiento(base, Reloj())() as contexto:
        assert isinstance(contexto.membresias, LectorMembresiasEntrenamiento)
        membresias = contexto.membresias.listar_para_entrenamiento()

    assert len(membresias) == total - 1
    assert borrada not in {m.membresia_id for m in membresias}
    assert [m.membresia_id for m in membresias] == sorted(m.membresia_id for m in membresias)
    assert {m.registrada_en for m in membresias} == {datetime(2026, 9, 1, 10, 0, tzinfo=UTC)}
    with base.connect() as conexion:
        assert conexion.execute(text("SELECT count(*) FROM socios")).scalar_one() == 200
