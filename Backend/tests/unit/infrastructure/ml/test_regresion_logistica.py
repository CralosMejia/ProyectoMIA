"""Adaptador de Regresion Logistica (M06, R-020) con datos sinteticos (sin personas)."""

import io
import json
import random
import re
from decimal import ROUND_HALF_EVEN, Decimal

import joblib
import numpy as np
import pytest
import shap

from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel
from app.domain.modelo.variables import (
    VARIABLES_CATEGORICAS,
    VARIABLES_CATEGORICAS_MODELO,
    VARIABLES_NUMERICAS,
    VARIABLES_NUMERICAS_MODELO,
)
from app.infrastructure.ml.random_forest import (
    APORTE_MINIMO,
    NOMBRE_VARIABLE,
    RandomForestPredictor,
    _a_frame,
    formatear_aporte,
    seleccionar_factores,
    texto_valor,
)
from app.infrastructure.ml.regresion_logistica import (
    FORMATO_ARTEFACTO,
    HIPERPARAMETROS,
    METODO_FACTORES,
    LogisticRegressionPredictor,
    aportes_lineales,
    artefacto_desde_contenido,
    cargar_artefacto,
    construir_pipeline,
)

pytestmark = pytest.mark.unit

NUMERICAS = list(VARIABLES_NUMERICAS_MODELO)
CATEGORICAS = list(VARIABLES_CATEGORICAS_MODELO)
PLANES = ["MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "OTRO"]
MESES = [f"2025-{m:02d}" for m in range(1, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]
TOLERANCIA = 1e-9


def _sinteticos(n: int = 300, semilla: int = 11) -> tuple[list[FeatureRow], list[int]]:
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
            "mes_vencimiento": azar.choice(MESES),
        }
        riesgo = 0.85 - 0.12 * previos + (0.2 if plan == "TRIMESTRAL" else 0.0)
        filas.append(fila)
        etiquetas.append(int(azar.random() < riesgo))
    return filas, etiquetas


FILAS, ETIQUETAS = _sinteticos()


@pytest.fixture(scope="module")
def predictor() -> LogisticRegressionPredictor:
    return LogisticRegressionPredictor()


@pytest.fixture(scope="module")
def artefacto(predictor: LogisticRegressionPredictor) -> bytes:
    return predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto


def _matriz_preparada(artefacto: bytes, filas: list[FeatureRow]) -> np.ndarray:
    modelo = cargar_artefacto(artefacto)
    matriz = modelo.pipeline.named_steps["preparacion"].transform(
        _a_frame(filas, modelo.numericas, modelo.categoricas)
    )
    return np.asarray(matriz.toarray() if hasattr(matriz, "toarray") else matriz, dtype=np.float64)


def test_cumple_el_puerto(predictor: LogisticRegressionPredictor) -> None:
    puerto: PredictorModel = predictor

    assert isinstance(puerto, PredictorModel)


# ---------------------------------------------------------------- pipeline (definicion (a))


def test_pipeline_con_la_preparacion_del_rf_y_los_hiperparametros_del_notebook(
    artefacto: bytes,
) -> None:
    params = cargar_artefacto(artefacto).pipeline.get_params()

    assert [nombre for nombre, _ in cargar_artefacto(artefacto).pipeline.steps] == [
        "preparacion",
        "modelo",
    ]
    assert params["preparacion__numericas__imputar__strategy"] == "median"
    assert type(params["preparacion__numericas__escalar"]).__name__ == "StandardScaler"
    assert params["preparacion__categoricas__imputar__strategy"] == "most_frequent"
    assert params["preparacion__categoricas__one_hot__handle_unknown"] == "ignore"
    assert list(params["preparacion"].transformers[0][2]) == NUMERICAS
    assert list(params["preparacion"].transformers[1][2]) == CATEGORICAS
    assert type(params["modelo"]).__name__ == "LogisticRegression"
    assert params["modelo__class_weight"] == "balanced"
    assert params["modelo__max_iter"] == 2000
    assert params["modelo__random_state"] == 42
    assert params["modelo__C"] == 1.0
    assert params["modelo__solver"] == "lbfgs"


def test_hiperparametros_son_los_del_notebook() -> None:
    assert dict(HIPERPARAMETROS) == {
        "class_weight": "balanced",
        "max_iter": 2000,
        "random_state": 42,
    }


def test_construir_pipeline_sin_entrenar_tiene_los_mismos_parametros() -> None:
    params = construir_pipeline(NUMERICAS, CATEGORICAS).get_params()

    assert type(params["modelo"]).__name__ == "LogisticRegression"
    assert params["modelo__max_iter"] == 2000


# ---------------------------------------------------------------- artefacto y metadata (d)


def test_artefacto_formato_2_con_algoritmo_y_media_del_fondo(artefacto: bytes) -> None:
    contenido = joblib.load(io.BytesIO(artefacto))

    assert set(contenido) == {
        "formato",
        "algoritmo",
        "pipeline",
        "numericas",
        "categoricas",
        "referencia",
        "media_fondo",
    }
    assert contenido["formato"] == FORMATO_ARTEFACTO == 2
    assert contenido["algoritmo"] == "LogisticRegression"
    esperada = _matriz_preparada(artefacto, FILAS).mean(axis=0)
    assert np.array_equal(np.asarray(contenido["media_fondo"]), esperada)


def test_metadata_tecnica_incluye_algoritmo_hiperparametros_y_versiones(
    predictor: LogisticRegressionPredictor,
) -> None:
    metadata = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).metadata_tecnica

    assert metadata["algoritmo"] == "LogisticRegression"
    assert metadata["hiperparametros"] == json.dumps(dict(HIPERPARAMETROS), sort_keys=True)
    assert metadata["metodo_factores"] == METODO_FACTORES == "shap_lineal"
    assert "StandardScaler()" in metadata["preprocesamiento"]
    assert json.loads(metadata["variables_numericas"]) == NUMERICAS
    assert json.loads(metadata["variables_categoricas"]) == CATEGORICAS
    for clave in ("python", "scikit_learn", "numpy", "pandas", "joblib", "shap"):
        assert re.fullmatch(r"\d+\.\d+.*", metadata[clave])
    assert metadata["filas_entrenamiento"] == "300"
    assert all(isinstance(v, str) for v in metadata.values())


