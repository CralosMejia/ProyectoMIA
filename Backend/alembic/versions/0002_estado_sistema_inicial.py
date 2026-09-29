"""Migracion de datos: fila unica inicial de ``estado_sistema``.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28

Las migraciones no disponen del ``Clock`` de la aplicacion: ``created_at``/``updated_at``
toman ``CURRENT_TIMESTAMP`` de PostgreSQL (excepcion documentada). Idempotente con
``ON CONFLICT (id) DO NOTHING``; ``downgrade()`` borra solo esa fila.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ESTADO_SISTEMA_ID = 1
MIGRACION_PENDIENTE = "PENDIENTE"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO estado_sistema "
            "(id, migracion_historica, proxima_fecha_reentrenamiento, created_at, updated_at) "
            "VALUES (:id, :migracion_historica, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=ESTADO_SISTEMA_ID, migracion_historica=MIGRACION_PENDIENTE)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM estado_sistema WHERE id = :id").bindparams(id=ESTADO_SISTEMA_ID)
    )
