"""Robustez del esquema contra PostgreSQL 16 real: atomicidad de ``upgrade``, concurrencia
sobre los indices unicos parciales y ``alembic current`` por CLI.

Sin login (RT-12): no hay ``user_id``; el aislamiento entre usuarios no aplica.
Cada prueba restaura la base a ``head`` y borra las filas que confirmo.
"""

import threading
from collections.abc import Callable

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.infrastructure.persistence.models import Base
from tests.integration.persistence.test_migrations import carga, modelo
from tests.unit.infrastructure.persistence.test_alembic_config import run_alembic

pytestmark = pytest.mark.integration

BUSINESS_TABLES = set(Base.metadata.tables)


def table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def race(engine: Engine, action: Callable[[Connection, int], object]) -> list[str]:
    """Ejecuta ``action`` en dos transacciones simultaneas; devuelve el resultado de cada una."""
    barrier = threading.Barrier(2, timeout=30)
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(n: int) -> None:
        try:
            with engine.connect() as connection, connection.begin():
                connection.execute(text("SET LOCAL lock_timeout = '20s'"))
                barrier.wait()
                action(connection, n)
            result = "ok"
        except IntegrityError:
            result = "integrity_error"
        except Exception as exc:
            result = f"unexpected:{type(exc).__name__}"
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker, args=(n,)) for n in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not any(t.is_alive() for t in threads), "una transaccion quedo bloqueada"
    return sorted(outcomes)


# ------------------------------------------------------------------ T6: alembic current por CLI
def test_alembic_current_with_test_database_url_exits_zero_at_head(
    migrated_engine: Engine, test_database_url: URL
) -> None:
    result = run_alembic(
        "current", database_url=test_database_url.render_as_string(hide_password=False)
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "0006 (head)" in output
    if test_database_url.password:
        assert test_database_url.password not in output


# ------------------------------------------------------------------ T8: marcas de tiempo
def test_estado_sistema_row_has_database_timestamps(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        created_at, updated_at = connection.execute(
            text("SELECT created_at, updated_at FROM estado_sistema WHERE id = 1")
        ).one()
    assert created_at is not None
    assert created_at.tzinfo is not None
    assert updated_at is not None


# ------------------------------------------------------------------ atomicidad del upgrade
def test_upgrade_failing_midway_leaves_no_partial_schema(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    """Si ``0001`` falla en su ultima tabla, no queda ninguna tabla creada ni version marcada."""
    command.downgrade(alembic_config, "base")
    try:
        with migrated_engine.begin() as connection:
            connection.execute(text("CREATE TABLE gestiones_retencion (x INTEGER)"))
        with pytest.raises(ProgrammingError):
            command.upgrade(alembic_config, "head")
        assert table_names(migrated_engine) == {"alembic_version", "gestiones_retencion"}
        with migrated_engine.connect() as connection:
            versions = connection.execute(text("SELECT version_num FROM alembic_version")).all()
        assert versions == []
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS gestiones_retencion"))
        command.upgrade(alembic_config, "head")
    assert table_names(migrated_engine) == BUSINESS_TABLES | {"alembic_version"}


# ------------------------------------------------------------------ concurrencia
def test_concurrent_current_models_only_one_commits(migrated_engine: Engine) -> None:
    try:
        outcomes = race(
            migrated_engine, lambda conn, n: modelo(conn, version=9000 + n, vigente=True)
        )
        with migrated_engine.connect() as connection:
            vigentes = connection.execute(
                text("SELECT count(*) FROM modelos WHERE vigente")
            ).scalar_one()
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(text("DELETE FROM modelos WHERE version IN (9001, 9002)"))
    assert outcomes == ["integrity_error", "ok"]
    assert vigentes == 1


def test_concurrent_historical_migrations_only_one_commits(migrated_engine: Engine) -> None:
    marker = "concurrencia-migracion.xlsx"
    try:
        outcomes = race(
            migrated_engine,
            lambda conn, _n: carga(conn, tipo="MIGRACION_HISTORICA", nombre_archivo=marker),
        )
        with migrated_engine.connect() as connection:
            activas = connection.execute(
                text(
                    "SELECT count(*) FROM cargas "
                    "WHERE tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL"
                )
            ).scalar_one()
    finally:
        with migrated_engine.begin() as connection:
            connection.execute(text("DELETE FROM cargas WHERE nombre_archivo = :m"), {"m": marker})
    assert outcomes == ["integrity_error", "ok"]
    assert activas == 1
