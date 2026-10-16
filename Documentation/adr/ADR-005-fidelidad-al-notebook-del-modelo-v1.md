# ADR-005 · Fidelidad del modelo v1 al notebook: scikit-learn 1.8.0 y referencia de factores del periodo 2025

- **Estado:** aceptada · 2026-09-29 · R-004 (D3-BE-02, D3-BE-05)
- **Origen:** criterio de D3-BE-05 en [05 §3](../05-cronograma-semana.md): la lista al 31-08-2026 debe coincidir con la del notebook
- **Sustituida en parte por [ADR-014](ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) (R-015, M01):** el punto 3 (percentiles) deja de aplicar —los niveles usan los cortes fijos 0,70/0,50— y `PERIODO_REFERENCIA_FACTORES` del punto 2 pasa a vencimientos ≤ 01-12-2025 (el nuevo `X_train`). El punto 1 sigue vigente.
- **Se aparta de:** la decisión de R-002 en `ACTION_PLAN.md` (versiones de datos/ML "estables, no las del notebook") para scikit-learn, y de la decisión (a) inicial del plan de R-004 (referencia de factores = todo el entrenamiento)

## Contexto

El Random Forest (`random_state=42`) depende de la versión de scikit-learn y del orden de las filas. Con scikit-learn 1.9.1 la conciliación (`scripts/verificar_lista.py`) daba 24/25 del top iguales y probabilidades desplazadas entre 0,001 y 0,016. Además, los factores de §13.3 se calculan contra las medianas y modas de `X_train`; con la referencia "todo el entrenamiento" los factores no coincidían.

## Decisión

1. scikit-learn se fija a **1.8.0** (la del notebook) en `Backend/pyproject.toml`. `metadata_tecnica` del modelo guarda las versiones usadas.
2. La referencia de los factores son los ciclos evaluables con vencimiento en `PERIODO_REFERENCIA_FACTORES` = [2025-01-01, 2026-01-01), constante parametrizable en `domain/modelo/variables.py`. El modelo se sigue entrenando con **todos** los evaluables.
3. Se mantiene la diferencia por diseño en los niveles: percentiles 20/30/50 (CU-05), no los umbrales fijos 0,70/0,50 del notebook.

Resultado: salida `0`; 25/25 probabilidades, orden y factores iguales (empate en la posición 25 comparado como conjunto).

## Alternativas descartadas

- **scikit-learn 1.9.1 y documentar la diferencia** (permitido por 05 §5): la lista no sería idéntica sin necesidad.
- **Referencia = todo el entrenamiento** (criterio general sin fecha fija): factores distintos al notebook.
- **Umbrales fijos del notebook:** contradicen CU-05.

## Consecuencias

- Actualizar scikit-learn exige repetir `verificar_lista.py` y, si cambia el resultado, una nueva decisión. Cambiar la versión puede además impedir o alterar la carga de artefactos joblib ya guardados en `modelos`.
- Cuando CU-02 reentrene (día 6), el periodo de referencia de los factores debe revisarse: hoy es fijo en 2025.
- El nivel de riesgo de un socio puede diferir del notebook aunque el score coincida.
