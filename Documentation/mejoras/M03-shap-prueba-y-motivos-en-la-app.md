# M03 · SHAP en prueba, entrenamiento y lista, y "Motivos principales" con SHAP en el notebook y la app

| | |
|---|---|
| **Requerimiento** | R-017 (harness), cerrado el 2026-10-16 |
| **Notebook** | `Notebookes/MVP.ipynb`: **§12.12 · M03** (nueva subsección al final de §12.12), **§13.3** (motivos con SHAP), **§13.8** (lista de septiembre con motivos SHAP), §14.2 (controles nuevos), §15.4 (limitación de los motivos actualizada) |
| **App** | `Backend/app/infrastructure/ml/random_forest.py` (`aportes_shap`, `predecir_con`), `Backend/scripts/verificar_lista.py`, `Backend/pyproject.toml` (`shap==0.54.1`), `Frontend/src/features/lista/components/AyudaLista.tsx` (sección "Motivos") |
| **Alcance** | Cambia **cómo se explica** el riesgo. **No cambian** las variables, la etiqueta, la partición, el modelo, las probabilidades, el orden ni los niveles. No se reentrenó ni se adoptó ningún modelo. Decisión de arquitectura: [ADR-015](../adr/ADR-015-motivos-con-shap-en-la-app.md). |
| **Datos fuente (fuera de git)** | `salidas/m03/`: `resumen_m03.md`, `m03_contrato_motivos_shap.md`, `m03_prueba_grupos_tamanos.csv`, `m03_prueba_aporte_por_grupo_top25.csv`, `m03_prueba_aporte_por_grupo_umbral.csv`, `m03_prueba_importancia_por_mes.csv`, `m03_importancia_comparada.csv`, `m03_conclusiones_fp_fn.csv`, `m03_lista_importancia.csv`, `m03_motivos_antes.csv`, `m03_motivos_antes_despues.csv`, `m03_shap_prueba.csv`, `m03_shap_lista.csv`, `m03_prueba_casos_waterfall.csv` |
| **Figuras (fuera de git)** | `Documentation/claude/mejoras/M03/` (15 PNG) |

Este documento reúne lo necesario para actualizar la tesis. Solo contiene cifras agregadas: ningún código de socio, nombre, cédula ni fecha exacta.

---

## 1. Objetivo

Continuación de [M02](M02-explicabilidad-shap.md), que explicó con SHAP el Random Forest corregido (M01) solo sobre los 247 casos de validación. M03 tiene dos partes:

1. **Parte 1 (notebook):** repetir el análisis SHAP en el **conjunto de prueba** (277 casos), en la **lista de septiembre** (57 socios) y, como dato informativo, en **entrenamiento** (845 casos), y comprobar si las conclusiones de M02 se mantienen fuera de validación.
2. **Parte 2 (notebook y app):** calcular los **"Motivos principales"** de la lista con SHAP, en lugar del método anterior por sustitución, con la misma regla en el notebook y en la app y la lista idéntica en ambos.

## 2. Parte 1 · SHAP en otros conjuntos

### 2.1 Método

El mismo de M02 §2: `shap.TreeExplainer` sobre el bosque, matriz = salida del preprocesamiento del propio *pipeline*, clase explicada "no renovó" (clase 1), columnas *one-hot* sumadas a su variable original (8 variables). shap **0.54.1**, scikit-learn 1.8.0, numpy 2.5.3, semilla 42.

| Conjunto | Modelo explicado | Uso |
|---|---|---|
| Prueba (277, may–ago 2026) | `modelo_seleccionado` de §12.11 (el mismo de M02) | Resultados: aciertos y errores, estabilidad |
| Entrenamiento (845) | `modelo_seleccionado` | **Solo informativo**: dentro de muestra |
| Lista de septiembre (57) | Modelo operativo de §13.8 (el que produce la lista y el que reproduce la app) | Importancia global y 2 *waterfalls*; sin grupos (aún sin resultado) |

