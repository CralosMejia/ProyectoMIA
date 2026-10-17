# Backend · 12 · Modelo v1, migración al arrancar, lista priorizada y Excel

R-004 (día 3). CU-03 completo, CU-04, CU-05 y CU-12. Réplica del notebook `Notebookes/MVP.ipynb` §7.2–7.4, §9.5, §13.3 y §13.8. Lectura y limpieza del histórico: [11-historico.md](11-historico.md). Esquema: [09](09-esquema-base-de-datos.md). Contrato: [API_CONTRACT](../API_CONTRACT.md). Decisiones: [ADR-002](../../adr/ADR-002-ml-en-infraestructura.md), [ADR-003](../../adr/ADR-003-reentrenamiento-y-versionado.md), [ADR-004](../../adr/ADR-004-migracion-datos-al-arrancar.md), [ADR-005](../../adr/ADR-005-fidelidad-al-notebook-del-modelo-v1.md).

## Componentes por capa

| Capa | Módulo | Responsabilidad |
|---|---|---|
| domain | `modelo/variables.py` | Variables en T−30 (§7.2–7.4): `mes_vencimiento` `"AAAA-MM"`, `inicio_aproximado` como texto, historial previo = ciclos no excluidos del socio con `fecha_actividad` estrictamente menor **y ≤ T−30** (M01: un previo con actividad = T−30 cuenta, con T−29 no), `monto_historico` (`None` = 0), `dias_desde_ultima_membresia`, `antiguedad_dias` (desde T−30), imputación de `monto_actual` (mediana del plan → general) y `duracion_modelo` (`DURACION_ESTANDAR`). `construir_variables` devuelve siempre las 10 columnas (el artefacto v1 sigue prediciendo). `calcular_medianas` solo recibe ciclos de entrenamiento. `ConjuntoVariables`, `CONJUNTO_COMPLETO`, `CONJUNTO_MODELO` (= variante sin `forma_pago` ni `inicio_aproximado`). Orden de entrenamiento (`identidad`, `fecha_actividad`, `fecha_vencimiento`, orden de lectura). `PERIODO_REFERENCIA_FACTORES`. |
| domain | `modelo/cartera.py` | Cartera en `(fecha, fecha + horizonte]` sin `DIARIO` ni duración ≤ 21 o > 400; "ya renovó"; orden por score y top K (empates: vencimiento y `membresia_id` ascendentes). |
| domain | `modelo/umbrales.py` | Cortes fijos `UMBRAL_ALTO = 0.70`, `UMBRAL_MEDIO = 0.50` (`umbrales_fijos`, reparto observado por nivel), `nivel_de` y `meses_recientes_con_resultado` (R-015; antes, percentil lineal). |
| domain | `common/predictor.py`, `common/fechas.py` | Puerto `PredictorModel`: recibe `Decimal \| int \| str \| None`, devuelve `score: Decimal` cuantizado a 8 decimales (`NUMERIC(10,8)`). |
| application | `modelo/{mapeo,entrenar_modelo}.py` | `EntrenarModeloInicial(predictor, variables=CONJUNTO_MODELO)`: ciclos evaluables → medianas de esos evaluables (los pendientes no las cambian) → variables → entrenamiento con las columnas del conjunto → referencia de factores → umbrales. Medianas en `metadata_tecnica["medianas_monto"]`. |
| application | `modelo/adoptar_modelo.py` | `AdoptarModelo` (R-015): comando `adoptar-modelo`, ver §Reentrenamiento. |
| application | `sistema/{ports,migrar_historico,consultar_estado}.py` | `MigrarHistorico` (CU-03) y estado del sistema. |
| application | `listas/{generar_lista,consultar_listas,ports,dtos}.py` | `GenerarLista` (CU-04) y consultas (CU-05). |
| infrastructure | `ml/random_forest.py` | Único punto con scikit-learn, shap y `Decimal ↔ float`. Pipeline §9.5, factores §13.3 con SHAP (`aportes_shap`, R-017), artefacto joblib y `metadata_tecnica` con parámetros y versiones. |
| infrastructure | `exportacion/excel_lista.py` | Excel en memoria (CU-12). |
| infrastructure | `persistence/{unit_of_work,unit_of_work_listas}.py`, `repositories/{modelo,listas,sistema}.py`, `historico/localizador_libros.py` | Unidades de trabajo, repositorios, bloqueo consultivo y localizador `*Control*Gym*.xlsx`. |
| api | `routers/sistema.py`, `routers/listas.py`, `main.py` | Estado real, endpoints de listas y lanzamiento de la migración en un hilo al arrancar. |

