"""Migraciones ``0001`` (esquema) y ``0002`` (fila de ``estado_sistema``) contra PostgreSQL 16.

Sin login (RT-12): no hay ``user_id``; las pruebas de aislamiento entre usuarios no aplican.
Cada prueba deja la base como la encontro: transaccion con rollback, o ciclo de migraciones
que termina en ``head``; la fixture ``migrated_engine`` vuelve a ``base`` al final.
"""

import re
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import CheckConstraint, Connection, Engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.infrastructure.persistence.models import Base
from tests.integration import conftest as integration_conftest

pytestmark = pytest.mark.integration

BUSINESS_TABLES = set(Base.metadata.tables)
NOW = datetime(2026, 1, 1, tzinfo=UTC)
LITERAL = re.compile(r"'([A-Z0-9_]+)'")


# ------------------------------------------------------------------ guarda de la BD de pruebas
@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@127.0.0.1:5432/app_db",
        "postgresql+psycopg://u:p@127.0.0.1:5432/app_test_db",
        "postgresql+psycopg://u:p@127.0.0.1:5432/",
        'postgresql+psycopg://u:p@127.0.0.1:5432/x"_test',
    ],
    ids=["dev", "suffix-in-middle", "no-db", "bad-chars"],
)
def test_guard_test_database_non_test_name_aborts_without_showing_url(url: str) -> None:
    with pytest.raises(pytest.fail.Exception) as excinfo:
        integration_conftest._guard_test_database(make_url(url))
    message = str(excinfo.value)
    assert "_test" in message
    assert "u:p@" not in message


def test_guard_test_database_accepts_test_suffix() -> None:
    url = make_url("postgresql+psycopg://u:p@127.0.0.1:5432/app_db_test")
    assert integration_conftest._guard_test_database(url) is url


# ------------------------------------------------------------------ helpers
@pytest.fixture
def conn(migrated_engine: Engine) -> Iterator[Connection]:
    """Conexion en una transaccion que siempre se revierte."""
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def _stamps() -> dict[str, object]:
    return {"created_at": NOW, "updated_at": NOW}


def insert(conn: Connection, table: str, values: Mapping[str, object]) -> int:
    """INSERT parametrizado; ``table`` y columnas vienen solo del codigo de la prueba."""
    assert table in BUSINESS_TABLES
    row = {**_stamps(), **values}
    columns = ", ".join(row)
    params = ", ".join(f":{c}" for c in row)
    sql = f"INSERT INTO {table} ({columns}) VALUES ({params}) RETURNING id"  # noqa: S608 - nombres fijos de la prueba
    result = conn.execute(text(sql), row).scalar_one()
    return int(result)


def socio(conn: Connection, **values: object) -> int:
    return insert(conn, "socios", {"nombre": "Ana", "nombre_normalizado": "ANA", **values})


def carga(conn: Connection, **values: object) -> int:
    base = {
        "tipo": "PLANTILLA",
        "fecha_carga": NOW,
        "nombre_archivo": "plantilla.xlsx",
        "filas_leidas": 0,
        "filas_guardadas": 0,
        "filas_duplicadas": 0,
        "socios_enlazados": 0,
    }
    return insert(conn, "cargas", {**base, **values})


def membresia(conn: Connection, **values: object) -> int:
    base = {
        "carga_id": carga(conn),
        "plan": "MENSUAL",
        "forma_pago": "EFECTIVO",
        "origen": "PLANTILLA",
        "inicio_aproximado": False,
    }
    return insert(conn, "membresias", {**base, **values})


def modelo(conn: Connection, **values: object) -> int:
    base = {
        "version": 1,
        "vigente": False,
        "fecha_entrenamiento": NOW,
        "ciclos_entrenamiento": 10,
        "periodo_desde": NOW.date(),
        "periodo_hasta": NOW.date(),
        "prevalencia": "0.25",
        "umbral_alto": "0.7",
        "umbral_medio": "0.4",
        "porcentajes_umbral": "{}",
        "artefacto": b"\x00",
        "metadata_tecnica": "{}",
    }
    return insert(conn, "modelos", {**base, **values})


def gestion(conn: Connection, membresia_id: int) -> int:
    lista_id = insert(
        conn,
        "listas_priorizadas",
        {
            "modelo_id": modelo(conn, version=100 + membresia_id),
            "fecha_generacion": NOW.date(),
            "horizonte_dias": 30,
            "top_k": 10,
            "creada_en": NOW,
        },
    )
    prediccion_id = insert(
        conn,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "score": "0.5",
            "nivel_riesgo": "ALTO",
            "factores_principales": "[]",
            "prioridad": 1,
            "dentro_top_k": True,
        },
    )
    return insert(
        conn,
        "gestiones_retencion",
        {
            "prediccion_id": prediccion_id,
            "membresia_id": membresia_id,
            "fecha_asignacion": NOW.date(),
            "fecha_seguimiento": NOW.date(),
            "estado": "PENDIENTE",
        },
    )


def campania(conn: Connection, **values: object) -> int:
    base = {
        "nombre": "Ejemplo",
        "activa": True,
        "niveles_riesgo": ["ALTO"],
        "planes": ["MENSUAL"],
        "prioridad": 1,
        "es_ejemplo": True,
    }
    return insert(conn, "campanias", {**base, **values})


def table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


# ------------------------------------------------------------------ 0001: esquema
def test_upgrade_head_creates_the_ten_tables(migrated_engine: Engine) -> None:
    assert table_names(migrated_engine) == BUSINESS_TABLES | {"alembic_version"}
    assert len(BUSINESS_TABLES) == 10


