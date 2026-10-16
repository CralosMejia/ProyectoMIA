# M02 · Explicabilidad del modelo con SHAP

| | |
|---|---|
| **Requerimiento** | R-016 (harness), cerrado el 2026-10-16 |
| **Notebook** | `Notebookes/MVP.ipynb`: §1.1 (herramientas, `shap` con versión fija), **§12.12 (nueva)**, encabezado M02, §14.2 (controles 13 y 14), §15 (tabla de trabajo futuro, punto 8) |
| **Alcance** | Solo análisis en el notebook. **No cambian** las variables, la etiqueta, la partición, el modelo, el umbral ni la lista; todas las cifras de [M01](M01-modelo-sin-fuga-temporal.md) se mantienen. La aplicación no cambia. |
| **Datos fuente (fuera de git)** | `salidas/m02/`: `resumen_m02.md`, `m02_grupos_tamanos.csv`, `m02_aporte_por_grupo_top25.csv`, `m02_aporte_por_grupo_umbral.csv`, `m02_importancia_por_mes.csv`, `m02_shap_validacion.csv`, `m02_casos_waterfall.csv` |
| **Figuras (fuera de git)** | `Documentation/claude/mejoras/M02/` (12 PNG) |

Este documento reúne todo lo necesario para actualizar la tesis. Solo contiene cifras agregadas: ningún código de socio, nombre, cédula ni fecha exacta.

---

## 1. Objetivo y recomendación del tutor

Después de M01, el tutor recomendó explicar con **SHAP** (*SHapley Additive exPlanations*) qué variables llevan al modelo a **acertar** y a **equivocarse**: comparar los verdaderos positivos (VP), falsos positivos (FP), falsos negativos (FN) y verdaderos negativos (VN) en el conjunto de validación, con la importancia global, la explicación de casos individuales y la estabilidad mes a mes.

**Cifras del tutor frente a las usadas.** El tutor citó **355 casos de validación y umbral 0,31**. Eran las cifras del MVP **anterior a M01**: la partición sin márgenes (354–355 ciclos de validación) y el umbral del Random Forest con todas las variables. Con M01 la partición tiene márgenes de 30 días y el modelo adoptado es la variante sin `forma_pago` ni `inicio_aproximado`. Por eso aquí se usan **247 casos de validación** y **umbral 0,32**, que son los del modelo vigente.

## 2. Método paso a paso

| Paso | Qué se hizo |
|---|---|
| 1. Entorno | `shap` **0.54.1** (versión fija), instalado **solo** en el entorno del notebook, sin `numba`. scikit-learn **1.8.0** y numpy **2.5.3** no cambiaron (comprobado con `assert` en §1.1). Python 3.12, semilla 42. |
| 2. Modelo explicado | El Random Forest corregido de M01 (variante, `modelo_seleccionado` de §12.11), 300 árboles, `class_weight="balanced"`. Control: reproduce la PR-AUC de validación **0,7204**, así que se explica exactamente el modelo adoptado. |
| 3. Matriz explicada | La salida del preprocesamiento del propio *pipeline* sobre los 247 casos de validación (columnas numéricas escaladas y columnas 0/1 del *one-hot*). Clase explicada: **"no renovó"** (clase 1). |
| 4. Explicador | `shap.TreeExplainer` sobre el bosque: calcula valores SHAP exactos para árboles (no aproximados por muestreo). |
| 5. Agregación *one-hot* | Los valores SHAP de las columnas 0/1 se **suman** a su variable original (`plan_*` → `plan`, `mes_vencimiento_*` → `mes_vencimiento`); las numéricas quedan 1:1. Resultado: 247 casos × 8 variables. La suma por fila no cambia al agregar. |
| 6. Valores mostrados | En las figuras se muestran los valores **originales** (sin escalar), redondeados (§10). |
| 7. Clasificaciones | Dos (§5): top 25 por mes (regla de uso) y umbral 0,32. |
| 8. Tablas | Aporte medio con signo y \|SHAP\| medio por variable, por grupo y por mes (CSV en `salidas/m02/`). |
| 9. Figuras | Resumen global (barras y *beeswarm*), 8 *waterfalls*, importancia por mes y aporte por grupo. |
| 10. Controles | §14.2: control 13 "aditividad SHAP" y control 14 "salidas M02 sin datos personales", ambos en verde. |

Variables del modelo (8): `ciclos_previos`, `antiguedad_dias`, `duracion_modelo`, `monto_actual`, `monto_historico`, `dias_desde_ultima_membresia`, `plan`, `mes_vencimiento`.

## 3. Valor base y por qué no coincide con la prevalencia

