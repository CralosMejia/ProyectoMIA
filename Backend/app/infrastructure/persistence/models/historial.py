"""Tablas del historial de membresias: ``socios``, ``cargas`` y ``membresias``."""

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
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.common.enums import (
    EstadoRegistro,
    FormaPago,
    OrigenMembresia,
    Plan,
    TipoCarga,
)
from app.infrastructure.persistence.models.base import (
    Base,
    IdMixin,
    SoftDeleteMixin,
    TimestampMixin,
    check_in,
)

MONTO = Numeric(19, 4, asdecimal=True)
MAX_ASISTENCIAS = 400


class Socio(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "socios"

    # Cedula o pasaporte (hasta 20, D-14); vacia en registros historicos sin identidad.
    cedula: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_normalizado: Mapped[str] = mapped_column(Text, nullable=False)
    celular: Mapped[str | None] = mapped_column(Text, nullable=True)
    correo: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "ux_socios_cedula",
            "cedula",
            unique=True,
            postgresql_where=text("cedula IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_socios_nombre_normalizado", "nombre_normalizado"),
    )


_CONTEOS_CARGA = ("filas_leidas", "filas_guardadas", "filas_duplicadas", "socios_enlazados")


class Carga(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "cargas"

    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    filas_leidas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_guardadas: Mapped[int] = mapped_column(Integer, nullable=False)
    filas_duplicadas: Mapped[int] = mapped_column(Integer, nullable=False)
    socios_enlazados: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        check_in("tipo", TipoCarga),
        *(CheckConstraint(f"{c} >= 0", name=f"{c}_no_negativo") for c in _CONTEOS_CARGA),
        # Solo puede existir una migracion historica activa.
        Index(
            "ux_cargas_migracion_historica",
            "tipo",
            unique=True,
            postgresql_where=text("tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL"),
        ),
    )


class Membresia(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "membresias"

    # NULL: registros historicos sin identidad utilizable (decision final en el dia 2).
    socio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("socios.id", ondelete="RESTRICT"), nullable=True
    )
    carga_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cargas.id", ondelete="RESTRICT"), nullable=False
    )
    estado_registro: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    forma_pago: Mapped[str] = mapped_column(Text, nullable=False)
    monto_facturado: Mapped[Decimal | None] = mapped_column(MONTO, nullable=True)
    monto_cobrado: Mapped[Decimal | None] = mapped_column(MONTO, nullable=True)
    asistencias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    origen: Mapped[str] = mapped_column(Text, nullable=False)
    # Anio, hoja y fila del libro de origen (solo historico).
    referencia_origen: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    plan_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    forma_pago_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    inicio_aproximado: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        check_in("plan", Plan),
        check_in("forma_pago", FormaPago),
        check_in("estado_registro", EstadoRegistro),
        check_in("origen", OrigenMembresia),
        CheckConstraint("monto_facturado >= 0", name="monto_facturado_no_negativo"),
        CheckConstraint("monto_cobrado >= 0", name="monto_cobrado_no_negativo"),
        CheckConstraint(f"asistencias BETWEEN 0 AND {MAX_ASISTENCIAS}", name="asistencias_rango"),
        Index("ix_membresias_socio_id_fecha_vencimiento", "socio_id", "fecha_vencimiento"),
        Index("ix_membresias_fecha_vencimiento", "fecha_vencimiento"),
    )