## Modelo (adaptador `RandomForestPredictor`)

- `SimpleImputer(median)` + `StandardScaler` para las numéricas; `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")` para las categóricas; `RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=20, class_weight="balanced", random_state=42)`, entrenado con **todos** los evaluables (1.564 con los libros reales).
- **scikit-learn 1.8.0** (la del notebook): con 1.9.1 el bosque cambia (24/25 del top iguales, probabilidades ±0,001–0,016). Ver `Backend/README.md`.
- El artefacto (joblib) se guarda en `modelos.artefacto` y **solo** se deserializa desde ahí (ADR-003). Serializar → deserializar da scores idénticos.
- **Factores con SHAP (§13.3, R-017/M03, [ADR-015](../../adr/ADR-015-motivos-con-shap-en-la-app.md)):** `aportes_shap(modelo, frame)` aplica `shap.TreeExplainer` al bosque sobre `preparacion.transform(X)` densa, toma la clase "no renovó" (`[:, :, 1]`) y suma las columnas *one-hot* a su variable de izquierda a derecha desde 0,0 (`float64`); shap comprueba la aditividad (`check_additivity`). `predecir_con` elige candidatas de `NOMBRE_VARIABLE` presentes en el modelo (**nunca** `mes_vencimiento`), aporte > 0,005 sin redondear, de mayor a menor (empate: orden de `NOMBRE_VARIABLE`), hasta 3; formato `"Plan: TRIMESTRAL (+0,09)"`, numéricos con separador de miles `.`, `None` → `"sin dato"`; ninguno → tupla vacía. El `score` no cambia. Coste medido: ~0,02 s para 57 filas, ~0,4 s para 1.600. `shap==0.54.1` (transitivas slicer y tqdm; **no** numba ni llvmlite); `import-linter` prohíbe `shap` en `domain`/`application`.
  - El método lo decide el adaptador: v1 y v2 explican con SHAP sin reentrenar. `metadata_tecnica` registra `shap` y `metodo_factores: "shap"` solo en modelos entrenados después de M03.
  - ~~Factores por sustitución contra una referencia (medianas y modas de `PERIODO_REFERENCIA_FACTORES`)~~ — sustituido en R-017. La referencia se sigue calculando y guardando en el artefacto (`referencia_factores`) por compatibilidad, pero no interviene en los motivos. Las listas guardadas conservan los motivos con que se generaron.
- **Variables del modelo (M01):** numéricas `ciclos_previos`, `antiguedad_dias`, `duracion_modelo`, `monto_actual`, `monto_historico`, `dias_desde_ultima_membresia`; categóricas `plan`, `mes_vencimiento`. Elegidas por la regla (d) de R-015 ([ADR-014](../../adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md)).
- **Umbrales (CU-05, R-015, decisión del usuario):** cortes fijos del notebook; ALTO si `score ≥ 0,70`, MEDIO si `≥ 0,50`, si no BAJO (igualdad → nivel superior). `porcentajes_umbral` = reparto observado (entero, redondeo bancario) de los scores sobre los evaluables de los 3 meses de vencimiento más recientes; informativo. App y notebook asignan ya el mismo nivel. ~~P80/P50 con `porcentajes_umbral = {"ALTO":20,"MEDIO":30,"BAJO":50}`~~ (R-004 (d), sustituido; el v1 del stack principal conserva esos umbrales y sus listas sus niveles).
- La `version` la calcula el llamante (v1 en la migración).

## Migración al arrancar (CU-03, ADR-004)