def test_alembic_check_detects_no_differences(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.check(alembic_config)


def test_database_checks_match_metadata_checks(migrated_engine: Engine) -> None:
    """Deriva ORM/migracion/enums: mismos ``CHECK`` por nombre y mismos valores de catalogo."""
    expected = {
        str(c.name): set(LITERAL.findall(str(c.sqltext)))
        for t in Base.metadata.tables.values()
        for c in t.constraints
        if isinstance(c, CheckConstraint)
    }
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE contype = 'c' AND connamespace = 'public'::regnamespace"
            )
        ).all()
    actual = {name: set(LITERAL.findall(definition)) for name, definition in rows}
    assert actual == expected


def test_membresia_plan_outside_catalog_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_membresias_plan"):
        membresia(conn, plan="SEMANAL")


def test_monto_cobrado_negative_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_membresias_monto_cobrado_no_negativo"):
        membresia(conn, monto_cobrado="-1")


def test_socio_duplicate_cedula_is_rejected(conn: Connection) -> None:
    socio(conn, cedula="0102030405")
    with pytest.raises(IntegrityError, match="ux_socios_cedula"):
        socio(conn, cedula="0102030405")


def test_socios_without_cedula_can_repeat(conn: Connection) -> None:
    socio(conn, cedula=None)
    socio(conn, cedula=None)


def test_socio_cedula_can_be_reused_after_soft_delete(conn: Connection) -> None:
    socio(conn, cedula="0102030405", deleted_at=NOW)
    socio(conn, cedula="0102030405")


def test_second_historical_migration_is_rejected(conn: Connection) -> None:
    carga(conn, tipo="MIGRACION_HISTORICA")
    carga(conn, tipo="PLANTILLA")
    with pytest.raises(IntegrityError, match="ux_cargas_migracion_historica"):
        carga(conn, tipo="MIGRACION_HISTORICA")


def test_second_current_model_is_rejected(conn: Connection) -> None:
    modelo(conn, version=1, vigente=True)
    modelo(conn, version=2, vigente=False)
    with pytest.raises(IntegrityError, match="ux_modelos_vigente"):
        modelo(conn, version=3, vigente=True)


def test_second_gestion_for_same_membresia_is_rejected(conn: Connection) -> None:
    membresia_id = membresia(conn)
    gestion(conn, membresia_id)
    prediccion_id = conn.execute(
        text("SELECT id FROM predicciones WHERE membresia_id = :m"), {"m": membresia_id}
    ).scalar_one()
    with pytest.raises(IntegrityError, match="ux_gestiones_retencion_membresia_id"):
        insert(
            conn,
            "gestiones_retencion",
            {
                "prediccion_id": prediccion_id,
                "membresia_id": membresia_id,
                "fecha_asignacion": NOW.date(),
                "fecha_seguimiento": NOW.date(),
                "estado": "PENDIENTE",
            },
        )


def test_campania_with_diario_plan_is_rejected(conn: Connection) -> None:
    campania(conn)
    with pytest.raises(IntegrityError, match="ck_campanias_planes"):
        campania(conn, planes=["DIARIO"])


def test_campania_with_empty_levels_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_campanias_niveles_riesgo"):
        campania(conn, niveles_riesgo=[])


def test_foreign_keys_restrict_physical_delete(conn: Connection) -> None:
    socio_id = socio(conn)
    membresia(conn, socio_id=socio_id)
    with pytest.raises(IntegrityError, match="fk_membresias_socio_id_socios"):
        conn.execute(text("DELETE FROM socios WHERE id = :id"), {"id": socio_id})


# ------------------------------------------------------------------ 0002: estado_sistema
def test_estado_sistema_has_single_pending_row(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT id, migracion_historica, proxima_fecha_reentrenamiento FROM estado_sistema"
            )
        ).all()
    assert [tuple(r) for r in rows] == [(1, "PENDIENTE", None)]


def test_estado_sistema_second_row_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="ck_estado_sistema_fila_unica"):
        conn.execute(
            text(
                "INSERT INTO estado_sistema (id, migracion_historica, created_at, updated_at) "
                "VALUES (2, 'PENDIENTE', :now, :now)"
            ),
            {"now": NOW},
        )


# ------------------------------------------------------------------ ciclos de migracion
def _estado_sistema_rows(engine: Engine) -> list[tuple[object, ...]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, migracion_historica FROM estado_sistema ORDER BY id")
        ).all()
    return [tuple(r) for r in rows]


def test_0002_downgrade_removes_only_its_row_and_upgrade_restores_it(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0001")
    try:
        assert "estado_sistema" in table_names(migrated_engine)
        assert _estado_sistema_rows(migrated_engine) == []
    finally:
        command.upgrade(alembic_config, "head")
    assert _estado_sistema_rows(migrated_engine) == [(1, "PENDIENTE")]


def test_0002_upgrade_is_idempotent_over_existing_row(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0001")
    try:
        with migrated_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO estado_sistema (id, migracion_historica, created_at, updated_at) "
                    "VALUES (1, 'EN_CURSO', :now, :now)"
                ),
                {"now": NOW},
            )
        command.upgrade(alembic_config, "head")
        assert _estado_sistema_rows(migrated_engine) == [(1, "EN_CURSO")]
    finally:
        command.downgrade(alembic_config, "0001")
        command.upgrade(alembic_config, "head")
    assert _estado_sistema_rows(migrated_engine) == [(1, "PENDIENTE")]


def test_downgrade_base_leaves_only_alembic_version_and_upgrade_again_works(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "base")
    try:
        assert table_names(migrated_engine) == {"alembic_version"}
    finally:
        command.upgrade(alembic_config, "head")
    assert table_names(migrated_engine) == BUSINESS_TABLES | {"alembic_version"}
    assert _estado_sistema_rows(migrated_engine) == [(1, "PENDIENTE")]
