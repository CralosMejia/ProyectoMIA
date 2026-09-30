# Backend · 12 · Modelo v1, migración al arrancar, lista priorizada y Excel

R-004 (día 3). CU-03 completo, CU-04, CU-05 y CU-12. Réplica del notebook `Notebookes/MVP.ipynb` §7.2–7.4, §9.5, §13.3 y §13.8. Lectura y limpieza del histórico: [11-historico.md](11-historico.md). Esquema: [09](09-esquema-base-de-datos.md). Contrato: [API_CONTRACT](../API_CONTRACT.md). Decisiones: [ADR-002](../../adr/ADR-002-ml-en-infraestructura.md), [ADR-003](../../adr/ADR-003-reentrenamiento-y-versionado.md), [ADR-004](../../adr/ADR-004-migracion-datos-al-arrancar.md), [ADR-005](../../adr/ADR-005-fidelidad-al-notebook-del-modelo-v1.md).

## Componentes por capa

| Capa | Módulo | Responsabilidad |
|---|---|---|
| domain | `modelo/variables.py` | Variables en T−30 (§7.2–7.4): `mes_vencimiento` `"AAAA-MM"`, `inicio_aproximado` como texto, historial previo = ciclos no excluidos del socio con `fecha_actividad` estrictamente menor, `monto_historico` (`None` = 0), `dias_desde_ultima_membresia`, `antiguedad_dias`, imputación de `monto_actual` (mediana del plan → general) y `duracion_modelo` (`DURACION_ESTANDAR`). Orden de entrenamiento (`identidad`, `fecha_actividad`, `fecha_vencimiento`, orden de lectura). `PERIODO_REFERENCIA_FACTORES`. |
| domain | `modelo/cartera.py` | Cartera en `(fecha, fecha + horizonte]` sin `DIARIO` ni duración ≤ 21 o > 400; "ya renovó"; orden por score y top K (empates: vencimiento y `membresia_id` ascendentes). |
| domain | `modelo/umbrales.py` | Umbrales por percentil lineal en `Decimal`, nivel de riesgo y próxima fecha de reentrenamiento. |
| domain | `common/predictor.py`, `common/fechas.py` | Puerto `PredictorModel`: recibe `Decimal \| int \| str \| None`, devuelve `score: Decimal` cuantizado a 8 decimales (`NUMERIC(10,8)`). |
| application | `modelo/{mapeo,entrenar_modelo}.py` | `EntrenarModeloInicial`: ciclos evaluables → variables → entrenamiento → referencia de factores → umbrales. |
| application | `sistema/{ports,migrar_historico,consultar_estado}.py` | `MigrarHistorico` (CU-03) y estado del sistema. |
| application | `listas/{generar_lista,consultar_listas,ports,dtos}.py` | `GenerarLista` (CU-04) y consultas (CU-05). |
| infrastructure | `ml/random_forest.py` | Único punto con scikit-learn y `Decimal ↔ float`. Pipeline §9.5, factores §13.3, artefacto joblib y `metadata_tecnica` con parámetros y versiones. |
| infrastructure | `exportacion/excel_lista.py` | Excel en memoria (CU-12). |
| infrastructure | `persistence/{unit_of_work,unit_of_work_listas}.py`, `repositories/{modelo,listas,sistema}.py`, `historico/localizador_libros.py` | Unidades de trabajo, repositorios, bloqueo consultivo y localizador `*Control*Gym*.xlsx`. |
| api | `routers/sistema.py`, `routers/listas.py`, `main.py` | Estado real, endpoints de listas y lanzamiento de la migración en un hilo al arrancar. |

## Modelo (adaptador `RandomForestPredictor`)