1. `main.py` lanza `MigrarHistorico` en un hilo si `MIGRAR_HISTORICO_AL_ARRANCAR` (defecto `true`); `/health` responde durante toda la migración.
2. Bloqueo consultivo de **sesión** en una conexión propia con `AUTOCOMMIT`; se libera en `finally` y la conexión se invalida al salir. Si otro proceso lo tiene, no hace nada.
3. Ya migrado (carga `MIGRACION_HISTORICA`, membresías o `COMPLETADA`) → no hace nada: reiniciar no vuelve a migrar. Un `EN_CURSO` huérfano con la base vacía se trata como `PENDIENTE`.
4. `EN_CURSO` en transacción corta → lectura, limpieza y entrenamiento → **una** unidad de trabajo guarda carga, socios (datos del registro más reciente en orden de lectura), membresías (con `fecha_actividad`), modelo v1 vigente, intento `INICIAL`/`ENTRENADO`, próxima fecha de reentrenamiento (6 meses) y `COMPLETADA`. `cargas.filas_duplicadas = 0`.
5. Fallo → nada se guarda; transacción corta a `PENDIENTE`. `GET /sistema/estado` responde `FALTAN_DATOS_HISTORICOS` (faltan libros, ilegibles o cualquier otro fallo); el motivo vive solo en memoria y en el log técnico (conteos, libro, hoja, tipo de excepción; nunca datos personales). Se reintenta al reiniciar el backend. No se añadió un estado nuevo.

Con los libros reales: `LISTO` en ~5 s; 2.748 membresías, 1.410 socios, 1 modelo vigente, 1 intento `INICIAL`.

## Reentrenamiento (CU-02, R-011)

