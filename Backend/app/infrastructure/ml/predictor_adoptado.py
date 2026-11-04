"""Predictor del composition root (R-020 T4, definicion (d); M06).

Entrena siempre la Regresion Logistica, el modelo adoptado. Al predecir lee el ``formato`` del
artefacto guardado en ``modelos.artefacto``: 2 -> Regresion Logistica, 1 -> Random Forest
(compatibilidad de lectura: una base con un v1 RF sigue generando listas hasta que se adopte
la RL). Cualquier otro contenido -> ``ValueError`` con un mensaje sin datos.

El artefacto se deserializa una sola vez por llamada y solo desde ``modelos.artefacto``
(ADR-003): nunca se cargan rutas ni artefactos de otra procedencia.
"""

import io
from collections.abc import Sequence

import joblib

from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.infrastructure.ml import random_forest, regresion_logistica
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.ml.regresion_logistica import LogisticRegressionPredictor


class PredictorAdoptado:
    """``PredictorModel`` que entrena RL y predice con el algoritmo del artefacto."""

    def __init__(self) -> None:
        self._regresion = LogisticRegressionPredictor()
        self._bosque = RandomForestPredictor()

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        return self._regresion.train(features, labels, numericas, categoricas, referencia)

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        if not features:
            return []
        contenido = joblib.load(io.BytesIO(artefacto))
        formato = contenido.get("formato") if isinstance(contenido, dict) else None
        if formato == regresion_logistica.FORMATO_ARTEFACTO:
            modelo_rl = regresion_logistica.artefacto_desde_contenido(contenido)
            return self._regresion.predecir_con(modelo_rl, features)
        if formato == random_forest.FORMATO_ARTEFACTO:
            modelo_rf = random_forest.artefacto_desde_contenido(contenido)
            return self._bosque.predecir_con(modelo_rf, features)
        raise ValueError("El artefacto no tiene el formato esperado del modelo.")
