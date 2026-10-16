"""Umbrales de riesgo fijos del notebook y nivel de riesgo (CU-05, R-015 T11).

- Cortes fijos del notebook MVP (seccion 13.2), decision del usuario en R-015: ALTO si
  ``score >= 0,70``; MEDIO si ``score >= 0,50``; si no, BAJO. Sustituyen a los percentiles
  20/30/50 sobre los 3 meses recientes (decision (d) de R-004), que dejan de calcularse.
- ``porcentajes`` es informativo: el porcentaje (entero, redondeo bancario) de los scores
  recibidos (los evaluables de los 3 meses de vencimiento mas recientes) que cae en cada
  nivel con esos cortes. Se guarda en ``modelos.porcentajes_umbral`` (misma forma que antes:
  ``{"ALTO": n, "MEDIO": n, "BAJO": n}``).
- Un score igual a un umbral queda en el nivel superior.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from app.domain.common.enums import NivelRiesgo
from app.domain.common.exceptions import DomainError
from app.domain.modelo.variables import CicloModelo

UMBRAL_ALTO = Decimal("0.70")
UMBRAL_MEDIO = Decimal("0.50")
MESES_RECIENTES = 3


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


def umbrales_fijos(scores: Sequence[Decimal]) -> Umbrales:
    """Cortes fijos del notebook con la reparticion observada de ``scores`` por nivel."""
    if not scores:
        raise SinScoresError("No hay scores para calcular los umbrales.")
    umbrales = Umbrales(alto=UMBRAL_ALTO, medio=UMBRAL_MEDIO, porcentajes={})
    conteo = dict.fromkeys(NivelRiesgo, 0)
    for score in scores:
        conteo[nivel_de(score, umbrales)] += 1
    total = Decimal(len(scores))
    return Umbrales(
        alto=UMBRAL_ALTO,
        medio=UMBRAL_MEDIO,
        porcentajes={
            nivel.value: int(
                (Decimal(conteo[nivel]) * 100 / total).quantize(Decimal(1), ROUND_HALF_EVEN)
            )
            for nivel in (NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO)
        },
    )


def nivel_de(score: Decimal, umbrales: Umbrales) -> NivelRiesgo:
    """Un score igual a un umbral queda en el nivel superior."""
    if score >= umbrales.alto:
        return NivelRiesgo.ALTO
    if score >= umbrales.medio:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO
