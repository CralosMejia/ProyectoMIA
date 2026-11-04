# ADR-016 · Regresión Logística como modelo adoptado (notebook y app)

- **Estado:** aceptada · 2026-11-03 · R-020 (mejora [M06](../mejoras/M06-regresion-logistica-modelo-adoptado.md))
- **Origen:** [mejoras/M05 §4–§5](../mejoras/M05-correcciones-evaluacion-semana-10.md) · petición del usuario · definiciones (a)–(e) de R-020 · decisión del usuario sobre los cortes (2026-11-03)
- **Sustituye en parte:** [M05 §5](../mejoras/M05-correcciones-evaluacion-semana-10.md) (desviación a favor del Random Forest); el algoritmo de [ADR-005](ADR-005-fidelidad-al-notebook-del-modelo-v1.md) y el método de motivos de [ADR-015](ADR-015-motivos-con-shap-en-la-app.md) para los modelos nuevos · **mantiene:** [ADR-014](ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) (variables, cortes 0,70/0,50, `adoptar-modelo`), [ADR-011](ADR-011-reglas-del-reentrenamiento.md), [ADR-003](ADR-003-reentrenamiento-y-versionado.md)

## Contexto

Con la partición corregida de M05, la regla de selección fijada de antemano (superar a la referencia en F1, PR-AUC y Brier en validación; gana el mayor PR-AUC) elige la Regresión Logística: PR-AUC de validación 0,724 frente a 0,707 del Random Forest. M05 adoptó el Random Forest como desviación explícita porque era el modelo ya integrado en la app. En prueba la Regresión Logística fue mejor (PR-AUC 0,820 vs 0,787; Precisión@25 1,00 vs 0,76, intervalo bootstrap de RF − RL −0,40 a −0,08). Mantener una desviación de la regla obligaba a justificarla en la tesis; el usuario pidió adoptar el modelo que elige la regla.

## Decisión

1. **Modelo adoptado = Regresión Logística** en el notebook oficial (v3) y en la app: `LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)`, resto por defecto, con la misma preparación (mediana/moda, `StandardScaler`, `OneHotEncoder(handle_unknown="ignore")`) y las mismas variables T−30 (`CONJUNTO_MODELO`). `modelo_adoptado == modelo_seleccionado`; la desviación desaparece. Umbral de evaluación 0,21.
2. **Cortes de riesgo fijos 0,70 / 0,50 (ADR-014), también para la RL** (decisión del usuario). La regla por precisión propuesta en el plan (ALTO = menor corte con precisión ≥ 0,90 y ≥ 10 socios en validación) no se cumplía; las bandas se informan solo como descripción (§M06).
3. **Motivos = SHAP lineal** analítico: `aporte_k = coef_k · (X'_k − μ_k)`, con `μ` la media de la matriz preparada del conjunto con que se entrenó el modelo; *one-hot* sumadas a su variable; unidad log-odds; `base + Σ aportes = decision_function`. Coincide con `shap.LinearExplainer` con `Independent(X'_ent, max_samples=len(X'_ent))` (diferencia 0,0). Misma regla de selección y formato que antes (hasta 3, > 0,005, sin `mes_vencimiento`). `metodo_factores = "shap_lineal"`.
4. **App:** adaptador `LogisticRegressionPredictor` (`app/infrastructure/ml/regresion_logistica.py`, artefacto `formato = 2`, `algoritmo = "LogisticRegression"`, `μ` guardada) y `PredictorAdoptado` (`predictor_adoptado.py`) en el composition root: entrena siempre RL; al predecir lee el `formato` (2 → RL, 1 → `RandomForestPredictor`, otro → `ValueError`). Migración (CU-03), listas (CU-04), reentrenamiento (CU-02) y `adoptar-modelo` (motivo "Adopción del modelo de Regresión Logística (M06)") usan `PredictorAdoptado`.
5. Sin cambios de contrato de API ni de esquema (`metadata_tecnica` ya guarda el algoritmo).

## Alternativas descartadas

- **Mantener el Random Forest (M05):** contradice la regla fijada de antemano y es peor en prueba en las dos métricas de uso real.
- **Cortes por precisión en validación:** con la RL no hay banda ALTO que llegue a 0,90 con ≥ 10 socios; bajar la exigencia sería ajustar los cortes a la vista de los datos.
- **Motivos con `shap.LinearExplainer` en la app:** el `max_samples` por defecto (100) submuestrea y rompe la paridad; la fórmula analítica es exacta y no depende del masker.
- **Borrar el adaptador RF:** los volúmenes `mtabolic-e2e`/`mtabolic-demo` y las listas antiguas tienen artefactos RF; sin el despacho por formato no se podrían leer ni comparar en CU-02.

## Consecuencias

- `verificar_lista.py` con 0 diferencias en 12 apartados (incluidos algoritmo, hiperparámetros y cortes); lista de septiembre: 57 socios, ALTO 9 / MEDIO 33 / BAJO 15.
- Stack principal reiniciado el 2026-11-03 tras respaldo: v1 RL, sin listas. e2e y demo pasaron a RL con `adoptar-modelo` (versiones RF conservadas). El demo con RL no muestra nivel ALTO.
- Los motivos se expresan en log-odds (no en probabilidad): no se comparan numéricamente con los de listas RF anteriores. Las listas guardadas conservan sus motivos y niveles.
- Riesgo diferido (S2): `joblib.load` ocurre antes de validar el `formato`; mismo riesgo que antes, los bytes solo vienen de `modelos.artefacto`.
- Detalle: [backend/12 §Modelo](../docs/backend/12-modelo-y-listas.md).
