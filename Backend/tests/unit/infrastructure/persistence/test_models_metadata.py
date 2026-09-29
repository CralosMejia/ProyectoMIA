"""Esquema declarado en ``Base.metadata`` (sin base de datos).

Sin login (RT-12): no hay ``user_id`` ni pruebas de aislamiento entre usuarios.
"""

import re
from enum import StrEnum

import pytest
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from app.domain.common.enums import (
    PLANES_CAMPANIA,
    RESPUESTAS_ACEPTACION,
    RESPUESTAS_OFRECIMIENTO,
    RESPUESTAS_RENOVACION,
    DisparadorReentrenamiento,
    EstadoGestion,
    EstadoMigracion,
    EstadoRegistro,
    FormaPago,
    NivelRiesgo,
    OrigenMembresia,
    Plan,
    ResultadoReentrenamiento,
    TipoCarga,
)
from app.infrastructure.persistence.models import Base
from app.infrastructure.persistence.models.base import check_array_subset, check_in

pytestmark = pytest.mark.unit

TABLES = Base.metadata.tables
ALL_TABLES = {
    "socios",
    "cargas",
    "membresias",
    "modelos",
    "intentos_reentrenamiento",
    "estado_sistema",
    "listas_priorizadas",
    "predicciones",
    "campanias",
    "gestiones_retencion",
}
SOFT_DELETE_TABLES = {"socios", "cargas", "membresias", "campanias", "gestiones_retencion"}
NO_SOFT_DELETE_TABLES = ALL_TABLES - SOFT_DELETE_TABLES
LITERAL = re.compile(r"'([A-Z0-9_]+)'")


# ------------------------------------------------------------------ helpers
def col(table: str, name: str) -> Column[object]:
    return TABLES[table].c[name]


def check(table: str, name: str) -> CheckConstraint:
    wanted = f"ck_{table}_{name}"
    for constraint in TABLES[table].constraints:
        if isinstance(constraint, CheckConstraint) and constraint.name == wanted:
            return constraint
    raise AssertionError(f"no existe el CHECK {wanted}")


def check_sql(table: str, name: str) -> str:
    return str(check(table, name).sqltext)


def check_literals(table: str, name: str) -> set[str]:
    return set(LITERAL.findall(check_sql(table, name)))


def index(table: str, name: str) -> Index:
    for idx in TABLES[table].indexes:
        if idx.name == name:
            return idx
    raise AssertionError(f"no existe el indice {name}")


def index_where(idx: Index) -> str:
    return str(idx.dialect_options["postgresql"]["where"])


def fk(table: str, column: str) -> ForeignKeyConstraint:
    for constraint in TABLES[table].foreign_key_constraints:
        if constraint.column_keys == [column]:
            return constraint
    raise AssertionError(f"{table}.{column} no tiene FK")


def values(enum_or_set: type[StrEnum] | frozenset[StrEnum]) -> set[str]:
    return {str(v) for v in enum_or_set}


def assert_nonnegative_check(table: str, column: str) -> None:
    sql = check_sql(table, f"{column}_no_negativo")
    assert sql.replace(" ", "") == f"{column}>=0"


def assert_probability(table: str, column: str) -> None:
    c = col(table, column)
    assert isinstance(c.type, Numeric)
    assert (c.type.precision, c.type.scale) == (10, 8)
    assert c.type.asdecimal is True
    assert check_sql(table, f"{column}_rango").replace(" ", "") == f"{column}BETWEEN0AND1"


# ------------------------------------------------------------------ helpers de CHECK
class _Color(StrEnum):
    ROJO = "ROJO"
    AZUL = "AZUL"


class _ColorAmpliado(StrEnum):
    ROJO = "ROJO"
    AZUL = "AZUL"
    VERDE = "VERDE"