Clasificaciones en prueba (como en M02): **top 25 por mes** (regla de uso; empate en el puesto 25 → código HMAC ascendente) y **umbral 0,32** (el de validación, sin reajustar). Una conclusión FP/FN de M02 §9 "se mantiene" si la variable que la sustenta conserva el signo del aporte medio y queda entre las 3 primeras del grupo en prueba.

### 2.2 Resultados en prueba

| Magnitud | Valor |
|---|---|
| Casos | 277 |
| PR-AUC del modelo explicado (control) | 0,7934 |
| Valor base SHAP (clase "no renovó") | 0,5029 (el mismo que en validación: es el mismo modelo) |
| Error máximo de aditividad | 2,22e-15 (< 1e-6) |

**Tamaños de los grupos**

| Clasificación | Mes | VP | FP | FN | VN | Casos | Priorizados (VP+FP) |
|---|---|---|---|---|---|---|---|
| Top 25 por mes | **Total** | **63** | **16** | **122** | **76** | 277 | 79 |
| Top 25 por mes | may 2026 | 20 | 5 | 42 | 27 | 94 | 25 |
| Top 25 por mes | jun 2026 | 18 | 7 | 36 | 25 | 86 | 25 |
| Top 25 por mes | jul 2026 | 24 | 1 | 44 | 24 | 93 | 25 |
| Top 25 por mes | ago 2026 | 1 | 3 | 0 | 0 | 4 | 4 |
| Umbral 0,32 | **Total** | **180** | **74** | **5** | **18** | 277 | 254 |
| Umbral 0,32 | may 2026 | 61 | 29 | 1 | 3 | 94 | 90 |
| Umbral 0,32 | jun 2026 | 52 | 24 | 2 | 8 | 86 | 76 |
| Umbral 0,32 | jul 2026 | 66 | 20 | 2 | 5 | 93 | 86 |
| Umbral 0,32 | ago 2026 | 1 | 1 | 0 | 2 | 4 | 2 |

Agosto de 2026 solo tiene 4 casos (fin de los libros): con el top 25 se priorizan todos. Precisión del top 25: 63/79 = 0,80 (igual que en validación). Capacidad: hay 185 no renovaciones y 79 cupos, así que **al menos 106 FN quedarían fuera aunque el orden fuera perfecto**. Con el umbral, FN (5) y VN (18) son demasiado pequeños para generalizar.

**Importancia global en prueba**

| Variable | \|SHAP\| medio | Aporte medio con signo |
|---|---|---|
| `monto_historico` | 0,049 | −0,022 |
| `ciclos_previos` | 0,033 | −0,016 |
| `plan` | 0,026 | +0,002 |
| `dias_desde_ultima_membresia` | 0,016 | −0,003 |
| `monto_actual` | 0,016 | +0,007 |
| `duracion_modelo` | 0,011 | +0,003 |
| `mes_vencimiento` | 0,009 | +0,009 |
| `antiguedad_dias` | 0,008 | +0,001 |

**Aporte medio con signo por grupo · top 25 por mes**

| Variable | VP (n=63) | FP (n=16) | FN (n=122) | VN (n=76) |
|---|---|---|---|---|
| `ciclos_previos` | +0,018 | +0,012 | −0,023 | −0,040 |
| `antiguedad_dias` | +0,005 | +0,011 | −0,000 | −0,003 |
| `duracion_modelo` | +0,007 | +0,006 | +0,002 | −0,001 |
| `monto_actual` | +0,019 | +0,023 | +0,001 | +0,002 |
| `monto_historico` | +0,027 | +0,018 | −0,031 | −0,057 |
| `dias_desde_ultima_membresia` | +0,012 | +0,006 | −0,004 | −0,017 |
| `plan` | +0,012 | +0,001 | +0,001 | −0,006 |
| `mes_vencimiento` | +0,012 | +0,012 | +0,009 | +0,007 |

