# ADR-011 · Reglas concretas del reentrenamiento: ciclos nuevos, PR-AUC, fechas perdidas y bloqueo

- **Estado:** aceptada · 2026-09-30 · R-011 (día 6)
- **Origen:** [03 §5](../03-casos-de-uso.md) (CU-02) · decisiones (d)–(g) de R-011
- **Detalla:** [ADR-003](ADR-003-reentrenamiento-y-versionado.md), que sigue vigente.

## Contexto

ADR-003 fijó el planificador dentro del backend, los criterios y el versionado, pero no qué es un "ciclo nuevo", cómo se calcula la PR-AUC sin `float` en el dominio, qué pasa si se pierden varias fechas seguidas ni cómo se evita que el planificador y el comando reentrenen a la vez.

## Decisión

1. **Ciclo nuevo evaluable:** evaluable al corte de hoy y con `fecha_vencimiento + 30 > fecha_corte` del modelo vigente (`metadata_tecnica["fecha_corte"]`). El `>` estricto evita contar dos veces el ciclo del borde. El dashboard usa la misma función.
2. **Criterios** configurables por `.env` (`REENTRENAR_*`; 150 / 0,60 / 20 / 3). La cobertura se mide sobre las membresías registradas (`created_at`) después del entrenamiento vigente; sin ninguna, el criterio no se cumple.
3. **PR-AUC = *average precision*** (igual a `sklearn.metrics.average_precision_score`), calculada en el dominio con `Decimal`. Candidato entrenado sin los evaluables de los 3 meses de vencimiento más recientes con resultado; `candidato < vigente` → `NO_SUPERA_VIGENTE`. Si no es peor, modelo final con todos los evaluables, versión = vigente + 1.
4. **Fechas:** programado → próxima = hoy + 6 meses tras cualquier resultado. Fecha pasada → **un `OMITIDO` por cada fecha perdida** y próxima = última fecha perdida + 6 meses (≥ hoy). Manual → solo mueve la fecha si `ENTRENADO`.
5. **Transacciones:** modelo, intento y próxima fecha en una sola; `FALLIDO` en una aparte, con el vigente intacto.
6. **Bloqueo consultivo propio** (clave distinta de la de CU-03): un segundo reentrenamiento no hace nada; el comando sale con código 2 y "Ya hay un reentrenamiento en curso.".
7. **Planificador:** hilo daemon, al arrancar y cada hora, solo al cambiar el día de negocio; `REENTRENAMIENTO_AUTOMATICO=false` lo desactiva. **Comando:** `python -m app.cli reentrenar`, salidas 0/1/2.

## Alternativas descartadas

- **Ciclo nuevo por fecha de carga de la membresía:** contaría ciclos cuya ventana T+30 ya estaba dentro del entrenamiento anterior.
- **scikit-learn para la métrica:** `domain`/`application` no importan ML (ADR-002), y la comparación exige exactitud.
- **Un solo `OMITIDO` aunque se pierdan varias fechas:** perdería trazabilidad de cada fecha programada.
- **Planificador externo (cron/Programador de Windows):** ya descartado en ADR-003.

## Consecuencias

- Con el PC apagado mucho tiempo puede haber varios `OMITIDO` de golpe al arrancar; el modelo solo se actualiza con el comando manual o en una fecha en que el PC esté encendido.
- La métrica coincide con la del notebook y se prueba contra valores conocidos.
- Detalle: [12 §Reentrenamiento](../docs/backend/12-modelo-y-listas.md#reentrenamiento-cu-02-r-011), [Backend/README §4](../../Backend/README.md).
