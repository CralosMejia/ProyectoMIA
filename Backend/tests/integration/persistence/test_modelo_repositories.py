"""Repositorios del modelo predictivo y bloqueo consultivo contra PostgreSQL real.

Los repositorios escriben dentro de la transaccion de quien llama (unit of work) y nunca la
confirman ni la revierten. Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso
restringido por IP, CU-00), por eso no hay pruebas de filtro por propietario.
Cada prueba deja la base como la encontro (rollback, o restauracion explicita).
"""

import inspect
import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.application.modelo.ports import (
    BloqueoMigracion,
    EstadoSistema,
    EstadoSistemaRepository,
    IntentoRepository,
    ModeloRepository,
    NuevoIntento,
    NuevoModelo,
)
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)
from app.infrastructure.persistence.models.modelo import IntentoReentrenamiento, Modelo
from app.infrastructure.persistence.repositories import modelo as modulo_repositorios
from app.infrastructure.persistence.repositories.modelo import (
    PgBloqueoMigracion,
    SqlAlchemyEstadoSistemaRepository,
    SqlAlchemyIntentoRepository,
    SqlAlchemyModeloRepository,
)

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
UN_MEGABYTE = bytes(range(256)) * 4096


class RelojFijo:
    def now(self) -> datetime:
        return INSTANTE


