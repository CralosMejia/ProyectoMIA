from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError

import pytest

from app.domain.common.predictor import Prediction, PredictorModel, TrainedModel

pytestmark = pytest.mark.unit

Features = Sequence[Mapping[str, float | int | str | None]]


class FakePredictor:
    """Doble minimo del puerto PredictorModel (sin librerias de ML)."""

    def train(self, features: Features, labels: Sequence[int]) -> TrainedModel:
        return TrainedModel(artefacto=b"modelo", metadata_tecnica={"filas": str(len(labels))})

    def predict(self, artefacto: bytes, features: Features) -> list[Prediction]:
        return [Prediction(score=0.5, factores_principales=("asistencias",)) for _ in features]


class TrainOnly:
    def train(self, features: Features, labels: Sequence[int]) -> TrainedModel:
        return TrainedModel(artefacto=b"", metadata_tecnica={})


def test_isinstance_with_minimal_double_returns_true() -> None:
    # La anotacion hace que mypy verifique la compatibilidad estructural del doble.
    modelo: PredictorModel = FakePredictor()

    assert isinstance(modelo, PredictorModel)


def test_isinstance_without_predict_returns_false() -> None:
    assert not isinstance(TrainOnly(), PredictorModel)


def test_train_and_predict_through_port_return_value_objects() -> None:
    modelo: PredictorModel = FakePredictor()
    features: Features = [{"asistencias": 12, "plan": "MENSUAL", "monto": None}]

    entrenado = modelo.train(features, [1])
    predicciones = modelo.predict(entrenado.artefacto, features)

    assert entrenado == TrainedModel(artefacto=b"modelo", metadata_tecnica={"filas": "1"})
    assert predicciones == [Prediction(score=0.5, factores_principales=("asistencias",))]


def test_trained_model_is_frozen() -> None:
    entrenado = TrainedModel(artefacto=b"x", metadata_tecnica={})

    with pytest.raises(FrozenInstanceError):
        entrenado.artefacto = b"y"  # type: ignore[misc]  # se prueba la inmutabilidad


def test_prediction_is_frozen() -> None:
    prediccion = Prediction(score=0.1, factores_principales=())

    with pytest.raises(FrozenInstanceError):
        prediccion.score = 0.9  # type: ignore[misc]  # se prueba la inmutabilidad


def test_value_objects_use_slots() -> None:
    assert not hasattr(TrainedModel(artefacto=b"", metadata_tecnica={}), "__dict__")
    assert not hasattr(Prediction(score=0.0, factores_principales=()), "__dict__")
