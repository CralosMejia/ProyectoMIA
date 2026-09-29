"""Base declarativa del ORM: convencion de nombres, mixins comunes y helpers de ``CHECK``.

El esquema fisico se crea solo con las migraciones versionadas (servicio ``migrate``);
este modulo describe el ``MetaData`` que ellas reflejan y con el que se comparan.
"""

import re
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Los valores de catalogo se escriben como literales en el DDL: solo se aceptan
# identificadores en mayusculas (nunca entrada del usuario).
_CATALOG_VALUE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_COLUMN_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Por defecto: texto sin limite y fechas-hora siempre con zona horaria.
    type_annotation_map = {  # noqa: RUF012 - atributo de configuracion de SQLAlchemy
        str: Text(),
        datetime: DateTime(timezone=True),
    }


class IdMixin:
    """PK ``BIGINT GENERATED ALWAYS AS IDENTITY``."""

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)


class TimestampMixin:
    """``created_at``/``updated_at`` ``TIMESTAMPTZ NOT NULL``, asignados desde el ``Clock``."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SoftDeleteMixin:
    """Borrado logico: ``deleted_at TIMESTAMPTZ NULL``."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _literals(values: Iterable[str]) -> str:
    ordered = sorted({str(value) for value in values})
    if not ordered:
        raise ValueError("el catalogo del CHECK no puede estar vacio")
    invalid = [value for value in ordered if not _CATALOG_VALUE.match(value)]
    if invalid:
        raise ValueError("los valores de catalogo deben ser identificadores en mayusculas")
    return ", ".join(f"'{value}'" for value in ordered)


def _require_column_name(column: str) -> str:
    if not _COLUMN_NAME.match(column):
        raise ValueError("nombre de columna invalido para un CHECK")
    return column


def check_in(column: str, values: Iterable[str]) -> CheckConstraint:
    """``CHECK (columna IN (...))`` con los valores del enum o subconjunto dado.

    El nombre final lo pone la convencion: ``ck_<tabla>_<columna>``.
    """
    name = _require_column_name(column)
    return CheckConstraint(f"{name} IN ({_literals(values)})", name=name)


def check_array_subset(column: str, values: Iterable[str]) -> CheckConstraint:
    """``CHECK`` de arreglo ``TEXT[]`` no vacio y contenido (``<@``) en el catalogo dado."""
    name = _require_column_name(column)
    return CheckConstraint(
        f"cardinality({name}) > 0 AND {name} <@ ARRAY[{_literals(values)}]::text[]",
        name=name,
    )
