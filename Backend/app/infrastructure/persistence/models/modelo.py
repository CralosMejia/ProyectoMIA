"""Tablas del modelo predictivo: ``modelos``, ``intentos_reentrenamiento`` y ``estado_sistema``.

``modelos`` e ``intentos_reentrenamiento`` no llevan ``deleted_at``: son instantaneas
inmutables (RT-07) y auditoria append-only. ``estado_sistema`` es una fila unica de control.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)
from app.infrastructure.persistence.models.base import Base, IdMixin, TimestampMixin, check_in

# Probabilidades del modelo como valor exacto en BD (0..1 con 8 decimales).
PROBABILIDAD = Numeric(10, 8, asdecimal=True)


def check_probabilidad(column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} BETWEEN 0 AND 1", name=f"{column}_rango")


class Modelo(IdMixin, TimestampMixin, Base):
    __tablename__ = "modelos"

    version: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    vigente: Mapped[bool] = mapped_column(nullable=False)
    fecha_entrenamiento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ciclos_entrenamiento: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    prevalencia: Mapped[Decimal] = mapped_column(PROBABILIDAD, nullable=False)
    umbral_alto: Mapped[Decimal] = mapped_column(PROBABILIDAD, nullable=False)
    umbral_medio: Mapped[Decimal] = mapped_column(PROBABILIDAD, nullable=False)
    porcentajes_umbral: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    artefacto: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Parametros y versiones de librerias del entrenamiento.
    metadata_tecnica: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        CheckConstraint("ciclos_entrenamiento >= 0", name="ciclos_entrenamiento_no_negativo"),
        check_probabilidad("prevalencia"),
        check_probabilidad("umbral_alto"),
        check_probabilidad("umbral_medio"),
        # Un solo modelo vigente a la vez.
        Index("ux_modelos_vigente", "vigente", unique=True, postgresql_where=text("vigente")),
    )


class IntentoReentrenamiento(IdMixin, TimestampMixin, Base):
    __tablename__ = "intentos_reentrenamiento"

    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_programada: Mapped[date | None] = mapped_column(Date, nullable=True)
    disparador: Mapped[str] = mapped_column(Text, nullable=False)
    resultado: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciclos_nuevos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_auc_candidato: Mapped[Decimal | None] = mapped_column(PROBABILIDAD, nullable=True)
    pr_auc_vigente: Mapped[Decimal | None] = mapped_column(PROBABILIDAD, nullable=True)
    modelo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("modelos.id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        check_in("disparador", DisparadorReentrenamiento),
        check_in("resultado", ResultadoReentrenamiento),
        CheckConstraint("ciclos_nuevos >= 0", name="ciclos_nuevos_no_negativo"),
        check_probabilidad("pr_auc_candidato"),
        check_probabilidad("pr_auc_vigente"),
    )


class EstadoSistema(TimestampMixin, Base):
    __tablename__ = "estado_sistema"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    migracion_historica: Mapped[str] = mapped_column(Text, nullable=False)
    proxima_fecha_reentrenamiento: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("id = 1", name="fila_unica"),
        check_in("migracion_historica", EstadoMigracion),
    )
