# M01 · Modelo sin fuga temporal

| | |
|---|---|
| **Requerimiento** | R-015 (harness), cerrado el 2026-10-15 |
| **Notebook** | `Notebookes/MVP.ipynb`: bloque M01 tras el resumen ejecutivo, §7.2, §7.5 (nueva), §8.2, §11–§15 (§12.11 nueva) |
| **Decisiones** | [ADR-014](../adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) · [12 · Modelo y listas](../docs/backend/12-modelo-y-listas.md) |
| **Datos fuente (fuera de git)** | `salidas/m01/antes/*.csv`, `salidas/m01/despues/*` (`comparacion_antes_despues.csv`, `particiones_con_margenes.csv`, `bootstrap_por_socio_*.csv`, `importancia_permutacion.csv`, `decision_variante.json`, `prueba_anti_fuga*.csv`, `parametros_modelo_operativo.json`) |
| **Figuras (fuera de git)** | `Documentation/claude/mejoras/M01/antes/` y `/despues/` |

Este documento reúne todo lo necesario para actualizar la tesis. Solo contiene cifras agregadas: ningún código de socio, nombre ni cédula.

---

## 1. Recomendación del tutor y por qué

El tutor observó que el modelo podía estar aprendiendo con información que no estaría disponible en el momento real de la predicción (**fuga de información** o *data leakage*). En el caso de uso, la lista se genera 30 días antes del vencimiento (T−30); cualquier dato posterior a esa fecha que entre en las variables, en la imputación o en la separación de conjuntos vuelve optimistas las métricas y hace que el desempeño en producción sea peor que el reportado. Recomendó cinco puntos:

1. **Variables solo con datos hasta T−30.** Ningún registro con fecha posterior a la fecha de predicción puede influir en las variables históricas del ciclo.
2. **Medianas de imputación calculadas solo con el conjunto de entrenamiento** y aplicadas tal cual a validación y prueba.
3. **Márgenes entre conjuntos** en la partición cronológica, para que la etiqueta de un ciclo de entrenamiento (que se conoce en T+30) no se solape con el periodo del conjunto siguiente.
4. **Reentrenar y reportar de nuevo** las métricas con semilla fija, con intervalos de confianza obtenidos por *bootstrap* **por socio** (no por fila, porque un socio aporta varios ciclos correlacionados) y la importancia por permutación.
5. **Evaluar una variante sin `forma_pago` ni `inicio_aproximado`**: la primera es poco informativa y la segunda es una bandera de calidad del dato (la fecha de inicio se aproximó con el mes de la hoja), no una característica del socio.

## 2. Qué cambió en la metodología

| Aspecto | Antes (MVP entregado) | Después (M01) |
|---|---|---|
| Historial de un ciclo | Registros del socio con actividad anterior a la del ciclo, sin tope temporal | Además, actividad ≤ T−30 |
| `antiguedad_dias` | Desde la primera actividad hasta la fecha del ciclo | Hasta T−30 |
| Medianas de monto | Todos los ciclos modelables | Solo entrenamiento (evaluación) / solo evaluables con que se entrena (modelo operativo) |
| Partición | Cronológica, contigua, sin márgenes | Con márgenes de 30 días descartados |
| Prueba de fuga | No existía | Prueba automática §7.5 escrita **antes** de corregir (TDD) y repetida en §14.2 |
| Bootstrap | Por fila, solo RF − piso en prueba | Por socio, 1.000 réplicas, para cada modelo, el piso y las diferencias |
| Importancia | Por permutación solo para RF | RF y RL, conjunto completo y variante |
| Variables del modelo | 10 | 8 (variante sin `forma_pago` ni `inicio_aproximado`) |
| Niveles de riesgo en la app | Percentiles 20/30/50 | Cortes fijos del notebook 0,70 / 0,50 |

## 3. Definición exacta de cada variable (corte T−30)

T = fecha de vencimiento del ciclo; T−30 = fecha de predicción. `fecha_actividad` = fecha de inicio o, si falta, el primer día del mes de la hoja (`inicio_aproximado = True`).

