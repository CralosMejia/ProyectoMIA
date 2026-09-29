"""Ciclos de membresia y etiqueta de no renovacion (notebook MVP, secciones 1.2 y 5.1-5.5).

La fecha de corte se deriva de los meses de las hojas leidas (nunca del reloj del sistema).
Un ciclo es evaluable solo si su ventana ``[T, T+30]`` cabe completa antes del corte
(RN-01.5, caso del tutor); las reglas de ``clasificar`` siguen el orden exacto del notebook.
"""

import calendar
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum, unique

from app.domain.common.enums import EstadoCiclo, Plan
from app.domain.common.exceptions import DomainError
from app.domain.historico.registro import RegistroHistorico

FECHA_MINIMA_RAZONABLE = date(2024, 12, 1)
DIAS_OBSERVACION = 30
DIAS_RENOVACION_ANTICIPADA = 0
DURACION_MINIMA_PLAUSIBLE = 21  # duraciones <= 21 dias se excluyen
DURACION_MAXIMA_PLAUSIBLE = 400  # duraciones > 400 dias se excluyen


class SinMesesDisponiblesError(DomainError, ValueError):
    """No hay meses de hojas a partir de los cuales calcular la fecha de corte."""


@unique
class MotivoCiclo(StrEnum):
    SIN_VENCIMIENTO = "SIN_VENCIMIENTO"
    FECHA_FUERA_DE_RANGO = "FECHA_FUERA_DE_RANGO"
    VENCIMIENTO_POSTERIOR_AL_CORTE = "VENCIMIENTO_POSTERIOR_AL_CORTE"
    PASE_DIARIO = "PASE_DIARIO"
    DURACION_IMPLAUSIBLE = "DURACION_IMPLAUSIBLE"
    VENTANA_INCOMPLETA = "VENTANA_INCOMPLETA"
    EVALUABLE = "EVALUABLE"


@dataclass(frozen=True, slots=True)
class CicloEtiquetado:
    registro: RegistroHistorico
    estado: EstadoCiclo
    motivo: MotivoCiclo
    no_renovo: bool | None
    fecha_renovacion: date | None


def fecha_corte(meses_hoja: Iterable[date]) -> date:
    """Ultimo dia del mes maximo entre los meses de las hojas."""
    ultimo = max(meses_hoja, default=None)
    if ultimo is None:
        raise SinMesesDisponiblesError("No hay meses de hojas para calcular la fecha de corte.")
    return date(ultimo.year, ultimo.month, calendar.monthrange(ultimo.year, ultimo.month)[1])


def clasificar(registro: RegistroHistorico, corte: date) -> tuple[EstadoCiclo, MotivoCiclo]:
    """Estado del ciclo segun ``motivo_estado_ciclo`` (seccion 5.3); gana la primera regla."""
    vence = registro.fecha_vencimiento
    if vence is None:
        return EstadoCiclo.EXCLUIDO, MotivoCiclo.SIN_VENCIMIENTO
    if vence < FECHA_MINIMA_RAZONABLE:
        return EstadoCiclo.EXCLUIDO, MotivoCiclo.FECHA_FUERA_DE_RANGO
    if vence > corte:
        return EstadoCiclo.EXCLUIDO, MotivoCiclo.VENCIMIENTO_POSTERIOR_AL_CORTE
    if registro.plan is Plan.DIARIO:
        return EstadoCiclo.EXCLUIDO, MotivoCiclo.PASE_DIARIO
    duracion = registro.duracion_dias
    if duracion is not None and (
        duracion <= DURACION_MINIMA_PLAUSIBLE or duracion > DURACION_MAXIMA_PLAUSIBLE
    ):
        return EstadoCiclo.EXCLUIDO, MotivoCiclo.DURACION_IMPLAUSIBLE
    if vence + timedelta(days=DIAS_OBSERVACION) > corte:
        return EstadoCiclo.PENDIENTE, MotivoCiclo.VENTANA_INCOMPLETA
    return EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE


def etiquetar(registros: Sequence[RegistroHistorico], corte: date) -> list[CicloEtiquetado]:
    """Clasifica cada registro y, si es evaluable, busca su renovacion (seccion 5.5).

    Renovacion: otra membresia no ``DIARIO`` del mismo socio con ``fecha_actividad`` en
    ``[T - DIAS_RENOVACION_ANTICIPADA, T + DIAS_OBSERVACION]``. Solo se excluye el propio
    registro (por posicion), de modo que un duplicado exacto si cuenta, como en el notebook.
    """
    actividades: defaultdict[str, list[tuple[int, date]]] = defaultdict(list)
    for posicion, registro in enumerate(registros):
        if registro.plan is not Plan.DIARIO:
            actividades[registro.identidad].append((posicion, registro.fecha_actividad))

    ciclos: list[CicloEtiquetado] = []
    for posicion, registro in enumerate(registros):
        estado, motivo = clasificar(registro, corte)
        no_renovo: bool | None = None
        fecha_renovacion: date | None = None
        if estado is EstadoCiclo.EVALUABLE and registro.fecha_vencimiento is not None:
            vence = registro.fecha_vencimiento
            inicio = vence - timedelta(days=DIAS_RENOVACION_ANTICIPADA)
            fin = vence + timedelta(days=DIAS_OBSERVACION)
            fecha_renovacion = min(
                (
                    actividad
                    for otra, actividad in actividades.get(registro.identidad, [])
                    if otra != posicion and inicio <= actividad <= fin
                ),
                default=None,
            )
            no_renovo = fecha_renovacion is None
        ciclos.append(CicloEtiquetado(registro, estado, motivo, no_renovo, fecha_renovacion))
    return ciclos
