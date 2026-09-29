"""Puerto del modelo predictivo.

El dominio define el contrato; la implementacion (scikit-learn, joblib) vive en
``infrastructure``. Aqui solo se usa la libreria estandar.

``float`` esta permitido en este modulo porque ``score`` y los valores de ``features`` son
entradas y probabilidades del modelo, no valores exactos de negocio: la conversion desde
``Decimal`` ocurre en el borde con el modelo (04 §5.7).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

type FeatureRow = Mapping[str, float | int | str | None]


@dataclass(frozen=True, slots=True)
class TrainedModel:
    """Resultado de un entrenamiento: artefacto serializado y su metadata tecnica."""

    artefacto: bytes
    metadata_tecnica: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Prediction:
    """Probabilidad estimada para una fila y los factores que mas la explican."""

    score: float
    factores_principales: tuple[str, ...]


@runtime_checkable
class PredictorModel(Protocol):
    """Entrena y aplica el modelo de riesgo de abandono."""

    def train(self, features: Sequence[FeatureRow], labels: Sequence[int]) -> TrainedModel:
        """Entrena con una fila de ``features`` por etiqueta y devuelve el artefacto."""
        ...

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        """Aplica el artefacto a cada fila; devuelve una prediccion por fila, en orden."""
        ...
