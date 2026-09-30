"""``membresias.fecha_actividad`` (fecha que ordena el historial del socio).

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-29

Prerrequisito de la prediccion (D3-BE-05): las variables en T-30 y la regla "ya renovo"
comparan ``fecha_actividad`` (inicio, o el mes de la hoja si falta), que hasta ahora solo
vivia en memoria. ``upgrade()`` anade la columna ``NULL``, la rellena con ``fecha_inicio``
donde exista y despues la pasa a ``NOT NULL``: si queda alguna fila sin valor, el
``SET NOT NULL`` falla y la migracion se revierte entera (hoy ninguna base tiene filas).
Anade ``ix_membresias_socio_id_fecha_actividad``. ``downgrade()`` quita el indice y la columna.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICE = "ix_membresias_socio_id_fecha_actividad"


def upgrade() -> None:
    op.add_column("membresias", sa.Column("fecha_actividad", sa.Date(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE membresias SET fecha_actividad = fecha_inicio "
            "WHERE fecha_actividad IS NULL AND fecha_inicio IS NOT NULL"
        )
    )
    op.alter_column("membresias", "fecha_actividad", existing_type=sa.Date(), nullable=False)
    op.create_index(INDICE, "membresias", ["socio_id", "fecha_actividad"])


def downgrade() -> None:
    op.drop_index(INDICE, table_name="membresias")
    op.drop_column("membresias", "fecha_actividad")
