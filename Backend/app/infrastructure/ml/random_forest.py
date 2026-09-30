"""Adaptador scikit-learn del puerto ``PredictorModel`` (ADR-002).

Replica el notebook MVP:

- 9.5: ``ColumnTransformer`` con ``SimpleImputer(median)`` + ``StandardScaler`` para las
  numericas y ``SimpleImputer(most_frequent)`` + ``OneHotEncoder(handle_unknown="ignore")``
  para las categoricas, y ``RandomForestClassifier(n_estimators=300, max_depth=6,
  min_samples_leaf=20, class_weight="balanced", random_state=42)``.
- 13.3: factores principales. Para cada variable explicable se sustituye su valor por el del
  socio "tipico" (mediana o moda de las filas de referencia) y el aporte es
  ``p(fila) - p(fila con la variable sustituida)``. Se muestran hasta 3 aportes ``> 0,005``,
  de mayor a menor, con el formato ``"Plan: TRIMESTRAL (+0,09)"``. ``mes_vencimiento`` no se
  explica (no es accionable).

Es el unico sitio donde ``Decimal`` pasa a ``float`` (entrada del modelo) y la probabilidad
vuelve a ``Decimal`` cuantizada a 8 decimales (``NUMERIC(10,8)``).

El artefacto es un ``joblib`` (pickle): solo se deserializa desde ``modelos.artefacto``, que
escribe este mismo adaptador (ADR-003). Nunca se carga un artefacto de otra procedencia.
"""

import io
import json
import math
import platform
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import joblib
import numpy as np
import pandas as pd  # type: ignore[import-untyped]  # pandas no publica tipos (sin pandas-stubs)
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel

SEMILLA = 42
HIPERPARAMETROS: Mapping[str, Any] = {
    "n_estimators": 300,
    "max_depth": 6,
    "min_samples_leaf": 20,
    "class_weight": "balanced",
    "random_state": SEMILLA,
}
MAX_FACTORES = 3
APORTE_MINIMO = 0.005
FORMATO_ARTEFACTO = 1
_OCHO_DECIMALES = Decimal("0.00000001")

# Nombres comprensibles para el personal (notebook 13.3). mes_vencimiento no se explica.
NOMBRE_VARIABLE: Mapping[str, str] = {
    "ciclos_previos": "Membresías previas",
    "antiguedad_dias": "Antigüedad (días)",
    "duracion_modelo": "Duración del plan (días)",
    "monto_actual": "Monto actual (USD)",
    "monto_historico": "Monto histórico (USD)",
    "dias_desde_ultima_membresia": "Días desde la membresía anterior",
    "plan": "Plan",
    "forma_pago": "Forma de pago",
    "inicio_aproximado": "Fecha de inicio aproximada",
}

type ValorReferencia = float | str


@dataclass(frozen=True, slots=True)
class ArtefactoRandomForest:
    """Contenido deserializado del artefacto."""

    pipeline: Pipeline
    numericas: tuple[str, ...]
    categoricas: tuple[str, ...]
    referencia: Mapping[str, ValorReferencia]


