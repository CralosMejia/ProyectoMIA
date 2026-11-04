"""Predictor del composition root: entrena RL y predice segun el formato (R-020 T4)."""

import io
import random
from decimal import Decimal
from unittest.mock import patch

import joblib
import pytest

from app.domain.common.predictor import FeatureRow, PredictorModel
from app.domain.modelo.variables import VARIABLES_CATEGORICAS_MODELO, VARIABLES_NUMERICAS_MODELO
from app.infrastructure.ml import predictor_adoptado
from app.infrastructure.ml.predictor_adoptado import PredictorAdoptado
from app.infrastructure.ml.random_forest import RandomForestPredictor
from app.infrastructure.ml.regresion_logistica import LogisticRegressionPredictor

pytestmark = pytest.mark.unit

NUMERICAS = list(VARIABLES_NUMERICAS_MODELO)
CATEGORICAS = list(VARIABLES_CATEGORICAS_MODELO)
PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]


def _sinteticos(n: int = 200, semilla: int = 5) -> tuple[list[FeatureRow], list[int]]:
    azar = random.Random(semilla)  # noqa: S311  # datos sinteticos reproducibles, no criptografia
    filas: list[FeatureRow] = []
    etiquetas: list[int] = []
    for _ in range(n):
        plan = azar.choice(PLANES)
        previos = azar.randint(0, 5)
        filas.append(
            {
                "ciclos_previos": previos,
                "antiguedad_dias": azar.randint(0, 500),
                "duracion_modelo": {"MENSUAL": 30, "TRIMESTRAL": 90}.get(plan, 365),
                "monto_actual": Decimal(azar.randint(2000, 30000)) / 100,
                "monto_historico": Decimal(azar.randint(0, 100000)) / 100,
                "dias_desde_ultima_membresia": None if previos == 0 else azar.randint(1, 300),
                "plan": plan,
                "mes_vencimiento": f"2025-{azar.randint(1, 12):02d}",
            }
        )
        etiquetas.append(int(azar.random() < 0.8 - 0.12 * previos))
    return filas, etiquetas


FILAS, ETIQUETAS = _sinteticos()


@pytest.fixture(scope="module")
def artefacto_rl() -> bytes:
    return LogisticRegressionPredictor().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto


@pytest.fixture(scope="module")
def artefacto_rf() -> bytes:
    return RandomForestPredictor().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto


def test_cumple_el_puerto() -> None:
    puerto: PredictorModel = PredictorAdoptado()

    assert isinstance(puerto, PredictorModel)


def test_train_entrena_la_regresion_logistica() -> None:
    entrenado = PredictorAdoptado().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS)

    assert entrenado.metadata_tecnica["algoritmo"] == "LogisticRegression"
    assert entrenado.metadata_tecnica["metodo_factores"] == "shap_lineal"
    assert joblib.load(io.BytesIO(entrenado.artefacto))["formato"] == 2


def test_predict_con_artefacto_formato_2_usa_la_regresion_logistica(artefacto_rl: bytes) -> None:
    esperado = LogisticRegressionPredictor().predict(artefacto_rl, FILAS[:30])

    assert PredictorAdoptado().predict(artefacto_rl, FILAS[:30]) == esperado


def test_predict_con_artefacto_formato_1_usa_el_random_forest(artefacto_rf: bytes) -> None:
    esperado = RandomForestPredictor().predict(artefacto_rf, FILAS[:30])

    assert PredictorAdoptado().predict(artefacto_rf, FILAS[:30]) == esperado


def test_predict_deserializa_una_sola_vez_por_llamada(artefacto_rl: bytes) -> None:
    with patch.object(predictor_adoptado.joblib, "load", wraps=joblib.load) as carga:
        PredictorAdoptado().predict(artefacto_rl, FILAS[:5])

    assert carga.call_count == 1


@pytest.mark.parametrize("contenido", [{"formato": 3, "pipeline": None}, {"sin": "formato"}, [1]])
def test_predict_con_formato_desconocido_lanza_error_sin_datos(contenido: object) -> None:
    buffer = io.BytesIO()
    joblib.dump(contenido, buffer)

    with pytest.raises(ValueError, match="formato esperado") as error:
        PredictorAdoptado().predict(buffer.getvalue(), FILAS[:1])
    assert "MENSUAL" not in str(error.value)


def test_predict_sin_filas_devuelve_lista_vacia(artefacto_rl: bytes) -> None:
    assert PredictorAdoptado().predict(artefacto_rl, []) == []


def test_predict_con_formato_2_de_otro_algoritmo_lanza_error_sin_datos(artefacto_rl: bytes) -> None:
    contenido = dict(joblib.load(io.BytesIO(artefacto_rl)))
    contenido["algoritmo"] = "RandomForestClassifier"
    buffer = io.BytesIO()
    joblib.dump(contenido, buffer)

    with pytest.raises(ValueError, match="formato esperado") as error:
        PredictorAdoptado().predict(buffer.getvalue(), FILAS[:1])
    assert "MENSUAL" not in str(error.value)


def test_predict_vigente_rl_y_candidato_rl_con_la_misma_instancia_no_mezcla_resultados(
    artefacto_rl: bytes,
) -> None:
    # Reentrenamiento RL vs RL (CU-02): la misma instancia predice con el vigente y el candidato.
    filas_b, etiquetas_b = _sinteticos(semilla=17)
    candidato = PredictorAdoptado().train(filas_b, etiquetas_b, NUMERICAS, CATEGORICAS).artefacto
    esperado_vigente = LogisticRegressionPredictor().predict(artefacto_rl, FILAS[:30])
    esperado_candidato = LogisticRegressionPredictor().predict(candidato, FILAS[:30])
    predictor = PredictorAdoptado()

    vigente = predictor.predict(artefacto_rl, FILAS[:30])
    nuevo = predictor.predict(candidato, FILAS[:30])

    assert vigente == esperado_vigente
    assert nuevo == esperado_candidato
    assert [p.score for p in vigente] != [p.score for p in nuevo]


def test_predict_alterna_vigente_rf_heredado_y_candidato_rl_sin_mezclar_resultados(
    artefacto_rf: bytes, artefacto_rl: bytes
) -> None:
    esperado_rf = RandomForestPredictor().predict(artefacto_rf, FILAS[:30])
    esperado_rl = LogisticRegressionPredictor().predict(artefacto_rl, FILAS[:30])
    predictor = PredictorAdoptado()

    resultados = [
        predictor.predict(artefacto_rf, FILAS[:30]),
        predictor.predict(artefacto_rl, FILAS[:30]),
        predictor.predict(artefacto_rf, FILAS[:30]),
    ]

    assert resultados == [esperado_rf, esperado_rl, esperado_rf]
