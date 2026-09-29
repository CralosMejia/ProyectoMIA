"""Esquema inicial: las 10 tablas, sus restricciones e indices.

Revision ID: 0001
Revises:
Create Date: 2026-09-28

Autogenerado desde ``Base.metadata`` y revisado a mano. Los ``CHECK ... IN (...)`` son una
instantanea de los enums del dominio al crear la revision: un cambio posterior de un enum
exige una migracion nueva (lo detecta la prueba de integracion que compara los ``CHECK``).
``downgrade()`` elimina todo lo creado, en orden inverso de dependencias.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "campanias",
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("niveles_riesgo", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("planes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False),
        sa.Column("es_ejemplo", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "cardinality(niveles_riesgo) > 0 AND "
            "niveles_riesgo <@ ARRAY['ALTO', 'BAJO', 'MEDIO']::text[]",
            name=op.f("ck_campanias_niveles_riesgo"),
        ),
        sa.CheckConstraint(
            "cardinality(planes) > 0 AND "
            "planes <@ ARRAY['ANUAL', 'MENSUAL', 'OTRO', 'SEMESTRAL', 'TRIMESTRAL']::text[]",
            name=op.f("ck_campanias_planes"),
        ),
        sa.CheckConstraint("prioridad >= 1", name=op.f("ck_campanias_prioridad_minima")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campanias")),
    )
    op.create_table(
        "cargas",
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("fecha_carga", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nombre_archivo", sa.Text(), nullable=False),
        sa.Column("filas_leidas", sa.Integer(), nullable=False),
        sa.Column("filas_guardadas", sa.Integer(), nullable=False),
        sa.Column("filas_duplicadas", sa.Integer(), nullable=False),
        sa.Column("socios_enlazados", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tipo IN ('MIGRACION_HISTORICA', 'PLANTILLA')", name=op.f("ck_cargas_tipo")
        ),
        sa.CheckConstraint(
            "filas_duplicadas >= 0", name=op.f("ck_cargas_filas_duplicadas_no_negativo")
        ),
        sa.CheckConstraint(
            "filas_guardadas >= 0", name=op.f("ck_cargas_filas_guardadas_no_negativo")
        ),
        sa.CheckConstraint("filas_leidas >= 0", name=op.f("ck_cargas_filas_leidas_no_negativo")),
        sa.CheckConstraint(
            "socios_enlazados >= 0", name=op.f("ck_cargas_socios_enlazados_no_negativo")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cargas")),
    )
    op.create_index(
        "ux_cargas_migracion_historica",
        "cargas",
        ["tipo"],
        unique=True,
        postgresql_where=sa.text("tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL"),
    )
    op.create_table(
        "estado_sistema",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("migracion_historica", sa.Text(), nullable=False),
        sa.Column("proxima_fecha_reentrenamiento", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "migracion_historica IN ('COMPLETADA', 'EN_CURSO', 'PENDIENTE')",
            name=op.f("ck_estado_sistema_migracion_historica"),
        ),
        sa.CheckConstraint("id = 1", name=op.f("ck_estado_sistema_fila_unica")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_estado_sistema")),
    )
    op.create_table(
        "modelos",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("fecha_entrenamiento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ciclos_entrenamiento", sa.Integer(), nullable=False),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("prevalencia", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("umbral_alto", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("umbral_medio", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("porcentajes_umbral", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artefacto", sa.LargeBinary(), nullable=False),
        sa.Column("metadata_tecnica", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ciclos_entrenamiento >= 0", name=op.f("ck_modelos_ciclos_entrenamiento_no_negativo")
        ),
        sa.CheckConstraint(
            "prevalencia BETWEEN 0 AND 1", name=op.f("ck_modelos_prevalencia_rango")
        ),
        sa.CheckConstraint(
            "umbral_alto BETWEEN 0 AND 1", name=op.f("ck_modelos_umbral_alto_rango")
        ),
        sa.CheckConstraint(
            "umbral_medio BETWEEN 0 AND 1", name=op.f("ck_modelos_umbral_medio_rango")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modelos")),
        sa.UniqueConstraint("version", name=op.f("uq_modelos_version")),
    )
    op.create_index(
        "ux_modelos_vigente",
        "modelos",
        ["vigente"],
        unique=True,
        postgresql_where=sa.text("vigente"),
    )
    op.create_table(
        "socios",
        sa.Column("cedula", sa.String(length=20), nullable=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("nombre_normalizado", sa.Text(), nullable=False),
        sa.Column("celular", sa.Text(), nullable=True),
        sa.Column("correo", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_socios")),
    )
    op.create_index("ix_socios_nombre_normalizado", "socios", ["nombre_normalizado"], unique=False)
    op.create_index(
        "ux_socios_cedula",
        "socios",
        ["cedula"],
        unique=True,
        postgresql_where=sa.text("cedula IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "intentos_reentrenamiento",
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_programada", sa.Date(), nullable=True),
        sa.Column("disparador", sa.Text(), nullable=False),
        sa.Column("resultado", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("ciclos_nuevos", sa.Integer(), nullable=True),
        sa.Column("pr_auc_candidato", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("pr_auc_vigente", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("modelo_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "disparador IN ('INICIAL', 'MANUAL', 'PROGRAMADO')",
            name=op.f("ck_intentos_reentrenamiento_disparador"),
        ),
        sa.CheckConstraint(
            "resultado IN ('CRITERIOS_NO_CUMPLIDOS', 'ENTRENADO', 'FALLIDO', "
            "'NO_SUPERA_VIGENTE', 'OMITIDO')",
            name=op.f("ck_intentos_reentrenamiento_resultado"),
        ),
        sa.CheckConstraint(
            "ciclos_nuevos >= 0", name=op.f("ck_intentos_reentrenamiento_ciclos_nuevos_no_negativo")
        ),
        sa.CheckConstraint(
            "pr_auc_candidato BETWEEN 0 AND 1",
            name=op.f("ck_intentos_reentrenamiento_pr_auc_candidato_rango"),
        ),
        sa.CheckConstraint(
            "pr_auc_vigente BETWEEN 0 AND 1",
            name=op.f("ck_intentos_reentrenamiento_pr_auc_vigente_rango"),
        ),
        sa.ForeignKeyConstraint(
            ["modelo_id"],
            ["modelos.id"],
            name=op.f("fk_intentos_reentrenamiento_modelo_id_modelos"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intentos_reentrenamiento")),
    )
    op.create_table(
        "listas_priorizadas",
        sa.Column("modelo_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha_generacion", sa.Date(), nullable=False),
        sa.Column("horizonte_dias", sa.Integer(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "horizonte_dias > 0", name=op.f("ck_listas_priorizadas_horizonte_dias_positivo")
        ),
        sa.CheckConstraint("top_k > 0", name=op.f("ck_listas_priorizadas_top_k_positivo")),
        sa.ForeignKeyConstraint(
            ["modelo_id"],
            ["modelos.id"],
            name=op.f("fk_listas_priorizadas_modelo_id_modelos"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listas_priorizadas")),
    )
    op.create_table(
        "membresias",
        sa.Column("socio_id", sa.BigInteger(), nullable=True),
        sa.Column("carga_id", sa.BigInteger(), nullable=False),
        sa.Column("estado_registro", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("forma_pago", sa.Text(), nullable=False),
        sa.Column("monto_facturado", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("monto_cobrado", sa.Numeric(precision=19, scale=4), nullable=True),
        sa.Column("asistencias", sa.Integer(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("origen", sa.Text(), nullable=False),
        sa.Column("referencia_origen", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plan_original", sa.Text(), nullable=True),
        sa.Column("forma_pago_original", sa.Text(), nullable=True),
        sa.Column("inicio_aproximado", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado_registro IN ('BAJA', 'CONGELAMIENTO', 'NUEVO', 'REINGRESO', 'RENOVACION')",
            name=op.f("ck_membresias_estado_registro"),
        ),
        sa.CheckConstraint(
            "forma_pago IN ('EFECTIVO', 'OTRO', 'SIN_DATO', 'TARJETA_DATAFAST', 'TRANSFERENCIA')",
            name=op.f("ck_membresias_forma_pago"),
        ),
        sa.CheckConstraint(
            "origen IN ('HISTORICO', 'PLANTILLA')", name=op.f("ck_membresias_origen")
        ),
        sa.CheckConstraint(
            "plan IN ('ANUAL', 'DIARIO', 'MENSUAL', 'OTRO', 'SEMESTRAL', 'TRIMESTRAL')",
            name=op.f("ck_membresias_plan"),
        ),
        sa.CheckConstraint(
            "asistencias BETWEEN 0 AND 400", name=op.f("ck_membresias_asistencias_rango")
        ),
        sa.CheckConstraint(
            "monto_cobrado >= 0", name=op.f("ck_membresias_monto_cobrado_no_negativo")
        ),
        sa.CheckConstraint(
            "monto_facturado >= 0", name=op.f("ck_membresias_monto_facturado_no_negativo")
        ),
        sa.ForeignKeyConstraint(
            ["carga_id"],
            ["cargas.id"],
            name=op.f("fk_membresias_carga_id_cargas"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["socio_id"],
            ["socios.id"],
            name=op.f("fk_membresias_socio_id_socios"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_membresias")),
    )
    op.create_index(
        "ix_membresias_fecha_vencimiento", "membresias", ["fecha_vencimiento"], unique=False
    )
    op.create_index(
        "ix_membresias_socio_id_fecha_vencimiento",
        "membresias",
        ["socio_id", "fecha_vencimiento"],
        unique=False,
    )
    op.create_table(
        "predicciones",
        sa.Column("lista_id", sa.BigInteger(), nullable=False),
        sa.Column("membresia_id", sa.BigInteger(), nullable=False),
        sa.Column("socio_id", sa.BigInteger(), nullable=True),
        sa.Column("score", sa.Numeric(precision=10, scale=8), nullable=False),
        sa.Column("nivel_riesgo", sa.Text(), nullable=False),
        sa.Column("factores_principales", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prioridad", sa.Integer(), nullable=False),
        sa.Column("dentro_top_k", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "nivel_riesgo IN ('ALTO', 'BAJO', 'MEDIO')", name=op.f("ck_predicciones_nivel_riesgo")
        ),
        sa.CheckConstraint("prioridad > 0", name=op.f("ck_predicciones_prioridad_positiva")),
        sa.CheckConstraint("score BETWEEN 0 AND 1", name=op.f("ck_predicciones_score_rango")),
        sa.ForeignKeyConstraint(
            ["lista_id"],
            ["listas_priorizadas.id"],
            name=op.f("fk_predicciones_lista_id_listas_priorizadas"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["membresia_id"],
            ["membresias.id"],
            name=op.f("fk_predicciones_membresia_id_membresias"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["socio_id"],
            ["socios.id"],
            name=op.f("fk_predicciones_socio_id_socios"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predicciones")),
        sa.UniqueConstraint(
            "lista_id", "membresia_id", name=op.f("uq_predicciones_lista_id_membresia_id")
        ),
    )
    op.create_index(
        "ix_predicciones_lista_id_prioridad",
        "predicciones",
        ["lista_id", "prioridad"],
        unique=False,
    )
    op.create_table(
        "gestiones_retencion",
        sa.Column("prediccion_id", sa.BigInteger(), nullable=False),
        sa.Column("membresia_id", sa.BigInteger(), nullable=False),
        sa.Column("campania_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha_asignacion", sa.Date(), nullable=False),
        sa.Column("fecha_seguimiento", sa.Date(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("responsable", sa.Text(), nullable=True),
        sa.Column("contactado", sa.Boolean(), nullable=True),
        sa.Column("campania_ofrecida", sa.Text(), nullable=True),
        sa.Column("campania_aceptada", sa.Text(), nullable=True),
        sa.Column("renovo_declarado", sa.Text(), nullable=True),
        sa.Column("fecha_contacto", sa.Date(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "campania_aceptada IN ('NO', 'NO_APLICA', 'PENDIENTE', 'SI')",
            name=op.f("ck_gestiones_retencion_campania_aceptada"),
        ),
        sa.CheckConstraint(
            "campania_ofrecida IN ('NO', 'NO_APLICA', 'SI')",
            name=op.f("ck_gestiones_retencion_campania_ofrecida"),
        ),
        sa.CheckConstraint(
            "estado IN ('CERRADA', 'PENDIENTE')", name=op.f("ck_gestiones_retencion_estado")
        ),
        sa.CheckConstraint(
            "renovo_declarado IN ('NO', 'PENDIENTE', 'SI')",
            name=op.f("ck_gestiones_retencion_renovo_declarado"),
        ),
        sa.ForeignKeyConstraint(
            ["campania_id"],
            ["campanias.id"],
            name=op.f("fk_gestiones_retencion_campania_id_campanias"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["membresia_id"],
            ["membresias.id"],
            name=op.f("fk_gestiones_retencion_membresia_id_membresias"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prediccion_id"],
            ["predicciones.id"],
            name=op.f("fk_gestiones_retencion_prediccion_id_predicciones"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gestiones_retencion")),
    )
    op.create_index(
        "ix_gestiones_retencion_estado_fecha_seguimiento",
        "gestiones_retencion",
        ["estado", "fecha_seguimiento"],
        unique=False,
    )
    op.create_index(
        "ux_gestiones_retencion_membresia_id",
        "gestiones_retencion",
        ["membresia_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_gestiones_retencion_membresia_id",
        table_name="gestiones_retencion",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_gestiones_retencion_estado_fecha_seguimiento", table_name="gestiones_retencion"
    )
    op.drop_table("gestiones_retencion")
    op.drop_index("ix_predicciones_lista_id_prioridad", table_name="predicciones")
    op.drop_table("predicciones")
    op.drop_index("ix_membresias_socio_id_fecha_vencimiento", table_name="membresias")
    op.drop_index("ix_membresias_fecha_vencimiento", table_name="membresias")
    op.drop_table("membresias")
    op.drop_table("listas_priorizadas")
    op.drop_table("intentos_reentrenamiento")
    op.drop_index(
        "ux_socios_cedula",
        table_name="socios",
        postgresql_where=sa.text("cedula IS NOT NULL AND deleted_at IS NULL"),
    )
    op.drop_index("ix_socios_nombre_normalizado", table_name="socios")
    op.drop_table("socios")
    op.drop_index("ux_modelos_vigente", table_name="modelos", postgresql_where=sa.text("vigente"))
    op.drop_table("modelos")
    op.drop_table("estado_sistema")
    op.drop_index(
        "ux_cargas_migracion_historica",
        table_name="cargas",
        postgresql_where=sa.text("tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL"),
    )
    op.drop_table("cargas")
    op.drop_table("campanias")
