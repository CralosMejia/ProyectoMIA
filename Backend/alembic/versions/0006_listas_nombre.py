"""Nombre de la lista priorizada (R-008, punto 5; decisiones (g) e (i)).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-29

``upgrade()`` en tres pasos para que aplique igual sobre una base con listas:

1. Anade ``listas_priorizadas.nombre TEXT`` admitiendo ``NULL``.
2. Rellena las filas existentes con el nombre por defecto de su ``fecha_generacion``:
   ``"Lista del <d> <mmm> <aaaa>"`` (dia sin cero, meses cortos fijos sin punto), el mismo
   formato que ``app.domain.listas.nombre.nombre_por_defecto``. SQL fijo, sin entrada externa.
3. ``SET NOT NULL`` y ``CHECK (char_length(nombre) BETWEEN 1 AND 80)`` (``nombre_longitud``).

Sin indice: no se busca por nombre. La lista sigue inmutable (RN-04.5).
``downgrade()`` elimina la columna (solo en desarrollo).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "listas_priorizadas"
CHECK = "nombre_longitud"

_RELLENAR_NOMBRE = """
UPDATE listas_priorizadas
SET nombre = 'Lista del '
    || EXTRACT(DAY FROM fecha_generacion)::int
    || ' '
    || (ARRAY['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'])
       [EXTRACT(MONTH FROM fecha_generacion)::int]
    || ' '
    || EXTRACT(YEAR FROM fecha_generacion)::int
WHERE nombre IS NULL
"""


def upgrade() -> None:
    op.add_column(TABLA, sa.Column("nombre", sa.Text(), nullable=True))
    op.execute(_RELLENAR_NOMBRE)
    op.alter_column(TABLA, "nombre", existing_type=sa.Text(), nullable=False)
    op.create_check_constraint(
        op.f(f"ck_{TABLA}_{CHECK}"), TABLA, "char_length(nombre) BETWEEN 1 AND 80"
    )


def downgrade() -> None:
    op.drop_constraint(op.f(f"ck_{TABLA}_{CHECK}"), TABLA, type_="check")
    op.drop_column(TABLA, "nombre")
