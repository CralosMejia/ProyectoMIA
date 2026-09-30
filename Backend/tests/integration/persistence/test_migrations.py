"""Migraciones ``0001`` (esquema), ``0002`` (fila de ``estado_sistema``), ``0003``
(``membresias.socio_id NOT NULL``), ``0004`` (``membresias.fecha_actividad``), ``0005``
(indice de socios sin cedula por nombre) y ``0006`` (``listas_priorizadas.nombre``) contra
PostgreSQL 16.

Sin login (RT-12): no hay ``user_id``; las pruebas de aislamiento entre usuarios no aplican.
Cada prueba deja la base como la encontro: transaccion con rollback, o ciclo de migraciones
que termina en ``head``; la fixture ``migrated_engine`` vuelve a ``base`` al final.
"""

import re
from collections.abc import Iterator, Mapping
from datetime import UTC, date, datetime

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
HEAD = "0006"


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


def membresia(conn: Connection, *, con_actividad: bool = True, **values: object) -> int:
    """Membresia valida; crea un socio por defecto salvo que se pase ``socio_id``.

    ``con_actividad=False`` omite ``fecha_actividad`` (esquema anterior a ``0004``).
    """
    base: dict[str, object] = {
        "socio_id": values["socio_id"] if "socio_id" in values else socio(conn),
        "carga_id": carga(conn),
        "plan": "MENSUAL",
        "forma_pago": "EFECTIVO",
        "origen": "PLANTILLA",
        "inicio_aproximado": False,
    }
    if con_actividad:
        base["fecha_actividad"] = NOW.date()
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
            "nombre": "Lista de prueba",
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


# ------------------------------------------------------------------ 0003: socio_id NOT NULL
def _is_nullable(engine: Engine, table: str, column: str) -> bool:
    columns = {c["name"]: c for c in inspect(engine).get_columns(table)}
    return bool(columns[column]["nullable"])


def test_membresia_without_socio_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="socio_id"):
        membresia(conn, socio_id=None)


def test_membresia_with_valid_socio_is_accepted(conn: Connection) -> None:
    socio_id = socio(conn)
    membresia_id = membresia(conn, socio_id=socio_id)
    stored = conn.execute(
        text("SELECT socio_id FROM membresias WHERE id = :id"), {"id": membresia_id}
    ).scalar_one()
    assert stored == socio_id


def test_0003_leaves_predicciones_socio_id_nullable(migrated_engine: Engine) -> None:
    assert _is_nullable(migrated_engine, "membresias", "socio_id") is False
    assert _is_nullable(migrated_engine, "predicciones", "socio_id") is True