def test_check_in_lists_every_enum_value_and_follows_enum_changes() -> None:
    before = check_in("color", _Color)
    after = check_in("color", _ColorAmpliado)

    assert set(LITERAL.findall(str(before.sqltext))) == {"ROJO", "AZUL"}
    assert set(LITERAL.findall(str(after.sqltext))) == {"ROJO", "AZUL", "VERDE"}
    assert str(before.sqltext).startswith("color IN (")


@pytest.mark.parametrize("bad", ["x'); DROP TABLE socios; --", "minuscula", ""])
def test_check_in_rejects_non_catalog_values(bad: str) -> None:
    with pytest.raises(ValueError):
        check_in("color", [bad])


def test_check_in_rejects_empty_catalog_and_bad_column() -> None:
    with pytest.raises(ValueError):
        check_in("color", [])
    with pytest.raises(ValueError):
        check_in("color; DROP", ["ROJO"])


def test_check_array_subset_requires_non_empty_subset() -> None:
    sql = str(check_array_subset("colores", _Color).sqltext)
    assert "cardinality(colores) > 0" in sql
    assert "colores <@ ARRAY[" in sql
    assert set(LITERAL.findall(sql)) == {"ROJO", "AZUL"}


# ------------------------------------------------------------------ transversales
def test_metadata_has_exactly_the_ten_tables() -> None:
    assert set(TABLES) == ALL_TABLES


def test_no_column_uses_floating_point() -> None:
    offenders = [
        f"{t.name}.{c.name}"
        for t in TABLES.values()
        for c in t.columns
        if isinstance(c.type, Float | postgresql.REAL | postgresql.DOUBLE_PRECISION)
        or (isinstance(c.type, Numeric) and c.type.asdecimal is False)
    ]
    assert offenders == []


def test_every_datetime_column_is_timezone_aware() -> None:
    offenders = [
        f"{t.name}.{c.name}"
        for t in TABLES.values()
        for c in t.columns
        if isinstance(c.type, DateTime) and not c.type.timezone
    ]
    assert offenders == []


def test_no_varchar_without_length() -> None:
    offenders = [
        f"{t.name}.{c.name}"
        for t in TABLES.values()
        for c in t.columns
        if type(c.type) is String and c.type.length is None
    ]
    assert offenders == []


@pytest.mark.parametrize("table", sorted(ALL_TABLES))
def test_every_table_has_timestamps(table: str) -> None:
    for name in ("created_at", "updated_at"):
        c = col(table, name)
        assert isinstance(c.type, DateTime)
        assert c.type.timezone is True
        assert c.nullable is False


@pytest.mark.parametrize("table", sorted(ALL_TABLES - {"estado_sistema"}))
def test_bigint_identity_primary_key(table: str) -> None:
    pk = col(table, "id")
    assert pk.primary_key
    assert isinstance(pk.type, BigInteger)
    assert pk.identity is not None
    assert pk.identity.always is True


@pytest.mark.parametrize("table", sorted(SOFT_DELETE_TABLES))
def test_soft_delete_tables_have_nullable_deleted_at(table: str) -> None:
    c = col(table, "deleted_at")
    assert isinstance(c.type, DateTime)
    assert c.type.timezone is True
    assert c.nullable is True


@pytest.mark.parametrize("table", sorted(NO_SOFT_DELETE_TABLES))
def test_documented_exceptions_have_no_deleted_at(table: str) -> None:
    assert "deleted_at" not in TABLES[table].c


def test_no_foreign_key_cascades_and_all_restrict() -> None:
    fks = [f for t in TABLES.values() for f in t.foreign_key_constraints]
    assert fks
    assert all((f.ondelete or "").upper() == "RESTRICT" for f in fks)


def test_json_columns_use_jsonb() -> None:
    for t in TABLES.values():
        for c in t.columns:
            assert type(c.type).__name__ != "JSON", f"{t.name}.{c.name}"


