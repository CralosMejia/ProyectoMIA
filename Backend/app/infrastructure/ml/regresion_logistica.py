"""Adaptador de Regresion Logistica del puerto ``PredictorModel`` (ADR-002; M06, R-020).

Es el modelo adoptado (``Notebookes/Prototipo_Final_Mtabolic.ipynb`` v3):

- Pipeline: la misma preparacion que el Random Forest (``construir_preparacion``: mediana +
  ``StandardScaler`` para las numericas; moda + ``OneHotEncoder(handle_unknown="ignore")``
  para las categoricas) y ``LogisticRegression(class_weight="balanced", max_iter=2000,
  random_state=42)``; el resto por defecto de scikit-learn (``C=1.0``, ``lbfgs``, L2).
- Motivos con SHAP lineal intervencional, calculado de forma analitica (definicion (b)): sobre
  la matriz preparada ``X'``, ``aporte_k = coef_k * (X'_ik - mu_k)``, con ``mu`` la media por
  columna de ``X'`` de las filas con que se entreno el modelo (se guarda en el artefacto como
  ``media_fondo``). Unidad: log-odds; ``base + suma de aportes = decision_function`` con
  ``base = intercepto + coef . mu``. Coincide con ``shap.LinearExplainer`` con el fondo
  completo. Las columnas *one-hot* se suman a su variable original en el orden de la matriz y
  se aplica la misma regla de seleccion y formato que el Random Forest (hasta 3 aportes
  ``> 0,005``, sin ``mes_vencimiento``, ``"Plan: TRIMESTRAL (+0,45)"``).

El artefacto (``formato`` 2) es un ``joblib`` (pickle): solo se deserializa desde
``modelos.artefacto``, que escribe este mismo adaptador (ADR-003). Igual que el Random Forest,
es el unico sitio donde ``Decimal`` pasa a ``float`` y la probabilidad vuelve a ``Decimal``.
"""

import io
import json
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd  # type: ignore[import-untyped]  # pandas no publica tipos (sin pandas-stubs)
import shap
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.infrastructure.ml.random_forest import (
    CLASE_NO_RENOVO,
    NOMBRE_VARIABLE,
    SEMILLA,
    ValorReferencia,
    _a_frame,
    _a_score,
    _calcular_referencia,
    _es_nulo,
    _variable_original,
    construir_preparacion,
    formatear_aporte,
    seleccionar_factores,
    texto_valor,
)

ALGORITMO = "LogisticRegression"
HIPERPARAMETROS: Mapping[str, Any] = {
    "class_weight": "balanced",
    "max_iter": 2000,
    "random_state": SEMILLA,
}
METODO_FACTORES = "shap_lineal"
FORMATO_ARTEFACTO = 2


@dataclass(frozen=True, slots=True)
class ArtefactoRegresionLogistica:
    """Contenido deserializado del artefacto."""

    pipeline: Pipeline
    numericas: tuple[str, ...]
    categoricas: tuple[str, ...]
    referencia: Mapping[str, ValorReferencia]
    media_fondo: np.ndarray


@dataclass(frozen=True, slots=True)
class AportesLineales:
    """SHAP lineal por variable original de cada fila, en log-odds.

    ``valor_base + valores[i].sum()`` es ``decision_function`` de la fila ``i``.
    """

    valor_base: float
    variables: tuple[str, ...]
    valores: np.ndarray


def construir_pipeline(numericas: Sequence[str], categoricas: Sequence[str]) -> Pipeline:
    """Pipeline sin entrenar, identico al ``modelo_operativo`` del notebook v3."""
    return Pipeline(
        [
            ("preparacion", construir_preparacion(numericas, categoricas)),
            ("modelo", LogisticRegression(**HIPERPARAMETROS)),
        ]
    )


def cargar_artefacto(artefacto: bytes) -> ArtefactoRegresionLogistica:
    """Deserializa un artefacto escrito por ``LogisticRegressionPredictor.train``."""
    return artefacto_desde_contenido(joblib.load(io.BytesIO(artefacto)))


def artefacto_desde_contenido(contenido: object) -> ArtefactoRegresionLogistica:
    """Valida el contenido ya deserializado (``formato`` 2) y lo convierte en el artefacto."""
    if (
        not isinstance(contenido, dict)
        or contenido.get("formato") != FORMATO_ARTEFACTO
        or contenido.get("algoritmo") != ALGORITMO
    ):
        raise ValueError("El artefacto no tiene el formato esperado del modelo.")
    return ArtefactoRegresionLogistica(
        pipeline=contenido["pipeline"],
        numericas=tuple(contenido["numericas"]),
        categoricas=tuple(contenido["categoricas"]),
        referencia=dict(contenido["referencia"]),
        media_fondo=np.asarray(contenido["media_fondo"], dtype=np.float64),
    )


# ---------------------------------------------------------------- SHAP lineal (definicion (b))