**Historial admitido** de un ciclo: registros del mismo socio, con estado distinto de `EXCLUIDO` (evaluables y pendientes), distintos del ciclo, con `fecha_actividad` anterior a la del ciclo **y** `fecha_actividad ≤ T−30`. Un registro con actividad exactamente en T−30 cuenta; en T−29, no.

| Variable | Tipo | Definición | En el modelo elegido |
|---|---|---|---|
| `ciclos_previos` | numérica | número de registros del historial admitido | sí |
| `monto_historico` | numérica | suma de montos cobrados del historial admitido (vacío = 0) | sí |
| `dias_desde_ultima_membresia` | numérica | `fecha_actividad` del ciclo − máxima `fecha_actividad` del historial admitido, en días; vacío si no hay historial (imputado con la mediana de entrenamiento en el pipeline) | sí |
| `antiguedad_dias` | numérica | máx(0, T−30 − mínima `fecha_actividad` del historial admitido y del ciclo) | sí |
| `duracion_modelo` | numérica | fin − inicio en días; si falta, duración estándar del plan (mensual 30, trimestral 90, semestral 180, anual 365, otro 30) | sí |
| `monto_actual` | numérica | monto cobrado del ciclo; si falta, mediana del plan; si falta, mediana general (medianas de entrenamiento) | sí |
| `plan` | categórica | plan normalizado (MENSUAL, TRIMESTRAL, SEMESTRAL, ANUAL, OTRO) | sí |
| `mes_vencimiento` | categórica | vencimiento como texto `AAAA-MM` | sí |
| `forma_pago` | categórica | forma de pago normalizada del ciclo | **no** |
| `inicio_aproximado` | categórica | verdadero si la fecha de inicio se aproximó | **no** |

Los campos del propio ciclo (plan, monto, duración, vencimiento) son el objeto de la predicción y se admiten: en T−30 el socio ya contrató la membresía que vence.

**Medianas de monto (USD)**

| Plan | Evaluación: entrenamiento (≤ 01-12-2025) | Operativo / app: 1.564 evaluables | Antes (todos los modelables) |
|---|---|---|---|
| ANUAL | 224,52 | 237,50 | 250,00 |
| MENSUAL | 37,50 | 39,00 | 39,00 |
| OTRO | 65,00 | 65,00 | 65,00 |
| SEMESTRAL | 175,00 | 175,00 | 174,63 |
| TRIMESTRAL | 90,00 | 90,00 | 90,00 |
| General | 39,00 | 39,00 | 39,00 |

Control: alterar los montos de los 815 ciclos fuera de entrenamiento no cambia las medianas de evaluación.

## 4. Partición con márgenes de 30 días

Entrenamiento: vencimiento ≤ 01-12-2025. Margen 1: 02-12 a 31-12-2025 (descartado). Validación: 01-01-2026 a 31-03-2026. Margen 2: abril de 2026 (descartado). Prueba: desde 01-05-2026. El modelo operativo sí usa los ciclos de los márgenes (entrena con los 1.564 evaluables).

| Conjunto | Ciclos | Socios | No renovaciones | Prevalencia | Vencimientos |
|---|---|---|---|---|---|
| Entrenamiento | 845 | 610 | 628 | 74,3 % | 05-02-2025 a 01-12-2025 |
| Margen 1 (descartado) | 87 | 86 | 66 | 75,9 % | 02-12-2025 a 30-12-2025 |
| Validación | 247 | 198 | 158 | 64,0 % | 01-01-2026 a 29-03-2026 |
| Margen 2 (descartado) | 108 | 107 | 61 | 56,5 % | 02-04-2026 a 30-04-2026 |
| Prueba | 277 | 215 | 185 | 66,8 % | 02-05-2026 a 01-08-2026 |

Antes: entrenamiento 932 (74,5 %), validación 355 (61,7 %), prueba 277 (66,8 %), sin márgenes.

