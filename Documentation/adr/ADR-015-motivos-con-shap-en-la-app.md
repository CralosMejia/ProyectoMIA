# ADR-015 · Motivos principales de la lista calculados con SHAP en la app

- **Estado:** aceptada · 2026-10-16 · R-017 (mejora M03)
- **Origen:** [mejoras/M03](../mejoras/M03-shap-prueba-y-motivos-en-la-app.md) · definición (e) de R-017 · M02 §11 punto 7
- **Sustituye:** el método de factores por sustitución de §13.3 ([ADR-005](ADR-005-fidelidad-al-notebook-del-modelo-v1.md) punto 2 y [ADR-014](ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) punto 6 dejan de afectar a los motivos) · **complementa:** [ADR-002](ADR-002-ml-en-infraestructura.md), [ADR-007](ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md)

## Contexto

Los "Motivos principales" se calculaban sustituyendo cada variable por la de un socio "típico" (medianas y modas de un periodo de referencia) y midiendo cuánto bajaba la probabilidad. Los aportes no sumaban a nada, contaban varias veces las interacciones y no coincidían con el análisis SHAP de la tesis (M02): en septiembre, los 25 socios priorizados tenían el mismo primer motivo ("Días desde la membresía anterior: sin dato"). El notebook pasó a calcular los motivos con SHAP (§13.3/§13.8) y la app debía dar la misma lista.

## Decisión

1. El adaptador `RandomForestPredictor` (`app/infrastructure/ml/random_forest.py`) calcula los motivos con `shap.TreeExplainer` sobre la matriz preprocesada del `pipeline` del artefacto, clase "no renovó", con las columnas *one-hot* sumadas a su variable (`aportes_shap`).
2. Regla, igual que el notebook: candidatas de `NOMBRE_VARIABLE` (nunca `mes_vencimiento`), aporte > 0,005 sin redondear, de mayor a menor (empate: orden de `NOMBRE_VARIABLE`), hasta 3, formato `"Plan: TRIMESTRAL (+0,09)"`.
3. `shap==0.54.1` fijado en `pyproject.toml`; solo en infraestructura (`import-linter` lo prohíbe en `domain` y `application`).
4. **Sin reentrenar ni adoptar:** el método lo decide el adaptador, no el artefacto; v1 y v2 explican con SHAP. Los modelos nuevos registran `metodo_factores: "shap"` en `metadata_tecnica`. La `referencia` se sigue guardando por compatibilidad, sin uso.
5. Contrato de la API, esquema, probabilidades, orden y niveles sin cambios. Las listas guardadas conservan sus motivos. Pantalla y Excel siguen sin mostrar el número (ADR-007).
6. `verificar_lista.py` compara los motivos SHAP con el notebook (criterio bloqueante: 0 diferencias).

## Alternativas descartadas

- **Mantener la sustitución en la app y SHAP solo en el notebook:** la lista de la app dejaría de ser igual a la del notebook y a lo que se explica en la tesis.
- **Reentrenar para guardar el explicador en el artefacto:** innecesario (el `pipeline` basta) y crearía una versión nueva del modelo sin cambio de predicciones.
- **Recalcular los motivos de las listas guardadas:** rompería la inmutabilidad de las predicciones (RT-07).
- **Mostrar el aporte en pantalla:** cambio aparte; ADR-007 sigue vigente.

## Consecuencias

- Dependencia nueva (shap 0.54.1 con slicer y tqdm; sin numba ni llvmlite). Transitivas sin *lockfile* (diferido, S1 de R-017, como S10).
- Coste: ~0,02 s para 57 filas y ~0,4 s para 1.600.
- En el historial conviven listas con motivos por sustitución (anteriores al 2026-10-16) y por SHAP.
- Puesto en uso en el stack principal el 2026-10-16 con respaldo previo y conteos idénticos; vuelta atrás = restaurar la imagen anterior (no hay datos que revertir).
- Detalle: [12 §Modelo](../docs/backend/12-modelo-y-listas.md#modelo-adaptador-randomforestpredictor).
