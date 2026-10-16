# Mejoras posteriores a la entrega

Cambios al proyecto hechos después del cierre del Día 7 ([07-cierre.md](../07-cierre.md)) a partir de las recomendaciones del tutor.

Cada mejora tiene su propio documento en esta carpeta, con el nombre `M##-<tema-corto>.md`, y explica:

- **Recomendación:** qué pidió el tutor y por qué.
- **Qué se cambió:** funcionalidad, pantallas y datos afectados.
- **Cómo se verificó:** pruebas y resultados.
- **Requerimiento:** el `R-###` del harness y los commits.

## Dónde están las imágenes

Las figuras de cada mejora están en `Documentation/claude/mejoras/M##/`, separadas en `antes/` (línea base) y `despues/` (resultado de la mejora). Cada documento `M##` cita sus figuras con esa ruta para poder llevarlas a la tesis. Las tablas y demás salidas del notebook que no son imágenes están en `salidas/m##/` (y las del MVP en `salidas/mvp/`), en la raíz del proyecto. Esa carpeta está fuera de git porque contiene datos personales. `Notebookes/` contiene solo los notebooks.

## Índice

| Mejora | Tema | Requerimiento | Estado |
|---|---|---|---|
| [M01](M01-modelo-sin-fuga-temporal.md) | Modelo sin fuga temporal: variables con corte T−30, medianas solo de entrenamiento, márgenes de 30 días, bootstrap por socio, variante sin `forma_pago`/`inicio_aproximado`, cortes de riesgo 0,70/0,50 y adopción como v2 | R-015 | Hecha (2026-10-15) |
| [M02](M02-explicabilidad-shap.md) | Explicabilidad SHAP del Random Forest corregido (solo notebook, §12.12): valor base, aditividad, VP/FP/FN/VN con top 25 por mes y umbral 0,32, importancia global y por mes, 8 *waterfalls* sin datos personales | R-016 | Hecha (2026-10-16) |
| [M03](M03-shap-prueba-y-motivos-en-la-app.md) | SHAP en prueba (277), lista de septiembre y entrenamiento (informativo); 10 de 11 conclusiones de M02 se mantienen; "Motivos principales" con SHAP en el notebook y la app (shap 0.54.1, sin reentrenar), paridad con `verificar_lista` | R-017 | Hecha (2026-10-16) |
