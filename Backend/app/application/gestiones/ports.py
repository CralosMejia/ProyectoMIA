"""Puertos de la gestion de retencion (CU-08, CU-10).

Unidad de trabajo: la transaccion la gestiona siempre quien llama. El repositorio recibe la
sesion ya abierta (infraestructura) y **nunca** hace ``commit`` ni ``rollback``. No expone
borrado: una gestion solo cambia de estado (``PENDIENTE`` -> ``CERRADA``) o nace ``CERRADA``
si no se le asigna campana. Ningun puerto
recibe ni devuelve sesiones ni modelos ORM: solo los tipos de aqui.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.application.campanias.ports import CampaniaRepository
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan, Respuesta


@dataclass(frozen=True, slots=True)
class DatosPrediccionGestion:
    """Lo que la gestion necesita de una prediccion (y de su lista, modelo y membresia).

    ``nivel_riesgo``, ``score`` y ``modelo_version`` son los de esa lista (RT-07).
    """

    prediccion_id: int
    membresia_id: int
    fecha_vencimiento: date
    nivel_riesgo: NivelRiesgo
    plan: Plan
    score: Decimal
    modelo_version: int
    socio_nombre: str


@dataclass(frozen=True, slots=True)
class NuevaGestion:
    """Gestion a crear. ``created_at``/``updated_at`` los pone el repositorio desde el reloj.

    ``campania_nombre`` es la instantanea del nombre al asignar (RN-08.2): nulo si y solo si
    ``campania_id`` es nulo. ``cerrada_en`` es el instante de cierre de una gestion que nace
    cerrada (sin campana, R-010 (c)): no nulo si y solo si ``estado`` es ``CERRADA``.
    """

    prediccion_id: int
    membresia_id: int
    campania_id: int | None
    campania_nombre: str | None
    fecha_asignacion: date
    fecha_seguimiento: date
    responsable: str | None
    estado: EstadoGestion = EstadoGestion.PENDIENTE
    cerrada_en: datetime | None = None

    def __post_init__(self) -> None:
        if (self.campania_id is None) != (self.campania_nombre is None):
            raise ValueError("campania_id y campania_nombre deben ser ambos nulos o no nulos")
        if (self.estado is EstadoGestion.CERRADA) != (self.cerrada_en is not None):
            raise ValueError("cerrada_en debe informarse si y solo si el estado es CERRADA")


@dataclass(frozen=True, slots=True)
class ResultadoGestion:
    """Campos del resultado (CU-10) que reemplazan a los guardados."""

    contactado: bool
    campania_ofrecida: Respuesta
    campania_aceptada: Respuesta
    renovo_declarado: Respuesta
    fecha_contacto: date | None
    observaciones: str | None
    responsable: str | None
    fecha_seguimiento: date
    estado: EstadoGestion
    cerrada_en: datetime | None


@dataclass(frozen=True, slots=True)
class GestionDetalle:
    """Gestion guardada con los datos originales de su prediccion.

    ``fecha_asignacion`` es la fecha de negocio (Ecuador); ``creada_en`` el instante UTC de
    creacion (``created_at``).
    """

    id: int
    prediccion_id: int
    membresia_id: int
    socio_nombre: str
    plan: Plan
    fecha_vencimiento: date
    modelo_version: int
    score: Decimal
    nivel_riesgo: NivelRiesgo
    campania_id: int | None
    campania_nombre: str | None
    estado: EstadoGestion
    fecha_asignacion: date
    creada_en: datetime
    fecha_seguimiento: date
    responsable: str | None
    contactado: bool | None
    campania_ofrecida: Respuesta | None
    campania_aceptada: Respuesta | None
    renovo_declarado: Respuesta | None
    fecha_contacto: date | None
    observaciones: str | None
    cerrada_en: datetime | None


@runtime_checkable
class GestionRepository(Protocol):
    """Gestiones de retencion dentro de la transaccion de quien llama (sin ``commit``)."""

    def datos_prediccion(self, prediccion_id: int) -> DatosPrediccionGestion | None:
        """Datos de la prediccion para crear la gestion, o ``None`` si no existe."""
        ...

    def existe_para_membresia(self, membresia_id: int) -> bool:
        """``True`` si el ciclo ya tiene una gestion no borrada (RN-08.1)."""
        ...

    def crear(self, nueva: NuevaGestion) -> int:
        """Inserta la gestion y devuelve su id.

        La unidad de trabajo traduce la violacion de ``ux_gestiones_retencion_membresia_id``
        a ``GestionDuplicadaError``.
        """
        ...

    def obtener(self, gestion_id: int) -> GestionDetalle | None:
        """Gestion no borrada con sus datos originales, o ``None``. Solo lectura."""
        ...

    def obtener_para_actualizar(self, gestion_id: int) -> GestionDetalle | None:
        """Como ``obtener`` pero bloqueando la fila (``SELECT ... FOR UPDATE``)."""
        ...

    def guardar_resultado(self, gestion_id: int, resultado: ResultadoGestion) -> None:
        """Reemplaza los campos del resultado; ``updated_at`` desde el reloj."""
        ...


class ContextoGestiones(Protocol):
    """Repositorios que comparten una sola transaccion (unidad de trabajo de gestiones).

    Si se sale del contexto sin ``commit()`` (o con una excepcion) todo se revierte.
    """

    @property
    def gestiones(self) -> GestionRepository: ...

    @property
    def campanias(self) -> CampaniaRepository: ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...


class UnidadDeTrabajoGestiones(Protocol):
    """Abre una unidad de trabajo nueva en cada llamada."""

    def __call__(self) -> AbstractContextManager[ContextoGestiones]: ...
