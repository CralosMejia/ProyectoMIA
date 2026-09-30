"""Puertos del historial: lector de libros, escritura masiva y lecturas para predecir.

Unidad de trabajo: la transaccion la gestiona siempre quien llama. Los repositorios reciben
la sesion ya abierta en su construccion (infraestructura) y **nunca** hacen ``commit`` ni
``rollback`` ni abren o cierran transacciones; asi la carga, los socios y las membresias se
escriben de forma atomica en una unica transaccion (RN-03.2). Ningun puerto recibe ni
devuelve sesiones, engines ni modelos ORM: solo los DTOs de este modulo.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.domain.common.enums import (
    EstadoRegistro,
    FormaPago,
    OrigenMembresia,
    Plan,
    TipoCarga,
)
from app.domain.historico.registro import FilaCruda


@dataclass(frozen=True, slots=True)
class LibroLeido:
    """Resumen de un libro leido: hojas mensuales incluidas y auxiliares omitidas."""

    nombre: str
    anio: int
    hojas_incluidas: tuple[str, ...]
    hojas_omitidas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LibrosLeidos:
    """Resultado del lector: filas crudas de todas las hojas mensuales y resumen por libro."""

    filas: Sequence[FilaCruda]
    libros: Sequence[LibroLeido]


@dataclass(frozen=True, slots=True)
class ReferenciaOrigen:
    """Anio, hoja y fila (1-based, como en Excel) del libro de origen."""

    anio: int
    hoja: str
    fila: int


@dataclass(frozen=True, slots=True)
class NuevoSocio:
    """Socio a insertar."""

    cedula: str | None
    nombre: str
    nombre_normalizado: str
    celular: str | None = None
    correo: str | None = None


@dataclass(frozen=True, slots=True)
class NuevaMembresia:
    """Membresia a insertar.

    ``socio_id`` es obligatorio (``NOT NULL`` desde la ``0003``). ``fecha_actividad`` (inicio,
    o el mes de la hoja si falta) tambien (``NOT NULL`` desde la ``0004``).
    """

    socio_id: int
    carga_id: int
    plan: Plan
    forma_pago: FormaPago
    origen: OrigenMembresia
    inicio_aproximado: bool
    fecha_actividad: date
    estado_registro: EstadoRegistro | None = None
    fecha_inicio: date | None = None
    fecha_vencimiento: date | None = None
    monto_facturado: Decimal | None = None
    monto_cobrado: Decimal | None = None
    asistencias: int | None = None
    observaciones: str | None = None
    referencia_origen: ReferenciaOrigen | None = None
    plan_original: str | None = None
    forma_pago_original: str | None = None


@dataclass(frozen=True, slots=True)
class MembresiaParaPrediccion:
    """Membresia vigente (no borrada) con los datos que necesitan las variables y la cartera.

    ``socio_con_cedula`` indica si el socio tiene cedula registrada: la lista priorizada
    excluye a los socios sin cedula (no se entrega su valor, solo si existe).
    """

    membresia_id: int
    socio_id: int
    plan: Plan
    forma_pago: FormaPago
    fecha_inicio: date | None
    fecha_vencimiento: date | None
    fecha_actividad: date
    monto_cobrado: Decimal | None
    inicio_aproximado: bool
    socio_con_cedula: bool


@dataclass(frozen=True, slots=True)
class NuevaCarga:
    """Carga a registrar. ``fecha_carga`` debe tener zona horaria."""

    tipo: TipoCarga
    fecha_carga: datetime
    nombre_archivo: str
    filas_leidas: int
    filas_guardadas: int
    filas_duplicadas: int
    socios_enlazados: int

    def __post_init__(self) -> None:
        if self.fecha_carga.tzinfo is None or self.fecha_carga.utcoffset() is None:
            raise ValueError("fecha_carga debe tener zona horaria")


@runtime_checkable
class LectorHistorico(Protocol):
    """Lee los libros historicos y entrega valores crudos de celda (sin convertir)."""

    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        """Lee los libros de ``rutas``; solo hojas mensuales. No escribe nada."""
        ...


@runtime_checkable
class SocioRepository(Protocol):
    """Escritura de socios dentro de la transaccion de quien llama (sin ``commit``)."""

    def insertar_en_bloque(self, socios: Sequence[NuevoSocio]) -> list[int]:
        """Inserta ``socios`` y devuelve sus ids en el mismo orden de entrada."""
        ...


@runtime_checkable
class MembresiaRepository(Protocol):
    """Membresias dentro de la transaccion de quien llama (sin ``commit``)."""

    def insertar_en_bloque(self, membresias: Sequence[NuevaMembresia]) -> int:
        """Inserta ``membresias`` y devuelve cuantas se insertaron."""
        ...

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        """Todas las membresias no borradas logicamente, en una sola consulta.

        Cada una indica si su socio tiene cedula (``socio_con_cedula``).
        """
        ...


@runtime_checkable
class CargaRepository(Protocol):
    """Cargas dentro de la transaccion de quien llama (sin ``commit``)."""

    def crear(self, carga: NuevaCarga) -> int:
        """Inserta la carga y devuelve su id."""
        ...

    def ultima_fecha_carga(self) -> datetime | None:
        """Mayor ``fecha_carga`` de las cargas no borradas, o ``None`` si no hay ninguna."""
        ...

    def hay_migracion_o_membresias(self) -> bool:
        """``True`` si existe la migracion historica o alguna membresia (no borradas)."""
        ...