def nuevo_modelo(version: int = 1, **cambios: object) -> NuevoModelo:
    base = NuevoModelo(
        version=version,
        fecha_entrenamiento=INSTANTE,
        ciclos_entrenamiento=4321,
        periodo_desde=date(2023, 1, 1),
        periodo_hasta=date(2026, 8, 31),
        prevalencia=Decimal("0.35123456"),
        umbral_alto=Decimal("0.71234567"),
        umbral_medio=Decimal("0.40000001"),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=UN_MEGABYTE,
        metadata_tecnica={"sklearn": "1.5.2", "parametros": {"n_estimators": 300}},
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # construccion generica del test


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def modelos(db_session: Session, reloj: RelojFijo) -> SqlAlchemyModeloRepository:
    return SqlAlchemyModeloRepository(db_session, reloj)


def test_repositories_implement_the_ports(
    db_session: Session, reloj: RelojFijo, migrated_engine: Engine
) -> None:
    assert isinstance(SqlAlchemyModeloRepository(db_session, reloj), ModeloRepository)
    assert isinstance(SqlAlchemyIntentoRepository(db_session, reloj), IntentoRepository)
    assert isinstance(SqlAlchemyEstadoSistemaRepository(db_session, reloj), EstadoSistemaRepository)
    with migrated_engine.connect() as conexion:
        assert isinstance(PgBloqueoMigracion(conexion), BloqueoMigracion)


# ------------------------------------------------------------------ modelos
def test_obtener_vigente_without_models_returns_none(
    modelos: SqlAlchemyModeloRepository,
) -> None:
    assert modelos.obtener_vigente() is None


def test_crear_modelo_round_trips_bytes_json_and_decimals(
    db_session: Session, modelos: SqlAlchemyModeloRepository
) -> None:
    modelo_id = modelos.crear(nuevo_modelo())

    vigente = modelos.obtener_vigente()
    assert vigente is not None
    assert vigente.id == modelo_id
    assert vigente.version == 1
    assert vigente.artefacto == UN_MEGABYTE
    assert len(vigente.artefacto) == 1024 * 1024
    assert vigente.metadata_tecnica == {
        "sklearn": "1.5.2",
        "parametros": {"n_estimators": 300},
    }
    assert vigente.porcentajes_umbral == {"ALTO": 20, "MEDIO": 30, "BAJO": 50}
    for campo, esperado in (
        ("prevalencia", Decimal("0.35123456")),
        ("umbral_alto", Decimal("0.71234567")),
        ("umbral_medio", Decimal("0.40000001")),
    ):
        valor = getattr(vigente, campo)
        assert isinstance(valor, Decimal)
        assert valor == esperado
    assert vigente.fecha_entrenamiento == INSTANTE
    assert vigente.ciclos_entrenamiento == 4321

    tipos = db_session.execute(
        text(
            "SELECT pg_typeof(artefacto)::text, jsonb_typeof(metadata_tecnica), "
            "jsonb_typeof(porcentajes_umbral), created_at, updated_at FROM modelos WHERE id = :id"
        ),
        {"id": modelo_id},
    ).one()
    assert tuple(tipos) == ("bytea", "object", "object", INSTANTE, INSTANTE)


def test_crear_second_model_unmarks_previous_and_keeps_it(
    db_session: Session, modelos: SqlAlchemyModeloRepository
) -> None:
    v1 = modelos.crear(nuevo_modelo(version=1))
    v2 = modelos.crear(nuevo_modelo(version=2, artefacto=b"v2"))

    vigente = modelos.obtener_vigente()
    assert vigente is not None
    assert (vigente.id, vigente.version, vigente.artefacto) == (v2, 2, b"v2")
    filas = db_session.execute(select(Modelo.id, Modelo.vigente).order_by(Modelo.id)).all()
    assert [tuple(f) for f in filas] == [(v1, False), (v2, True)]


def test_direct_insert_of_second_current_model_is_rejected(
    db_session: Session, modelos: SqlAlchemyModeloRepository
) -> None:
    modelos.crear(nuevo_modelo(version=1))

    with pytest.raises(IntegrityError, match="ux_modelos_vigente"):
        db_session.execute(
            text(
                "INSERT INTO modelos (version, vigente, fecha_entrenamiento, "
                "ciclos_entrenamiento, periodo_desde, periodo_hasta, prevalencia, umbral_alto, "
                "umbral_medio, porcentajes_umbral, artefacto, metadata_tecnica, created_at, "
                "updated_at) VALUES (2, true, :t, 1, :d, :d, 0.3, 0.7, 0.4, '{}', :a, '{}', "
                ":t, :t)"
            ),
            {"t": INSTANTE, "d": date(2026, 1, 1), "a": b"\x00"},
        )


def test_crear_duplicate_version_is_rejected(modelos: SqlAlchemyModeloRepository) -> None:
    modelos.crear(nuevo_modelo(version=1))

    with pytest.raises(IntegrityError, match="version"):
        modelos.crear(nuevo_modelo(version=1))


# ------------------------------------------------------------------ intentos
def test_crear_intento_persists_fields_and_link_to_model(
    db_session: Session, reloj: RelojFijo, modelos: SqlAlchemyModeloRepository
) -> None:
    modelo_id = modelos.crear(nuevo_modelo())
    intento_id = SqlAlchemyIntentoRepository(db_session, reloj).crear(
        NuevoIntento(
            fecha=INSTANTE,
            disparador=DisparadorReentrenamiento.INICIAL,
            resultado=ResultadoReentrenamiento.ENTRENADO,
            fecha_programada=date(2026, 9, 1),
            ciclos_nuevos=4321,
            pr_auc_candidato=Decimal("0.61234567"),
            modelo_id=modelo_id,
        )
    )

    guardado = db_session.get_one(IntentoReentrenamiento, intento_id)
    assert guardado.disparador == "INICIAL"
    assert guardado.resultado == "ENTRENADO"
    assert guardado.modelo_id == modelo_id
    assert guardado.pr_auc_candidato == Decimal("0.61234567")
    assert guardado.pr_auc_vigente is None
    assert guardado.created_at == INSTANTE


def test_crear_concurrent_sessions_never_leave_two_current_models(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    # Concurrencia: dos transacciones crean un modelo a la vez sobre el mismo vigente. La
    # segunda espera el bloqueo de fila del vigente (aqui con lock_timeout) o choca con el
    # indice unico parcial; nunca quedan dos vigentes.
    try:
        with migrated_engine.begin() as conexion:
            SqlAlchemyModeloRepository(Session(bind=conexion), reloj).crear(
                nuevo_modelo(version=9101, artefacto=b"\x01")
            )
        with Session(migrated_engine) as primera, Session(migrated_engine) as segunda:
            SqlAlchemyModeloRepository(primera, reloj).crear(
                nuevo_modelo(version=9102, artefacto=b"\x02")
            )
            segunda.execute(text("SET LOCAL lock_timeout = '500ms'"))
            with pytest.raises(DBAPIError):
                SqlAlchemyModeloRepository(segunda, reloj).crear(
                    nuevo_modelo(version=9103, artefacto=b"\x03")
                )
            segunda.rollback()
            primera.commit()

        with migrated_engine.connect() as conexion:
            vigentes = (
                conexion.execute(
                    text("SELECT version FROM modelos WHERE vigente AND version >= 9101")
                )
                .scalars()
                .all()
            )
            versiones = (
                conexion.execute(
                    text("SELECT version FROM modelos WHERE version >= 9101 ORDER BY version")
                )
                .scalars()
                .all()
            )
        assert vigentes == [9102]
        assert versiones == [9101, 9102]
    finally:
        with migrated_engine.begin() as conexion:
            conexion.execute(text("DELETE FROM modelos WHERE version IN (9101, 9102, 9103)"))


# ------------------------------------------------------------------ estado_sistema
def test_obtener_estado_returns_initial_pending_row(db_session: Session, reloj: RelojFijo) -> None:
    estado = SqlAlchemyEstadoSistemaRepository(db_session, reloj).obtener()

    assert estado == EstadoSistema(EstadoMigracion.PENDIENTE, None)


def test_fijar_estado_is_visible_after_caller_commit(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    try:
        with Session(migrated_engine) as session:
            repo = SqlAlchemyEstadoSistemaRepository(session, reloj)
            repo.fijar_migracion(EstadoMigracion.EN_CURSO)
            repo.fijar_proxima_fecha(date(2027, 2, 28))

            with Session(migrated_engine) as otra:
                antes = SqlAlchemyEstadoSistemaRepository(otra, reloj).obtener()
            assert antes == EstadoSistema(EstadoMigracion.PENDIENTE, None)

            session.commit()

        with Session(migrated_engine) as otra:
            despues = SqlAlchemyEstadoSistemaRepository(otra, reloj).obtener()
            updated_at = otra.execute(
                text("SELECT updated_at FROM estado_sistema WHERE id = 1")
            ).scalar_one()
        assert despues == EstadoSistema(EstadoMigracion.EN_CURSO, date(2027, 2, 28))
        assert updated_at == INSTANTE
    finally:
        with migrated_engine.begin() as conexion:
            conexion.execute(
                text(
                    "UPDATE estado_sistema SET migracion_historica = 'PENDIENTE', "
                    "proxima_fecha_reentrenamiento = NULL WHERE id = 1"
                )
            )


# ------------------------------------------------------------------ bloqueo consultivo
@pytest.fixture
def dos_conexiones(migrated_engine: Engine) -> Iterator[tuple[PgBloqueoMigracion, ...]]:
    with (
        migrated_engine.connect() as primera,
        migrated_engine.connect() as segunda,
    ):
        primera = primera.execution_options(isolation_level="AUTOCOMMIT")
        segunda = segunda.execution_options(isolation_level="AUTOCOMMIT")
        bloqueos = (PgBloqueoMigracion(primera), PgBloqueoMigracion(segunda))
        try:
            yield bloqueos
        finally:
            for bloqueo in bloqueos:
                bloqueo.liberar()


def test_bloqueo_second_connection_cannot_acquire_until_first_releases(
    dos_conexiones: tuple[PgBloqueoMigracion, ...],
) -> None:
    primera, segunda = dos_conexiones

    assert primera.intentar_adquirir() is True
    assert segunda.intentar_adquirir() is False

    primera.liberar()

    assert segunda.intentar_adquirir() is True
    assert primera.intentar_adquirir() is False


def test_bloqueo_uses_session_level_advisory_lock_with_constant_key() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    assert "pg_try_advisory_lock(:clave)" in fuente
    assert "pg_advisory_xact_lock" not in fuente
    assert isinstance(modulo_repositorios.CLAVE_BLOQUEO_MIGRACION, int)


# ------------------------------------------------------------------ unit of work
def test_repositories_module_never_controls_the_transaction() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    for metodo in ("commit", "rollback", "begin", "close"):
        assert re.search(rf"\.{metodo}\s*\(", fuente) is None, metodo


def test_repositories_module_never_reads_system_time() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    assert "datetime.now" not in fuente
    assert "utcnow" not in fuente
    assert "date.today" not in fuente
