"""Puertos del dashboard de retencion (CU-11, decision (c) de R-011).

Solo lectura. El mes se pasa como rango de instantes UTC ``[desde, hasta)`` ya calculado en
fecha de negocio (Ecuador) por el caso de uso; el lector filtra por el instante de creacion
de la gestion (``created_at``) e ignora las gestiones borradas. Un valor nulo nunca cuenta
(R-010 (h)). Ningun puerto devuelve sesiones ni modelos ORM.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from app.domain.modelo.piloto import MontoMembresia
from app.domain.modelo.variables import CicloModelo

__all__ = [
    "FilaCampania",
    "FilaEmbudo",
    "FilaPiloto",
    "LectorDashboard",
    "ListaPiloto",
    "ModeloDashboard",
    "MontoMembresia",
]


@dataclass(frozen=True, slots=True)
class FilaEmbudo:
    """Embudo del mes sobre las gestiones **con campana**.

    ``contactadas`` = ``contactado IS TRUE``; ``ofrecidas`` = ``campania_ofrecida = 'SI'``;
    ``aceptadas`` = ``campania_aceptada = 'SI'``; ``renovaron`` = ``renovo_declarado = 'SI'``.
    """

    asignadas: int
    contactadas: int
    ofrecidas: int
    aceptadas: int
    renovaron: int


@dataclass(frozen=True, slots=True)
class FilaCampania:
    """Cifras de una campana en el mes; ``campania_id`` nulo = gestiones sin campana.

    ``nombre`` es el nombre actual de la campana (nulo solo sin campana).
    ``gestiones_cerradas`` = gestiones cerradas **con resultado** (``renovo_declarado`` SI/NO).
    """

    campania_id: int | None
    nombre: str | None
    gestiones: int
    contactados: int
    renovaciones: int
    gestiones_cerradas: int


@dataclass(frozen=True, slots=True)
class ModeloDashboard:
    """Datos ligeros del modelo vigente (sin el artefacto).

    ``fecha_corte`` sale de ``metadata_tecnica["fecha_corte"]``; ``None`` si no la tiene.
    """

    version: int
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int
    fecha_corte: date | None


@dataclass(frozen=True, slots=True)
class FilaPiloto:
    """Prediccion del top del piloto (``prioridad <= 25``), sin datos personales.

    ``contactado``/``fecha_contacto`` salen de la gestion **no borrada** del mismo
    ``membresia_id`` (una por ciclo, RN-08.1), venga de la lista que venga; sin gestion -> nulos.
    """

    membresia_id: int
    prioridad: int
    contactado: bool | None
    fecha_contacto: date | None


@dataclass(frozen=True, slots=True)
class ListaPiloto:
    """Lista del mes (definicion (a)) con sus filas del top ordenadas por ``prioridad``."""

    id: int
    nombre: str
    fecha_generacion: date
    filas: tuple[FilaPiloto, ...]


@runtime_checkable
class LectorDashboard(Protocol):
    """Lecturas del dashboard (cada llamada con su propia transaccion de solo lectura)."""

    def embudo(self, desde: datetime, hasta: datetime) -> FilaEmbudo: ...

    def por_campania(self, desde: datetime, hasta: datetime) -> list[FilaCampania]:
        """Filas ordenadas por ``gestiones DESC, lower(nombre), campania_id``, con la fila sin
        campana (si existe) al final."""
        ...

    def modelo_vigente(self) -> ModeloDashboard | None: ...

    def proxima_fecha_reentrenamiento(self) -> date | None: ...

    def ciclos(self) -> list[CicloModelo]:
        """Membresias no borradas como ciclos sin etiquetar (``excluido=False``,
        ``no_renovo=None``); ``clave_socio`` = id del socio y ``ref`` = id de la membresia."""
        ...

    def lista_piloto(self, desde: date, hasta: date) -> ListaPiloto | None:
        """Ultima lista con ``fecha_generacion`` en ``[desde, hasta]`` (orden
        ``fecha_generacion DESC, creada_en DESC, id DESC``) con sus filas ``prioridad <= 25``;
        ``None`` si no hay ninguna en el rango."""
        ...

    def montos(self, ids: Sequence[int]) -> dict[int, MontoMembresia]:
        """Montos exactos de las membresias no borradas de ``ids`` (las borradas no salen)."""
        ...

    def ultima_carga_plantilla(self) -> datetime | None:
        """Instante de la carga por plantilla no borrada mas reciente."""
        ...