Controles: máx(T entrenamiento) + 30 = 31-12-2025 < mín(T validación) = 01-01-2026; máx(T validación) + 30 = 28-04-2026 < mín(T prueba) = 02-05-2026; ningún socio-ciclo aparece en dos conjuntos (48 socios tienen ciclos distintos en entrenamiento y en prueba).

## 5. Semilla e hiperparámetros

`SEMILLA = 42` en todo: `random_state` de la regresión logística, del Random Forest y de la importancia por permutación; `numpy.random.default_rng(42)` en el bootstrap y en la muestra de la prueba anti-fuga.

- **Random Forest:** `n_estimators=300`, `max_depth=6`, `min_samples_leaf=20`, `class_weight="balanced"`, `random_state=42`.
- **Preprocesamiento:** numéricas con imputación por mediana + estandarización; categóricas con imputación por moda + *one-hot* (`handle_unknown="ignore"`).
- Hiperparámetros sin cambio respecto al MVP. Entorno: Python 3.12, scikit-learn 1.8.0, pandas 3.0.6, numpy 2.5.3.
- **Umbral de clasificación:** el que maximiza F1 en validación (antes RL 0,22 y RF 0,31; completo RL 0,22 y RF 0,31; variante RL 0,20 y RF 0,32).

## 6. Métricas antes / después

RL = regresión logística, RF = Random Forest, Piso = clasificador trivial (siempre "no renueva"). P@25 y Lift@25 sobre los 25 primeros. Selección según §11.3 del notebook.

### 6.1 Validación

| Versión | Modelo | Umbral | PR-AUC | ROC-AUC | Brier | F1 | P@25 | Lift@25 |
|---|---|---|---|---|---|---|---|---|
| Antes (n = 355) | Piso | 0,50 | 0,6169 | 0,5000 | 0,2526 | 0,7631 | 0,6169 | 1,0000 |
| Antes | RL | 0,22 | 0,6799 | 0,5945 | 0,2467 | 0,7770 | 0,7600 | 1,2320 |
| Antes | **RF** | 0,31 | 0,7069 | 0,6243 | 0,2367 | 0,7751 | 0,8400 | 1,3616 |
| Después completo (n = 247) | Piso | 0,50 | 0,6397 | 0,5000 | 0,2412 | 0,7802 | 0,6397 | 1,0000 |
| Después completo | RL | 0,22 | 0,7214 | 0,6290 | 0,2435 | 0,7851 | 0,6800 | 1,0630 |
| Después completo | **RF** | 0,31 | 0,7284 | 0,6347 | 0,2420 | 0,7917 | 0,8000 | 1,2506 |
| Después variante | RL | 0,20 | 0,7242 | 0,6320 | 0,2454 | 0,7853 | 0,6800 | 1,0630 |
| Después variante | **RF** | 0,32 | 0,7204 | 0,6452 | 0,2398 | 0,7876 | 0,7600 | 1,1881 |

### 6.2 Prueba (solo informativa; no se usó para decidir)

| Versión | Modelo | Umbral | PR-AUC | ROC-AUC | Brier | F1 | P@25 | Lift@25 |
|---|---|---|---|---|---|---|---|---|
| Antes (n = 277) | Piso | 0,50 | 0,6679 | 0,5000 | 0,2277 | 0,8009 | 0,6679 | 1,0000 |
| Antes | RL | 0,22 | 0,7974 | 0,6743 | 0,2343 | 0,7896 | 0,8400 | 1,2577 |
| Antes | **RF** | 0,31 | 0,7899 | 0,6952 | 0,2299 | 0,8198 | 0,8000 | 1,1978 |
| Después completo (n = 277) | Piso | 0,50 | 0,6679 | 0,5000 | 0,2275 | 0,8009 | 0,6679 | 1,0000 |
| Después completo | RL | 0,22 | 0,8168 | 0,6991 | 0,2377 | 0,7866 | 0,9200 | 1,3775 |
| Después completo | **RF** | 0,31 | 0,8015 | 0,7208 | 0,2352 | 0,8227 | 0,7600 | 1,1379 |
| Después variante | RL | 0,20 | 0,8268 | 0,6963 | 0,2368 | 0,8000 | 0,9600 | 1,4374 |
| Después variante | **RF** | 0,32 | 0,7934 | 0,7163 | 0,2319 | 0,8200 | 0,8000 | 1,1978 |

