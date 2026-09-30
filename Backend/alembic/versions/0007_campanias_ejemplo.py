"""Migracion de datos: tres campanas de ejemplo (D5-BD-02, D-17; R-009 decision (d)).

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-29

La ejecuta el servicio ``migrate`` como cualquier otra revision (no es una migracion al
arrancar). Cada campana se inserta con ``es_ejemplo = true`` y ``activa = true`` **solo si no
existe** ya una campana no borrada con ese nombre, asi que aplicar sobre una base con datos no
duplica nada. Las migraciones no disponen del ``Clock`` de la aplicacion: ``created_at`` y
``updated_at`` toman ``now()`` de PostgreSQL (excepcion documentada, como ``0002``). Valores
enlazados; nada de SQL construido con entrada externa. La aplicacion no calcula descuentos
(RN-06.1): el texto solo describe la accion.

``downgrade()`` borra solo esas campanas de ejemplo y falla con un mensaje claro, sin borrar
nada, si alguna gestion las referencia (solo desarrollo).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TODOS_LOS_PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]

CAMPANIAS_EJEMPLO: tuple[dict[str, object], ...] = (
    {
        "nombre": "Ejemplo: Llamada personal antes del vencimiento",
        "descripcion": "Llamar al socio antes de que venza su plan para recordarle sus avances "
        "y resolver dudas.",
        "niveles_riesgo": ["ALTO"],
        "planes": TODOS_LOS_PLANES,
        "prioridad": 1,
    },
    {
        "nombre": "Ejemplo: Renovación anticipada",
        "descripcion": "Ofrecer renovar antes del vencimiento con el beneficio que Mtabolic "
        "defina.",
        "niveles_riesgo": ["ALTO", "MEDIO"],
        "planes": ["MENSUAL", "TRIMESTRAL"],
        "prioridad": 2,
    },
    {
        "nombre": "Ejemplo: Recordatorio de renovación",
        "descripcion": "Enviar un recordatorio amable de la fecha de vencimiento.",
        "niveles_riesgo": ["MEDIO", "BAJO"],
        "planes": TODOS_LOS_PLANES,
        "prioridad": 3,
    },
)
NOMBRES_EJEMPLO = [str(c["nombre"]) for c in CAMPANIAS_EJEMPLO]

MENSAJE_DOWNGRADE_CON_GESTIONES = (
    "No se puede revertir 0007: hay gestiones que usan campanas de ejemplo. "
    "Elimine o reasigne esas gestiones (solo en desarrollo) antes de hacer downgrade."
)

_INSERTAR_SI_NO_EXISTE = sa.text(
    "INSERT INTO campanias "
    "(nombre, descripcion, activa, niveles_riesgo, planes, prioridad, es_ejemplo, "
    "created_at, updated_at) "
    "SELECT :nombre, :descripcion, true, :niveles_riesgo, :planes, :prioridad, true, "
    "now(), now() "
    "WHERE NOT EXISTS ("
    "SELECT 1 FROM campanias WHERE nombre = :nombre AND deleted_at IS NULL)"
).bindparams(
    sa.bindparam("niveles_riesgo", type_=ARRAY(sa.Text())),
    sa.bindparam("planes", type_=ARRAY(sa.Text())),
)

_NOMBRES = sa.bindparam("nombres", value=NOMBRES_EJEMPLO, type_=ARRAY(sa.Text()))

_GESTIONES_CON_EJEMPLO = sa.text(
    "SELECT count(*) FROM gestiones_retencion g JOIN campanias c ON c.id = g.campania_id "
    "WHERE c.es_ejemplo AND c.nombre = ANY(:nombres)"
).bindparams(_NOMBRES)

_BORRAR_EJEMPLO = sa.text(
    "DELETE FROM campanias WHERE es_ejemplo AND nombre = ANY(:nombres)"
).bindparams(_NOMBRES)


def upgrade() -> None:
    conexion = op.get_bind()
    for campania in CAMPANIAS_EJEMPLO:
        conexion.execute(_INSERTAR_SI_NO_EXISTE, campania)


def downgrade() -> None:
    conexion = op.get_bind()
    if conexion.execute(_GESTIONES_CON_EJEMPLO).scalar_one() > 0:
        raise RuntimeError(MENSAJE_DOWNGRADE_CON_GESTIONES)
    conexion.execute(_BORRAR_EJEMPLO)
