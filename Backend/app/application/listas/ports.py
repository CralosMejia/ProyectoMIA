"""Puerto de las listas priorizadas y sus predicciones (CU-04, CU-05).

Unidad de trabajo: la transaccion la gestiona siempre quien llama. El repositorio recibe la
sesion ya abierta en su construccion (infraestructura) y **nunca** hace ``commit`` ni
``rollback`` ni abre o cierra transacciones; asi la lista y todas sus predicciones se
escriben de forma atomica. No expone ``delete`` ni actualizaciones: una lista es una
instantanea inmutable y generar otra no modifica las anteriores (RN-04.5, RT-07).
Ningun puerto recibe ni devuelve sesiones, engines ni modelos ORM: solo los DTOs de aqui.
"""

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.application.historial.ports import MembresiaRepository
from app.application.modelo.ports import EstadoSistemaRepository, ModeloRepository
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan
from app.domain.listas.nombre import LONGITUD_MAXIMA_NOMBRE

_CERO = Decimal(0)
_UNO = Decimal(1)


@dataclass(frozen=True, slots=True)
class NuevaLista:
    """Cabecera de la lista a guardar. ``creada_en`` la pone el repositorio desde el reloj.

    ``nombre`` llega ya recortado (1..80 caracteres, CHECK ``nombre_longitud``).
    """

    modelo_id: int
    fecha_generacion: date
    horizonte_dias: int
    top_k: int
    nombre: str

    def __post_init__(self) -> None:
        if not 1 <= len(self.nombre) <= LONGITUD_MAXIMA_NOMBRE:
            raise ValueError(f"nombre debe tener entre 1 y {LONGITUD_MAXIMA_NOMBRE} caracteres")
        if self.horizonte_dias < 1:
            raise ValueError("horizonte_dias debe ser positivo")
        if self.top_k < 1:
            raise ValueError("top_k debe ser positivo")


@dataclass(frozen=True, slots=True)
class NuevaPrediccion:
    """Prediccion de una membresia dentro de la lista."""

    membresia_id: int
    socio_id: int | None
    score: Decimal
    nivel_riesgo: NivelRiesgo
    factores_principales: tuple[str, ...]
    prioridad: int
    dentro_top_k: bool

    def __post_init__(self) -> None:
        if not _CERO <= self.score <= _UNO:
            raise ValueError("score debe estar entre 0 y 1")
        if self.prioridad < 1:
            raise ValueError("prioridad debe ser positiva")


@dataclass(frozen=True, slots=True)
class ItemLista:
    """Una prediccion guardada con los datos del socio y de la membresia.

    ``gestion_id``, ``gestion_estado`` y ``campania_asignada`` son los de la gestion no borrada
    del **ciclo** (``membresia_id``) al momento de consultar, aunque se creara desde otra lista;
    los tres nulos si el ciclo no tiene gestion. ``campania_asignada`` es la instantanea del
    nombre (RN-08.2) y es nula si la gestion no tiene campana.
    """

    prediccion_id: int
    membresia_id: int
    socio_id: int | None
    prioridad: int
    socio_nombre: str
    celular: str | None
    cedula: str | None
    plan: Plan
    fecha_vencimiento: date
    monto_cobrado: Decimal | None
    score: Decimal
    nivel_riesgo: NivelRiesgo
    factores_principales: list[str]
    dentro_top_k: bool
    gestion_id: int | None = None
    gestion_estado: EstadoGestion | None = None
    campania_asignada: str | None = None


@dataclass(frozen=True, slots=True)
class ListaDetalle:
    """Lista guardada con los umbrales de su modelo y los items ordenados por prioridad."""

    id: int
    modelo_id: int
    modelo_version: int
    fecha_generacion: date
    creada_en: datetime
    horizonte_dias: int
    top_k: int
    umbral_alto: Decimal
    umbral_medio: Decimal
    items: tuple[ItemLista, ...]
    nombre: str


@dataclass(frozen=True, slots=True)
class ListaResumen:
    """Resumen de una lista para el historial de listas generadas."""

    id: int
    fecha_generacion: date
    creada_en: datetime
    modelo_version: int
    horizonte_dias: int
    top_k: int
    total_items: int
    nombre: str


@runtime_checkable
class ListaRepository(Protocol):
    """Listas priorizadas dentro de la transaccion de quien llama (sin ``commit``)."""

    def crear(self, lista: NuevaLista, predicciones: Sequence[NuevaPrediccion]) -> int:
        """Inserta la lista y sus predicciones en bloque; devuelve el id de la lista."""
        ...

    def obtener(self, lista_id: int) -> ListaDetalle | None:
        """Devuelve la lista con sus items, o ``None`` si no existe."""
        ...

    def ultima(self) -> ListaDetalle | None:
        """Devuelve la lista mas reciente (mayor ``creada_en`` y despues mayor id)."""
        ...

    def listar(self) -> list[ListaResumen]:
        """Resumen de todas las listas, de la mas reciente a la mas antigua."""
        ...


@runtime_checkable
class FechasCarga(Protocol):
    """Lectura de la fecha de la ultima carga de datos (advertencia de datos antiguos)."""

    def ultima_fecha_carga_hasta(self, instante: datetime) -> datetime | None:
        """Mayor ``fecha_carga`` no borrada con ``fecha_carga <= instante``, o ``None``."""
        ...


class ContextoListas(Protocol):
    """Repositorios que comparten una sola transaccion (unidad de trabajo de listas).

    Si se sale del contexto sin ``commit()`` (o con una excepcion) todo se revierte.
    """

    @property
    def listas(self) -> ListaRepository: ...

    @property
    def modelos(self) -> ModeloRepository: ...

    @property
    def estado(self) -> EstadoSistemaRepository: ...

    @property
    def membresias(self) -> MembresiaRepository: ...

    @property
    def cargas(self) -> FechasCarga: ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...


class UnidadDeTrabajoListas(Protocol):
    """Abre una unidad de trabajo nueva en cada llamada."""

    def __call__(self) -> AbstractContextManager[ContextoListas]: ...


@runtime_checkable
class ExportadorLista(Protocol):
    """Genera el libro Excel de una lista guardada, en memoria (CU-12)."""

    def generar(self, lista: ListaDetalle) -> bytes:
        """Devuelve el ``.xlsx`` como bytes; la misma lista produce los mismos bytes."""
        ...
