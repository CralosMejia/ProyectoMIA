"""Puerto del modelo predictivo.

El dominio define el contrato; la implementacion (scikit-learn, joblib) vive en
``infrastructure`` (ADR-002). Aqui solo se usa la libreria estandar.

Los valores exactos cruzan el puerto como ``Decimal``: la conversion ``Decimal -> float``
ocurre solo dentro del adaptador, en el borde con la libreria de ML (04 §5.7), y el score
vuelve como ``Decimal`` cuantizado a 8 decimales (``NUMERIC(10,8)``).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

type FeatureRow = Mapping[str, Decimal | int | str | None]

_CERO = Decimal(0)
_UNO = Decimal(1)


@dataclass(frozen=True, slots=True)
class TrainedModel:
    """Resultado de un entrenamiento: artefacto serializado y su metadata tecnica."""

    artefacto: bytes
    metadata_tecnica: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class Prediction:
    """Score estimado para una fila (``[0, 1]``) y los factores que mas lo elevan."""

    score: Decimal
    factores_principales: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _CERO <= self.score <= _UNO:
            raise ValueError("El score debe estar entre 0 y 1.")


@runtime_checkable
class PredictorModel(Protocol):
    """Entrena y aplica el modelo de riesgo de no renovacion."""

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        """Entrena con una fila de ``features`` por etiqueta, en el orden recibido.

        ``numericas`` y ``categoricas`` nombran las columnas de cada fila. ``referencia`` son
        las filas cuyo socio "tipico" (medianas y modas) sirve para explicar los factores;
        ``None`` o vacio usa todas las filas de entrenamiento.
        """
        ...

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        """Aplica el artefacto a cada fila; devuelve una prediccion por fila, en orden."""
        ...
