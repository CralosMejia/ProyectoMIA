"""Cartera a vencer, renovaciones anticipadas y priorizacion (notebook MVP 13.8, CU-04).

- Cartera: vencimiento en ``(fecha, fecha + horizonte]``, sin ``DIARIO`` y sin duracion
  ``<= 21`` o ``> 400`` (una duracion desconocida pasa).
- Ya renovo: otra membresia no ``DIARIO`` del mismo socio con ``fecha_actividad`` mayor.
- Priorizacion: score descendente; en empate, vencimiento ascendente y despues
  ``membresia_id`` ascendente (decision (e) del plan). Una fila por socio: la primera en ese
  orden, es decir, la de mayor score.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.common.enums import Plan
from app.domain.historico.ciclos import DURACION_MAXIMA_PLAUSIBLE, DURACION_MINIMA_PLAUSIBLE
from app.domain.modelo.variables import CicloModelo


@dataclass(frozen=True, slots=True)
class CicloPuntuado:
    """Ciclo de la cartera con el score que le dio el modelo."""

    membresia_id: int
    clave_socio: str
    fecha_vencimiento: date
    score: Decimal
    factores_principales: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FilaPriorizada:
    ciclo: CicloPuntuado
    prioridad: int
    dentro_top_k: bool
    dias_para_vencer: int


def seleccionar_cartera(
    ciclos: Iterable[CicloModelo], fecha: date, horizonte: int
) -> list[CicloModelo]:
    """Ciclos que vencen en ``(fecha, fecha + horizonte]``, en el orden de entrada."""
    if horizonte < 1:
        raise ValueError("El horizonte debe ser de al menos 1 dia.")
    fin = fecha + timedelta(days=horizonte)
    return [
        ciclo
        for ciclo in ciclos
        if ciclo.fecha_vencimiento is not None
        and fecha < ciclo.fecha_vencimiento <= fin
        and ciclo.plan is not Plan.DIARIO
        and not (
            ciclo.duracion_dias is not None
            and (
                ciclo.duracion_dias <= DURACION_MINIMA_PLAUSIBLE
                or ciclo.duracion_dias > DURACION_MAXIMA_PLAUSIBLE
            )
        )
    ]


def ya_renovo(ciclo: CicloModelo, actividades_del_socio: Iterable[CicloModelo]) -> bool:
    """``True`` si el socio registro otra membresia no ``DIARIO`` con actividad posterior."""
    return any(
        otra is not ciclo
        and otra.ref != ciclo.ref
        and otra.clave_socio == ciclo.clave_socio
        and otra.plan is not Plan.DIARIO
        and otra.fecha_actividad > ciclo.fecha_actividad
        for otra in actividades_del_socio
    )


def priorizar(puntuados: Sequence[CicloPuntuado], top_k: int, fecha: date) -> list[FilaPriorizada]:
    """Una fila por socio, ordenada por riesgo, con ``prioridad`` 1..n y marca de top K."""
    if top_k < 1:
        raise ValueError("top_k debe ser al menos 1.")
    ordenados = sorted(puntuados, key=lambda p: (-p.score, p.fecha_vencimiento, p.membresia_id))
    vistos: set[str] = set()
    filas: list[FilaPriorizada] = []
    for p in ordenados:
        if p.clave_socio in vistos:
            continue
        vistos.add(p.clave_socio)
        prioridad = len(filas) + 1
        filas.append(
            FilaPriorizada(
                ciclo=p,
                prioridad=prioridad,
                dentro_top_k=prioridad <= top_k,
                dias_para_vencer=(p.fecha_vencimiento - fecha).days,
            )
        )
    return filas
