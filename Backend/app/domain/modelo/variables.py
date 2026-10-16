"""Variables del modelo en T-30 (notebook MVP, secciones 6.1 y 7.2-7.4).

Replica fiel del notebook, solo con la libreria estandar:

- Historial previo (corte T-30, mejora M01): ciclos **no excluidos** del mismo socio con
  ``fecha_actividad`` estrictamente menor que la del ciclo actual **y** menor o igual que
  ``T-30`` (el propio ciclo nunca cuenta). Ningun registro con actividad posterior a T-30
  cambia una variable. Los campos del propio ciclo (plan, forma de pago, monto, duracion,
  vencimiento e ``inicio_aproximado``) son el objeto de la prediccion y se admiten.
- ``monto_historico``: suma de los montos previos, con ``None`` como 0.
- ``dias_desde_ultima_membresia``: ``None`` si no hay previos.
- ``antiguedad_dias``: ``max(0, (vencimiento - 30) - primera_actividad)``.
- ``monto_actual``: monto; si falta, la mediana del plan y despues la mediana general. Las
  medianas las provee quien entrena (solo con sus ciclos de entrenamiento) y se aplican tal
  cual a validacion, comparacion y prediccion.
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


@dataclass(frozen=True, slots=True)
class ConjuntoVariables:
    """Variables con que se entrena un modelo: subconjunto de las que ``construir_variables``
    devuelve siempre (el artefacto guarda las suyas y selecciona sus columnas al predecir).
    """

    numericas: tuple[str, ...]
    categoricas: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.numericas and not self.categoricas:
            raise ValueError("El conjunto de variables del modelo no puede estar vacio.")
        if not set(self.numericas) <= set(VARIABLES_NUMERICAS) or not set(self.categoricas) <= set(
            VARIABLES_CATEGORICAS
        ):
            raise ValueError("El conjunto de variables del modelo tiene variables desconocidas.")
        if len(set(self.numericas)) != len(self.numericas) or len(set(self.categoricas)) != len(
            self.categoricas
        ):
            raise ValueError("El conjunto de variables del modelo repite variables.")

    def sin(self, *variables: str) -> "ConjuntoVariables":
        """El mismo conjunto sin ``variables`` (conserva el orden)."""
        return ConjuntoVariables(
            numericas=tuple(v for v in self.numericas if v not in variables),
            categoricas=tuple(v for v in self.categoricas if v not in variables),
        )


VARIABLES_EXCLUIBLES_M01: tuple[str, ...] = ("forma_pago", "inicio_aproximado")
"""Variables que la variante de M01 (decision (d) del plan R-015) deja fuera."""

CONJUNTO_COMPLETO = ConjuntoVariables(VARIABLES_NUMERICAS, VARIABLES_CATEGORICAS)
CONJUNTO_SIN_FORMA_PAGO_NI_INICIO = CONJUNTO_COMPLETO.sin(*VARIABLES_EXCLUIBLES_M01)

CONJUNTO_MODELO: ConjuntoVariables = CONJUNTO_SIN_FORMA_PAGO_NI_INICIO
"""Conjunto con que la app entrena (CU-03, CU-02 y ``adoptar-modelo``).

El que eligio el notebook M01 (seccion 12.11, regla (d) de R-015): la variante sin
``forma_pago`` ni ``inicio_aproximado`` (``salidas/m01/despues/decision_variante.json``).
"""
VARIABLES_NUMERICAS_MODELO: tuple[str, ...] = CONJUNTO_MODELO.numericas
VARIABLES_CATEGORICAS_MODELO: tuple[str, ...] = CONJUNTO_MODELO.categoricas

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

    El notebook (13.3) toma como socio "tipico" las medianas y modas de ``X_train``: con los
    margenes de M01, la particion de entrenamiento = vencimiento ``< 2026-01-01 - 30 d``
    (hasta el 2025-12-01 inclusive) y sin limite inferior (``asignar_particion``, 7.3). Es un
    parametro para que un reentrenamiento futuro pueda moverlo.
    """

    desde: date
    hasta: date

    def __post_init__(self) -> None:
        if self.hasta <= self.desde:
            raise ValueError("El periodo de referencia debe terminar despues de empezar.")

    def contiene(self, ciclo: CicloModelo) -> bool:
        vence = ciclo.fecha_vencimiento
        return vence is not None and self.desde <= vence < self.hasta


PERIODO_REFERENCIA_FACTORES = PeriodoReferencia(desde=date.min, hasta=date(2025, 12, 2))


def calcular_medianas(ciclos: Iterable[CicloModelo]) -> MedianasMonto:
    """Mediana por plan y general de los montos conocidos de los ciclos no excluidos.

    Solo con los ciclos de entrenamiento (decision (b) de M01): quien llama pasa exactamente
    esos ciclos y las medianas resultantes se aplican sin recalcular al resto.
    """
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

    ``historial`` puede contener ciclos de otros socios, excluidos, posteriores a T-30 o el
    propio ciclo: aqui se filtran con las reglas del notebook y el corte T-30. Devuelve
    siempre las 10 variables; cada modelo usa las de su ``ConjuntoVariables``.
    """
    vence = ciclo.fecha_vencimiento
    if vence is None:
        raise ValueError("El ciclo necesita fecha de vencimiento para construir variables.")
    fecha_prediccion = vence - timedelta(days=DIAS_ANTES_PREDICCION)

    previos = [
        otro
        for otro in historial
        if otro is not ciclo
        and otro.clave_socio == ciclo.clave_socio
        and not otro.excluido
        and otro.fecha_actividad < ciclo.fecha_actividad
        and otro.fecha_actividad <= fecha_prediccion
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
