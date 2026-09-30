"""Indice parcial de socios sin cedula por nombre (enlace de la carga por plantilla, CU-01).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-29

RN-01.9 / D-03: al confirmar una plantilla, una cedula que no existe se enlaza con el unico
socio historico **sin cedula** que tenga el mismo ``nombre_normalizado``. ``upgrade()`` crea
``ix_socios_nombre_normalizado_sin_cedula`` sobre ``socios(nombre_normalizado)`` con
``WHERE cedula IS NULL AND deleted_at IS NULL`` para esa busqueda; ``downgrade()`` lo quita.
Solo crea un indice: aplica igual sobre una base con datos. ``socios`` es una tabla pequena
(miles de filas), asi que no hace falta ``CREATE INDEX CONCURRENTLY``.

La consulta de duplicados (RN-01.8 / D-04: socio + inicio + vencimiento + plan) no necesita
indice nuevo: reutiliza ``ix_membresias_socio_id_fecha_vencimiento`` (filtra por ``socio_id``).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICE = "ix_socios_nombre_normalizado_sin_cedula"


def upgrade() -> None:
    op.create_index(
        INDICE,
        "socios",
        ["nombre_normalizado"],
        postgresql_where=sa.text("cedula IS NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDICE, table_name="socios")