def _matriz_preparada(pipeline: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    """``preparacion.transform`` densa y en ``float64``, como ``matriz_preparada`` del notebook."""
    matriz = pipeline.named_steps["preparacion"].transform(frame)
    return np.asarray(matriz.toarray() if hasattr(matriz, "toarray") else matriz, dtype=np.float64)


def aportes_lineales(modelo: ArtefactoRegresionLogistica, frame: pd.DataFrame) -> AportesLineales:
    """``coef * (X' - media_fondo)`` con las columnas *one-hot* sumadas a su variable."""
    regresion = modelo.pipeline.named_steps["modelo"]
    coef = np.asarray(regresion.coef_[0], dtype=np.float64)
    media = modelo.media_fondo
    por_columna = coef * (_matriz_preparada(modelo.pipeline, frame) - media)
    valor_base = float(regresion.intercept_[0] + coef @ media)

    variables = (*modelo.numericas, *modelo.categoricas)
    preparacion = modelo.pipeline.named_steps["preparacion"]
    originales = [
        _variable_original(c, modelo.categoricas) for c in preparacion.get_feature_names_out()
    ]
    # Suma secuencial en float64 desde 0,0, de izquierda a derecha en el orden de la matriz,
    # igual que agregar_por_variable del notebook: mismo redondeo en el borde de 0,005.
    agregados = np.zeros((por_columna.shape[0], len(variables)), dtype=np.float64)
    for k, original in enumerate(originales):
        agregados[:, variables.index(original)] += por_columna[:, k]
    return AportesLineales(valor_base=valor_base, variables=variables, valores=agregados)


# ---------------------------------------------------------------- adaptador


class LogisticRegressionPredictor:
    """Implementacion de ``PredictorModel`` con la Regresion Logistica (modelo adoptado)."""

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        if len(features) != len(labels):
            raise ValueError("Debe haber una etiqueta por fila de entrenamiento.")
        if len(set(labels)) < 2:  # dos clases: renueva / no renueva
            raise ValueError("El entrenamiento necesita ejemplos de las dos clases.")

        frame = _a_frame(features, numericas, categoricas)
        pipeline = construir_pipeline(numericas, categoricas)
        pipeline.fit(frame, np.asarray(labels, dtype=np.int64))
        media_fondo = _matriz_preparada(pipeline, frame).mean(axis=0)

        # La referencia (socio "tipico") no interviene en los motivos: se guarda por
        # compatibilidad con la metadata y la conciliacion, igual que en el Random Forest.
        filas_referencia = referencia if referencia else features
        valores_referencia = _calcular_referencia(
            _a_frame(filas_referencia, numericas, categoricas), numericas, categoricas
        )
        buffer = io.BytesIO()
        joblib.dump(
            {
                "formato": FORMATO_ARTEFACTO,
                "algoritmo": ALGORITMO,
                "pipeline": pipeline,
                "numericas": list(numericas),
                "categoricas": list(categoricas),
                "referencia": valores_referencia,
                "media_fondo": media_fondo,
            },
            buffer,
        )
        metadata = {
            "algoritmo": ALGORITMO,
            "hiperparametros": json.dumps(dict(HIPERPARAMETROS), sort_keys=True),
            "preprocesamiento": json.dumps(
                {
                    "numericas": ["SimpleImputer(strategy=median)", "StandardScaler()"],
                    "categoricas": [
                        "SimpleImputer(strategy=most_frequent)",
                        "OneHotEncoder(handle_unknown=ignore)",
                    ],
                }
            ),
            "variables_numericas": json.dumps(list(numericas)),
            "variables_categoricas": json.dumps(list(categoricas)),
            "referencia_factores": json.dumps(
                {v: None if _es_nulo(x) else x for v, x in valores_referencia.items()},
                ensure_ascii=False,
            ),
            "filas_entrenamiento": str(len(features)),
            "filas_referencia": str(len(filas_referencia)),
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
            "shap": shap.__version__,
            "metodo_factores": METODO_FACTORES,
        }
        return TrainedModel(artefacto=buffer.getvalue(), metadata_tecnica=metadata)

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        if not features:
            return []
        return self.predecir_con(cargar_artefacto(artefacto), features)

    def predecir_con(
        self, modelo: ArtefactoRegresionLogistica, features: Sequence[FeatureRow]
    ) -> list[Prediction]:
        """Predice con un artefacto ya deserializado: score ``predict_proba[:, 1]`` y motivos."""
        if not features:
            return []
        frame = _a_frame(features, modelo.numericas, modelo.categoricas)
        probabilidades = modelo.pipeline.predict_proba(frame)[:, CLASE_NO_RENOVO]

        aportes = aportes_lineales(modelo, frame)
        explicables = [
            (v, aportes.variables.index(v)) for v in NOMBRE_VARIABLE if v in aportes.variables
        ]

        predicciones: list[Prediction] = []
        for i in range(len(frame)):
            elegidos = seleccionar_factores(
                {v: float(aportes.valores[i, j]) for v, j in explicables}
            )
            factores = tuple(
                f"{NOMBRE_VARIABLE[v]}: "
                f"{texto_valor(v, frame.iloc[i][v], modelo.numericas)} ({formatear_aporte(a)})"
                for v, a in elegidos
            )
            predicciones.append(
                Prediction(score=_a_score(float(probabilidades[i])), factores_principales=factores)
            )
        return predicciones