**Aporte medio con signo por grupo · umbral 0,32 (complemento)**

| Variable | VP (n=180) | FP (n=74) | FN (n=5) | VN (n=18) |
|---|---|---|---|---|
| `ciclos_previos` | −0,008 | −0,027 | −0,047 | −0,047 |
| `antiguedad_dias` | +0,002 | +0,001 | −0,006 | −0,008 |
| `duracion_modelo` | +0,004 | +0,002 | −0,008 | −0,007 |
| `monto_actual` | +0,007 | +0,008 | −0,005 | −0,005 |
| `monto_historico` | −0,009 | −0,038 | −0,069 | −0,071 |
| `dias_desde_ultima_membresia` | +0,003 | −0,006 | −0,041 | −0,042 |
| `plan` | +0,006 | −0,001 | −0,019 | −0,019 |
| `mes_vencimiento` | +0,010 | +0,009 | +0,006 | +0,005 |

Las tablas de \|SHAP\| medio por grupo están en `salidas/m03/m03_prueba_aporte_por_grupo_top25.csv` y `m03_prueba_aporte_por_grupo_umbral.csv`.

**Importancia por mes en prueba (\|SHAP\| medio y puesto)**

| Variable | may 2026 (n=94) | jun 2026 (n=86) | jul 2026 (n=93) | ago 2026 (n=4) |
|---|---|---|---|---|
| `monto_historico` | 0,047 (1.º) | 0,048 (1.º) | 0,053 (1.º) | 0,062 (1.º) |
| `ciclos_previos` | 0,031 (2.º) | 0,033 (2.º) | 0,035 (2.º) | 0,041 (2.º) |
| `plan` | 0,027 (3.º) | 0,026 (3.º) | 0,025 (3.º) | 0,019 (4.º) |
| `dias_desde_ultima_membresia` | 0,017 (4.º) | 0,016 (5.º) | 0,015 (5.º) | 0,027 (3.º) |
| `monto_actual` | 0,012 (6.º) | 0,020 (4.º) | 0,016 (4.º) | 0,007 (7.º) |
| `duracion_modelo` | 0,014 (5.º) | 0,008 (8.º) | 0,011 (6.º) | 0,008 (6.º) |
| `antiguedad_dias` | 0,006 (8.º) | 0,012 (6.º) | 0,006 (8.º) | 0,009 (5.º) |
| `mes_vencimiento` | 0,009 (7.º) | 0,010 (7.º) | 0,009 (7.º) | 0,007 (8.º) |

Los tres primeros puestos son los mismos en mayo, junio y julio; agosto (4 casos) solo es ilustrativo.

### 2.3 Comparación validación ↔ prueba (y entrenamiento)

| Variable | \|SHAP\| medio entrenamiento (puesto) | Validación (puesto) | Prueba (puesto) |
|---|---|---|---|
| `monto_historico` | 0,037 (1.º) | 0,049 (1.º) | 0,049 (1.º) |
| `ciclos_previos` | 0,025 (2.º) | 0,033 (2.º) | 0,033 (2.º) |
| `plan` | 0,023 (3.º) | 0,025 (3.º) | 0,026 (3.º) |
| `dias_desde_ultima_membresia` | 0,015 (5.º) | 0,014 (4.º) | 0,016 (4.º) |
| `duracion_modelo` | 0,009 (8.º) | 0,014 (5.º) | 0,011 (6.º) |
| `antiguedad_dias` | 0,010 (7.º) | 0,011 (6.º) | 0,008 (8.º) |
| `monto_actual` | 0,013 (6.º) | 0,010 (7.º) | 0,016 (5.º) |
| `mes_vencimiento` | 0,017 (4.º) | 0,009 (8.º) | 0,009 (7.º) |

