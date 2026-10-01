"""Metricas del modelo calculadas en el dominio (CU-02, decision (d) de R-011).

``pr_auc`` es la *average precision* de ``sklearn.metrics.average_precision_score``:
``AP = sum_n (R_n - R_{n-1}) * P_n`` recorriendo un umbral por cada score distinto, de mayor
a menor (los empates entran juntos en el mismo umbral). Todo el calculo es en ``Decimal``;
el resultado se cuantiza a 8 decimales (``NUMERIC(10,8)``).
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import groupby

from app.domain.common.exceptions import DomainError

_OCHO_DECIMALES = Decimal("0.00000001")


class MetricaInvalidaError(DomainError, ValueError):
    """Los datos no permiten calcular la metrica (longitudes, etiquetas o sin positivos)."""


def pr_auc(scores: Sequence[Decimal], etiquetas: Sequence[int]) -> Decimal:
    """Average precision de ``scores`` frente a ``etiquetas`` (1 = clase positiva)."""
    if len(scores) != len(etiquetas):
        raise MetricaInvalidaError("Los scores y las etiquetas deben tener la misma longitud.")
    if any(e not in (0, 1) for e in etiquetas):
        raise MetricaInvalidaError("Las etiquetas deben ser 0 o 1.")
    positivos = sum(etiquetas)
    if positivos == 0:
        raise MetricaInvalidaError("No hay casos positivos para calcular la PR-AUC.")

    ordenados = sorted(zip(scores, etiquetas, strict=True), key=lambda par: par[0], reverse=True)
    suma = Decimal(0)
    verdaderos = 0
    vistos = 0
    for _, grupo in groupby(ordenados, key=lambda par: par[0]):
        etiquetas_grupo = [e for _, e in grupo]
        nuevos = sum(etiquetas_grupo)
        verdaderos += nuevos
        vistos += len(etiquetas_grupo)
        if nuevos:
            suma += Decimal(nuevos) * Decimal(verdaderos) / Decimal(vistos)
    return (suma / Decimal(positivos)).quantize(_OCHO_DECIMALES, rounding=ROUND_HALF_EVEN)