Tabla completa (accuracy, precisión, recall, especificidad, IC): `salidas/m01/despues/comparacion_antes_despues.csv`.

Lectura: las métricas **no empeoraron** al eliminar la fuga; la PR-AUC de validación del RF subió de 0,7069 a 0,7284 (completo), aunque el conjunto de validación es otro (más corto y con distinta prevalencia), así que la comparación antes/después es orientativa. En los libros reales la fuga casi no se materializaba (§9). Con el conjunto completo ningún modelo mejora el Brier del piso en validación (RF 0,2420 frente a 0,2412), por lo que la selección es provisional; con la variante el RF sí lo mejora (0,2398) y cumple los tres criterios de §11.3.

## 7. Bootstrap por socio (IC 95 %)

En cada una de las 1.000 réplicas se sortean con reemplazo tantos socios como tiene el conjunto y se toman todos sus ciclos; la PR-AUC del piso es la prevalencia de la réplica. Las réplicas son las mismas para todos los modelos (comparación emparejada). Todas las réplicas fueron válidas.

| Conjunto | Comparación | Media | IC 95 % | % réplicas > 0 |
|---|---|---|---|---|
| Validación | Piso | 0,641 | [0,576; 0,703] | — |
| Validación | RL completo | 0,724 | [0,633; 0,804] | — |
| Validación | RL completo − piso | 0,082 | [0,018; 0,147] | 99,2 % |
| Validación | RL variante − piso | 0,086 | [0,020; 0,151] | 99,5 % |
| Validación | RL variante − completo | 0,003 | [−0,018; 0,027] | 62,3 % |
| Validación | RF completo | 0,734 | [0,653; 0,811] | — |
| Validación | RF completo − piso | 0,093 | [0,035; 0,152] | 100,0 % |
| Validación | RF variante | 0,727 | [0,647; 0,802] | — |
| Validación | RF variante − piso | 0,086 | [0,024; 0,147] | 99,5 % |
| Validación | **RF variante − completo** | −0,008 | **[−0,040; 0,027]** | 32,4 % |
| Prueba | Piso | 0,669 | [0,604; 0,734] | — |
| Prueba | RL completo − piso | 0,149 | [0,093; 0,207] | 100,0 % |
| Prueba | RL variante − piso | 0,157 | [0,108; 0,209] | 100,0 % |
| Prueba | RL variante − completo | 0,008 | [−0,017; 0,037] | 70,0 % |
| Prueba | RF completo | 0,804 | [0,731; 0,871] | — |
| Prueba | RF completo − piso | 0,135 | [0,073; 0,192] | 100,0 % |
| Prueba | RF variante | 0,797 | [0,722; 0,861] | — |
| Prueba | RF variante − piso | 0,127 | [0,066; 0,190] | 100,0 % |
| Prueba | RF variante − completo | −0,007 | [−0,029; 0,017] | 26,1 % |

Antes solo existía el IC por fila de RF − piso en prueba: [0,073; 0,175]. Todos los modelos superan al piso con IC que no contienen 0.

## 8. Importancia por permutación (validación, `average_precision`, 10 repeticiones, semilla 42)

Media ± desviación de la caída de PR-AUC al permutar la variable.