def test_cargar_artefacto_del_random_forest_lanza_error_sin_datos() -> None:
    rf = RandomForestPredictor().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto

    with pytest.raises(ValueError, match="formato esperado") as error:
        cargar_artefacto(rf)
    assert "MENSUAL" not in str(error.value)


def test_artefacto_desde_contenido_rechaza_lo_que_no_es_un_diccionario() -> None:
    with pytest.raises(ValueError, match="formato esperado"):
        artefacto_desde_contenido(["no", "es", "un", "artefacto"])


def test_artefacto_desde_contenido_rechaza_otro_algoritmo(artefacto: bytes) -> None:
    contenido = dict(joblib.load(io.BytesIO(artefacto)))
    contenido["algoritmo"] = "RandomForestClassifier"

    with pytest.raises(ValueError, match="formato esperado"):
        artefacto_desde_contenido(contenido)


# ---------------------------------------------------------------- entrenamiento y score


def test_train_con_longitudes_distintas_lanza_error(predictor: LogisticRegressionPredictor) -> None:
    with pytest.raises(ValueError, match="etiqueta"):
        predictor.train(FILAS, ETIQUETAS[:-1], NUMERICAS, CATEGORICAS)


def test_train_con_una_sola_clase_lanza_error(predictor: LogisticRegressionPredictor) -> None:
    with pytest.raises(ValueError, match="clases"):
        predictor.train(FILAS, [1] * len(FILAS), NUMERICAS, CATEGORICAS)