Decisiones y motivos: [ADR-011](../../adr/ADR-011-reglas-del-reentrenamiento.md) (detalla [ADR-003](../../adr/ADR-003-reentrenamiento-y-versionado.md)). Guía para el operador: [Backend/README §4](../../../Backend/README.md#4-reentrenamiento-automático-cu-02).

| Capa | Módulo | Responsabilidad |
|---|---|---|
| domain | `modelo/reentrenamiento.py` | Etiquetado de ciclos al corte (misma regla que `historico.ciclos`), `es_ciclo_nuevo`, `CriteriosReentrenamiento`, `evaluar_criterios` (motivos), `accion_programada` (EJECUTAR/OMITIR/ESPERAR), `proxima_tras_omitido`. |
| domain | `modelo/metricas.py` | `pr_auc`: *average precision* igual a `sklearn.metrics.average_precision_score`, en `Decimal`, 8 decimales. |
| application | `modelo/reentrenar_modelo.py` | `ReentrenarModelo.revisar_programado()` / `.ejecutar_manual()` → `ResultadoReentrenamientoDTO(resultado, motivo, version)`. |
| application | `modelo/mapeo.py` | Única conversión membresía → ciclo; la usan el modelo y las listas. `EntrenarModeloInicial.ejecutar_ciclos` entrena sobre ciclos ya etiquetados (mismos resultados que antes). |
| infrastructure | `persistence/unit_of_work_reentrenamiento.py`, `repositories/{historial,modelo}.py` | Membresías para entrenamiento (con `created_at`, sin borradas), modelo e intento, próxima fecha; bloqueo consultivo propio (clave distinta de la migración). |
| infrastructure | `planificador/reentrenamiento.py` | Hilo daemon: revisa al arrancar y cada hora; llama al servicio solo cuando cambia el día de negocio; si falla o el bloqueo está ocupado, reintenta en la vuelta siguiente. |
| — | `app/cli.py` | `python -m app.cli reentrenar`: una línea con resultado y motivo; salida `0` intento registrado (`ENTRENADO`, `CRITERIOS_NO_CUMPLIDOS`, `NO_SUPERA_VIGENTE`), `1` `FALLIDO`/sistema no listo/configuración inválida, `2` reentrenamiento en curso o sin subcomando. `python -m app.cli adoptar-modelo` (R-015): ver abajo. |

- **Corte de los datos (R-015):** CU-02 y `adoptar-modelo` etiquetan los ciclos a `corte_de_datos(hoy, corte del vigente, día de la última carga por plantilla)` = `min(hoy, max(corte vigente, última carga))`, como el notebook (que etiqueta al 31-08-2026, fin de los libros). Etiquetar a "hoy" marcaría como "no renovó" a ciclos cuya renovación aún no se cargó. Desde R-018 el bloque `piloto` del dashboard verifica la renovación del top 25 con este mismo corte ([mejoras/M04](../../mejoras/M04-indicadores-del-piloto.md)).
- **Margen del candidato (R-015, decisión (f)):** `ciclos_para_candidato` excluye la comparación y los ciclos con `vencimiento + 30 ≥ min(vencimiento de la comparación)`; esos ciclos quedan en el historial como pendientes. Medianas del candidato = las de sus ciclos. El modelo final se sigue entrenando con todos los evaluables.
- **`adoptar-modelo` (R-015, ADR-014):** con migración `COMPLETADA` y modelo vigente, etiqueta al corte de los datos, entrena una vez con todos los evaluables y `CONJUNTO_MODELO` (sin candidato ni criterios), y en **una** transacción guarda la versión vigente + 1 como vigente (la anterior se conserva) y un intento `MANUAL`/`ENTRENADO` "Adopción del modelo M01" (`metadata_tecnica["adopcion"]`). No mueve la próxima fecha programada. Fallo del entrenamiento → nada guardado (ni `FALLIDO`). Comparte el bloqueo del reentrenamiento. Salidas: `0` "vN en uso"; `1` sistema no listo, fallo, base inaccesible o configuración inválida; `2` reentrenamiento en curso. **No es idempotente:** cada ejecución crea una versión; se ejecuta una sola vez. Ejecutado en el principal el 2026-10-15: v2 vigente (1.660 ciclos, `fecha_corte` 2026-09-30 por la carga mensual del 01-10-2026, reparto ALTO 15 / MEDIO 52 / BAJO 33 %); solo `modelos` +1 e `intentos_reentrenamiento` +1.

- **Ciclo nuevo evaluable:** evaluable al corte de hoy y con `fecha_vencimiento + 30 > fecha_corte` del vigente (`metadata_tecnica["fecha_corte"]`; `>` estricto para no contar dos veces el borde). El dashboard usa la misma función (`ciclos_nuevos_evaluables`).
- **Criterios** (configurables, `REENTRENAR_*`): ≥ 150 ciclos nuevos; ≥ 60 % de las membresías con `created_at` posterior al entrenamiento vigente con vencimiento (ninguna → no se cumple); ≥ 20 por clase entre los nuevos; todas las variables del pipeline presentes.
- **Comparación:** evaluables de los 3 meses de vencimiento más recientes con resultado; el candidato se entrena sin ellos ni los del margen de 30 días (arriba); `PR-AUC candidato < vigente` → `NO_SUPERA_VIGENTE` con ambas cifras. Si no es peor, el modelo final se entrena con **todos** los evaluables, versión = vigente + 1, con `fecha_corte` en `metadata_tecnica`.
- **Transacciones:** modelo nuevo (desmarca el anterior, que se conserva), intento y próxima fecha en **una**; si algo falla, nada de eso se guarda y el intento `FALLIDO` va en una transacción aparte.
- **Fechas:** programado → próxima = hoy + 6 meses tras `ENTRENADO`, `CRITERIOS_NO_CUMPLIDOS`, `NO_SUPERA_VIGENTE` o `FALLIDO`. Fecha pasada → un intento `OMITIDO` **por cada** fecha perdida, y la próxima = última fecha perdida + 6 meses (si cae hoy, reentrena a continuación). Manual → la fecha solo cambia si `ENTRENADO`.
- Una carga por plantilla no dispara el reentrenamiento. Logs y motivos sin datos de socios (de una excepción, solo su tipo).
- Verificado en el stack E2E (T31): `OMITIDO` forzado con fecha pasada → un solo intento; comando manual → `CRITERIOS_NO_CUMPLIDOS`, código 0. En el stack principal no se ejecutó.

## Lista priorizada (CU-04, CU-05)

- `POST /listas` exige estado `LISTO` con modelo vigente (si no, `409`, que tiene precedencia). La clasificación de los ciclos del historial usa corte = fecha de generación. Cartera → excluye los que ya renovaron → **excluye a los socios sin cédula** (R-005) → predice con el modelo vigente → ordena → marca top K → guarda lista e ítems en una transacción.
- **R-005 · fecha y horizonte:** "hoy" = fecha de negocio de Ecuador, `hoy_en_negocio(clock.now())` en `domain/common/fechas.py` (UTC−5 fijo, `ZONA_NEGOCIO`; un `datetime` sin zona → `ValueError`). Sin `fecha_referencia` se usa ese día; una fecha anterior → `FechaReferenciaPasadaError` (`422` "La fecha de la lista debe ser hoy o posterior."), sin guardar ni predecir. `horizonte_dias` de entrada 1..31 (`400` fuera de rango); los DTO de respuesta admiten 1..365 para listas antiguas.
- **R-005 · socios sin cédula:** `MembresiaParaPrediccion.socio_con_cedula` (`socios.cedula IS NOT NULL`, misma consulta única). Se filtran solo de la cartera: siguen en la base, en el entrenamiento y en el historial usado para las variables de los demás. Todos sin cédula → lista válida con 0 ítems.
- **R-005 · cédula en lugar de correo:** `ItemLista.cedula` y `PrediccionDTO.cedula` (string con cero inicial o `null`); el repositorio de listas lee `Socio.cedula` y ninguna consulta suya lee `socios.correo`.
- `advertencia_datos_antiguos` se evalúa con la última carga cuya `fecha_carga ≤ creada_en` de la lista frente a `fecha_generacion` (`datos_antiguos`), también al consultar listas anteriores.
- **R-008 · nombre de la lista:** `GenerarListaDTO.nombre` opcional; se recorta y debe quedar en 1..80 caracteres sin caracteres de control (`\x00-\x1f`, `\x7f`); si no, `400 validation_error`. Ausente o `null` → `nombre_por_defecto(fecha efectiva)` de `domain/listas/nombre.py`: `"Lista del <d> <mmm> <aaaa>"` con la tabla fija de meses sin punto (`ene … dic`), sin `locale` ni reloj (`2026-09-29` → `"Lista del 29 sep 2026"`). Nombres repetidos permitidos; se guarda recortado y la neutralización `= + - @` solo ocurre al escribir el Excel. `NuevaLista`, `ListaDetalle` y `ListaResumen` llevan `nombre`; el mismo formato está en la migración `0006` y en el frontend (`fechaCorta`).
- Una lista guardada es inmutable (RN-04.5): sus ítems no filtran `deleted_at`, y el nombre no se edita después de generarla.
- **R-009 · gestión de cada ítem:** `ItemLista` y `PrediccionDTO` llevan `gestion_id`, `gestion_estado` y `campania_asignada`. El repositorio de listas los trae con un `LEFT JOIN` a la gestión del **ciclo** (`membresia_id`, `deleted_at IS NULL`) en la misma consulta de los ítems (sin N+1): una gestión creada desde una lista se ve en todas las listas que contienen esa membresía. `campania_asignada` es el nombre congelado (`gestiones_retencion.campania_nombre`). Sustituye la nota anterior ("salen `null` hasta CU-08").
- Sin prueba todavía de dos `POST /listas` simultáneos.

## Excel (CU-12)

`GET /listas/{id}/excel`: libro generado en `BytesIO` (openpyxl, sin temporales en disco, RN-12.1). Textos con prefijo `'` si empiezan por `= + - @` (sin fórmulas, incluido el nombre de la lista); bytes deterministas para la misma lista. Nombre del archivo `lista_<id>_<fecha>.xlsx`, sin datos personales.

**R-008 · el Excel es igual a la tabla de la pantalla:**

- Hojas: `Socios prioritarios a contactar` (ítems con `dentro_top_k`), `Otros socios por vencer` (el resto; solo encabezados si no hay) y `Resumen`. Las dos primeras por `prioridad` ascendente.
- Columnas A..H: Prioridad, Nombre, Cédula (texto con cero inicial; `null` → vacía), Plan, Vence el (fecha `dd/mm/yyyy`), Días para vencer (vencimiento − `fecha_generacion`), Nivel de riesgo (`Alto`/`Medio`/`Bajo`), Motivos principales (unidos con `"; "`, sin el aporte final entre paréntesis, misma regla que `APORTE_FINAL` de `TablaLista.tsx`; sin motivos → "Sin factores de riesgo destacados").
- `Resumen`: Nombre de la lista, Fecha de la lista, Vencen hasta, Socios prioritarios a contactar, Otros socios por vencer, Total de socios por vencer, Riesgo alto, Riesgo medio, Riesgo bajo. Sin versión del modelo, umbrales, Top K ni score.
- **R-009 · columnas I "Gestión" y J "Campaña"** en las dos hojas de socios, con los mismos textos que la pantalla y el estado **al momento de descargar**: sin gestión → "Sin gestión" y "—"; pendiente → "Pendiente"; cerrada → "Cerrada"; gestión sin campaña → "Sin campaña". El nombre de la campaña se neutraliza como el resto de textos (`= + - @`). El botón de acción no va al Excel. **Corrige** el criterio de R-008, que excluía estado de gestión y campaña: la regla vigente sigue siendo "Excel igual a la tabla" (ADR-007) y la tabla ahora las tiene.
- No incluye Celular, Score ni Monto. La API (`GET /listas/{id}`) **sigue** devolviendo `celular`, `score` y `monto_cobrado`.

~~R-005: el Excel conserva el score y los factores con su aporte~~ — **sustituido por R-008** (decisión del usuario). También queda revertido R-006 ("el celular se mantiene en el Excel"). De R-005 sigue vigente: "Cédula" en lugar de "Correo".

## Conciliación con el notebook (T19)

**Desde R-015 (M01):** `python scripts/verificar_lista.py <carpeta> [--referencia ../salidas]` (en memoria, sin BD, scikit-learn 1.8.0) lee las referencias **en tiempo de ejecución** de la carpeta git-ignorada `salidas/` del notebook (`m01/despues/parametros_modelo_operativo.json` y la hoja `cartera_completa` de `mvp/lista_operativa_2026-09.xlsx`; nunca se copian a archivos versionados) y compara **todas** las filas de la cartera: probabilidad a 8 decimales, nivel (0,70/0,50 en ambos), factores (texto exacto) y orden por grupo de empate. Los códigos de socio son HMAC-SHA256 con sal secreta (`MTABOLIC_SAL_CODIGOS` o `salidas/.sal_codigos`); la sal nunca se imprime. Ante un error no controlado solo imprime el tipo. Salidas: `0` sin diferencias, `1` alguna, `2` faltan libros, salidas o sal. Resultado: `0`, 0 diferencias en 57 filas (ALTO 2, MEDIO 39, BAJO 16), cartera 59, ya renovaron 2, 1.564 ciclos de entrenamiento.

**Desde R-017 (M03):** los factores comparados son los **motivos SHAP** (texto exacto, aporte a 2 decimales) y se comprueba también `metodo_factores`; la comparación de `referencia_factores` pasa a informativa (no cuenta como diferencia). La línea de resultado informa "motivos (SHAP) distintos: N". Resultado con scikit-learn 1.8.0 y shap 0.54.1: `0`, 0 diferencias en 57 filas, incluidos los 146 motivos.

~~R-004: top 25 comparado contra cifras fijas en el script~~ (sustituido por lo anterior): salida `0`, 25/25 probabilidades, orden y factores iguales, empate en la posición 25 como conjunto.

R-005 (decisión c): el script no pasa por la API ni por `GenerarLista` con la validación de fecha; construye su entrada con `model_construct` para mantener su ventana de 180 días y marca todas las membresías con `socio_con_cedula=True` para seguir comparando con el notebook. Sigue saliendo con `0`. Consecuencia: la lista de la app puede diferir del top 25 del notebook si en él hay socios sin cédula (por diseño).

## Decisiones de R-004

| | Decisión |
|---|---|
| (a) | Referencia de factores = evaluables con vencimiento en 2025 (`PERIODO_REFERENCIA_FACTORES`), como el notebook. Sustituye al criterio inicial del plan ("todo el entrenamiento"), con el que los factores no coincidían. |
| (b) | Contrato: `GET /listas` nuevo; `fecha_generacion` pasa a `date`, se añaden `creada_en` y `monto_cobrado`; factores `[]` → "Sin factores de riesgo destacados". |
| (c) | Fallo de migración → `PENDIENTE` + `FALTAN_DATOS_HISTORICOS`; reintento al reiniciar el backend. |
| (d) | ~~Umbrales por percentiles 20/30/50 (CU-05), no los fijos del notebook.~~ Sustituida en R-015: cortes fijos 0,70/0,50. |
| (e) | Empates de score: vencimiento y `membresia_id` ascendentes. |
| (f) | Datos del socio del registro más reciente en orden de lectura; `filas_duplicadas = 0`. |
| — | scikit-learn fijado a 1.8.0; localizador solo `*Control*Gym*.xlsx`. |

## Decisiones de R-005

| | Decisión |
|---|---|
| (a) | "Hoy" = fecha de negocio de Ecuador (UTC−5 fijo) en el backend; en el navegador, la fecha local (el PC del gimnasio está en Ecuador). |
| (b) | Fecha pasada → `422 domain_rule_violated`; horizonte fuera de 1..31 → `400 validation_error`. |
| (c) | `verificar_lista.py` conserva su ventana y trata a todos como "con cédula"; la app puede diferir del notebook. |
| (d) | Las listas guardadas no se modifican: pueden tener socios sin cédula (`null`, "—" en pantalla) y horizontes > 31. Ninguna respuesta incluye `correo`. |
| (e) | El Excel cambia Correo → Cédula y conserva score y aportes; la pantalla no. **Sustituida en R-008:** el Excel ya no lleva score ni aportes (ver §Excel). |

## Decisiones de R-015 (mejora M01)

Detalle metodológico: [mejoras/M01](../../mejoras/M01-modelo-sin-fuga-temporal.md). Decisión de arquitectura: [ADR-014](../../adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md).

| | Decisión |
|---|---|
| (a) | Historial de un ciclo solo con registros de actividad ≤ T−30 (prueba anti-fuga primero). |
| (b) | Medianas de monto solo con los ciclos de entrenamiento (app: evaluables con que entrena). |
| (c)(f) | Márgenes de 30 días en la evaluación del notebook y entre el candidato y la comparación de CU-02. |
| (d) | Variante sin `forma_pago` ni `inicio_aproximado` (`CONJUNTO_MODELO`). |
| (e) | Puesta en uso con `adoptar-modelo` (vigente + 1), no por CU-02. |
| (g) | `PERIODO_REFERENCIA_FACTORES` = vencimientos < 2025-12-02. |
| — | Niveles con cortes fijos 0,70/0,50 (decisión del usuario); corte de los datos para etiquetar. |

## Decisiones de R-017 (mejora M03)

Detalle: [mejoras/M03](../../mejoras/M03-shap-prueba-y-motivos-en-la-app.md). Decisión de arquitectura: [ADR-015](../../adr/ADR-015-motivos-con-shap-en-la-app.md).

| | Decisión |
|---|---|
| (e) | Motivos con SHAP, misma regla que el notebook (hasta 3, > 0,005, sin `mes_vencimiento`, formato sin cambios). Sustituye a (a) de R-004 y (g) de R-015 en lo que toca a los motivos. |
| (f) | Pantalla y Excel siguen sin mostrar el número (ADR-007). |
| — | Sin reentrenar ni adoptar; sin migraciones, endpoints ni cambio de contrato. Puesto en uso en el principal el 2026-10-16 (v2, conteos idénticos, sin generar listas). |

## Pendientes

- `mypy` sobre `tests/` con errores de tipado estricto en dobles (no incluido en `mypy app`).
- El motivo de un fallo de migración solo está en memoria (se pierde al reiniciar).
- Concurrencia de dos `POST /listas` sin prueba.
- S23 y revisión de seguridad → día 7.
