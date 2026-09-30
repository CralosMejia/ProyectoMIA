"""Adaptador scikit-learn de PredictorModel con datos sinteticos deterministas (sin personas)."""

import math
import random
import re
from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np
import pandas as pd  # type: ignore[import-untyped]  # pandas no publica tipos (sin pandas-stubs)
import pytest

from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel
from app.domain.modelo.variables import VARIABLES_CATEGORICAS, VARIABLES_NUMERICAS
from app.infrastructure.ml.random_forest import (
    NOMBRE_VARIABLE,
    RandomForestPredictor,
    _a_score,
    cargar_artefacto,
    construir_pipeline,
    formatear_aporte,
    seleccionar_factores,
    texto_valor,
)

pytestmark = pytest.mark.unit

NUMERICAS = list(VARIABLES_NUMERICAS)
CATEGORICAS = list(VARIABLES_CATEGORICAS)
PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]
FORMAS = ["EFECTIVO", "TRANSFERENCIA", "TARJETA_DATAFAST", "OTRO", "SIN_DATO"]
MESES = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]


def _sinteticos(n: int = 300, semilla: int = 7) -> tuple[list[FeatureRow], list[int]]:
    azar = random.Random(semilla)  # noqa: S311  # datos sinteticos reproducibles, no criptografia
    filas: list[FeatureRow] = []
    etiquetas: list[int] = []
    for _ in range(n):
        plan = azar.choice(PLANES)
        previos = azar.randint(0, 6)
        fila: FeatureRow = {
            "ciclos_previos": previos,
            "antiguedad_dias": azar.randint(0, 600),
            "duracion_modelo": {"MENSUAL": 30, "TRIMESTRAL": 90, "SEMESTRAL": 180}.get(plan, 365),
            "monto_actual": Decimal(azar.randint(2000, 30000)) / 100,
            "monto_historico": Decimal(azar.randint(0, 200000)) / 100,
            "dias_desde_ultima_membresia": None if previos == 0 else azar.randint(1, 400),
            "plan": plan,
            "forma_pago": azar.choice(FORMAS),
            "mes_vencimiento": azar.choice(MESES),
            "inicio_aproximado": azar.choice(["True", "False"]),
        }
        riesgo = 0.8 - 0.1 * previos + (0.15 if plan == "TRIMESTRAL" else 0.0)
        filas.append(fila)
        etiquetas.append(int(azar.random() < riesgo))
    return filas, etiquetas


FILAS, ETIQUETAS = _sinteticos()


@pytest.fixture(scope="module")
def predictor() -> RandomForestPredictor:
    return RandomForestPredictor()


@pytest.fixture(scope="module")
def artefacto(predictor: RandomForestPredictor) -> bytes:
    return predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto


def test_cumple_el_puerto(predictor: RandomForestPredictor) -> None:
    puerto: PredictorModel = predictor

    assert isinstance(puerto, PredictorModel)


# ---------------------------------------------------------------- pipeline del notebook (9.5)


def test_pipeline_con_los_parametros_del_notebook(artefacto: bytes) -> None:
    pipeline = cargar_artefacto(artefacto).pipeline
    params = pipeline.get_params()

    assert [nombre for nombre, _ in pipeline.steps] == ["preparacion", "modelo"]
    assert params["preparacion__numericas__imputar__strategy"] == "median"
    assert type(params["preparacion__numericas__escalar"]).__name__ == "StandardScaler"
    assert params["preparacion__categoricas__imputar__strategy"] == "most_frequent"
    assert params["preparacion__categoricas__one_hot__handle_unknown"] == "ignore"
    assert list(params["preparacion"].transformers[0][2]) == NUMERICAS
    assert list(params["preparacion"].transformers[1][2]) == CATEGORICAS
    modelo = params["modelo"]
    assert type(modelo).__name__ == "RandomForestClassifier"
    assert params["modelo__n_estimators"] == 300
    assert params["modelo__max_depth"] == 6
    assert params["modelo__min_samples_leaf"] == 20
    assert params["modelo__class_weight"] == "balanced"
    assert params["modelo__random_state"] == 42


