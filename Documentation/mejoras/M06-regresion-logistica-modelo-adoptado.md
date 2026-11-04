# M06 · Regresión Logística como modelo adoptado

| Campo | Valor |
|---|---|
| **Fecha** | 2026-11-03 |
| **Origen** | Petición del usuario tras M05: adoptar el modelo que elige la regla de selección y eliminar la desviación |
| **Alcance** | Notebook oficial (v3), adaptador del modelo en la app, `verificar_lista.py`, pruebas, datos del stack principal y documentación |
| **Notebook** | [`Notebookes/Prototipo_Final_Mtabolic.ipynb`](../../Notebookes/Prototipo_Final_Mtabolic.ipynb), versión v3 |
| **Modelo adoptado** | **Regresión Logística** (la que elige la regla); el Random Forest queda como comparación |
| **Decisión de arquitectura** | [ADR-016](../adr/ADR-016-regresion-logistica-como-modelo-adoptado.md) |
| **Datos fuente (fuera de git)** | `salidas/prototipo_final/` |

Solo cifras agregadas: ningún nombre, cédula ni código de socio. Sustituye la decisión de [M05 §5](M05-correcciones-evaluacion-semana-10.md); el resto de M05 (partición, métricas, bootstrap) sigue vigente.

## 1. Qué cambió

| Pieza | v2 (M05) | v3 (M06) |
|---|---|---|
| Modelo adoptado | Random Forest, desviación de la regla | Regresión Logística = modelo seleccionado (`desviacion_regla = False`) |
| Hiperparámetros | RF `n_estimators=300, max_depth=6, min_samples_leaf=20, class_weight="balanced"` | RL `class_weight="balanced", max_iter=2000, random_state=42` (C=1,0, lbfgs, l2) |
| Umbral de evaluación | 0,32 | 0,21 |
| Cortes de riesgo | 0,70 / 0,50 | 0,70 / 0,50 (sin cambio, decisión del usuario) |
| Motivos | SHAP `TreeExplainer` (probabilidad) | SHAP lineal (log-odds), `metodo_factores = "shap_lineal"` |
| Lista de septiembre | 57 socios: ALTO 2, MEDIO 39, BAJO 16 | 57 socios: ALTO 9, MEDIO 33, BAJO 15 |
| Controles del notebook | 17 | 21, `TODOS LOS CONTROLES OK` |

Sin cambios: datos (2.748 registros, 1.410 socios, 1.564 evaluables, 1.098 no renovaron), partición 721 / 180 / 277, cronología, prueba anti-fuga (0), variables T−30, preparación, priorización, top 25, contrato de la API y esquema.

## 2. Por qué

La regla fijada de antemano elige la Regresión Logística (M05 §4.1). En la comprobación final también es mejor:

| Métrica | Regresión Logística | Random Forest |
|---|---|---|
| PR-AUC validación | **0,724** | 0,707 |
| PR-AUC prueba | **0,820** (0,8197) | 0,787 |
| Precisión@25 prueba | **1,00** (25 de 25) | 0,76 (19 de 25) |
| Matriz de confusión en prueba (VN, FP, FN, VP) | 22, 70, 15, 170 | 5, 87, 3, 182 |

Bootstrap por socio (M05 §4.3): la diferencia de PR-AUC RF − RL incluye el cero; en Precisión@25 de prueba RF − RL = −0,22 (−0,40 a −0,08), que excluye el cero. Adoptar la RL deja la tesis sin desviación que justificar.

## 3. Cortes de riesgo

El plan proponía fijar los cortes en validación (ALTO = menor corte con precisión ≥ 0,90 y ≥ 10 socios por encima; MEDIO con ≥ 0,80). Con la RL **no hay corte ALTO que cumpla** en validación, así que el usuario decidió mantener los cortes fijos de ADR-014 (0,70 / 0,50). Las bandas se informan solo como descripción (`bandas_riesgo.csv`):

| Banda | Validación: membresías · precisión | Prueba: membresías · precisión |
|---|---|---|
| ALTO (≥ 0,70) | 32 · 0,656 | 45 · 0,889 |
| MEDIO (0,50–0,70) | 80 · 0,712 | 133 · 0,707 |
| BAJO (< 0,50) | 68 · 0,529 | 99 · 0,515 |

Precisión = proporción que no renovó. En validación la banda ALTO no ordena mejor que MEDIO; en prueba sí. Es una limitación que se declara.

## 4. Motivos con SHAP lineal