def test_predict_sin_filas_devuelve_lista_vacia(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    assert predictor.predict(artefacto, []) == []


def test_score_es_predict_proba_cuantizado_a_ocho_decimales(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    modelo = cargar_artefacto(artefacto)
    probabilidades = modelo.pipeline.predict_proba(
        _a_frame(FILAS, modelo.numericas, modelo.categoricas)
    )[:, 1]
    esperados = [
        Decimal(float(p)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        for p in probabilidades
    ]

    predicciones = predictor.predict(artefacto, FILAS)

    assert all(isinstance(p, Prediction) and isinstance(p.score, Decimal) for p in predicciones)
    assert [p.score for p in predicciones] == esperados


def test_dos_entrenamientos_iguales_dan_las_mismas_probabilidades(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    otro = LogisticRegressionPredictor().train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).artefacto

    assert predictor.predict(otro, FILAS) == predictor.predict(artefacto, FILAS)


def test_categoria_no_vista_y_numericos_none_no_fallan(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    fila = dict(FILAS[0])
    fila["mes_vencimiento"] = "2027-01"
    for v in NUMERICAS:
        fila[v] = None

    (prediccion,) = predictor.predict(artefacto, [fila])

    assert Decimal(0) <= prediccion.score <= Decimal(1)


# ---------------------------------------------------------------- SHAP lineal (definicion (b))


def test_aportes_cumplen_la_aditividad_con_decision_function(artefacto: bytes) -> None:
    modelo = cargar_artefacto(artefacto)
    frame = _a_frame(FILAS, modelo.numericas, modelo.categoricas)

    aportes = aportes_lineales(modelo, frame)

    decision = modelo.pipeline.decision_function(frame)
    assert aportes.variables == (*NUMERICAS, *CATEGORICAS)
    assert np.max(np.abs(aportes.valor_base + aportes.valores.sum(axis=1) - decision)) < TOLERANCIA


def test_aportes_iguales_a_shap_linear_explainer_con_fondo_completo(artefacto: bytes) -> None:
    modelo = cargar_artefacto(artefacto)
    fondo = _matriz_preparada(artefacto, FILAS)
    explicador = shap.LinearExplainer(
        modelo.pipeline.named_steps["modelo"],
        shap.maskers.Independent(fondo, max_samples=len(fondo)),
    )
    por_columna = np.asarray(explicador.shap_values(fondo[:40]), dtype=np.float64)
    columnas = modelo.pipeline.named_steps["preparacion"].get_feature_names_out()
    esperados = np.zeros((40, len(NUMERICAS) + len(CATEGORICAS)))
    variables = [*NUMERICAS, *CATEGORICAS]
    for k, columna in enumerate(columnas):
        tipo, nombre = columna.split("__", 1)
        original = (
            nombre
            if tipo == "numericas"
            else next(v for v in CATEGORICAS if nombre.startswith(v + "_"))
        )
        esperados[:, variables.index(original)] += por_columna[:, k]

    aportes = aportes_lineales(modelo, _a_frame(FILAS[:40], modelo.numericas, modelo.categoricas))

    assert np.max(np.abs(aportes.valores - esperados)) < TOLERANCIA
    base_shap = float(np.atleast_1d(explicador.expected_value)[0])
    assert abs(aportes.valor_base - base_shap) < TOLERANCIA


def test_aporte_de_un_caso_a_mano_es_coef_por_desvio_de_la_media(artefacto: bytes) -> None:
    modelo = cargar_artefacto(artefacto)
    regresion = modelo.pipeline.named_steps["modelo"]
    fila: FeatureRow = {
        "ciclos_previos": 0,
        "antiguedad_dias": 10,
        "duracion_modelo": 90,
        "monto_actual": Decimal("90.00"),
        "monto_historico": Decimal("0"),
        "dias_desde_ultima_membresia": None,
        "plan": "TRIMESTRAL",
        "mes_vencimiento": "2026-03",
    }
    x = _matriz_preparada(artefacto, [fila])[0]
    media = _matriz_preparada(artefacto, FILAS).mean(axis=0)
    coef = regresion.coef_[0]
    columnas = list(modelo.pipeline.named_steps["preparacion"].get_feature_names_out())
    de_plan = [k for k, c in enumerate(columnas) if c.startswith("categoricas__plan_")]
    esperado_plan = sum(coef[k] * (x[k] - media[k]) for k in de_plan)
    k_ciclos = columnas.index("numericas__ciclos_previos")

    aportes = aportes_lineales(modelo, _a_frame([fila], modelo.numericas, modelo.categoricas))

    plan = aportes.valores[0, aportes.variables.index("plan")]
    ciclos = aportes.valores[0, aportes.variables.index("ciclos_previos")]
    assert abs(plan - esperado_plan) < TOLERANCIA
    assert abs(ciclos - coef[k_ciclos] * (x[k_ciclos] - media[k_ciclos])) < TOLERANCIA
    assert plan > APORTE_MINIMO  # TRIMESTRAL sube el riesgo en los datos sinteticos


# ---------------------------------------------------------------- factores principales


FORMATO_FACTOR = re.compile(r"^(?P<nombre>[^:]+): (?P<valor>.+) \(\+(?P<aporte>\d+,\d{2})\)$")


def test_factores_salen_de_los_aportes_lineales_con_el_formato_del_notebook(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    modelo = cargar_artefacto(artefacto)
    frame = _a_frame(FILAS, modelo.numericas, modelo.categoricas)
    aportes = aportes_lineales(modelo, frame)

    predicciones = predictor.predict(artefacto, FILAS)

    assert any(p.factores_principales for p in predicciones)
    for i, p in enumerate(predicciones):
        candidatos = {
            v: float(aportes.valores[i, aportes.variables.index(v)])
            for v in NOMBRE_VARIABLE
            if v in aportes.variables
        }
        esperados = tuple(
            f"{NOMBRE_VARIABLE[v]}: {texto_valor(v, frame.iloc[i][v], modelo.numericas)} "
            f"({formatear_aporte(a)})"
            for v, a in seleccionar_factores(candidatos)
        )
        assert p.factores_principales == esperados
        assert len(p.factores_principales) <= 3
        valores = []
        for texto in p.factores_principales:
            coincidencia = FORMATO_FACTOR.match(texto)
            assert coincidencia is not None, texto
            valores.append(Decimal(coincidencia["aporte"].replace(",", ".")))
        assert valores == sorted(valores, reverse=True)


def test_factores_nunca_mencionan_el_mes_de_vencimiento(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    for p in predictor.predict(artefacto, FILAS):
        assert not any("2025-" in f or "2026-" in f for f in p.factores_principales)
        assert all(f.split(":", 1)[0] in NOMBRE_VARIABLE.values() for f in p.factores_principales)


def test_factor_del_plan_trimestral_con_formato_exacto(
    predictor: LogisticRegressionPredictor, artefacto: bytes
) -> None:
    fila = dict(FILAS[0])
    fila["plan"] = "TRIMESTRAL"
    modelo = cargar_artefacto(artefacto)
    aportes = aportes_lineales(modelo, _a_frame([fila], modelo.numericas, modelo.categoricas))
    aporte_plan = float(aportes.valores[0, aportes.variables.index("plan")])

    (prediccion,) = predictor.predict(artefacto, [fila])

    assert f"Plan: TRIMESTRAL ({formatear_aporte(aporte_plan)})" in prediccion.factores_principales


def test_funciona_con_el_conjunto_amplio_de_variables(
    predictor: LogisticRegressionPredictor,
) -> None:
    filas = [{**f, "forma_pago": "EFECTIVO", "inicio_aproximado": "False"} for f in FILAS]
    numericas, categoricas = list(VARIABLES_NUMERICAS), list(VARIABLES_CATEGORICAS)

    entrenado = predictor.train(filas, ETIQUETAS, numericas, categoricas)
    predicciones = predictor.predict(entrenado.artefacto, filas[:5])

    assert len(predicciones) == 5
