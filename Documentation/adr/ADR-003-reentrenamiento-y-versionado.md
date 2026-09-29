# ADR-003 · Reentrenamiento programado y versionado de modelos en la base de datos

- **Estado:** aceptada · 2026-09-28 · R-002 (D1-OP-04)
- **Origen:** D-05, D-06, D-07 y D-10 de [04 §2](../04-pendientes-para-iniciar-desarrollo.md); CU-02, RT-05 a RT-07 de [03](../03-casos-de-uso.md)

## Contexto

El modelo debe actualizarse a medida que llegan datos por plantilla (CU-01), sin empeorar el vigente, y cada lista y gestión debe conservar la versión y los umbrales con que se generó (RT-07). El sistema corre en un solo PC que puede estar apagado en la fecha programada, y la base es la única fuente de verdad (04 §3).

## Decisión

- **Planificador dentro del backend**: la fecha próxima vive en `estado_sistema.proxima_fecha_reentrenamiento`, cada 6 meses, calculada con el puerto `Clock`.
- **Sin recuperar fechas perdidas** (D-05): si al arrancar la fecha ya pasó, se registra un intento `OMITIDO` y la próxima fecha pasa a 6 meses después.
- **Comando manual** (D-06) con el mismo caso de uso; su nombre final se documenta en `Backend/README.md`.
- **Criterios** (D-07): ≥150 ciclos nuevos evaluables, ≥60 % de membresías nuevas con vencimiento, ≥20 casos por clase, y PR-AUC del candidato **no peor** que el vigente en los últimos 3 meses con resultado conocido. Los umbrales de riesgo se recalculan en cada entrenamiento (D-10).
- **Versionado en la base**: tabla `modelos` (versión, `vigente`, periodo, prevalencia, umbrales, `artefacto` serializado, `metadata_tecnica`); un solo modelo vigente. Cada ejecución deja una fila en `intentos_reentrenamiento` (`PROGRAMADO`/`MANUAL`/`INICIAL`; `ENTRENADO`/`CRITERIOS_NO_CUMPLIDOS`/`NO_SUPERA_VIGENTE`/`OMITIDO`/`FALLIDO`).
- El cambio de vigente y el registro del intento ocurren en la misma transacción.

## Alternativas descartadas

- **Programador del sistema operativo (Programador de tareas de Windows, cron):** depende del lugar de instalación, que no debe condicionar el desarrollo (04 §3).
- **Recuperar la fecha perdida al arrancar:** diferido a una versión posterior ([03 §20](../03-casos-de-uso.md)).
- **Artefactos en archivos o volumen:** exigiría un respaldo aparte y podría desalinearse de la fila del modelo.
- **Registro de modelos externo (MLflow u otro):** desproporcionado para un solo PC.

## Consecuencias

- Si el PC suele estar apagado, el modelo puede quedar desactualizado; el comando manual es el respaldo.
- El artefacto ocupa espacio en la base y entra en el `pg_dump`; se deserializa solo desde la propia base (nunca desde entradas del usuario).
- La lógica de fechas se prueba con reloj simulado.
- Las tablas `modelos` e `intentos_reentrenamiento` no llevan `deleted_at` ([DEVELOPMENT_GUIDELINES](../DEVELOPMENT_GUIDELINES.md) §Excepciones).