| Magnitud | Valor |
|---|---|
| Valor base SHAP (clase "no renovó") | **0,5029** |
| Media de la raíz de los 300 árboles | 0,5029 (coincide) |
| Media ponderada de entrenamiento con `class_weight="balanced"` | 0,5000 |
| Prevalencia de "no renovó" en entrenamiento | 0,7432 |
| Prevalencia de "no renovó" en validación | 0,6397 |

El valor base es el punto de partida de toda explicación: la probabilidad media que el modelo daría sin conocer nada del socio. En un Random Forest es la media de las hojas raíz de los árboles **con los pesos de entrenamiento**. Con `class_weight="balanced"` cada clase pesa lo mismo, así que esa media queda cerca de **0,50** y no de la prevalencia real (0,74 en entrenamiento, 0,64 en validación). La diferencia entre 0,5029 y 0,5000 se debe al muestreo *bootstrap* de cada árbol.

Consecuencia para la lectura: los aportes se miden respecto de ≈ 0,50, no respecto de la tasa real de no renovación. Es coherente con lo ya documentado en M01: las probabilidades del modelo ordenan bien pero no están calibradas.

## 4. Comprobación de aditividad

Para cada caso, valor base + suma de los valores SHAP = probabilidad del modelo. Se comprobó en los 247 casos:

| Nivel | Error máximo | Control |
|---|---|---|
| Columnas del preprocesamiento (*one-hot*) | 2,22e-15 | < 1e-6 |
| Tras sumar a las 8 variables originales | 2,22e-15 | < 1e-6 |

El error es del orden de la precisión de coma flotante: la explicación corresponde exactamente al modelo.

## 5. Clasificaciones y tamaños de los grupos

Grupos respecto de la etiqueta `no_renovo`:

- **Top 25 por mes (regla de uso, base de las conclusiones).** En cada mes de vencimiento de validación (enero, febrero y marzo de 2026), predicho positivo = los 25 casos de mayor probabilidad; empates en el puesto 25 resueltos por código HMAC ascendente (regla fija). VP + FP = 25 por mes.
- **Umbral 0,32 (complemento).** Predicho positivo si la probabilidad ≥ 0,32. Reproduce la matriz de confusión del RF variante en validación de §12.11: **recall 0,962** y **especificidad 0,146**.

| Clasificación | Mes | VP | FP | FN | VN | Casos | Priorizados (VP+FP) |
|---|---|---|---|---|---|---|---|
| Top 25 por mes | **Total** | **60** | **15** | **98** | **74** | 247 | 75 |
| Top 25 por mes | ene 2026 | 19 | 6 | 27 | 24 | 76 | 25 |
| Top 25 por mes | feb 2026 | 20 | 5 | 47 | 30 | 102 | 25 |
| Top 25 por mes | mar 2026 | 21 | 4 | 24 | 20 | 69 | 25 |
| Umbral 0,32 | **Total** | **152** | **76** | **6** | **13** | 247 | 228 |
| Umbral 0,32 | ene 2026 | 43 | 21 | 3 | 9 | 76 | 64 |
| Umbral 0,32 | feb 2026 | 64 | 31 | 3 | 4 | 102 | 95 |
| Umbral 0,32 | mar 2026 | 45 | 24 | 0 | 0 | 69 | 69 |

Precisión del top 25: 60/75 = 0,80. Con el umbral, FN (6) y VN (13) son demasiado pequeños para generalizar (en marzo, 0 y 0).

## 6. Importancia global (\|SHAP\| medio, 247 casos)

| Variable | \|SHAP\| medio | Aporte medio con signo |
|---|---|---|
| `monto_historico` | 0,049 | −0,022 |
| `ciclos_previos` | 0,033 | −0,015 |
| `plan` | 0,025 | +0,002 |
| `dias_desde_ultima_membresia` | 0,014 | −0,001 |
| `duracion_modelo` | 0,014 | +0,008 |
| `antiguedad_dias` | 0,011 | +0,003 |
| `monto_actual` | 0,010 | +0,002 |
| `mes_vencimiento` | 0,009 | +0,009 |

`monto_historico`, `ciclos_previos` y `plan` concentran la mayor parte de la explicación. En el *beeswarm*, los valores **bajos** de `monto_historico` y `ciclos_previos` empujan hacia "no renueva" y los **altos** hacia "renueva"; en `plan`, MENSUAL baja el riesgo y TRIMESTRAL, ANUAL, SEMESTRAL y OTRO lo suben. Coincide con el efecto de las variables de §12.10 (a mayor historia, menor riesgo).