- Fórmula: `aporte_k = coef_k · (X'_k − μ_k)`, con `X'` la matriz preparada y `μ` su media en el conjunto de entrenamiento del modelo (el operativo: los 1.564 evaluables). Las columnas *one-hot* se suman a su variable. Unidad: log-odds; `valor base + Σ aportes = decision_function`.
- Valor base del modelo evaluado: 0,1469 log-odds. Error de aditividad 4,4e-16; diferencia con `shap.LinearExplainer` (fondo completo) 0,0.
- Regla igual que antes: hasta 3 aportes > 0,005, de mayor a menor, nunca `mes_vencimiento`. Ejemplo: `Plan: TRIMESTRAL (+0,35); Duración del plan (días): 123 (+0,18); Monto histórico (USD): 0 (+0,16)`.
- SHAP lineal medio absoluto (log-odds), validación / prueba: membresías previas 0,602 / 0,817; duración del plan 0,518 / 0,226; monto actual 0,505 / 0,228; plan 0,338 / 0,224; mes de vencimiento 0,322 / 0,322; monto histórico 0,124 / 0,167; días desde la anterior 0,110 / 0,108; antigüedad 0,043 / 0,043.
- `mes_vencimiento` aporta 0,322 en los dos conjuntos aunque sus meses de 2026 no existen en entrenamiento: con SHAP lineal, una categoría no vista vale `coef · (0 − μ)` para cada columna del mes, que es un desplazamiento constante, no información del socio. Por eso nunca es motivo.
- Los aportes en log-odds no se comparan en magnitud con los del Random Forest (probabilidad).

## 5. Lista de septiembre (producto)

57 socios (cartera 59, ya renovaron 2): ALTO 9, MEDIO 33, BAJO 15. De los 25 primeros, 23 coinciden con los del Random Forest. El top 25 del Random Forest sigue siendo igual al de `MVP.ipynb` (control de continuidad).

## 6. App

- `LogisticRegressionPredictor` (artefacto `formato = 2`) y `PredictorAdoptado`, que entrena siempre RL y predice según el formato del artefacto (2 → RL, 1 → RF heredado). Así se siguen leyendo las listas y comparando en CU-02 vigentes RF antiguos.
- `adoptar-modelo` registra "Adopción del modelo de Regresión Logística (M06)".
- Stack principal: respaldo y reinicio el 2026-11-03; v1 RL (`shap_lineal`), 0 listas, 3 campañas de ejemplo. e2e: v4 RL por `adoptar-modelo` (v1–v3 RF conservadas). Demo: RL, lista de 78 filas MEDIO 33 / BAJO 45, sin ALTO.

## 7. Cómo se verificó

| Verificación | Resultado |
|---|---|
| Notebook v3 con kernel limpio | 21/21 controles OK, sin errores; salidas sin cédulas ni nombres |
| `verificar_lista.py` frente a `salidas/prototipo_final/` | Código 0, 0 diferencias en 12 apartados (conteos, variables, medianas, método, algoritmo, hiperparámetros, cortes, filas, probabilidades, niveles, motivos, orden) |
| `pytest -m unit` | 1.507 aprobadas |
| `pytest` completo (PostgreSQL 16 efímero) | 2.172 aprobadas |
| `ruff`, `mypy app`, `lint-imports` | Sin errores (7 contratos) |
| Playwright E2E contra `mtabolic-e2e` | 11 aprobadas (`--workers=1`) |
| Revisión de seguridad | Sin hallazgos bloqueantes; dos *low* diferidos (códigos seudónimos con fecha/plan/monto en salidas del notebook, como en v2; `joblib.load` antes de validar el formato) |

## 8. Qué cambiar en el documento de la tesis

1. **Selección del modelo:** decir que la regla elige la Regresión Logística y que es el modelo adoptado; eliminar el apartado que justificaba la desviación a favor del Random Forest (M05 §5).
2. **Tablas de resultados (validación y prueba):** marcar como adoptada la Regresión Logística (umbral 0,21); el Random Forest pasa a "comparación". Las cifras no cambian (M05 §4.1–§4.4).
3. **Matriz de confusión del modelo adoptado en prueba:** 22, 70, 15, 170 (VN, FP, FN, VP) en lugar de 5, 87, 3, 182.
4. **Niveles de riesgo:** mantener 0,70 / 0,50 y añadir la tabla de bandas de §3 con la limitación de validación.
5. **Interpretabilidad:** sustituir SHAP `TreeExplainer` del modelo adoptado por SHAP lineal (fórmula, log-odds, valor base 0,1469, aditividad, coincidencia con `LinearExplainer`) y la tabla de importancias de §4; el `TreeExplainer` queda como comparación. Explicar por qué `mes_vencimiento` no es motivo.
6. **Lista de septiembre:** 57 socios, ALTO 9, MEDIO 33, BAJO 15; ejemplo de motivos de §4; 23/25 coinciden con el RF.
7. **Arquitectura de la app:** el adaptador del modelo es `LogisticRegressionPredictor` con compatibilidad de lectura de artefactos RF (ADR-016).
8. **Verificación:** cifras de §7 (21 controles, 0 diferencias, 2.172 pruebas, 11 E2E).
9. **Limitaciones:** quitar "el modelo adoptado no es el que elige la regla"; añadir que la banda ALTO no supera a MEDIO en validación y que el demo sintético no tiene nivel ALTO.

Figuras: no se generaron figuras nuevas en `Documentation/claude/mejoras/M06/`; la gráfica de importancia SHAP lineal está en la Parte 9 del notebook.

## 9. Requerimiento

R-020 (harness `req`). Archivos de código: `Backend/app/infrastructure/ml/{regresion_logistica,predictor_adoptado,random_forest}.py`, `Backend/app/api/dependencies.py`, `Backend/app/application/modelo/adoptar_modelo.py`, `Backend/app/domain/modelo/umbrales.py` (docstring), `Backend/scripts/verificar_lista.py` y sus pruebas. Commits: pendientes del usuario.