| Variable | Antes (RF) | RF completo | RF variante | RL completo | RL variante |
|---|---|---|---|---|---|
| plan | 0,0159 ± 0,0089 | 0,0269 ± 0,0118 | 0,0238 ± 0,0103 | 0,0617 ± 0,0181 | 0,0659 ± 0,0200 |
| forma_pago | 0,0129 ± 0,0083 | 0,0074 ± 0,0166 | — | −0,0008 ± 0,0127 | — |
| inicio_aproximado | 0,0055 ± 0,0031 | 0,0054 ± 0,0046 | — | −0,0011 ± 0,0009 | — |
| monto_historico | 0,0030 ± 0,0096 | 0,0100 ± 0,0151 | 0,0046 ± 0,0148 | 0,0031 ± 0,0027 | −0,0006 ± 0,0053 |
| antiguedad_dias | 0,0014 ± 0,0026 | 0,0034 ± 0,0056 | 0,0154 ± 0,0102 | 0,0140 ± 0,0079 | 0,0049 ± 0,0033 |
| monto_actual | 0,0008 ± 0,0047 | −0,0064 ± 0,0103 | −0,0236 ± 0,0132 | −0,0378 ± 0,0082 | −0,0387 ± 0,0099 |
| mes_vencimiento | 0,0000 ± 0,0000 | 0,0000 ± 0,0000 | 0,0000 ± 0,0000 | 0,0000 ± 0,0000 | 0,0000 ± 0,0000 |
| dias_desde_ultima_membresia | −0,0003 ± 0,0121 | 0,0076 ± 0,0085 | 0,0074 ± 0,0057 | 0,0036 ± 0,0012 | 0,0025 ± 0,0034 |
| ciclos_previos | −0,0015 ± 0,0098 | 0,0030 ± 0,0126 | −0,0012 ± 0,0103 | 0,0483 ± 0,0201 | 0,0360 ± 0,0250 |
| duracion_modelo | −0,0024 ± 0,0043 | 0,0060 ± 0,0072 | 0,0132 ± 0,0051 | 0,0463 ± 0,0136 | 0,0601 ± 0,0135 |

Lectura: `plan` sigue siendo la variable más importante. `forma_pago` e `inicio_aproximado` aportan poco y con desviación mayor que la media en el RF completo. `mes_vencimiento` no aporta nada: codificada como año-mes, sus categorías de validación no existen en entrenamiento y el *one-hot* las ignora (limitación, §13).

## 9. Prueba anti-fuga (§7.5) y efecto en los datos reales

Se alteran montos, fechas, planes, formas de pago e `inicio_aproximado` de todos los registros con actividad posterior a T−30, se borra un tercio, se duplican hasta 10 y se añaden 4 ciclos nuevos del socio (T−30 + 1, 2, 10 y 40 días); luego se recalculan las 10 variables con medianas fijas. Muestra: 278 ciclos (hasta 30 por conjunto más los 98 con actividad posterior a su T−30), 2 alteraciones por ciclo.

| Regla | Ciclos probados | Ciclos con cambios | Variables afectadas |
|---|---|---|---|
| Anterior (sin corte T−30) | 278 | 103 | `ciclos_previos` (102), `dias_desde_ultima_membresia` (102), `monto_historico` (103) |
| M01 | 278 | 0 | — |

La prueba se escribió primero y falló con la regla anterior; con la regla M01 pasa, y también pasa en el control 9 de §14.2 sobre los 57 ciclos de la cartera de septiembre. En los libros reales el corte cambia las variables de **1 de 1.660 ciclos**: la fuga existía en la regla, pero casi no se materializaba en estos datos.

## 10. Variante y decisión final

Regla fijada **antes** de ver los resultados: se adopta la variante si su PR-AUC en validación es ≥ la del modelo completo, **o** si el IC 95 % bootstrap por socio de la diferencia (variante − completo) contiene 0. El conjunto de prueba solo informa.

- PR-AUC validación: completo (RF) 0,7284; variante (RF) 0,7204; diferencia −0,0080 → primer criterio no se cumple.
- IC 95 % de la diferencia: [−0,0400; +0,0269] → contiene 0 → segundo criterio se cumple.
- **Decisión: se adopta la variante (Random Forest, umbral 0,32, 8 variables).**

Justificación: la pérdida de 0,008 no se distingue del azar (32,4 % de las réplicas favorecen a la variante); el modelo es más simple, no depende de una bandera de calidad del dato y cumple los tres criterios de §11.3, incluido el Brier, que el completo no cumple. En prueba: 0,7934 frente a 0,8015, IC de la diferencia [−0,029; +0,017]; P@25 0,80 frente a 0,76.