def test_construir_pipeline_sin_entrenar_tiene_los_mismos_parametros() -> None:
    params = construir_pipeline(NUMERICAS, CATEGORICAS).get_params()

    assert params["modelo__n_estimators"] == 300
    assert params["modelo__min_samples_leaf"] == 20


def test_metadata_tecnica_incluye_parametros_y_versiones(predictor: RandomForestPredictor) -> None:
    metadata = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).metadata_tecnica

    for clave in ("python", "scikit_learn", "numpy", "pandas", "joblib"):
        assert re.fullmatch(r"\d+\.\d+.*", metadata[clave])
    assert '"n_estimators": 300' in metadata["hiperparametros"]
    assert '"max_depth": 6' in metadata["hiperparametros"]
    assert metadata["algoritmo"] == "RandomForestClassifier"
    assert metadata["filas_entrenamiento"] == "300"
    assert metadata["filas_referencia"] == "300"
    assert all(isinstance(v, str) for v in metadata.values())


# ---------------------------------------------------------------- serializacion y determinismo


def test_artefacto_deserializado_da_los_mismos_scores_que_en_memoria(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    en_memoria = predictor.predecir_con(cargar_artefacto(artefacto), FILAS[:50])

    desde_bytes = predictor.predict(artefacto, FILAS[:50])

    assert isinstance(artefacto, bytes)
    assert len(artefacto) > 0
    assert [p.score for p in desde_bytes] == [p.score for p in en_memoria]
    assert desde_bytes == en_memoria


def _numero(valor: Decimal | int | str | None) -> float:
    return math.nan if valor is None else float(valor)


def _frame_como_el_notebook(filas: Sequence[FeatureRow]) -> pd.DataFrame:
    """Numericas float64 (None -> NaN) y categoricas texto, como ``datos_modelables``."""
    datos = {v: pd.Series([_numero(f[v]) for f in filas], dtype="float64") for v in NUMERICAS}
    datos.update({v: pd.Series([str(f[v]) for f in filas], dtype=object) for v in CATEGORICAS})
    return pd.DataFrame(datos, columns=[*NUMERICAS, *CATEGORICAS])


def test_artefacto_da_los_mismos_scores_que_un_pipeline_entrenado_en_memoria(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    # "Hecho cuando" (05): el modelo que nunca se serializo y el deserializado coinciden.
    en_memoria = construir_pipeline(NUMERICAS, CATEGORICAS)
    en_memoria.fit(_frame_como_el_notebook(FILAS), np.asarray(ETIQUETAS, dtype=np.int64))
    probabilidades = en_memoria.predict_proba(_frame_como_el_notebook(FILAS))[:, 1]
    esperados = [
        Decimal(float(p)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        for p in probabilidades
    ]

    assert [p.score for p in predictor.predict(artefacto, FILAS)] == esperados


def test_predict_da_el_mismo_score_por_fila_sin_importar_el_lote(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    lote = predictor.predict(artefacto, FILAS[:20])
    invertido = predictor.predict(artefacto, list(reversed(FILAS[:20])))

    assert [p.score for p in lote] == [p.score for p in reversed(invertido)]


@pytest.mark.parametrize(
    ("probabilidad", "esperado"),
    [(1 / 512, "0.00195312"), (3 / 512, "0.00585938"), (0.0, "0E-8"), (1.0, "1.00000000")],
)
def test_score_cuantizado_con_redondeo_bancario(probabilidad: float, esperado: str) -> None:
    # 1/512 = 0,001953125 y 3/512 = 0,005859375 son exactos en binario: caen en la mitad.
    score = _a_score(probabilidad)

    assert score == Decimal(esperado)
    assert str(score) == esperado


def test_dos_entrenamientos_iguales_dan_los_mismos_scores(predictor: RandomForestPredictor) -> None:
    otro = RandomForestPredictor().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto
    uno = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto

    assert predictor.predict(uno, FILAS) == predictor.predict(otro, FILAS)


def test_score_decimal_en_rango_con_ocho_decimales(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    predicciones = predictor.predict(artefacto, FILAS)

    assert len(predicciones) == len(FILAS)
    for p in predicciones:
        assert isinstance(p, Prediction)
        assert isinstance(p.score, Decimal)
        assert Decimal(0) <= p.score <= Decimal(1)
        assert p.score == p.score.quantize(Decimal("0.00000001"))


def test_categoria_no_vista_y_numericos_none_no_fallan(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    fila = dict(FILAS[0])
    fila["mes_vencimiento"] = "2027-01"
    for v in NUMERICAS:
        fila[v] = None

    (prediccion,) = predictor.predict(artefacto, [fila])

    assert Decimal(0) <= prediccion.score <= Decimal(1)


def test_predict_sin_filas_devuelve_lista_vacia(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    assert predictor.predict(artefacto, []) == []


def test_train_con_longitudes_distintas_lanza_error(predictor: RandomForestPredictor) -> None:
    with pytest.raises(ValueError, match="etiqueta"):
        predictor.train(FILAS, ETIQUETAS[:-1], NUMERICAS, CATEGORICAS)


def test_train_con_una_sola_clase_lanza_error(predictor: RandomForestPredictor) -> None:
    with pytest.raises(ValueError, match="clases"):
        predictor.train(FILAS, [1] * len(FILAS), NUMERICAS, CATEGORICAS)


# ---------------------------------------------------------------- referencia de los factores (13.3)


def test_referencia_por_defecto_son_medianas_y_modas_de_todo_el_entrenamiento(
    artefacto: bytes,
) -> None:
    referencia = cargar_artefacto(artefacto).referencia
    ciclos = sorted(int(f["ciclos_previos"] or 0) for f in FILAS)
    planes = [str(f["plan"]) for f in FILAS]
    moda = max(sorted(set(planes)), key=planes.count)  # la menor entre empatadas, como pandas

    assert referencia["ciclos_previos"] == (ciclos[149] + ciclos[150]) / 2
    assert referencia["plan"] == moda
    assert set(referencia) == set(NUMERICAS) | set(CATEGORICAS)


def test_referencia_mediana_ignora_los_numericos_sin_dato(artefacto: bytes) -> None:
    # X_train[v].median() del notebook (13.3) omite NaN (skipna).
    conocidos = sorted(int(v) for f in FILAS if (v := f["dias_desde_ultima_membresia"]) is not None)
    mitad = len(conocidos) // 2
    mediana = (
        float(conocidos[mitad])
        if len(conocidos) % 2
        else (conocidos[mitad - 1] + conocidos[mitad]) / 2
    )

    assert len(conocidos) < len(FILAS)
    assert cargar_artefacto(artefacto).referencia["dias_desde_ultima_membresia"] == mediana


def test_referencia_moda_empatada_es_la_menor(predictor: RandomForestPredictor) -> None:
    # pandas .mode() ordena los empates y el notebook toma .iloc[0].
    filas = [dict(f) for f in FILAS[:4]]
    for fila, forma in zip(
        filas, ["TRANSFERENCIA", "EFECTIVO", "TRANSFERENCIA", "EFECTIVO"], strict=True
    ):
        fila["forma_pago"] = forma

    entrenado = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS, referencia=filas)

    assert cargar_artefacto(entrenado.artefacto).referencia["forma_pago"] == "EFECTIVO"


def test_referencia_explicita_usa_solo_esas_filas(predictor: RandomForestPredictor) -> None:
    subconjunto = [f for f in FILAS if f["plan"] == "ANUAL"]

    entrenado = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS, referencia=subconjunto)

    referencia = cargar_artefacto(entrenado.artefacto).referencia
    assert referencia["plan"] == "ANUAL"
    assert entrenado.metadata_tecnica["filas_referencia"] == str(len(subconjunto))


def test_referencia_vacia_usa_todo_el_entrenamiento(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    entrenado = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS, referencia=[])

    assert (
        cargar_artefacto(entrenado.artefacto).referencia == cargar_artefacto(artefacto).referencia
    )


# ---------------------------------------------------------------- factores principales


FORMATO_FACTOR = re.compile(r"^(?P<nombre>[^:]+): (?P<valor>.+) \(\+(?P<aporte>\d+,\d{2})\)$")


def _aporte(texto: str) -> Decimal:
    coincidencia = FORMATO_FACTOR.match(texto)
    assert coincidencia is not None, texto
    return Decimal(coincidencia["aporte"].replace(",", "."))


def test_factores_hasta_tres_con_formato_del_notebook_y_ordenados(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    predicciones = predictor.predict(artefacto, FILAS)

    con_factores = [p for p in predicciones if p.factores_principales]
    assert con_factores, "los datos sinteticos deben producir factores"
    nombres_validos = set(NOMBRE_VARIABLE.values())
    for p in predicciones:
        assert len(p.factores_principales) <= 3
        aportes = [_aporte(f) for f in p.factores_principales]
        assert aportes == sorted(aportes, reverse=True)
        for f in p.factores_principales:
            coincidencia = FORMATO_FACTOR.match(f)
            assert coincidencia is not None
            assert coincidencia["nombre"] in nombres_validos


def test_factores_excluyen_mes_vencimiento() -> None:
    assert "mes_vencimiento" not in NOMBRE_VARIABLE
    assert set(NOMBRE_VARIABLE) == (set(NUMERICAS) | set(CATEGORICAS)) - {"mes_vencimiento"}


def test_fila_igual_a_la_referencia_no_tiene_factores(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    referencia = cargar_artefacto(artefacto).referencia
    fila: dict[str, Decimal | int | str | None] = {
        v: Decimal(str(referencia[v])) for v in NUMERICAS
    }
    fila.update({v: str(referencia[v]) for v in CATEGORICAS})

    (prediccion,) = predictor.predict(artefacto, [fila])

    assert prediccion.factores_principales == ()


def test_seleccionar_factores_umbral_orden_y_maximo() -> None:
    aportes = {
        "plan": 0.09,
        "forma_pago": 0.005,  # no supera 0,005
        "duracion_modelo": 0.03,
        "monto_actual": 0.011,
        "ciclos_previos": 0.2,
        "antiguedad_dias": -0.4,
    }

    assert seleccionar_factores(aportes, n=3) == [
        ("ciclos_previos", 0.2),
        ("plan", 0.09),
        ("duracion_modelo", 0.03),
    ]
    assert seleccionar_factores({"plan": 0.001, "forma_pago": -0.2}) == []


@pytest.mark.parametrize(
    ("aporte", "texto"), [(0.0912, "+0,09"), (0.005001, "+0,01"), (1.5, "+1,50")]
)
def test_formatear_aporte_con_coma_decimal_y_signo(aporte: float, texto: str) -> None:
    assert formatear_aporte(aporte) == texto


@pytest.mark.parametrize(
    ("variable", "valor", "texto"),
    [
        ("duracion_modelo", 91.0, "91"),
        ("monto_historico", 1234.4, "1.234"),
        ("monto_actual", 87.5, "88"),
        ("antiguedad_dias", 1234567, "1.234.567"),
        ("dias_desde_ultima_membresia", float("nan"), "sin dato"),
        ("dias_desde_ultima_membresia", None, "sin dato"),
        ("plan", "TRIMESTRAL", "TRIMESTRAL"),
        ("forma_pago", None, "sin dato"),
        ("inicio_aproximado", "True", "sí"),
        ("inicio_aproximado", "False", "no"),
    ],
)
def test_texto_valor_formato_del_notebook(variable: str, valor: object, texto: str) -> None:
    assert texto_valor(variable, valor, NUMERICAS) == texto


def test_factor_completo_con_formato_del_notebook() -> None:
    assert (
        f"{NOMBRE_VARIABLE['plan']}: {texto_valor('plan', 'TRIMESTRAL', NUMERICAS)} "
        f"({formatear_aporte(0.09)})"
    ) == "Plan: TRIMESTRAL (+0,09)"


def _sin_float(filas: Sequence[FeatureRow]) -> bool:
    return not any(isinstance(v, float) for f in filas for v in f.values())


def test_datos_sinteticos_cruzan_el_puerto_sin_float() -> None:
    assert _sin_float(FILAS)