- **Spearman de rangos validación–prueba: 0,881.** Las tres primeras variables son las mismas y en el mismo orden; el modelo usa la misma lógica en datos que no vio.
- **Validación–entrenamiento: 0,667.** La diferencia viene sobre todo de `mes_vencimiento`, que en entrenamiento es 4.ª: allí sus columnas *one-hot* sí toman valores (meses de 2025), mientras que en validación y prueba valen 0 (M02 §6). Por eso el entrenamiento es **solo informativo** (dentro de muestra).

### 2.4 ¿Se mantienen las conclusiones FP/FN de M02 en prueba?

| | Clasificación | Grupo | Variable | Conclusión de M02 | Validación: aporte (puesto) | Prueba: aporte (puesto) | ¿Se mantiene? |
|---|---|---|---|---|---|---|---|
| C1 | Top 25 | FP | `monto_historico` | Los FP se ven como los VP: poca historia pagada sube el riesgo | +0,029 (2.º) | +0,018 (1.º) | Sí |
| C2 | Top 25 | FP | `ciclos_previos` | Pocos ciclos previos suben el riesgo de los FP | +0,019 (4.º) | +0,012 (3.º) | Sí |
| C3 | Top 25 | FP | `plan` | El plan sube el riesgo de los FP | +0,020 (1.º) | +0,001 (4.º) | **No** |
| C4 | Top 25 | FP | `monto_actual` | Lo único que distingue a los FP: el monto actual sube su riesgo | +0,018 (3.º) | +0,023 (2.º) | Sí, **más débil** |
| C5 | Top 25 | FN | `monto_historico` | Los FN son socios con historia: el monto histórico baja su riesgo | −0,041 (1.º) | −0,031 (1.º) | Sí |
| C6 | Top 25 | FN | `ciclos_previos` | Los ciclos previos bajan el riesgo de los FN | −0,026 (2.º) | −0,023 (2.º) | Sí |
| C7 | Umbral | FP | `monto_historico` | Los FP tienen monto histórico que baja el riesgo | −0,029 (1.º) | −0,038 (1.º) | Sí |
| C8 | Umbral | FP | `ciclos_previos` | Los FP tienen ciclos previos que bajan el riesgo | −0,019 (2.º) | −0,027 (2.º) | Sí |
| C9 | Umbral | FN | `monto_historico` | (solo ilustrativo) baja el riesgo de los FN | −0,074 (1.º) | −0,069 (1.º) | Sí |
| C10 | Umbral | FN | `ciclos_previos` | (solo ilustrativo) baja el riesgo de los FN | −0,049 (2.º) | −0,047 (2.º) | Sí |
| C11 | Umbral | FN | `dias_desde_ultima_membresia` | (solo ilustrativo) baja el riesgo de los FN | −0,035 (3.º) | −0,041 (3.º) | Sí |

**Se mantienen 10 de 11.**

- **C3 no se mantiene:** en prueba, `plan` en los FP del top 25 queda en +0,0013 (4.º puesto), frente a +0,0124 en los VP. El plan no es lo que lleva a los FP al top 25 en prueba.
- **C4 se mantiene, pero más débil como rasgo distintivo:** el aporte de `monto_actual` en los FP sigue siendo positivo y alto (+0,023, 2.º), pero en prueba los VP también lo tienen (+0,019; en validación, +0,001). Ya no separa con claridad a los FP de los VP.
- La lectura general de M02 se confirma: los FP se parecen a los VP (poca historia pagada, pocos ciclos previos) y los FN a los VN (socios con historia); los errores no tienen una señal propia con las variables disponibles.

### 2.5 Lista de septiembre

57 socios, modelo operativo de §13.8, valor base **0,5000**, error máximo de aditividad 6,33e-15.

