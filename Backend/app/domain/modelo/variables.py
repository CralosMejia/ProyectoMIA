"""Variables del modelo en T-30 (notebook MVP, secciones 6.1 y 7.2-7.4).

Replica fiel del notebook, solo con la libreria estandar:

- Historial previo: ciclos **no excluidos** del mismo socio con ``fecha_actividad``
  estrictamente menor que la del ciclo actual (el propio ciclo nunca cuenta).
- ``monto_historico``: suma de los montos previos, con ``None`` como 0.
- ``dias_desde_ultima_membresia``: ``None`` si no hay previos.
- ``antiguedad_dias``: ``max(0, (vencimiento - 30) - primera_actividad)``.
- ``monto_actual``: monto; si falta, la mediana del plan y despues la mediana general.
- ``duracion_modelo``: duracion; si falta, ``DURACION_ESTANDAR`` del plan.
- Categoricas como ``str``: ``mes_vencimiento`` = ``"AAAA-MM"``, ``inicio_aproximado`` =
  ``"True"``/``"False"``, ``plan`` y ``forma_pago`` por su ``.value``.

Ningun valor devuelto es ``float``: los montos son ``Decimal`` y la conversion a ``float``
ocurre solo en el adaptador del modelo (infraestructura).
"""

import statistics
from collections import defaultdict
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.common.enums import FormaPago, Plan

DIAS_ANTES_PREDICCION = 30  # T-30: momento en que se estima el riesgo

VARIABLES_NUMERICAS: tuple[str, ...] = (
    "ciclos_previos",
    "antiguedad_dias",
    "duracion_modelo",
    "monto_actual",
    "monto_historico",
    "dias_desde_ultima_membresia",
)
VARIABLES_CATEGORICAS: tuple[str, ...] = (
    "plan",
    "forma_pago",
    "mes_vencimiento",
    "inicio_aproximado",
)

DURACION_ESTANDAR: Mapping[Plan, int] = {
    Plan.MENSUAL: 30,
    Plan.TRIMESTRAL: 90,
    Plan.SEMESTRAL: 180,
    Plan.ANUAL: 365,
    Plan.OTRO: 30,
}

type ValorVariable = Decimal | int | str | None


@dataclass(frozen=True, slots=True)
class CicloModelo:
    """Ciclo de membresia tal como lo necesita el modelo (sin datos personales).

    ``clave_socio`` agrupa los ciclos de un mismo socio; ``ref`` identifica el ciclo (id de
    membresia o referencia de origen) y solo se usa para distinguirlo del resto.
    ``no_renovo`` es ``None`` mientras el resultado no se conoce (pendiente o excluido).
    """

    clave_socio: str
    ref: Hashable
    plan: Plan
    forma_pago: FormaPago
    fecha_actividad: date
    fecha_vencimiento: date | None
    duracion_dias: int | None
    monto_cobrado: Decimal | None
    inicio_aproximado: bool
    excluido: bool
    no_renovo: bool | None


@dataclass(frozen=True, slots=True)
class MedianasMonto:
    """Medianas de ``monto_cobrado`` de los ciclos no excluidos; se guardan con el modelo."""

    por_plan: Mapping[Plan, Decimal]
    general: Decimal | None


@dataclass(frozen=True, slots=True)
class PeriodoReferencia:
    """Periodo de vencimientos ``[desde, hasta)`` que sirve de referencia a los factores.

    El notebook (13.3) toma como socio "tipico" las medianas y modas de los ciclos de
    entrenamiento con vencimiento anterior a 2026-01-01 (los de 2025). Es un parametro para
    que un reentrenamiento futuro pueda moverlo.
    """

    desde: date
    hasta: date

    def __post_init__(self) -> None:
        if self.hasta <= self.desde:
            raise ValueError("El periodo de referencia debe terminar despues de empezar.")

    def contiene(self, ciclo: CicloModelo) -> bool:
        vence = ciclo.fecha_vencimiento
        return vence is not None and self.desde <= vence < self.hasta


PERIODO_REFERENCIA_FACTORES = PeriodoReferencia(desde=date(2025, 1, 1), hasta=date(2026, 1, 1))


def calcular_medianas(ciclos: Iterable[CicloModelo]) -> MedianasMonto:
    """Mediana por plan y general de los montos conocidos de los ciclos no excluidos."""
    por_plan: defaultdict[Plan, list[Decimal]] = defaultdict(list)
    todos: list[Decimal] = []
    for ciclo in ciclos:
        if ciclo.excluido or ciclo.monto_cobrado is None:
            continue
        por_plan[ciclo.plan].append(ciclo.monto_cobrado)
        todos.append(ciclo.monto_cobrado)
    return MedianasMonto(
        por_plan={plan: statistics.median(montos) for plan, montos in por_plan.items()},
        general=statistics.median(todos) if todos else None,
    )


def _monto_actual(ciclo: CicloModelo, medianas: MedianasMonto) -> Decimal | None:
    if ciclo.monto_cobrado is not None:
        return ciclo.monto_cobrado
    return medianas.por_plan.get(ciclo.plan, medianas.general)


def construir_variables(
    ciclo: CicloModelo, historial: Iterable[CicloModelo], medianas: MedianasMonto
) -> dict[str, ValorVariable]:
    """Variables del ciclo en T-30, en el orden ``VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS``.

    ``historial`` puede contener ciclos de otros socios, excluidos o el propio ciclo: aqui se
    filtran con las reglas del notebook.
    """
    vence = ciclo.fecha_vencimiento
    if vence is None:
        raise ValueError("El ciclo necesita fecha de vencimiento para construir variables.")

    previos = [
        otro
        for otro in historial
        if otro is not ciclo
        and otro.clave_socio == ciclo.clave_socio
        and not otro.excluido
        and otro.fecha_actividad < ciclo.fecha_actividad
    ]
    monto_historico = sum(
        (p.monto_cobrado for p in previos if p.monto_cobrado is not None), Decimal(0)
    )
    if previos:
        ultima = max(p.fecha_actividad for p in previos)
        dias_desde_ultima: int | None = (ciclo.fecha_actividad - ultima).days
        primera = min(min(p.fecha_actividad for p in previos), ciclo.fecha_actividad)
    else:
        dias_desde_ultima = None
        primera = ciclo.fecha_actividad
    fecha_prediccion = vence - timedelta(days=DIAS_ANTES_PREDICCION)
    duracion = (
        ciclo.duracion_dias
        if ciclo.duracion_dias is not None
        else DURACION_ESTANDAR.get(ciclo.plan)
    )

    return {
        "ciclos_previos": len(previos),
        "antiguedad_dias": max(0, (fecha_prediccion - primera).days),
        "duracion_modelo": duracion,
        "monto_actual": _monto_actual(ciclo, medianas),
        "monto_historico": monto_historico,
        "dias_desde_ultima_membresia": dias_desde_ultima,
        "plan": ciclo.plan.value,
        "forma_pago": ciclo.forma_pago.value,
        "mes_vencimiento": f"{vence.year:04d}-{vence.month:02d}",
        "inicio_aproximado": str(ciclo.inicio_aproximado),
    }


def ordenar_para_entrenamiento(ciclos: Sequence[CicloModelo]) -> list[CicloModelo]:
    """Orden del notebook: (socio, actividad, vencimiento); estable ante empates.

    El bootstrap del bosque aleatorio depende de este orden. Un vencimiento ausente va al
    final, como en el notebook.
    """
    return sorted(
        ciclos,
        key=lambda c: (
            c.clave_socio,
            c.fecha_actividad,
            c.fecha_vencimiento is None,
            c.fecha_vencimiento or date.min,
        ),
    )