## 11. Cortes de riesgo y efecto en el reparto

Decisión del usuario: la app usa los cortes fijos del notebook, **ALTO ≥ 0,70, MEDIO ≥ 0,50, BAJO < 0,50**, en lugar de los percentiles 20/30/50 de CU-05 (decisión (d) de R-004). Así el nivel de cada socio es el mismo en la app y en el notebook.

| Ámbito | ALTO | MEDIO | BAJO |
|---|---|---|---|
| Cartera de septiembre del notebook (57 socios, corte 31-08-2026) | 2 | 39 | 16 |
| Modelo v2 del stack principal: evaluables de los 3 meses recientes (reparto observado) | 15 % | 52 % | 33 % |
| Regla anterior de la app (por construcción) | 20 % | 30 % | 50 % |

Consecuencia: en una lista concreta puede haber muy pocos socios en ALTO; el orden de prioridad (por probabilidad) no cambia.

## 12. Efecto en la aplicación y cómo se verificó

**Cambios en la app** (backend; sin cambios de esquema ni de endpoints):

- Variables con corte T−30 y medianas solo de los evaluables con que se entrena; el modelo entrena con las 8 variables elegidas; la referencia de los factores es el nuevo conjunto de entrenamiento (vencimientos ≤ 01-12-2025), y "Forma de pago" e "Inicio aproximado" ya no aparecen como motivo.
- Niveles con cortes fijos 0,70/0,50; la ayuda de la Lista lo explica en lenguaje sencillo.
- Reentrenamiento (CU-02): margen de 30 días entre el entrenamiento del candidato y la comparación, y etiquetado al **corte de los datos** (`min(hoy, max(corte vigente, última carga))`).
- Comando nuevo `python -m app.cli adoptar-modelo`: crea la versión vigente + 1 en una transacción y conserva la anterior. Listas, predicciones y gestiones hechas con v1 no cambian.

**Verificación:**

| Prueba | Resultado |
|---|---|
| Prueba anti-fuga del notebook (§7.5, §14.2) | Falla con la regla anterior (103 de 278); pasa con M01 |
| Pruebas automáticas del backend (pytest) | En verde (más de 2.028), con pruebas nuevas TDD de T−30 (actividad = T−30 cuenta, T−29 no), medianas, margen del candidato y `adoptar-modelo` (incluida la reversión ante fallo) |
| Frontend | 862 pruebas Vitest y 10 E2E en verde |
| `verificar_lista.py` (app en memoria frente al notebook) | 0 diferencias en las 57 filas: probabilidad, nivel, factores y orden |
| Ensayo en el stack aislado de pruebas | Tablas idénticas fila a fila salvo el modelo y el intento nuevos; E2E 10/10 |
| Puesta en uso en el stack principal (2026-10-15) | Respaldo previo; `adoptar-modelo` código 0; v2 vigente (1.660 ciclos, umbrales 0,70/0,50); v1 conservado; conteos de negocio idénticos (socios 1.516, membresías 2.854, cargas 2, listas 1, predicciones 28, campañas 4, gestiones 6); intentos 1 → 2 |

Nota: el v2 del stack principal tiene corte de datos 30-09-2026 porque esa base incluye una carga mensual del 01-10-2026; por eso su lista no es comparable 1:1 con la del notebook, que usa los libros hasta el 31-08-2026.

## 13. Limitaciones

