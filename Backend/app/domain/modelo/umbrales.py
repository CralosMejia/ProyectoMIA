"""Umbrales de riesgo por percentiles y nivel de riesgo (CU-05, decision (d) de R-004).

- Los umbrales salen de los scores del modelo nuevo sobre los evaluables de los ultimos
  ``n`` meses de vencimiento con resultado conocido.
- Percentil lineal (interpolacion entre vecinos), calculado en ``Decimal``: con los
  porcentajes (ALTO, MEDIO, BAJO) = (20, 30, 50), ``alto`` = P80 y ``medio`` = P50.
- ALTO si ``score >= alto``; MEDIO si ``score >= medio``; si no, BAJO.
- Los umbrales se cuantizan a 8 decimales (``NUMERIC(10,8)``).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from app.domain.common.enums import NivelRiesgo
from app.domain.common.exceptions import DomainError
from app.domain.modelo.variables import CicloModelo

PORCENTAJES_POR_DEFECTO: tuple[int, int, int] = (20, 30, 50)
MESES_RECIENTES = 3
_OCHO_DECIMALES = Decimal("0.00000001")


class SinScoresError(DomainError, ValueError):
    """No hay scores o ciclos evaluables con los que calcular los umbrales."""


@dataclass(frozen=True, slots=True)
class Umbrales:
    alto: Decimal
    medio: Decimal
    porcentajes: Mapping[str, int]


def _mes(ciclo: CicloModelo) -> tuple[int, int]:
    vence = ciclo.fecha_vencimiento
    if vence is None:
        raise ValueError("El ciclo necesita fecha de vencimiento.")
    return vence.year, vence.month


def meses_recientes_con_resultado(
    ciclos: Sequence[CicloModelo], n: int = MESES_RECIENTES
) -> list[CicloModelo]:
    """Evaluables (no excluidos y con resultado) de los ``n`` meses de vencimiento mas recientes.

    Conserva el orden de entrada.
    """
    if n < 1:
        raise ValueError("n debe ser al menos 1.")
    evaluables = [
        c
        for c in ciclos
        if not c.excluido and c.no_renovo is not None and c.fecha_vencimiento is not None
    ]
    meses = sorted({_mes(c) for c in evaluables})
    if not meses:
        raise SinScoresError("No hay ciclos evaluables para calcular los umbrales.")
    recientes = set(meses[-n:])
    return [c for c in evaluables if _mes(c) in recientes]


def _percentil(ordenados: Sequence[Decimal], q: int) -> Decimal:
    """Percentil lineal: ``h = (N - 1) * q / 100`` e interpolacion entre vecinos."""
    h = Decimal(len(ordenados) - 1) * q / 100
    inferior = int(h)
    superior = min(inferior + 1, len(ordenados) - 1)
    fraccion = h - inferior
    valor = ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * fraccion
    return valor.quantize(_OCHO_DECIMALES, rounding=ROUND_HALF_EVEN)


def calcular_umbrales(
    scores: Sequence[Decimal], porcentajes: tuple[int, int, int] = PORCENTAJES_POR_DEFECTO
) -> Umbrales:
    """``alto`` = percentil ``100 - p_alto``; ``medio`` = percentil ``p_bajo``."""
    p_alto, p_medio, p_bajo = porcentajes
    if min(porcentajes) < 0 or p_alto + p_medio + p_bajo != 100:
        raise ValueError("Los porcentajes deben ser no negativos y sumar 100.")
    if not scores:
        raise SinScoresError("No hay scores para calcular los umbrales.")
    ordenados = sorted(scores)
    return Umbrales(
        alto=_percentil(ordenados, 100 - p_alto),
        medio=_percentil(ordenados, p_bajo),
        porcentajes={
            NivelRiesgo.ALTO.value: p_alto,
            NivelRiesgo.MEDIO.value: p_medio,
            NivelRiesgo.BAJO.value: p_bajo,
        },
    )


def nivel_de(score: Decimal, umbrales: Umbrales) -> NivelRiesgo:
    """Un score igual a un umbral queda en el nivel superior."""
    if score >= umbrales.alto:
        return NivelRiesgo.ALTO
    if score >= umbrales.medio:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO
