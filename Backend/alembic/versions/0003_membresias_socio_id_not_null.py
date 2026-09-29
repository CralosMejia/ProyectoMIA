"""``membresias.socio_id`` pasa a ``NOT NULL``.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29

Decision del dia 2: toda membresia pertenece a un socio. ``predicciones.socio_id`` no se toca
(sigue admitiendo ``NULL``). ``upgrade()`` falla si ya existen membresias sin socio; deben
enlazarse antes de aplicar la migracion. ``downgrade()`` vuelve a admitir ``NULL``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("membresias", "socio_id", existing_type=sa.BigInteger(), nullable=False)


def downgrade() -> None:
    op.alter_column("membresias", "socio_id", existing_type=sa.BigInteger(), nullable=True)
