# ADR-006 · Lista priorizada desde hoy (fecha de negocio de Ecuador), horizonte ≤ 31 y cédula en lugar de correo

- **Estado:** aceptada · 2026-09-29 · R-005 (petición del usuario tras el Día 3)
- **Origen:** revisión de la lista por el usuario; [03 §7 CU-04 y §15 CU-12](../03-casos-de-uso.md)
- **Se aparta de:** el contrato de listas de R-004 ([API_CONTRACT](../docs/API_CONTRACT.md): `correo` en `PrediccionDTO`, `horizonte_dias` 1..365, fecha libre) y del criterio de CU-04 de generar la lista al 31-08-2026 desde la aplicación

## Contexto

La lista de R-004 permitía fechas pasadas y horizontes de hasta 365 días, mostraba el correo y a socios sin cédula, y usaba términos técnicos (score, top K, horizonte). El personal del gimnasio necesita una lista operativa: desde hoy, a un mes como máximo, identificando al socio por su cédula. El backend corre en UTC; el PC del gimnasio está en Ecuador (UTC−5).

## Decisión

1. "Hoy" = fecha de negocio de Ecuador, `hoy_en_negocio(clock.now())` (UTC−5 fijo, sin horario de verano) en `domain/common/fechas.py`. Es la fecha por defecto de `POST /listas`; una fecha anterior → `422 domain_rule_violated` "La fecha de la lista debe ser hoy o posterior." (el `409` de sistema no listo tiene precedencia). En el navegador se usa la fecha local.
2. `horizonte_dias` de entrada 1..31 (`400 validation_error` fuera de rango). Los DTO de respuesta admiten 1..365 para leer listas antiguas.
3. `PrediccionDTO`, `ItemLista` y el Excel sustituyen `correo` por `cedula` (texto con cero inicial, neutralizado en el Excel). El correo no sale por la API ni por el Excel; sigue en la base.
4. Los socios sin cédula se excluyen de la cartera antes de predecir y del top K; siguen en la base, en el entrenamiento y en el historial de variables.
5. Las listas guardadas no se modifican (RN-04.5): pueden mostrar socios sin cédula ("—") y horizontes > 31.
6. `scripts/verificar_lista.py` conserva su ventana (vía `model_construct`) y trata a todos como "con cédula" para seguir conciliando con el notebook.

## Alternativas descartadas

- **"Hoy" en UTC:** entre las 19:00 y las 24:00 de Ecuador el backend consideraría "mañana" y rechazaría la fecha que el navegador propone.
- **Fecha pasada como `400`:** depende del reloj; es regla de negocio, no validación de entrada.
- **Reescribir las listas antiguas** para quitar el correo o a los sin cédula: rompe la inmutabilidad de RN-04.5.
- **Quitar el score y los aportes también del Excel:** el usuario solo pidió simplificar la pantalla.

## Consecuencias

- Cambio de contrato incompatible para clientes que leían `correo` (solo el frontend propio, actualizado).
- La cédula (dato personal) viaja por la API y el Excel; mitigado por el acceso por IP (CU-00), sin logs ni nombre de archivo con datos personales. Se revisa en la revisión de seguridad del día 7.
- La conciliación con el notebook al 31-08-2026 ya no se puede hacer desde la aplicación, solo con el script; la lista de la app puede diferir del top 25 del notebook si en él hay socios sin cédula.
