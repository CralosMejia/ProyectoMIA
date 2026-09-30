"""Reglas de una campana de retencion (CU-06, CU-07; R-009 decisiones (e) y (f)).

``DatosCampania.crear`` valida y normaliza lo que el personal escribe: nombre recortado
(1..120), descripcion recortada (<= 500; vacia -> ``None``), niveles y planes no vacios, sin
``DIARIO``, sin repetidos y en orden canonico, y prioridad 1..999. ``es_compatible`` decide
si una campana se sugiere a un socio y ``clave_orden`` es el orden de las sugerencias
(prioridad, nombre sin distinguir mayusculas, id). Los mensajes de error nunca repiten lo
recibido: no llevan datos de socios.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Self

from app.domain.common.enums import PLANES_CAMPANIA, NivelRiesgo, Plan
from app.domain.common.exceptions import DomainError

LONGITUD_MAXIMA_NOMBRE = 120
LONGITUD_MAXIMA_DESCRIPCION = 500
PRIORIDAD_MINIMA = 1
PRIORIDAD_MAXIMA = 999

ORDEN_NIVELES: tuple[NivelRiesgo, ...] = (NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO)
ORDEN_PLANES: tuple[Plan, ...] = (
    Plan.MENSUAL,
    Plan.TRIMESTRAL,
    Plan.SEMESTRAL,
    Plan.ANUAL,
    Plan.OTRO,
)


class CampaniaInvalidaError(DomainError):
    """Los datos de la campana no cumplen las reglas de CU-06."""


def _nombre(valor: str) -> str:
    nombre = valor.strip()
    if not 1 <= len(nombre) <= LONGITUD_MAXIMA_NOMBRE:
        raise CampaniaInvalidaError(
            f"El nombre de la campana debe tener entre 1 y {LONGITUD_MAXIMA_NOMBRE} caracteres."
        )
    return nombre


def _descripcion(valor: str | None) -> str | None:
    if valor is None:
        return None
    descripcion = valor.strip()
    if len(descripcion) > LONGITUD_MAXIMA_DESCRIPCION:
        raise CampaniaInvalidaError(
            f"La descripcion no puede superar {LONGITUD_MAXIMA_DESCRIPCION} caracteres."
        )
    return descripcion or None


def _niveles(valores: Iterable[NivelRiesgo]) -> tuple[NivelRiesgo, ...]:
    recibidos = set(valores)
    if not recibidos:
        raise CampaniaInvalidaError("Elija al menos un nivel de riesgo.")
    return tuple(nivel for nivel in ORDEN_NIVELES if nivel in recibidos)


def _planes(valores: Iterable[Plan]) -> tuple[Plan, ...]:
    recibidos = set(valores)
    if not recibidos:
        raise CampaniaInvalidaError("Elija al menos un plan.")
    if not recibidos <= PLANES_CAMPANIA:
        raise CampaniaInvalidaError("Una campana no puede aplicar al plan DIARIO.")
    return tuple(plan for plan in ORDEN_PLANES if plan in recibidos)


def _prioridad(valor: int) -> int:
    if not PRIORIDAD_MINIMA <= valor <= PRIORIDAD_MAXIMA:
        raise CampaniaInvalidaError(
            f"La prioridad debe ser un numero entre {PRIORIDAD_MINIMA} y {PRIORIDAD_MAXIMA}."
        )
    return valor


@dataclass(frozen=True, slots=True)
class DatosCampania:
    """Datos editables de una campana, ya validados y normalizados (usar ``crear``)."""

    nombre: str
    descripcion: str | None
    niveles_riesgo: tuple[NivelRiesgo, ...]
    planes: tuple[Plan, ...]
    prioridad: int

    @classmethod
    def crear(
        cls,
        *,
        nombre: str,
        descripcion: str | None,
        niveles: Iterable[NivelRiesgo],
        planes: Iterable[Plan],
        prioridad: int,
    ) -> Self:
        """Valida y normaliza; lanza ``CampaniaInvalidaError`` si algo no cumple CU-06."""
        return cls(
            nombre=_nombre(nombre),
            descripcion=_descripcion(descripcion),
            niveles_riesgo=_niveles(niveles),
            planes=_planes(planes),
            prioridad=_prioridad(prioridad),
        )


def es_compatible(
    activa: bool,
    niveles: Iterable[NivelRiesgo],
    planes: Iterable[Plan],
    nivel: NivelRiesgo,
    plan: Plan,
) -> bool:
    """``True`` si la campana se puede sugerir a un socio con ese nivel y plan (RN-07.x).

    Solo campanas activas cuyo conjunto de niveles y de planes incluye los del socio; un
    plan ``DIARIO`` nunca tiene campanas.
    """
    if not activa or plan not in PLANES_CAMPANIA:
        return False
    return nivel in set(niveles) and plan in set(planes)


def clave_orden(prioridad: int, nombre: str, campania_id: int) -> tuple[int, str, int]:
    """Orden de las sugerencias: prioridad, nombre sin distinguir mayusculas e id."""
    return (prioridad, nombre.lower(), campania_id)