def test_0003_downgrade_accepts_null_socio_and_upgrade_again_works(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0002")
    try:
        assert _is_nullable(migrated_engine, "membresias", "socio_id") is True
        with migrated_engine.connect() as connection:
            transaction = connection.begin()
            try:
                assert membresia(connection, socio_id=None, con_actividad=False) > 0
            finally:
                transaction.rollback()
    finally:
        command.upgrade(alembic_config, "head")
    assert _is_nullable(migrated_engine, "membresias", "socio_id") is False
    assert _is_nullable(migrated_engine, "predicciones", "socio_id") is True


def _vaciar_historial(engine: Engine) -> None:
    """Limpieza de la base de pruebas tras datos confirmados (orden de las FK)."""
    with engine.begin() as connection:
        for tabla in ("membresias", "cargas", "socios"):
            connection.execute(text(f"DELETE FROM {tabla}"))  # noqa: S608 - nombres fijos


def _revision_actual(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def test_0003_upgrade_over_existing_membresias_with_socio_keeps_rows(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0002")
    try:
        with migrated_engine.begin() as connection:
            socio_id = socio(connection)
            membresia_id = membresia(connection, socio_id=socio_id, con_actividad=False)
        command.upgrade(alembic_config, "0003")

        assert _revision_actual(migrated_engine) == "0003"
        assert _is_nullable(migrated_engine, "membresias", "socio_id") is False
        with migrated_engine.connect() as connection:
            stored = connection.execute(
                text("SELECT socio_id FROM membresias WHERE id = :id"), {"id": membresia_id}
            ).scalar_one()
        assert stored == socio_id
    finally:
        _vaciar_historial(migrated_engine)
        command.upgrade(alembic_config, "head")


def test_0003_upgrade_with_membresia_without_socio_fails_and_stays_at_0002(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0002")
    try:
        with migrated_engine.begin() as connection:
            membresia(connection, socio_id=None, con_actividad=False)

        with pytest.raises(IntegrityError):
            command.upgrade(alembic_config, "head")

        assert _revision_actual(migrated_engine) == "0002"
        assert _is_nullable(migrated_engine, "membresias", "socio_id") is True
    finally:
        _vaciar_historial(migrated_engine)
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD


# ------------------------------------------------------------------ 0004: fecha_actividad
INDICE_ACTIVIDAD = "ix_membresias_socio_id_fecha_actividad"


def _columnas(engine: Engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _indices(engine: Engine, table: str) -> dict[str, list[str | None]]:
    return {str(i["name"]): list(i["column_names"]) for i in inspect(engine).get_indexes(table)}


def test_0004_fecha_actividad_is_not_null_and_indexed(migrated_engine: Engine) -> None:
    assert _is_nullable(migrated_engine, "membresias", "fecha_actividad") is False
    assert _indices(migrated_engine, "membresias")[INDICE_ACTIVIDAD] == [
        "socio_id",
        "fecha_actividad",
    ]


def test_membresia_without_fecha_actividad_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="fecha_actividad"):
        membresia(conn, con_actividad=False)


def test_membresia_with_fecha_actividad_is_stored(conn: Connection) -> None:
    membresia_id = membresia(conn, fecha_actividad=date(2025, 3, 10))
    stored = conn.execute(
        text("SELECT fecha_actividad FROM membresias WHERE id = :id"), {"id": membresia_id}
    ).scalar_one()
    assert stored == date(2025, 3, 10)


def test_0004_downgrade_removes_column_and_index_and_upgrade_restores_them(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0003")
    try:
        assert _revision_actual(migrated_engine) == "0003"
        assert "fecha_actividad" not in _columnas(migrated_engine, "membresias")
        assert INDICE_ACTIVIDAD not in _indices(migrated_engine, "membresias")
    finally:
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD
    assert _is_nullable(migrated_engine, "membresias", "fecha_actividad") is False
    assert INDICE_ACTIVIDAD in _indices(migrated_engine, "membresias")


def test_0004_upgrade_fills_fecha_actividad_from_fecha_inicio(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0003")
    try:
        with migrated_engine.begin() as connection:
            membresia_id = membresia(connection, con_actividad=False, fecha_inicio=date(2025, 1, 6))
        command.upgrade(alembic_config, "head")

        assert _revision_actual(migrated_engine) == HEAD
        with migrated_engine.connect() as connection:
            stored = connection.execute(
                text("SELECT fecha_actividad FROM membresias WHERE id = :id"),
                {"id": membresia_id},
            ).scalar_one()
        assert stored == date(2025, 1, 6)
    finally:
        _vaciar_historial(migrated_engine)
        command.upgrade(alembic_config, "head")


def test_0004_upgrade_with_membresia_without_fecha_inicio_fails_and_stays_at_0003(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0003")
    try:
        with migrated_engine.begin() as connection:
            membresia(connection, con_actividad=False, fecha_inicio=None)

        with pytest.raises(IntegrityError):
            command.upgrade(alembic_config, "head")

        assert _revision_actual(migrated_engine) == "0003"
        assert "fecha_actividad" not in _columnas(migrated_engine, "membresias")
    finally:
        _vaciar_historial(migrated_engine)
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD


# ------------------------------------------------------------------ 0005: socios sin cedula
INDICE_SIN_CEDULA = "ix_socios_nombre_normalizado_sin_cedula"


def _definicion_indice(engine: Engine, nombre: str) -> str | None:
    with engine.connect() as connection:
        definicion = connection.execute(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :nombre"),
            {"nombre": nombre},
        ).scalar_one_or_none()
    return None if definicion is None else str(definicion)


def test_0005_creates_partial_index_on_socios_without_cedula(migrated_engine: Engine) -> None:
    definicion = _definicion_indice(migrated_engine, INDICE_SIN_CEDULA)

    assert definicion is not None
    assert "ON public.socios" in definicion
    assert "(nombre_normalizado)" in definicion
    assert "WHERE ((cedula IS NULL) AND (deleted_at IS NULL))" in definicion
    assert "UNIQUE" not in definicion


def test_0005_downgrade_removes_index_and_upgrade_restores_it_over_data(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0004")
    try:
        assert _revision_actual(migrated_engine) == "0004"
        assert _definicion_indice(migrated_engine, INDICE_SIN_CEDULA) is None
        with migrated_engine.begin() as connection:
            membresia(connection, socio_id=socio(connection, cedula=None))
            socio(connection, cedula="1700000019")

        command.upgrade(alembic_config, "head")

        assert _revision_actual(migrated_engine) == HEAD
        assert _definicion_indice(migrated_engine, INDICE_SIN_CEDULA) is not None
        with migrated_engine.connect() as connection:
            total = connection.execute(text("SELECT count(*) FROM socios")).scalar_one()
        assert total == 2
    finally:
        _vaciar_historial(migrated_engine)
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD


# ------------------------------------------------------------------ 0006: nombre de la lista
def lista(conn: Connection, *, con_nombre: bool = True, **values: object) -> int:
    """Lista priorizada valida; ``con_nombre=False`` omite ``nombre`` (esquema anterior a 0006)."""
    base: dict[str, object] = {
        "modelo_id": modelo(conn, version=values.pop("version", 1)),
        "fecha_generacion": NOW.date(),
        "horizonte_dias": 30,
        "top_k": 10,
        "creada_en": NOW,
    }
    if con_nombre:
        base["nombre"] = "Campaña octubre"
    return insert(conn, "listas_priorizadas", {**base, **values})


def _vaciar_listas(engine: Engine) -> None:
    with engine.begin() as connection:
        for tabla in ("listas_priorizadas", "modelos"):
            connection.execute(text(f"DELETE FROM {tabla}"))  # noqa: S608 - nombres fijos


def _conteos(engine: Engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            tabla: int(
                connection.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one()  # noqa: S608 - nombres fijos
            )
            for tabla in sorted(BUSINESS_TABLES)
        }


def test_0006_nombre_is_not_null(migrated_engine: Engine) -> None:
    assert "nombre" in _columnas(migrated_engine, "listas_priorizadas")
    assert _is_nullable(migrated_engine, "listas_priorizadas", "nombre") is False


@pytest.mark.parametrize("nombre", ["", "a" * 81], ids=["vacio", "81-caracteres"])
def test_lista_with_invalid_name_length_is_rejected(conn: Connection, nombre: str) -> None:
    with pytest.raises(IntegrityError, match="ck_listas_priorizadas_nombre_longitud"):
        lista(conn, nombre=nombre)


def test_lista_without_nombre_is_rejected(conn: Connection) -> None:
    with pytest.raises(IntegrityError, match="nombre"):
        lista(conn, con_nombre=False)


def test_lista_with_80_characters_name_is_stored(conn: Connection) -> None:
    lista_id = lista(conn, nombre="a" * 80)
    stored = conn.execute(
        text("SELECT nombre FROM listas_priorizadas WHERE id = :id"), {"id": lista_id}
    ).scalar_one()
    assert stored == "a" * 80


def test_0006_upgrade_fills_default_name_from_fecha_generacion(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0005")
    try:
        assert _revision_actual(migrated_engine) == "0005"
        assert "nombre" not in _columnas(migrated_engine, "listas_priorizadas")
        with migrated_engine.begin() as connection:
            primera = lista(
                connection, con_nombre=False, version=1, fecha_generacion=date(2026, 9, 29)
            )
            segunda = lista(
                connection, con_nombre=False, version=2, fecha_generacion=date(2027, 1, 5)
            )
        antes = _conteos(migrated_engine)

        command.upgrade(alembic_config, "head")

        assert _revision_actual(migrated_engine) == HEAD
        assert _is_nullable(migrated_engine, "listas_priorizadas", "nombre") is False
        with migrated_engine.connect() as connection:
            nombres = dict(
                connection.execute(text("SELECT id, nombre FROM listas_priorizadas")).tuples().all()
            )
        assert nombres == {primera: "Lista del 29 sep 2026", segunda: "Lista del 5 ene 2027"}
        assert _conteos(migrated_engine) == antes
    finally:
        _vaciar_listas(migrated_engine)
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD


def test_0006_downgrade_removes_column_and_upgrade_over_empty_base_restores_it(
    migrated_engine: Engine, alembic_config: Config
) -> None:
    command.downgrade(alembic_config, "0005")
    try:
        assert "nombre" not in _columnas(migrated_engine, "listas_priorizadas")
    finally:
        command.upgrade(alembic_config, "head")
    assert _revision_actual(migrated_engine) == HEAD
    assert _is_nullable(migrated_engine, "listas_priorizadas", "nombre") is False
    command.check(alembic_config)


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