1. **Margen de 30 días, no 60.** El criterio estricto ("la etiqueta del entrenamiento se conoce en T−30 del primer ciclo del conjunto siguiente") exigiría 60 días; se usó 30, como se pidió.
2. **Estado `EXCLUIDO - Vencimiento posterior al período disponible`.** Depende de la fecha de corte de los datos (31-08-2026), no de T−30; afecta a 4 ciclos (2 del margen 1, 1 de validación, 1 de prueba). Se mantuvo para conservar la definición y la paridad con la app.
3. **`mes_vencimiento` codificado año-mes no aporta**: sus valores de validación y prueba nunca aparecen en entrenamiento. Se conservó para no cambiar más de lo pedido; una codificación por mes del año (estacionalidad) queda como trabajo futuro. **Recomendación (tras M02):** probar a codificarla como mes del año (1–12), de modo que los meses de validación y prueba sí aparezcan en entrenamiento, y **quitarla** si no mejora la PR-AUC de validación. En M02 su \|SHAP\| medio medido es 0,0092: desplaza a todos los casos casi por igual y no cambia el orden, coherente con su importancia por permutación 0 ([M02 §6](M02-explicabilidad-shap.md)).
4. **Conjuntos pequeños**: validación 247 y prueba 277 ciclos; los IC son anchos (≈ ±0,08 de PR-AUC).
5. **Comparación antes/después con conjuntos distintos**: los márgenes cambian el conjunto de validación; la mejora observada no se puede atribuir solo a la corrección.

## 14. Correcciones de privacidad del notebook

La revisión de seguridad de R-015 detectó y se cerraron:

- Los códigos anónimos `MTB-xxxxxxxx` eran un `sha256` sin sal de la identidad (cédula o nombre), reversibles por fuerza bruta. Ahora son **HMAC-SHA256 con una sal secreta** (variable `MTABOLIC_SAL_CODIGOS` o archivo `salidas/.sal_codigos`, fuera de git); los códigos antiguos que aparecían en la documentación se eliminaron.
- La salida de §2.5 mostraba transacciones bancarias: esa columna se tapó.
- `verificar_lista.py` solo imprime el tipo de un error, nunca su mensaje.
- `MVP_v1.ipynb` se limpió de salidas; la copia `MVP_antes_M01.ipynb` quedó fuera de git y sin salidas.

El repositorio es privado y no se reescribió el historial de git.

## 15. Figuras

Rutas relativas a `Documentation/claude/mejoras/M01/` (carpeta fuera de git). Cada figura "después" reemplaza a su par "antes" en la tesis.

| Antes | Después | Sección del notebook | Uso en la tesis |
|---|---|---|---|
| `antes/sec00_linea_de_tiempo.png` | `despues/sec00_linea_de_tiempo.png` | Resumen / línea de tiempo | Metodología: diseño temporal (T−30, T, T+30) |
| `antes/sec03_8_valores_faltantes.png` | `despues/sec03_8_valores_faltantes.png` | §3.8 | Datos: calidad y faltantes |
| `antes/sec05_3_estado_registros.png` | `despues/sec05_3_estado_registros.png` | §5.3 | Datos: estados de los ciclos |
| `antes/sec06_1_vencimientos_mensuales.png` | `despues/sec06_1_vencimientos_mensuales.png` | §6.1 | Análisis exploratorio |
| `antes/sec08_2_particion_cronologica.png` | `despues/sec08_2_particion_con_margenes.png` | §8.2 | Metodología: partición con márgenes |
| `antes/sec11_1_umbral_validacion.png` | `despues/sec11_1_umbral_validacion.png` | §11.1 | Resultados: umbral por F1 |
| `antes/sec11_3_comparacion_validacion.png` | `despues/sec11_3_comparacion_validacion.png` | §11.3 | Resultados: selección en validación |
| `antes/sec12_1_comparacion_prueba.png` | `despues/sec12_1_comparacion_prueba.png` | §12.1 | Resultados: prueba |
| `antes/sec12_4_matriz_confusion.png` | `despues/sec12_4_matriz_confusion.png` | §12.4 | Resultados: matriz de confusión |
| `antes/sec12_5_curvas_pr_ganancia_calibracion.png` | `despues/sec12_5_curvas_pr_ganancia_calibracion.png` | §12.5 | Resultados: curvas PR, ganancia y calibración |
| `antes/sec12_6_utilidad_top_k.png` | `despues/sec12_6_utilidad_top_k.png` | §12.6 | Resultados: utilidad del top K |
| `antes/sec12_8_prueba_mes_a_mes.png` | `despues/sec12_8_prueba_mes_a_mes.png` | §12.8 | Resultados: estabilidad mensual |
| `antes/sec12_9_importancia_permutacion.png` | `despues/sec12_9_importancia_permutacion.png` | §12.9 | Resultados: importancia |
| `antes/sec12_10_efecto_variables.png` | `despues/sec12_10_efecto_variables.png` | §12.10 | Resultados: efecto de las variables |
| — (nueva) | `despues/sec12_11_importancia_completo_vs_variante.png` | §12.11 | Resultados: variante y decisión |
| `antes/sec13_3_explicacion_individual.png` | `despues/sec13_3_explicacion_individual.png` | §13.3 | Uso operativo: factores por socio |
| `antes/sec13_6_composicion_listas.png` | `despues/sec13_6_composicion_listas.png` | §13.6 | Uso operativo: composición de listas |
| `antes/sec13_7_efectividad_listas.png` | `despues/sec13_7_efectividad_listas.png` | §13.7 | Uso operativo: efectividad de listas |
| `antes/sec13_8_lista_operativa.png` | `despues/sec13_8_lista_operativa.png` | §13.8 | Uso operativo: lista de septiembre |
| `antes/sec15_1_resumen_prueba.png` | `despues/sec15_1_resumen_prueba.png` | §15.1 | Conclusiones: resumen |