| Variable | \|SHAP\| medio | Aporte medio con signo | Puesto |
|---|---|---|---|
| `monto_historico` | 0,045 | +0,002 | 1 |
| `ciclos_previos` | 0,035 | −0,001 | 2 |
| `plan` | 0,029 | +0,019 | 3 |
| `dias_desde_ultima_membresia` | 0,020 | +0,011 | 4 |
| `monto_actual` | 0,018 | +0,011 | 5 |
| `duracion_modelo` | 0,013 | +0,006 | 6 |
| `antiguedad_dias` | 0,011 | −0,002 | 7 |
| `mes_vencimiento` | 0,005 | +0,004 | 8 |

El mismo orden de las tres primeras que en validación y prueba. Dos *waterfalls* ilustrativos (mayor y menor probabilidad del top 25: 0,71 y 0,62).

### 2.6 Entrenamiento (informativo)

845 casos, aditividad 2,55e-15. Al ser dentro de muestra, la importancia está sesgada hacia lo que el bosque memorizó (en especial `mes_vencimiento`, 4.ª); no se usa para conclusiones. Aparece como tercera serie en `m03_importancia_val_vs_prueba.png`.

## 3. Parte 2 · "Motivos principales" con SHAP

### 3.1 Método anterior frente a SHAP

| | Antes (hasta M02): sustitución | Ahora (M03): SHAP |
|---|---|---|
| Aporte de una variable | Probabilidad del socio menos la probabilidad con **esa** variable sustituida por la de un socio "típico" (medianas y modas de entrenamiento), una variable cada vez | Valor SHAP de la variable (clase "no renovó"), con las columnas *one-hot* sumadas |
| Suma de los aportes | No cuadra con nada | Valor base + suma = probabilidad del socio (aditividad < 1e-6) |
| Interacciones y variables correlacionadas | Cada variable se mide aislada: una misma interacción puede contarse en varias | El mérito se reparte entre las variables sin contarlo dos veces |
| Coherencia con el análisis de la tesis | Distinta de §12.12 | La misma técnica que M02/M03 |
| Necesita | La referencia guardada en el artefacto | Solo el `pipeline` del artefacto (v1 y v2 sirven sin reentrenar) |

### 3.2 Contrato (igual en notebook y app)

1. Aporte de una variable = su SHAP agregado; las columnas *one-hot* se suman de izquierda a derecha en el orden de la matriz, desde 0,0, en `float64`.
2. Candidatas = las variables de `NOMBRE_VARIABLE` presentes en el modelo, en ese orden. **`mes_vencimiento` nunca aparece** (no es accionable; se explica y se suma para que la aditividad cuadre, pero no es candidata).
3. Se toman las que tienen aporte **> 0,005 sin redondear**, de mayor a menor (orden estable: en empate manda el orden de `NOMBRE_VARIABLE`), **hasta 3**.
4. Formato `"<Nombre>: <valor> (+0,dd)"`, por ejemplo `Plan: TRIMESTRAL (+0,09)`; valores numéricos sin decimales y con punto de miles; vacío → `sin dato`. Sin ninguna → "Sin factores de riesgo destacados" (en la app, lista vacía).
5. **No cambian** las probabilidades, el orden ni los niveles (0,70 / 0,50). La pantalla y el Excel siguen mostrando el motivo **sin** el número ([ADR-007](../adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md)).

Texto completo del contrato: `salidas/m03/m03_contrato_motivos_shap.md`.

### 3.3 Efecto del cambio en la lista de septiembre

| Concepto | Socios |
|---|---|
| Socios de la lista | 57 |
| Mismo primer motivo (misma variable) | 17 |
| Mismo conjunto de variables | 14 |
| Conjunto de variables distinto | 43 |
| Texto idéntico (variables y aportes) | 9 |
| "Sin factores de riesgo destacados" antes → después | 7 → 6 |
| Top 25: mismo primer motivo | 6 |
| Top 25: mismo conjunto de variables | 0 |

**Veces que cada variable aparece entre los motivos de los 57 socios**

