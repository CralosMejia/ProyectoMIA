# ADR-002 · El modelo de ML vive en infraestructura, detrás del puerto `PredictorModel`

- **Estado:** aceptada · 2026-09-28 · R-002 (D1-OP-04)
- **Origen:** confirmada por el usuario en [04 §5](../04-pendientes-para-iniciar-desarrollo.md) (ítem 4)

## Contexto

La lógica de `Notebookes/MVP.ipynb` (limpieza, reconstrucción de ciclos, variables, Random Forest, score y factores principales) se adapta tal cual ([03 §18](../03-casos-de-uso.md)). Depende de pandas y scikit-learn. `.claude/rules/backend.md` exige capas con dependencias hacia dentro, verificadas con import-linter: `domain` y `application` no pueden depender de librerías técnicas y se prueban sin BD ni frameworks.

## Decisión

- `application` declara un puerto `PredictorModel` (`Protocol`) con las operaciones que necesitan los casos de uso: entrenar, puntuar una cartera y explicar factores principales. Sus entradas y salidas son DTOs con tipos del dominio (`Decimal`, fechas, enums), nunca `DataFrame` ni arrays.
- La implementación vive en `app/infrastructure` (adaptador con pandas + scikit-learn) y se enlaza en el composition root.
- Las reglas temporales puras (ciclo, T−30, T+30, elegibilidad, etiqueta) pueden quedar en `domain` como Python puro, sin pandas.
- La conversión `Decimal ↔ float` ocurre **solo** dentro del adaptador ([DEVELOPMENT_GUIDELINES](../DEVELOPMENT_GUIDELINES.md) §Excepciones).
- El artefacto entrenado se serializa en el adaptador y se guarda en la base ([ADR-003](ADR-003-reentrenamiento-y-versionado.md)).

## Alternativas descartadas

- **ML en `domain`/`application`:** rompe la regla de capas y obliga a cargar pandas/scikit-learn en las pruebas unitarias.
- **Servicio de ML separado (otro contenedor o API):** más infraestructura y latencia sin beneficio en un solo PC y una semana de entrega.
- **Reescribir el modelo sin pandas:** contradice la decisión de adaptar el notebook tal cual (D-11 a D-13).

## Consecuencias

- import-linter debe prohibir `pandas`, `numpy` y `sklearn` en `domain` y `application`.
- Los casos de uso CU-02, CU-03 y CU-04 se prueban con un doble de `PredictorModel`; el adaptador se prueba aparte con datos sintéticos.
- Cambiar de algoritmo o librería afecta solo al adaptador y a la versión registrada en `metadata_tecnica`.