**`mes_vencimiento`.** \|SHAP\| medio medido **0,0092** (no se forzó a 0). Sus columnas 0/1 corresponden a meses de 2025 (entrenamiento); en validación todas valen 0, así que la variable desplaza a **todos los casos casi por igual** (aporte con signo ≈ \|SHAP\| medio) y **no cambia el orden** de la lista. Por eso su importancia por permutación es **0** (§12.9, M01 §8): SHAP mide cuánto mueve la probabilidad; la permutación, cuánto cambia el orden. Ver la recomendación en [M01 §13](M01-modelo-sin-fuga-temporal.md#13-limitaciones).

## 7. Aporte medio por grupo

### 7.1 Top 25 por mes — aporte medio con signo

| Variable | VP (n=60) | FP (n=15) | FN (n=98) | VN (n=74) |
|---|---|---|---|---|
| `ciclos_previos` | +0,016 | +0,019 | −0,026 | −0,032 |
| `antiguedad_dias` | +0,010 | +0,010 | +0,002 | −0,002 |
| `duracion_modelo` | +0,015 | +0,011 | +0,006 | +0,006 |
| `monto_actual` | +0,001 | +0,018 | +0,000 | +0,001 |
| `monto_historico` | +0,027 | +0,029 | −0,041 | −0,048 |
| `dias_desde_ultima_membresia` | +0,012 | +0,013 | −0,003 | −0,012 |
| `plan` | +0,016 | +0,020 | −0,001 | −0,009 |
| `mes_vencimiento` | +0,012 | +0,013 | +0,008 | +0,007 |

\|SHAP\| medio de `monto_actual`: 0,023 en FP frente a 0,008 en VP (es la única variable que separa a los FP de los VP).

### 7.2 Umbral 0,32 — aporte medio con signo

| Variable | VP (n=152) | FP (n=76) | FN (n=6) | VN (n=13) |
|---|---|---|---|---|
| `ciclos_previos` | −0,009 | −0,019 | −0,049 | −0,048 |
| `antiguedad_dias` | +0,005 | +0,001 | −0,010 | −0,008 |
| `duracion_modelo` | +0,010 | +0,009 | −0,009 | −0,009 |
| `monto_actual` | +0,001 | +0,005 | −0,004 | −0,004 |
| `monto_historico` | −0,013 | −0,029 | −0,074 | −0,071 |
| `dias_desde_ultima_membresia` | +0,004 | −0,002 | −0,035 | −0,040 |
| `plan` | +0,007 | −0,001 | −0,019 | −0,019 |
| `mes_vencimiento` | +0,010 | +0,009 | +0,005 | +0,005 |

Las tablas de \|SHAP\| medio por grupo están en `salidas/m02/m02_aporte_por_grupo_top25.csv` y `m02_aporte_por_grupo_umbral.csv`.

## 8. Importancia por mes (\|SHAP\| medio y puesto)

| Variable | ene 2026 (n=76) | feb 2026 (n=102) | mar 2026 (n=69) |
|---|---|---|---|
| `monto_historico` | 0,047 (1.º) | 0,051 (1.º) | 0,049 (1.º) |
| `ciclos_previos` | 0,031 (2.º) | 0,034 (2.º) | 0,032 (2.º) |
| `plan` | 0,029 (3.º) | 0,023 (3.º) | 0,024 (4.º) |
| `dias_desde_ultima_membresia` | 0,016 (4.º) | 0,012 (5.º) | 0,016 (5.º) |
| `antiguedad_dias` | 0,012 (5.º) | 0,013 (4.º) | 0,008 (8.º) |
| `duracion_modelo` | 0,011 (6.º) | 0,008 (8.º) | **0,025 (3.º)** |
| `mes_vencimiento` | 0,009 (7.º) | 0,009 (7.º) | 0,009 (7.º) |
| `monto_actual` | 0,009 (8.º) | 0,011 (6.º) | 0,010 (6.º) |

Los dos primeros puestos son estables en los tres meses: el modelo usa la misma lógica todos los meses. En marzo, `duracion_modelo` sube al tercer puesto. `mes_vencimiento` queda séptima en los tres meses con ≈ 0,009.

## 9. Qué explica los falsos positivos y los falsos negativos

**Con la regla de uso (top 25 por mes):**

- **FP (15).** El modelo los ve **igual que a los VP**: mismos aportes positivos de `monto_historico` (+0,029 frente a +0,027), `ciclos_previos` (+0,019 frente a +0,016) y `plan` (+0,020 frente a +0,016). Son socios con **poca historia** pagada y pocos ciclos previos. Solo los distingue `monto_actual` (+0,018 en FP frente a +0,001 en VP): en algunos FP el monto del ciclo actual sube el riesgo más de la cuenta. Con las variables disponibles no hay ninguna señal fuerte que los separe de los VP.
- **FN (98).** Son **socios con historia**: `monto_historico` (−0,041) y `ciclos_previos` (−0,026) les bajan el riesgo **igual que a los VN** (−0,048 y −0,032). Además, buena parte de los FN se explica por la **capacidad**: en validación hay 158 no renovaciones y solo 75 cupos (25 por mes), así que **al menos 83 FN quedarían fuera aunque el orden fuera perfecto**.

**Como complemento, con el umbral 0,32:**

- **FP (76).** Tienen aportes negativos en `monto_historico` (−0,029) y `ciclos_previos` (−0,019), más fuertes que los VP (−0,013 y −0,009), pero su probabilidad sigue por encima de 0,32 porque el **valor base ronda 0,50** y el umbral es bajo: el umbral prioriza casi a todos.
- **FN (6) y VN (13).** Perfiles casi idénticos: `monto_historico` (−0,074 y −0,071), `ciclos_previos` (−0,049 y −0,048) y `dias_desde_ultima_membresia` (−0,035 y −0,040). Con tamaños tan pequeños estas cifras son **solo ilustrativas**.

## 10. Figuras

Rutas relativas a `Documentation/claude/mejoras/M02/` (carpeta fuera de git). Todas salen de §12.12 del notebook.

| Figura | Contenido | Sección de la tesis |
|---|---|---|
| `m02_resumen_global_bar.png` | \|SHAP\| medio por variable original | Resultados – explicabilidad: importancia global |
| `m02_resumen_global_beeswarm.png` | Aporte por caso coloreado por el valor original; `plan` por categoría | Resultados – explicabilidad: dirección del efecto |
| `m02_aporte_por_grupo.png` | Aporte medio con signo por grupo (top 25) | Resultados – explicabilidad: aciertos y errores |
| `m02_importancia_por_mes.png` | \|SHAP\| medio por variable en ene, feb y mar 2026 | Resultados – estabilidad mensual (junto a §12.8) |
| `m02_waterfall_vp_1.png` | VP · ene 2026 · probabilidad 0,70 | Resultados – explicación de casos (anexo si falta espacio) |
| `m02_waterfall_vp_2.png` | VP · feb 2026 · probabilidad 0,57 | Ídem |
| `m02_waterfall_fp_1.png` | FP · ene 2026 · probabilidad 0,71 | Ídem |
| `m02_waterfall_fp_2.png` | FP · feb 2026 · probabilidad 0,57 | Ídem |
| `m02_waterfall_fn_1.png` | FN · ene 2026 · probabilidad 0,61 | Ídem |
| `m02_waterfall_fn_2.png` | FN · ene 2026 · probabilidad 0,29 | Ídem |
| `m02_waterfall_vn_1.png` | VN · ene 2026 · probabilidad 0,61 | Ídem |
| `m02_waterfall_vn_2.png` | VN · ene 2026 · probabilidad 0,29 | Ídem |

**Selección de los *waterfalls*.** Dos por grupo de la clasificación top 25, con una regla fija: el caso de **mayor** y el de **menor** probabilidad del grupo, con desempate por código HMAC ascendente (reproducible: dos ejecuciones dan los mismos casos). Por decisión del usuario, un grupo con menos de 2 casos se mostraría igual, con su `n` y la leyenda "solo ilustrativo" (y con 0 casos se explicaría la causa); con el top 25 no hizo falta (el grupo menor, FP, tiene 15).

## 11. Limitaciones

1. **SHAP explica el modelo, no la causalidad.** Que un `monto_historico` alto baje el riesgo no significa que cobrar más retenga a los socios; solo dice cómo usa el modelo esa variable.
2. **Variables correlacionadas.** En validación, Spearman `ciclos_previos`–`monto_historico` = **0,96**, y ambas con `antiguedad_dias` 0,57 y 0,60. Miden casi lo mismo (cuánta historia tiene el socio) y se reparten el mérito; el reparto depende de cómo se construyeron los árboles y puede cambiar con otro entrenamiento. Conviene leerlas como un bloque de "historia del socio".
3. **`mes_vencimiento`** no aporta información útil (0,0092, casi constante; limitación de M01).
4. **Grupos pequeños del umbral.** FN (6) y VN (13) solo sirven como ilustración; las conclusiones se apoyan en el top 25 por mes.
5. **Valor base ≈ 0,50**, no la prevalencia: los aportes son relativos a las clases equilibradas por `class_weight="balanced"`.
6. ~~**Solo validación (247 casos).** No se analizó el conjunto de prueba; los *waterfalls* son 8 casos ilustrativos, no representativos.~~ **Cerrada por [M03](M03-shap-prueba-y-motivos-en-la-app.md)** (R-017): SHAP en prueba (277), lista de septiembre (57) y entrenamiento (845, informativo); se mantienen 10 de 11 conclusiones de §9.
7. ~~La lista de la aplicación sigue usando la explicación individual de §13.3 (factores por socio); SHAP queda como análisis del notebook.~~ **Cerrada por [M03](M03-shap-prueba-y-motivos-en-la-app.md)** (R-017, [ADR-015](../adr/ADR-015-motivos-con-shap-en-la-app.md)): los motivos de la lista se calculan con SHAP en el notebook (§13.3/§13.8) y en la app.

## 12. Privacidad

- Ninguna salida visible del notebook ni figura contiene código de socio, nombre, cédula ni fecha exacta; una celda de §12.12 lo verifica con `assert` y §14.2 lo incluye como control 14.
- En los *waterfalls*: montos redondeados al múltiplo de 10, días en rangos de 30 (`0–29`, `30–59`, …), mes como "ene 2026", probabilidad a 2 decimales; el título solo lleva grupo, mes y probabilidad.
- Los CSV de `salidas/m02/` llevan como máximo el código HMAC (con sal secreta, M01 §14), el mes `AAAA-MM`, el grupo, la probabilidad a 3 decimales y los SHAP agregados; nunca `socio_id`, nombre ni cédula. `salidas/` y `Documentation/claude/` están fuera de git.
- La revisión de seguridad retiró además un aviso de la celda de §1.1 que mostraba una ruta local del equipo.

## 13. Cómo se verificó

| Control | Resultado |
|---|---|
| Ejecución completa del notebook | Sin errores |
| §14.2 | 14 controles en verde (incluidos los nuevos 13 y 14) |
| Cifras de M01 | Sin cambios (PR-AUC val RF variante 0,7204, umbral 0,32) |
| `verificar_lista.py` | 0 diferencias |
| Versiones | shap 0.54.1; scikit-learn 1.8.0 y numpy 2.5.3 sin cambios |

## 14. Qué añadir/cambiar en el documento de la tesis

1. **Metodología – explicabilidad (sección nueva):** qué es SHAP, `TreeExplainer`, clase explicada "no renovó", agregación del *one-hot*, las dos clasificaciones y la regla de selección de *waterfalls* (§2, §5, §10). Citar a Lundberg y Lee (2017), *A unified approach to interpreting model predictions*, NeurIPS, y Lundberg et al. (2020), *From local explanations to global understanding with explainable AI for trees*, Nature Machine Intelligence 2, 56–67.
2. **Metodología – herramientas:** añadir `shap` 0.54.1 a la tabla de herramientas.
3. **Metodología – aclaración de cifras:** si el texto o los comentarios del tutor mencionan 355 casos y umbral 0,31, aclarar que son anteriores a M01; el análisis usa 247 y 0,32 (§1).
4. **Resultados – explicabilidad (sección nueva):** valor base y su explicación (§3), aditividad (§4), tabla de importancia global y figuras `m02_resumen_global_bar` y `m02_resumen_global_beeswarm` (§6).
5. **Resultados – aciertos y errores:** tabla de tamaños (§5), tabla 7.1 (y 7.2 como complemento), figura `m02_aporte_por_grupo` y el resumen de FP/FN (§9), incluido el argumento de capacidad (al menos 83 FN inevitables con 75 cupos).
6. **Resultados – estabilidad mensual:** junto a la figura de prueba mes a mes (§12.8), añadir la tabla 8 y `m02_importancia_por_mes`.
7. **Resultados – importancia:** junto a la importancia por permutación (M01 §8), explicar por qué `mes_vencimiento` vale 0 por permutación y 0,009 en SHAP (§6).
8. **Anexo:** los 8 *waterfalls* con su leyenda (grupo, mes, probabilidad).
9. **Ética y privacidad:** redondeos de las figuras, selección por regla fija y control automático de privacidad (§12).
10. **Limitaciones y trabajo futuro:** añadir los puntos de §11; en trabajo futuro, la recodificación de `mes_vencimiento` por mes del año ([M01 §13](M01-modelo-sin-fuga-temporal.md#13-limitaciones)) y, si se quiere, SHAP en el conjunto de prueba.
11. **Discusión / conclusiones:** el modelo prioriza a socios con poca historia pagada y pocos ciclos previos; sus errores no tienen una señal que los separe con las variables disponibles (FP iguales a VP, FN iguales a VN), lo que refuerza la recomendación de incorporar datos de asistencia.