## 16. Qué cambiar en el documento de la tesis

1. **Metodología – construcción de variables:** reemplazar la definición del historial por la del §3 de este documento (corte T−30) y añadir la tabla de variables con la columna "en el modelo elegido".
2. **Metodología – imputación:** indicar que las medianas se calculan solo con entrenamiento; añadir la tabla de medianas (§3).
3. **Metodología – partición:** reemplazar la tabla de particiones (932/355/277) por la de §4 (845/247/277 y márgenes descartados) y la figura `sec08_2_particion_cronologica` por `sec08_2_particion_con_margenes`.
4. **Metodología – validación de la ausencia de fuga:** sección nueva con la prueba anti-fuga (§9), incluido el resultado 103/278 → 0/278.
5. **Metodología – evaluación:** cambiar "bootstrap por fila" por "bootstrap por socio" (1.000 réplicas, semilla 42) y declarar la semilla y los hiperparámetros (§5).
6. **Resultados – validación y prueba:** reemplazar las tablas de métricas por las de §6.1 y §6.2, y las figuras §11.1, §11.3, §12.1, §12.4–§12.6, §12.8.
7. **Resultados – intervalos:** reemplazar el IC por fila por la tabla de §7.
8. **Resultados – importancia:** reemplazar la tabla y la figura §12.9 por §8 y añadir la figura §12.11.
9. **Resultados – variante:** sección nueva con la regla, las cifras y la decisión (§10).
10. **Uso operativo:** actualizar la lista de septiembre (figura §13.8, 57 socios: ALTO 2, MEDIO 39, BAJO 16), los factores (ya sin forma de pago ni inicio aproximado) y la explicación individual §13.3.
11. **Aplicación – niveles de riesgo:** sustituir los percentiles 20/30/50 por los cortes 0,70/0,50 y explicar el efecto (§11).
12. **Aplicación – versionado del modelo:** mencionar la adopción del modelo M01 como v2 con `adoptar-modelo`, el margen de 30 días en el reentrenamiento y el etiquetado al corte de los datos (§12).
13. **Aplicación – verificación:** actualizar la conciliación app ↔ notebook a "0 diferencias en las 57 filas" (§12).
14. **Ética y privacidad:** añadir la corrección de los códigos anónimos (HMAC con sal) y de la salida §2.5 (§14).
15. **Limitaciones y trabajo futuro:** añadir los cinco puntos de §13.
16. **Resumen y conclusiones:** actualizar las cifras principales (RF variante: PR-AUC validación 0,7204, prueba 0,7934; IC frente al piso en prueba [0,066; 0,190]) y la figura §15.1.