def construir_pipeline(numericas: Sequence[str], categoricas: Sequence[str]) -> Pipeline:
    """Pipeline sin entrenar, identico al ``modelo_operativo`` del notebook."""
    preparacion = ColumnTransformer(
        [
            (
                "numericas",
                Pipeline(
                    [
                        ("imputar", SimpleImputer(strategy="median")),
                        ("escalar", StandardScaler()),
                    ]
                ),
                list(numericas),
            ),
            (
                "categoricas",
                Pipeline(
                    [
                        ("imputar", SimpleImputer(strategy="most_frequent")),
                        ("one_hot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                list(categoricas),
            ),
        ]
    )
    return Pipeline(
        [("preparacion", preparacion), ("modelo", RandomForestClassifier(**HIPERPARAMETROS))]
    )


def cargar_artefacto(artefacto: bytes) -> ArtefactoRandomForest:
    """Deserializa un artefacto escrito por ``RandomForestPredictor.train``."""
    contenido = joblib.load(io.BytesIO(artefacto))
    if not isinstance(contenido, dict) or contenido.get("formato") != FORMATO_ARTEFACTO:
        raise ValueError("El artefacto no tiene el formato esperado del modelo.")
    return ArtefactoRandomForest(
        pipeline=contenido["pipeline"],
        numericas=tuple(contenido["numericas"]),
        categoricas=tuple(contenido["categoricas"]),
        referencia=dict(contenido["referencia"]),
    )


# ---------------------------------------------------------------- conversion en el borde


def _a_float(valor: Decimal | int | str | None) -> float:
    if valor is None:
        return math.nan
    if isinstance(valor, str):
        raise TypeError("Una variable numerica no puede ser texto.")
    return float(valor)


def _a_texto(valor: Decimal | int | str | None) -> object:
    return np.nan if valor is None else str(valor)


def _a_frame(
    filas: Sequence[FeatureRow], numericas: Sequence[str], categoricas: Sequence[str]
) -> pd.DataFrame:
    """Numericas como ``float64`` (``None`` -> NaN) y categoricas como ``object`` (``str``)."""
    columnas: dict[str, pd.Series] = {}
    for v in numericas:
        columnas[v] = pd.Series([_a_float(f[v]) for f in filas], dtype="float64")
    for v in categoricas:
        columnas[v] = pd.Series([_a_texto(f[v]) for f in filas], dtype=object)
    return pd.DataFrame(columnas, columns=[*numericas, *categoricas])


def _a_score(probabilidad: float) -> Decimal:
    return Decimal(probabilidad).quantize(_OCHO_DECIMALES, rounding=ROUND_HALF_EVEN)


def _calcular_referencia(
    frame: pd.DataFrame, numericas: Sequence[str], categoricas: Sequence[str]
) -> dict[str, ValorReferencia]:
    """Mediana (numericas) y moda (categoricas; la menor si hay empate), como el notebook."""
    referencia: dict[str, ValorReferencia] = {v: float(frame[v].median()) for v in numericas}
    for v in categoricas:
        modas = frame[v].mode()
        referencia[v] = str(modas.iloc[0]) if len(modas) else math.nan
    return referencia


# ---------------------------------------------------------------- textos de los factores


def formatear_aporte(aporte: float) -> str:
    """``es(a, 2, True)`` del notebook: signo, 2 decimales y coma decimal."""
    texto = f"{aporte:+,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _es_nulo(valor: object) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def texto_valor(variable: str, valor: object, numericas: Sequence[str]) -> str:
    """``texto_valor`` del notebook: miles con punto y sin decimales; ``sin dato``; ``sí/no``."""
    if _es_nulo(valor):
        return "sin dato"
    if variable in numericas:
        return f"{float(str(valor)):,.0f}".replace(",", ".")
    if variable == "inicio_aproximado":
        return "sí" if str(valor) == "True" else "no"
    return str(valor)


def seleccionar_factores(
    aportes: Mapping[str, float], n: int = MAX_FACTORES
) -> list[tuple[str, float]]:
    """Aportes ``> 0,005`` de mayor a menor (estable ante empates), como maximo ``n``."""
    positivos = [(v, a) for v, a in aportes.items() if a > APORTE_MINIMO]
    return sorted(positivos, key=lambda par: -par[1])[:n]


# ---------------------------------------------------------------- adaptador


class RandomForestPredictor:
    """Implementacion de ``PredictorModel`` con scikit-learn y joblib."""

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

        filas_referencia = referencia if referencia else features
        valores_referencia = _calcular_referencia(
            _a_frame(filas_referencia, numericas, categoricas), numericas, categoricas
        )
        buffer = io.BytesIO()
        joblib.dump(
            {
                "formato": FORMATO_ARTEFACTO,
                "pipeline": pipeline,
                "numericas": list(numericas),
                "categoricas": list(categoricas),
                "referencia": valores_referencia,
            },
            buffer,
        )
        metadata = {
            "algoritmo": "RandomForestClassifier",
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
        }
        return TrainedModel(artefacto=buffer.getvalue(), metadata_tecnica=metadata)

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        if not features:
            return []
        return self.predecir_con(cargar_artefacto(artefacto), features)

    def predecir_con(
        self, modelo: ArtefactoRandomForest, features: Sequence[FeatureRow]
    ) -> list[Prediction]:
        """Predice con un artefacto ya deserializado (score y factores de cada fila)."""
        if not features:
            return []
        frame = _a_frame(features, modelo.numericas, modelo.categoricas)
        base = modelo.pipeline.predict_proba(frame)[:, 1]

        explicables = [v for v in NOMBRE_VARIABLE if v in frame.columns]
        aportes: dict[str, np.ndarray] = {}
        for v in explicables:
            sustituido = frame.copy()
            valor = modelo.referencia[v]
            dtype = "float64" if v in modelo.numericas else object
            sustituido[v] = pd.Series([valor] * len(frame), index=frame.index, dtype=dtype)
            aportes[v] = base - modelo.pipeline.predict_proba(sustituido)[:, 1]

        predicciones: list[Prediction] = []
        for i in range(len(frame)):
            elegidos = seleccionar_factores({v: float(aportes[v][i]) for v in explicables})
            factores = tuple(
                f"{NOMBRE_VARIABLE[v]}: "
                f"{texto_valor(v, frame.iloc[i][v], modelo.numericas)} ({formatear_aporte(a)})"
                for v, a in elegidos
            )
            predicciones.append(
                Prediction(score=_a_score(float(base[i])), factores_principales=factores)
            )
        return predicciones
