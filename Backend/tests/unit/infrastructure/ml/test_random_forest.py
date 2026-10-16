"""Adaptador scikit-learn de PredictorModel con datos sinteticos deterministas (sin personas)."""

import math
import random
import re
from collections.abc import Sequence
from dataclasses import replace
from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np
import pandas as pd  # type: ignore[import-untyped]  # pandas no publica tipos (sin pandas-stubs)
import pytest

from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel
from app.domain.modelo.variables import (
    VARIABLES_CATEGORICAS,
    VARIABLES_CATEGORICAS_MODELO,
    VARIABLES_EXCLUIBLES_M01,
    VARIABLES_NUMERICAS,
    VARIABLES_NUMERICAS_MODELO,
)
from app.infrastructure.ml.random_forest import (
    APORTE_MINIMO,
    MAX_FACTORES,
    NOMBRE_VARIABLE,
    ArtefactoRandomForest,
    RandomForestPredictor,
    _a_frame,
    _a_score,
    aportes_shap,
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


# ---------------------------------------------------------------- motivos con SHAP (M03, R-017)


def _modelo(artefacto: bytes) -> ArtefactoRandomForest:
    return cargar_artefacto(artefacto)


@pytest.fixture(scope="module")
def artefacto_variante(predictor: RandomForestPredictor) -> bytes:
    """Artefacto con el conjunto vigente de la app (sin ``forma_pago`` ni ``inicio_aproximado``)."""
    return predictor.train(
        FILAS, ETIQUETAS, list(VARIABLES_NUMERICAS_MODELO), list(VARIABLES_CATEGORICAS_MODELO)
    ).artefacto


def _frame(modelo: ArtefactoRandomForest, filas: Sequence[FeatureRow]) -> pd.DataFrame:
    return _a_frame(filas, modelo.numericas, modelo.categoricas)


@pytest.mark.parametrize("nombre", ["artefacto", "artefacto_variante"])
def test_aportes_shap_base_mas_suma_igual_a_la_probabilidad(
    nombre: str, request: pytest.FixtureRequest
) -> None:
    modelo = _modelo(request.getfixturevalue(nombre))
    frame = _frame(modelo, FILAS)

    shap_filas = aportes_shap(modelo, frame)

    probabilidades = modelo.pipeline.predict_proba(frame)[:, 1]
    assert shap_filas.variables == (*modelo.numericas, *modelo.categoricas)
    assert shap_filas.valores.shape == (len(FILAS), len(shap_filas.variables))
    reconstruida = shap_filas.valor_base + shap_filas.valores.sum(axis=1)
    assert np.max(np.abs(reconstruida - probabilidades)) < 1e-6


def test_aportes_shap_agrega_el_one_hot_del_plan_en_una_sola_variable(artefacto: bytes) -> None:
    modelo = _modelo(artefacto)

    shap_filas = aportes_shap(modelo, _frame(modelo, FILAS[:10]))

    assert shap_filas.variables.count("plan") == 1
    assert not any(v.startswith("plan_") for v in shap_filas.variables)


def test_factor_elegido_es_el_shap_agregado_redondeado_a_dos_decimales(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    modelo = _modelo(artefacto)
    shap_filas = aportes_shap(modelo, _frame(modelo, FILAS))
    nombre_a_variable = {nombre: v for v, nombre in NOMBRE_VARIABLE.items()}

    predicciones = predictor.predecir_con(modelo, FILAS)

    comprobados = 0
    for i, p in enumerate(predicciones):
        aportes = dict(zip(shap_filas.variables, shap_filas.valores[i], strict=True))
        esperados = seleccionar_factores(
            {v: float(aportes[v]) for v in NOMBRE_VARIABLE if v in aportes}
        )
        assert [nombre_a_variable[f.split(":")[0]] for f in p.factores_principales] == [
            v for v, _ in esperados
        ]
        for f, (_, a) in zip(p.factores_principales, esperados, strict=True):
            assert f.endswith(f"({formatear_aporte(a)})")
            comprobados += 1
    assert comprobados > 0


def test_factores_sin_aporte_positivo_suficiente_son_tupla_vacia(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    modelo = _modelo(artefacto)
    shap_filas = aportes_shap(modelo, _frame(modelo, FILAS))
    explicables = [i for i, v in enumerate(shap_filas.variables) if v in NOMBRE_VARIABLE]
    sin_motivos = [
        i
        for i in range(len(FILAS))
        if all(shap_filas.valores[i, j] <= APORTE_MINIMO for j in explicables)
    ]
    assert sin_motivos, "los datos sinteticos deben tener filas sin aportes positivos"

    predicciones = predictor.predecir_con(modelo, [FILAS[i] for i in sin_motivos])

    assert all(p.factores_principales == () for p in predicciones)


def test_mes_vencimiento_nunca_es_motivo_aunque_sea_el_mayor_aporte(
    predictor: RandomForestPredictor,
) -> None:
    # Etiqueta que depende solo del mes: su SHAP domina, pero no se muestra (no accionable).
    # Dos meses (150 filas cada uno) para que el one-hot supere min_samples_leaf=20.
    filas = [{**f, "mes_vencimiento": MESES[i % 2]} for i, f in enumerate(FILAS)]
    etiquetas = [i % 2 for i in range(len(filas))]
    modelo = _modelo(predictor.train(filas, etiquetas, NUMERICAS, CATEGORICAS).artefacto)
    shap_filas = aportes_shap(modelo, _frame(modelo, filas))
    columna_mes = shap_filas.variables.index("mes_vencimiento")
    assert np.max(shap_filas.valores[:, columna_mes]) > np.max(
        np.delete(shap_filas.valores, columna_mes, axis=1)
    )

    predicciones = predictor.predecir_con(modelo, filas)

    for p in predicciones:
        assert len(p.factores_principales) <= MAX_FACTORES
        for f in p.factores_principales:
            assert not re.match(r"(?i)mes", f)
            assert f.split(":")[0] in set(NOMBRE_VARIABLE.values())


def test_artefacto_variante_explica_solo_sus_variables(
    predictor: RandomForestPredictor, artefacto_variante: bytes
) -> None:
    predicciones = predictor.predict(artefacto_variante, FILAS)

    nombres = {f.split(":")[0] for p in predicciones for f in p.factores_principales}
    assert nombres
    assert nombres <= {
        NOMBRE_VARIABLE[v] for v in NOMBRE_VARIABLE if v not in VARIABLES_EXCLUIBLES_M01
    }


def test_un_motivo_por_variable_en_cada_fila(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    for p in predictor.predict(artefacto, FILAS):
        nombres = [f.split(":")[0] for f in p.factores_principales]
        assert len(nombres) == len(set(nombres))


def test_metadata_registra_shap_y_metodo_de_factores(predictor: RandomForestPredictor) -> None:
    metadata = predictor.train(FILAS, ETIQUETAS, NUMERICAS, CATEGORICAS).metadata_tecnica

    assert metadata["shap"] == "0.54.1"
    assert metadata["metodo_factores"] == "shap"


def test_predecir_con_referencia_distinta_da_los_mismos_motivos_y_scores(
    predictor: RandomForestPredictor, artefacto: bytes
) -> None:
    # R-017 T5: la referencia se sigue cargando (compatibilidad) pero ya no interviene.
    modelo = _modelo(artefacto)
    otra_referencia = {
        **modelo.referencia,
        "plan": "TRIMESTRAL",
        "ciclos_previos": 99.0,
        "monto_actual": 0.0,
    }
    alterado = replace(modelo, referencia=otra_referencia)

    original = predictor.predecir_con(modelo, FILAS)
    con_otra = predictor.predecir_con(alterado, FILAS)

    assert alterado.referencia != modelo.referencia
    assert con_otra == original


def test_seleccionar_factores_con_empate_conserva_el_orden_de_entrada() -> None:
    # Regla (e): empate estable por el orden de NOMBRE_VARIABLE (el orden del mapa de aportes).
    aportes = {"ciclos_previos": 0.04, "monto_actual": 0.04, "plan": 0.04, "forma_pago": 0.04}

    assert seleccionar_factores(aportes) == [
        ("ciclos_previos", 0.04),
        ("monto_actual", 0.04),
        ("plan", 0.04),
    ]


def test_seleccionar_factores_aporte_igual_al_minimo_se_descarta() -> None:
    assert seleccionar_factores({"plan": APORTE_MINIMO, "monto_actual": APORTE_MINIMO + 1e-9}) == [
        ("monto_actual", APORTE_MINIMO + 1e-9)
    ]


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