# ------------------------------------------------------------------ socios
def test_socios_columns() -> None:
    cedula = col("socios", "cedula")
    assert isinstance(cedula.type, String)
    assert cedula.type.length == 20
    assert cedula.nullable is True
    for name in ("nombre", "nombre_normalizado"):
        assert isinstance(col("socios", name).type, Text)
        assert col("socios", name).nullable is False
    for name in ("celular", "correo"):
        assert isinstance(col("socios", name).type, Text)
        assert col("socios", name).nullable is True


def test_socios_indexes() -> None:
    unique = index("socios", "ux_socios_cedula")
    assert unique.unique
    assert [c.name for c in unique.columns] == ["cedula"]
    assert index_where(unique) == "cedula IS NOT NULL AND deleted_at IS NULL"
    by_name = index("socios", "ix_socios_nombre_normalizado")
    assert [c.name for c in by_name.columns] == ["nombre_normalizado"]


# ------------------------------------------------------------------ cargas
def test_cargas_columns_and_checks() -> None:
    assert check_literals("cargas", "tipo") == values(TipoCarga)
    assert col("cargas", "tipo").nullable is False
    fecha = col("cargas", "fecha_carga")
    assert isinstance(fecha.type, DateTime)
    assert fecha.type.timezone is True
    for name in ("filas_leidas", "filas_guardadas", "filas_duplicadas", "socios_enlazados"):
        assert isinstance(col("cargas", name).type, Integer)
        assert col("cargas", name).nullable is False
        assert_nonnegative_check("cargas", name)


def test_cargas_single_active_historical_migration() -> None:
    idx = index("cargas", "ux_cargas_migracion_historica")
    assert idx.unique
    assert [c.name for c in idx.columns] == ["tipo"]
    assert index_where(idx) == "tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL"


# ------------------------------------------------------------------ membresias
def test_membresias_foreign_keys() -> None:
    assert col("membresias", "socio_id").nullable is True
    assert col("membresias", "carga_id").nullable is False
    assert fk("membresias", "socio_id").referred_table.name == "socios"
    assert fk("membresias", "carga_id").referred_table.name == "cargas"


@pytest.mark.parametrize(
    ("column", "catalog", "nullable"),
    [
        ("plan", values(Plan), False),
        ("forma_pago", values(FormaPago), False),
        ("estado_registro", values(EstadoRegistro), True),
        ("origen", values(OrigenMembresia), False),
    ],
)
def test_membresias_catalog_checks(column: str, catalog: set[str], nullable: bool) -> None:
    assert col("membresias", column).nullable is nullable
    assert check_literals("membresias", column) == catalog


def test_membresias_value_columns() -> None:
    for name in ("fecha_inicio", "fecha_vencimiento"):
        assert isinstance(col("membresias", name).type, Date)
        assert col("membresias", name).nullable is True
    for name in ("monto_facturado", "monto_cobrado"):
        c = col("membresias", name)
        assert isinstance(c.type, Numeric)
        assert (c.type.precision, c.type.scale, c.type.asdecimal) == (19, 4, True)
        assert c.nullable is True
        assert_nonnegative_check("membresias", name)
    asistencias = col("membresias", "asistencias")
    assert isinstance(asistencias.type, Integer)
    assert asistencias.nullable is True
    assert check_sql("membresias", "asistencias_rango").replace(" ", "") == (
        "asistenciasBETWEEN0AND400"
    )
    assert isinstance(col("membresias", "referencia_origen").type, JSONB)
    assert col("membresias", "referencia_origen").nullable is True
    for name in ("plan_original", "forma_pago_original", "observaciones"):
        assert isinstance(col("membresias", name).type, Text)
        assert col("membresias", name).nullable is True
    assert isinstance(col("membresias", "inicio_aproximado").type, Boolean)
    assert col("membresias", "inicio_aproximado").nullable is False


