"""Instantanea del nombre de la campana en la gestion (RN-08.2; R-009 decision (c)).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-29

``upgrade()`` en tres pasos para que aplique igual sobre una base con gestiones:

1. Anade ``gestiones_retencion.campania_nombre TEXT NULL``.
2. Rellena las gestiones existentes que tienen campana con el nombre actual de esa campana
   (SQL fijo, sin entrada externa); las que no tienen campana quedan en ``NULL``.
3. ``CHECK ((campania_id IS NULL) = (campania_nombre IS NULL))`` (``campania_nombre_coherente``).

Editar o inactivar la campana despues no cambia el nombre guardado en la gestion.
``downgrade()`` elimina el ``CHECK`` y la columna (solo en desarrollo).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "gestiones_retencion"
CHECK = "campania_nombre_coherente"

_RELLENAR_NOMBRE = """
UPDATE gestiones_retencion AS g
SET campania_nombre = c.nombre
FROM campanias AS c
WHERE c.id = g.campania_id AND g.campania_nombre IS NULL
"""


def upgrade() -> None:
    op.add_column(TABLA, sa.Column("campania_nombre", sa.Text(), nullable=True))
    op.execute(_RELLENAR_NOMBRE)
    op.create_check_constraint(
        op.f(f"ck_{TABLA}_{CHECK}"), TABLA, "(campania_id IS NULL) = (campania_nombre IS NULL)"
    )


def downgrade() -> None:
    op.drop_constraint(op.f(f"ck_{TABLA}_{CHECK}"), TABLA, type_="check")
    op.drop_column(TABLA, "campania_nombre")