- `SimpleImputer(median)` + `StandardScaler` para las numéricas; `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")` para las categóricas; `RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=20, class_weight="balanced", random_state=42)`, entrenado con **todos** los evaluables (1.564 con los libros reales).
- **scikit-learn 1.8.0** (la del notebook): con 1.9.1 el bosque cambia (24/25 del top iguales, probabilidades ±0,001–0,016). Ver `Backend/README.md`.
- El artefacto (joblib) se guarda en `modelos.artefacto` y **solo** se deserializa desde ahí (ADR-003). Serializar → deserializar da scores idénticos.
- **Factores (§13.3):** hasta 3, aporte > 0,005, de mayor a menor, sin `mes_vencimiento`; formato `"Plan: TRIMESTRAL (+0,09)"`, numéricos con separador de miles `.`, `None` → `"sin dato"`. Referencia = medianas y modas de los evaluables con vencimiento en `PERIODO_REFERENCIA_FACTORES` = [2025-01-01, 2026-01-01), como `X_train` del notebook; parametrizable en `domain/modelo/variables.py`.
- **Umbrales (CU-05):** `umbral_alto` = P80 y `umbral_medio` = P50 de los scores del v1 sobre los evaluables de los 3 meses de vencimiento más recientes; ALTO si `score ≥ umbral_alto`, MEDIO si `≥ umbral_medio`, si no BAJO; `porcentajes_umbral = {"ALTO":20,"MEDIO":30,"BAJO":50}`. **Difiere del notebook por diseño**, que usa umbrales fijos 0,70/0,50: el score y el orden coinciden, el nivel puede no coincidir.
- La `version` la calcula el llamante (v1 en la migración).

## Migración al arrancar (CU-03, ADR-004)

1. `main.py` lanza `MigrarHistorico` en un hilo si `MIGRAR_HISTORICO_AL_ARRANCAR` (defecto `true`); `/health` responde durante toda la migración.
2. Bloqueo consultivo de **sesión** en una conexión propia con `AUTOCOMMIT`; se libera en `finally` y la conexión se invalida al salir. Si otro proceso lo tiene, no hace nada.
3. Ya migrado (carga `MIGRACION_HISTORICA`, membresías o `COMPLETADA`) → no hace nada: reiniciar no vuelve a migrar. Un `EN_CURSO` huérfano con la base vacía se trata como `PENDIENTE`.
4. `EN_CURSO` en transacción corta → lectura, limpieza y entrenamiento → **una** unidad de trabajo guarda carga, socios (datos del registro más reciente en orden de lectura), membresías (con `fecha_actividad`), modelo v1 vigente, intento `INICIAL`/`ENTRENADO`, próxima fecha de reentrenamiento (6 meses) y `COMPLETADA`. `cargas.filas_duplicadas = 0`.
5. Fallo → nada se guarda; transacción corta a `PENDIENTE`. `GET /sistema/estado` responde `FALTAN_DATOS_HISTORICOS` (faltan libros, ilegibles o cualquier otro fallo); el motivo vive solo en memoria y en el log técnico (conteos, libro, hoja, tipo de excepción; nunca datos personales). Se reintenta al reiniciar el backend. No se añadió un estado nuevo.

Con los libros reales: `LISTO` en ~5 s; 2.748 membresías, 1.410 socios, 1 modelo vigente, 1 intento `INICIAL`.

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

`python scripts/verificar_lista.py <carpeta>` (en memoria, sin BD) con scikit-learn 1.8.0: salida `0`. Cartera 59, ya renovaron 2, a priorizar 57 (57 socios), 1.564 ciclos de entrenamiento; top 25 con **probabilidades, orden y factores iguales** al notebook (§13.8). El empate en el corte (posición 25) se compara como conjunto.

R-005 (decisión c): el script no pasa por la API ni por `GenerarLista` con la validación de fecha; construye su entrada con `model_construct` para mantener su ventana de 180 días y marca todas las membresías con `socio_con_cedula=True` para seguir comparando con el notebook. Sigue saliendo con `0`. Consecuencia: la lista de la app puede diferir del top 25 del notebook si en él hay socios sin cédula (por diseño).

## Decisiones de R-004

| | Decisión |
|---|---|
| (a) | Referencia de factores = evaluables con vencimiento en 2025 (`PERIODO_REFERENCIA_FACTORES`), como el notebook. Sustituye al criterio inicial del plan ("todo el entrenamiento"), con el que los factores no coincidían. |
| (b) | Contrato: `GET /listas` nuevo; `fecha_generacion` pasa a `date`, se añaden `creada_en` y `monto_cobrado`; factores `[]` → "Sin factores de riesgo destacados". |
| (c) | Fallo de migración → `PENDIENTE` + `FALTAN_DATOS_HISTORICOS`; reintento al reiniciar el backend. |
| (d) | Umbrales por percentiles 20/30/50 (CU-05), no los fijos del notebook. |
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

## Pendientes

- `mypy` sobre `tests/` con errores de tipado estricto en dobles (no incluido en `mypy app`).
- El motivo de un fallo de migración solo está en memoria (se pierde al reiniciar).
- Concurrencia de dos `POST /listas` sin prueba.
- S23 y revisión de seguridad → día 7.