def test_membresias_query_indexes() -> None:
    by_socio = index("membresias", "ix_membresias_socio_id_fecha_vencimiento")
    assert [c.name for c in by_socio.columns] == ["socio_id", "fecha_vencimiento"]
    by_date = index("membresias", "ix_membresias_fecha_vencimiento")
    assert [c.name for c in by_date.columns] == ["fecha_vencimiento"]


# ------------------------------------------------------------------ modelos
def test_modelos_columns() -> None:
    version = col("modelos", "version")
    assert isinstance(version.type, Integer)
    assert version.nullable is False
    assert any(
        isinstance(u, UniqueConstraint) and [c.name for c in u.columns] == ["version"]
        for u in TABLES["modelos"].constraints
    )
    assert isinstance(col("modelos", "vigente").type, Boolean)
    assert col("modelos", "vigente").nullable is False
    assert isinstance(col("modelos", "artefacto").type, LargeBinary)
    assert col("modelos", "artefacto").nullable is False
    for name in ("metadata_tecnica", "porcentajes_umbral"):
        assert isinstance(col("modelos", name).type, JSONB)
        assert col("modelos", name).nullable is False
    for name in ("periodo_desde", "periodo_hasta"):
        assert isinstance(col("modelos", name).type, Date)
    for name in ("prevalencia", "umbral_alto", "umbral_medio"):
        assert_probability("modelos", name)


def test_modelos_single_current_model() -> None:
    idx = index("modelos", "ux_modelos_vigente")
    assert idx.unique
    assert [c.name for c in idx.columns] == ["vigente"]
    assert index_where(idx) == "vigente"


# ------------------------------------------------------------------ intentos_reentrenamiento
def test_intentos_reentrenamiento() -> None:
    t = "intentos_reentrenamiento"
    assert check_literals(t, "disparador") == values(DisparadorReentrenamiento)
    assert check_literals(t, "resultado") == values(ResultadoReentrenamiento)
    assert col(t, "modelo_id").nullable is True
    assert fk(t, "modelo_id").referred_table.name == "modelos"
    fecha = col(t, "fecha")
    assert isinstance(fecha.type, DateTime)
    assert fecha.nullable is False
    assert isinstance(col(t, "fecha_programada").type, Date)
    assert col(t, "fecha_programada").nullable is True
    for name in ("pr_auc_candidato", "pr_auc_vigente"):
        assert_probability(t, name)


# ------------------------------------------------------------------ estado_sistema
def test_estado_sistema_single_row() -> None:
    pk = col("estado_sistema", "id")
    assert pk.primary_key
    assert isinstance(pk.type, SmallInteger)
    assert pk.identity is None
    assert check_sql("estado_sistema", "fila_unica").replace(" ", "") == "id=1"
    assert col("estado_sistema", "migracion_historica").nullable is False
    assert check_literals("estado_sistema", "migracion_historica") == values(EstadoMigracion)
    proxima = col("estado_sistema", "proxima_fecha_reentrenamiento")
    assert isinstance(proxima.type, Date)
    assert proxima.nullable is True


# ------------------------------------------------------------------ listas_priorizadas
def test_listas_priorizadas() -> None:
    t = "listas_priorizadas"
    assert col(t, "modelo_id").nullable is False
    assert fk(t, "modelo_id").referred_table.name == "modelos"
    assert isinstance(col(t, "fecha_generacion").type, Date)
    for name in ("horizonte_dias", "top_k"):
        assert isinstance(col(t, name).type, Integer)
        assert check_sql(t, f"{name}_positivo").replace(" ", "") == f"{name}>0"
    creada = col(t, "creada_en")
    assert isinstance(creada.type, DateTime)
    assert creada.type.timezone is True


