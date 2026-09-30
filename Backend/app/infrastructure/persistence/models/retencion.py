"""Tablas de retencion: ``listas_priorizadas``, ``predicciones``, ``campanias`` y
``gestiones_retencion``.

``listas_priorizadas`` y ``predicciones`` son instantaneas inmutables (RT-07): sin
``deleted_at``.
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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.common.enums import (
    PLANES_CAMPANIA,
    RESPUESTAS_ACEPTACION,
    RESPUESTAS_OFRECIMIENTO,
    RESPUESTAS_RENOVACION,
    EstadoGestion,
    NivelRiesgo,
)
from app.infrastructure.persistence.models.base import (
    Base,
    IdMixin,
    SoftDeleteMixin,
    TimestampMixin,
    check_array_subset,
    check_in,
)
from app.infrastructure.persistence.models.modelo import PROBABILIDAD, check_probabilidad


def _fk(target: str) -> ForeignKey:
    return ForeignKey(target, ondelete="RESTRICT")


class ListaPriorizada(IdMixin, TimestampMixin, Base):
    __tablename__ = "listas_priorizadas"

    modelo_id: Mapped[int] = mapped_column(BigInteger, _fk("modelos.id"), nullable=False)
    fecha_generacion: Mapped[date] = mapped_column(Date, nullable=False)
    horizonte_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # R-008 (punto 5): nombre editable al generar; por defecto "Lista del 29 sep 2026".
    nombre: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("horizonte_dias > 0", name="horizonte_dias_positivo"),
        CheckConstraint("top_k > 0", name="top_k_positivo"),
        CheckConstraint("char_length(nombre) BETWEEN 1 AND 80", name="nombre_longitud"),
    )


class Prediccion(IdMixin, TimestampMixin, Base):
    __tablename__ = "predicciones"

    lista_id: Mapped[int] = mapped_column(BigInteger, _fk("listas_priorizadas.id"), nullable=False)
    membresia_id: Mapped[int] = mapped_column(BigInteger, _fk("membresias.id"), nullable=False)
    socio_id: Mapped[int | None] = mapped_column(BigInteger, _fk("socios.id"), nullable=True)
    score: Mapped[Decimal] = mapped_column(PROBABILIDAD, nullable=False)
    nivel_riesgo: Mapped[str] = mapped_column(Text, nullable=False)
    factores_principales: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False)
    dentro_top_k: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        check_probabilidad("score"),
        check_in("nivel_riesgo", NivelRiesgo),
        CheckConstraint("prioridad > 0", name="prioridad_positiva"),
        UniqueConstraint("lista_id", "membresia_id"),
        Index("ix_predicciones_lista_id_prioridad", "lista_id", "prioridad"),
    )


class Campania(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "campanias"

    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    activa: Mapped[bool] = mapped_column(nullable=False)
    niveles_riesgo: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    planes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, nullable=False)
    es_ejemplo: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        check_array_subset("niveles_riesgo", NivelRiesgo),
        check_array_subset("planes", PLANES_CAMPANIA),
        CheckConstraint("prioridad >= 1", name="prioridad_minima"),
    )


class GestionRetencion(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "gestiones_retencion"

    prediccion_id: Mapped[int] = mapped_column(BigInteger, _fk("predicciones.id"), nullable=False)
    membresia_id: Mapped[int] = mapped_column(BigInteger, _fk("membresias.id"), nullable=False)
    campania_id: Mapped[int | None] = mapped_column(BigInteger, _fk("campanias.id"), nullable=True)
    fecha_asignacion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_seguimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    responsable: Mapped[str | None] = mapped_column(Text, nullable=True)
    contactado: Mapped[bool | None] = mapped_column(nullable=True)
    campania_ofrecida: Mapped[str | None] = mapped_column(Text, nullable=True)
    campania_aceptada: Mapped[str | None] = mapped_column(Text, nullable=True)
    renovo_declarado: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_contacto: Mapped[date | None] = mapped_column(Date, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        check_in("estado", EstadoGestion),
        check_in("campania_ofrecida", RESPUESTAS_OFRECIMIENTO),
        check_in("campania_aceptada", RESPUESTAS_ACEPTACION),
        check_in("renovo_declarado", RESPUESTAS_RENOVACION),
        # RN-08.1: una sola gestion activa por ciclo de membresia.
        Index(
            "ux_gestiones_retencion_membresia_id",
            "membresia_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_gestiones_retencion_estado_fecha_seguimiento", "estado", "fecha_seguimiento"),
    )
