"""Puertos del dashboard de retencion (CU-11, decision (c) de R-011).

Solo lectura. El mes se pasa como rango de instantes UTC ``[desde, hasta)`` ya calculado en
fecha de negocio (Ecuador) por el caso de uso; el lector filtra por el instante de creacion
de la gestion (``created_at``) e ignora las gestiones borradas. Un valor nulo nunca cuenta
(R-010 (h)). Ningun puerto devuelve sesiones ni modelos ORM.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

from app.domain.modelo.variables import CicloModelo


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
