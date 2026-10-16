# ADR-014 · Modelo M01: variante sin `forma_pago`/`inicio_aproximado`, cortes fijos de riesgo, corte de los datos y comando `adoptar-modelo`

- **Estado:** aceptada · 2026-10-15 · R-015 (mejora M01 del tutor)
- **Origen:** recomendaciones del tutor ([mejoras/M01](../mejoras/M01-modelo-sin-fuga-temporal.md)) · decisiones (a)–(g) de R-015 · decisión del usuario sobre los niveles
- **Sustituye en parte:** [ADR-005](ADR-005-fidelidad-al-notebook-del-modelo-v1.md) punto 3 (percentiles) y la decisión (d) de R-004 · **complementa:** [ADR-011](ADR-011-reglas-del-reentrenamiento.md), [ADR-003](ADR-003-reentrenamiento-y-versionado.md)

## Contexto

El tutor señaló posibles fugas de información en el notebook: variables que podían usar registros posteriores a la fecha de predicción (T−30), medianas de monto calculadas con todos los datos y una partición sin separación entre conjuntos. El notebook se corrigió (M01) y la app debía calcular igual, entrenar con el conjunto de variables elegido y poner en uso el modelo nuevo sin perder listas, predicciones ni gestiones hechas con v1. CU-02 no servía para adoptarlo: exige ≥ 150 ciclos nuevos, que no había.

## Decisión

1. **Variables:** historial de un ciclo = registros no excluidos del socio con `fecha_actividad` anterior a la del ciclo **y** ≤ T−30. Medianas de monto solo con los ciclos de entrenamiento (en la app: los evaluables con que se entrena). `construir_variables` sigue devolviendo las 10 columnas para que el artefacto v1 prediga; cada artefacto elige las suyas.
2. **Conjunto del modelo** (`CONJUNTO_MODELO`): la variante **sin `forma_pago` ni `inicio_aproximado`**. Regla fijada antes de ver los resultados: adoptar la variante si su PR-AUC de validación ≥ la del completo **o** si el IC 95 % bootstrap por socio de la diferencia contiene 0. Resultado: 0,7204 vs 0,7284, IC [−0,040; +0,027] → se adopta. Hiperparámetros sin cambio.
3. **Niveles de riesgo** (decisión del usuario): cortes fijos del notebook, ALTO ≥ 0,70, MEDIO ≥ 0,50, si no BAJO. `porcentajes_umbral` pasa a ser el reparto observado sobre los evaluables de los 3 meses recientes (informativo).
4. **Corte de los datos:** CU-02 y `adoptar-modelo` etiquetan los ciclos a `min(hoy, max(corte del vigente, día de la última carga por plantilla))`, no a "hoy", como el notebook (que etiqueta a la fecha de corte de los libros).
5. **Margen en CU-02:** el candidato se entrena sin la comparación ni los ciclos con `vencimiento + 30 ≥ primer vencimiento de la comparación`, y con sus propias medianas.
6. **`PERIODO_REFERENCIA_FACTORES`** = vencimientos < 2025-12-02 (el `X_train` nuevo del notebook).
7. **Comando `python -m app.cli adoptar-modelo`:** entrena una vez con todos los evaluables, guarda versión vigente + 1 vigente y un intento `MANUAL`/`ENTRENADO` ("Adopción del modelo M01") en **una** transacción; conserva la anterior; no mueve la fecha programada; salidas 0/1/2. No es idempotente: cada ejecución crea una versión.

## Alternativas descartadas

- **Mantener el conjunto completo:** su ventaja en validación (0,008) no se distingue del azar y no cumple el criterio de Brier de §11.3; la variante sí.
- **Mantener percentiles 20/30/50:** el nivel de un socio no coincidiría con el notebook; el usuario prefirió los cortes del notebook.
- **Adoptar por CU-02 relajando criterios:** cambiaría la regla de negocio de todos los reentrenamientos futuros.
- **Etiquetar a "hoy":** con datos que terminan antes, marca como "no renovó" a quien aún no se cargó.
- **Margen de 60 días** (criterio estricto): reduce más los conjuntos; queda como limitación.

## Consecuencias

- Puesto en uso en el stack principal el 2026-10-15 (respaldo previo): v2 vigente, 1.660 ciclos, umbrales 0,70/0,50, reparto observado ALTO 15 / MEDIO 52 / BAJO 33 %; v1 conservado. Vuelta atrás = restaurar el respaldo.
- Las listas hechas con v1 conservan sus niveles por percentiles; las nuevas usan v2 y los cortes fijos. En una lista puede haber muy pocos ALTO.
- Una instalación limpia (CU-03) entrena directamente el modelo M01 como v1.
- `verificar_lista.py` compara las 57 filas de la cartera de septiembre (probabilidad, nivel, factores, orden) con las salidas del notebook en `salidas/` y da 0 diferencias.
- Detalle: [12 §Modelo](../docs/backend/12-modelo-y-listas.md), [Backend/README §4](../../Backend/README.md).
