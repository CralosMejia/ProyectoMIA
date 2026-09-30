from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel, TrainedModel

pytestmark = pytest.mark.unit


class FakePredictor:
    """Doble minimo del puerto PredictorModel (sin librerias de ML)."""

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        return TrainedModel(artefacto=b"modelo", metadata_tecnica={"filas": str(len(labels))})

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        return [
            Prediction(score=Decimal("0.5"), factores_principales=("Plan: MENSUAL (+0,05)",))
            for _ in features
        ]


class TrainOnly:
    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        return TrainedModel(artefacto=b"", metadata_tecnica={})


def test_isinstance_with_minimal_double_returns_true() -> None:
    # La anotacion hace que mypy verifique la compatibilidad estructural del doble.
    modelo: PredictorModel = FakePredictor()

    assert isinstance(modelo, PredictorModel)


def test_isinstance_without_predict_returns_false() -> None:
    assert not isinstance(TrainOnly(), PredictorModel)


def test_train_and_predict_through_port_return_value_objects() -> None:
    modelo: PredictorModel = FakePredictor()
    features: list[FeatureRow] = [
        {"ciclos_previos": 2, "plan": "MENSUAL", "monto_actual": Decimal("30.00"), "x": None}
    ]

    entrenado = modelo.train(features, [1], ["ciclos_previos", "monto_actual", "x"], ["plan"])
    predicciones = modelo.predict(entrenado.artefacto, features)

    assert entrenado == TrainedModel(artefacto=b"modelo", metadata_tecnica={"filas": "1"})
    assert predicciones == [
        Prediction(score=Decimal("0.5"), factores_principales=("Plan: MENSUAL (+0,05)",))
    ]


def test_prediction_score_is_decimal() -> None:
    assert isinstance(
        Prediction(score=Decimal("0.12345678"), factores_principales=()).score, Decimal
    )


@pytest.mark.parametrize("score", [Decimal("-0.00000001"), Decimal("1.00000001")])
def test_prediction_score_out_of_range_raises_value_error(score: Decimal) -> None:
    with pytest.raises(ValueError, match="score"):
        Prediction(score=score, factores_principales=())


@pytest.mark.parametrize("score", [Decimal(0), Decimal(1)])
def test_prediction_score_bounds_are_valid(score: Decimal) -> None:
    assert Prediction(score=score, factores_principales=()).score == score


def test_trained_model_is_frozen() -> None:
    entrenado = TrainedModel(artefacto=b"x", metadata_tecnica={})

    with pytest.raises(FrozenInstanceError):
        entrenado.artefacto = b"y"  # type: ignore[misc]  # se prueba la inmutabilidad


def test_prediction_is_frozen() -> None:
    prediccion = Prediction(score=Decimal("0.1"), factores_principales=())

    with pytest.raises(FrozenInstanceError):
        prediccion.score = Decimal("0.9")  # type: ignore[misc]  # se prueba la inmutabilidad


def test_value_objects_use_slots() -> None:
    assert not hasattr(TrainedModel(artefacto=b"", metadata_tecnica={}), "__dict__")
    assert not hasattr(Prediction(score=Decimal(0), factores_principales=()), "__dict__")