| Variable | Antes (sustitución) | Después (SHAP) |
|---|---|---|
| Monto histórico (USD) | 0 | 37 |
| Membresías previas | 0 | 33 |
| Plan | 40 | 40 |
| Días desde la membresía anterior | 45 | 16 |
| Monto actual (USD) | 22 | 13 |
| Duración del plan (días) | 2 | 5 |
| Antigüedad (días) | 0 | 2 |

Lectura: con el método anterior, los 25 socios de mayor riesgo mostraban "Días desde la membresía anterior: sin dato" porque están en su primera membresía y no tienen una membresía anterior (por definición, esa variable queda vacía cuando no hay membresía previa hasta T−30; al medir cada variable por separado, cambiar ese vacío por el valor del socio "típico" movía mucho la probabilidad). SHAP atribuye su riesgo a esa falta de historia: predominan "Membresías previas: 0" (22 de los 25) y "Monto histórico: 0" (los 25), junto con el plan, que es lo que el análisis global identifica como la lógica del modelo (poca historia pagada). Los motivos nuevos son coherentes con §12.12 y con la tesis.

### 3.4 App

- **Dependencia:** `shap==0.54.1` en `Backend/pyproject.toml` (la misma del notebook). Transitivas nuevas: slicer 0.0.8 y tqdm 4.70.1. **No instala numba ni llvmlite** (el plan inicial los suponía). scikit-learn 1.8.0 y numpy 2.5.3 no cambian.
- **Dónde:** solo en `app/infrastructure/ml/random_forest.py`: `aportes_shap(modelo, frame)` (explicador, matriz, salida `[:, :, 1]`, suma de *one-hot*) y `predecir_con` (selección y texto). shap comprueba la aditividad (`check_additivity`). `import-linter` prohíbe `shap` en `domain` y `application` ([ADR-002](../adr/ADR-002-ml-en-infraestructura.md)).
- **Tiempo:** unos 0,02 s para 57 filas y unos 0,4 s para 1.600 (entrenamiento y CU-02 llaman también a `predecir_con`).
- **Contrato de la API sin cambios:** `factores_principales: string[]`. Sin migraciones ni endpoints nuevos.
- **Listas guardadas:** conservan sus motivos (instantáneas inmutables); solo las listas nuevas usan SHAP.
- **Artefactos:** el método lo decide el adaptador, no el artefacto. `metadata_tecnica.metodo_factores = "shap"` (y la versión de `shap`) solo existe en los modelos entrenados después de M03; v1 y v2 no la tienen y aun así explican con SHAP. La `referencia` del método anterior se sigue guardando por compatibilidad, pero ya no interviene.
- **Ayuda de la Lista:** la sección "Motivos" de `AyudaLista.tsx` explica en lenguaje sencillo qué son los motivos (texto en [06 §4](../06-como-funciona-la-lista.md#4-motivos)).

### 3.5 Paridad notebook ↔ app

`Backend/scripts/verificar_lista.py` compara, además de probabilidades, niveles y orden, los **motivos SHAP** (texto exacto) y `metodo_factores`; `referencia_factores` pasa a ser solo informativa. Resultado con los libros reales: **0 diferencias en las 57 filas, incluidos los 146 motivos SHAP**.

### 3.6 Puesta en uso (stack principal, 2026-10-16)

Respaldo previo `respaldos/proyectofinal-20261016-074526`. Reconstrucción de backend y frontend: `LISTO` con v2 (sin reentrenar ni adoptar); el contenedor tiene shap 0.54.1, scikit-learn 1.8.0 y numpy 2.5.3; la ayuda nueva se sirve. Conteos antes = después: socios 1.516, membresías 2.854, modelos 2, listas 1, predicciones 28, gestiones 6. No se generó ninguna lista: la primera lista nueva del usuario será la primera con motivos SHAP. En el stack E2E los modelos sintéticos son constantes (16 ciclos) y no dan motivos; el formato quedó cubierto por las pruebas y por una comprobación en memoria dentro de la imagen.

## 4. Figuras

Rutas relativas a `Documentation/claude/mejoras/M03/` (carpeta fuera de git).

| Figura | Contenido | Notebook | Sección de la tesis |
|---|---|---|---|
| `m03_prueba_resumen_bar.png` | \|SHAP\| medio por variable en prueba | §12.12·M03 | Resultados – explicabilidad en prueba: importancia global |
| `m03_prueba_beeswarm.png` | Aporte por caso en prueba, coloreado por el valor original | §12.12·M03 | Resultados – explicabilidad en prueba: dirección del efecto |
| `m03_prueba_aporte_por_grupo.png` | Aporte medio con signo por grupo (top 25) en prueba | §12.12·M03 | Resultados – aciertos y errores en prueba |
| `m03_prueba_importancia_por_mes.png` | \|SHAP\| medio por variable, may–ago 2026 | §12.12·M03 | Resultados – estabilidad mensual |
| `m03_importancia_val_vs_prueba.png` | Importancia en validación, prueba y entrenamiento | §12.12·M03 | Resultados – estabilidad entre conjuntos (§2.3) |
| `m03_prueba_waterfall_vp_1.png` | VP · jun 2026 · probabilidad 0,75 | §12.12·M03 | Anexo – casos individuales en prueba |
| `m03_prueba_waterfall_vp_2.png` | VP · ago 2026 · probabilidad 0,33 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_fp_1.png` | FP · jun 2026 · probabilidad 0,68 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_fp_2.png` | FP · ago 2026 · probabilidad 0,31 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_fn_1.png` | FN · jun 2026 · probabilidad 0,57 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_fn_2.png` | FN · jul 2026 · probabilidad 0,31 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_vn_1.png` | VN · jun 2026 · probabilidad 0,57 | §12.12·M03 | Ídem |
| `m03_prueba_waterfall_vn_2.png` | VN · jun 2026 · probabilidad 0,29 | §12.12·M03 | Ídem |
| `m03_lista_waterfall_1.png` | Lista · sep 2026 · probabilidad 0,71 | §13.8 | Aplicación – cómo se obtienen los motivos de un socio |
| `m03_lista_waterfall_2.png` | Lista · sep 2026 · probabilidad 0,62 | §13.8 | Ídem |

Selección de *waterfalls*: la misma regla fija de M02 §10 (mayor y menor probabilidad del grupo, desempate por código HMAC ascendente); en la lista, mayor y menor probabilidad del top 25.

## 5. Limitaciones

**Que cierra M03** (de [M02 §11](M02-explicabilidad-shap.md#11-limitaciones)):

- **Punto 6 (solo validación):** el análisis se repitió en prueba (277), en la lista (57) y en entrenamiento (845, informativo); 10 de 11 conclusiones se mantienen.
- **Punto 7 (la app no usaba SHAP):** los motivos de la lista se calculan con SHAP en el notebook y en la app, con paridad comprobada.

**Que quedan:**

1. SHAP explica el modelo, no la causalidad: un motivo no es la causa de que el socio no renueve (se advierte en la ayuda).
2. Variables correlacionadas (`ciclos_previos`, `monto_historico`, `antiguedad_dias`) se reparten el mérito; en los motivos pueden aparecer juntas como "historia del socio".
3. `mes_vencimiento` sigue sin aportar información útil (limitación de M01) y se excluye de los motivos.
4. Grupos pequeños: FN (5) y VN (18) del umbral y agosto de 2026 (4 casos) solo son ilustrativos.
5. Valor base ≈ 0,50 por `class_weight="balanced"`: los aportes son relativos a ese punto, no a la tasa real.
6. Las listas generadas antes de M03 conservan los motivos por sustitución: en el historial conviven ambos métodos.
7. **Seguridad S1 (low, diferido):** las dependencias transitivas de shap no están fijadas (no hay *lockfile*); es el mismo diferido que S10.
8. **Seguridad S2 (low, diferido):** el notebook, en §13.3 y §13.8, muestra el código HMAC junto con fecha, plan y monto por socio (ya pasaba desde M01); conviene valorar mostrar solo agregados.

## 6. Privacidad

- Salidas visibles de §12.12·M03 y figuras sin código de socio, nombre, cédula ni fecha exacta (celda de control con `assert` y control en §14.2); *waterfalls* con montos redondeados, días en rangos, mes como "jun 2026" y probabilidad a 2 decimales.
- CSV de `salidas/m03/` con, como máximo, el código HMAC (sal secreta, M01 §14), el mes `AAAA-MM`, el grupo, la probabilidad a 3 decimales y los SHAP agregados. `salidas/` y `Documentation/claude/` están fuera de git.
- En la app, los motivos y los logs no añaden datos personales nuevos; el artefacto sigue deserializándose solo desde la base de datos.
- Excepción conocida: S2 (§5, punto 8).

## 7. Cómo se verificó

| Control | Resultado |
|---|---|
| Notebook completo (nbconvert) | Sin errores; §14.2 con los controles nuevos (aditividad SHAP en prueba y lista, motivos = SHAP sin `mes_vencimiento`, salidas M03 sin datos personales) en verde |
| Cifras de M01/M02 | Sin cambios (PR-AUC val 0,7204, umbral 0,32) |
| Lista de septiembre | 57 filas; probabilidades, orden y niveles idénticos a antes del cambio |
| `verificar_lista.py` | 0 diferencias en 57 filas, 146 motivos SHAP |
| Backend | pytest 2050+3 (unitarias e integración con PostgreSQL), `ruff`, `mypy app`, `lint-imports` |
| Frontend | 863 Vitest |
| E2E | 10 pruebas Playwright en el stack aislado (8081) |
| Seguridad | Clean (S1 y S2 low, diferidos) |

## 8. Qué añadir/cambiar en el documento de la tesis

1. **Metodología – explicabilidad:** ampliar la sección de M02 con la aplicación de SHAP a prueba, lista y entrenamiento (§2.1) y la regla "se mantiene / no se mantiene" de las conclusiones.
2. **Metodología – motivos de la lista:** sustituir la descripción del método por sustitución (socio "típico") por el contrato SHAP de §3.2; explicar por qué se cambió (§3.1) y que `mes_vencimiento` se excluye por no ser accionable.
3. **Resultados – explicabilidad en prueba (nuevo):** tabla de tamaños, importancia global, aporte por grupo (§2.2) y figuras `m03_prueba_resumen_bar`, `m03_prueba_beeswarm`, `m03_prueba_aporte_por_grupo`.
4. **Resultados – estabilidad:** tabla de §2.3, Spearman 0,881 y figura `m03_importancia_val_vs_prueba`; tabla por mes y `m03_prueba_importancia_por_mes` junto a la de M02.
5. **Resultados – aciertos y errores:** tabla de §2.4 (10 de 11 conclusiones se mantienen; C3 no, C4 más débil) y el argumento de capacidad en prueba (≥ 106 FN con 79 cupos).
6. **Aplicación / resultados operativos:** efecto del cambio de método en la lista de septiembre (§3.3) con sus dos tablas y los *waterfalls* de la lista; paridad notebook ↔ app (§3.5).
7. **Herramientas:** `shap` 0.54.1 ahora también en la aplicación (backend), sin numba ni llvmlite.
8. **Anexo:** los 8 *waterfalls* de prueba y los 2 de la lista con su leyenda.
9. **Limitaciones y trabajo futuro:** retirar "solo validación" y "la app no usa SHAP" (cerradas); añadir los puntos de §5 y, en trabajo futuro, fijar las dependencias transitivas con un *lockfile* y mostrar solo agregados en §13.3/§13.8 del notebook.
10. **Discusión / conclusiones:** la explicación del modelo es estable fuera de validación (mismas tres variables principales en prueba y en la lista) y los motivos que ve el personal son ahora coherentes con ese análisis.