# ------------------------------------------------------------------ predicciones
def test_predicciones() -> None:
    t = "predicciones"
    assert col(t, "lista_id").nullable is False
    assert col(t, "membresia_id").nullable is False
    assert col(t, "socio_id").nullable is True
    assert fk(t, "lista_id").referred_table.name == "listas_priorizadas"
    assert fk(t, "membresia_id").referred_table.name == "membresias"
    assert fk(t, "socio_id").referred_table.name == "socios"
    assert_probability(t, "score")
    assert check_literals(t, "nivel_riesgo") == values(NivelRiesgo)
    assert isinstance(col(t, "factores_principales").type, JSONB)
    assert check_sql(t, "prioridad_positiva").replace(" ", "") == "prioridad>0"
    assert isinstance(col(t, "dentro_top_k").type, Boolean)
    assert any(
        isinstance(u, UniqueConstraint)
        and [c.name for c in u.columns] == ["lista_id", "membresia_id"]
        for u in TABLES[t].constraints
    )
    idx = index(t, "ix_predicciones_lista_id_prioridad")
    assert [c.name for c in idx.columns] == ["lista_id", "prioridad"]


# ------------------------------------------------------------------ campanias
def test_campanias() -> None:
    t = "campanias"
    for name, catalog in (
        ("niveles_riesgo", values(NivelRiesgo)),
        ("planes", values(PLANES_CAMPANIA)),
    ):
        c = col(t, name)
        assert isinstance(c.type, ARRAY)
        assert isinstance(c.type.item_type, Text)
        assert c.nullable is False
        sql = check_sql(t, name)
        assert f"cardinality({name}) > 0" in sql
        assert "<@" in sql
        assert set(LITERAL.findall(sql)) == catalog
    assert "DIARIO" not in check_literals(t, "planes")
    assert check_sql(t, "prioridad_minima").replace(" ", "") == "prioridad>=1"
    for name in ("activa", "es_ejemplo"):
        assert isinstance(col(t, name).type, Boolean)
        assert col(t, name).nullable is False


# ------------------------------------------------------------------ gestiones_retencion
def test_gestiones_retencion_keys_and_uniqueness() -> None:
    t = "gestiones_retencion"
    assert col(t, "prediccion_id").nullable is False
    assert col(t, "membresia_id").nullable is False
    assert col(t, "campania_id").nullable is True
    assert fk(t, "prediccion_id").referred_table.name == "predicciones"
    assert fk(t, "membresia_id").referred_table.name == "membresias"
    assert fk(t, "campania_id").referred_table.name == "campanias"
    unique = index(t, "ux_gestiones_retencion_membresia_id")
    assert unique.unique
    assert [c.name for c in unique.columns] == ["membresia_id"]
    assert index_where(unique) == "deleted_at IS NULL"
    alerts = index(t, "ix_gestiones_retencion_estado_fecha_seguimiento")
    assert [c.name for c in alerts.columns] == ["estado", "fecha_seguimiento"]


@pytest.mark.parametrize(
    ("column", "catalog"),
    [
        ("campania_ofrecida", values(RESPUESTAS_OFRECIMIENTO)),
        ("campania_aceptada", values(RESPUESTAS_ACEPTACION)),
        ("renovo_declarado", values(RESPUESTAS_RENOVACION)),
    ],
)
def test_gestiones_retencion_answer_checks(column: str, catalog: set[str]) -> None:
    assert col("gestiones_retencion", column).nullable is True
    assert check_literals("gestiones_retencion", column) == catalog


def test_gestiones_retencion_columns() -> None:
    t = "gestiones_retencion"
    assert check_literals(t, "estado") == values(EstadoGestion)
    assert col(t, "estado").nullable is False
    assert isinstance(col(t, "contactado").type, Boolean)
    assert col(t, "contactado").nullable is True
    for name in ("fecha_asignacion", "fecha_seguimiento", "fecha_contacto"):
        assert isinstance(col(t, name).type, Date)
    cerrada = col(t, "cerrada_en")
    assert isinstance(cerrada.type, DateTime)
    assert cerrada.type.timezone is True
    assert cerrada.nullable is True


def test_table_objects_are_sqlalchemy_tables() -> None:
    assert all(isinstance(t, Table) for t in TABLES.values())
