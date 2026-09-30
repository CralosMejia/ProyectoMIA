# ADR-008 · Gestión por ciclo de membresía y nombre de la campaña congelado al asignar

- **Estado:** aceptada · 2026-09-30 · R-009 (día 5 del cronograma) · **modificada en parte por [ADR-009](ADR-009-reactivar-campanias-y-gestion-sin-campania-cerrada.md)** (R-010): las campañas sí se vuelven a activar (punto 4) y la gestión sin campaña nace cerrada
- **Origen:** [03 §9–§11, §13](../03-casos-de-uso.md) (CU-06, CU-07, CU-08, CU-10; RN-08.1, RN-08.2) · [04 §2 D-16..D-18](../04-pendientes-para-iniciar-desarrollo.md)
- **Se aparta de:** el contrato del día 1 (`PrediccionDTO` sin `gestion_id`, `prioridad` sin máximo), el esquema de R-002 (`gestiones_retencion` sin `campania_nombre`), el cronograma (`0003` para las campañas de ejemplo; fecha sugerida = vencimiento + 25) y el criterio de R-008 que excluía del Excel el estado de gestión y la campaña ([ADR-007](ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md))

## Contexto

RN-08.2 exige que la campaña de una gestión quede como estaba al asignarla, pero las campañas se pueden editar e inactivar. La misma membresía puede estar en varias listas y RN-08.1 permite una sola gestión por ciclo. La tabla de la Lista debía mostrar la gestión y abrirla, y el Excel debe seguir igual a la tabla.

## Decisión

1. **Nombre congelado.** Migración `0008`: `gestiones_retencion.campania_nombre` (instantánea del nombre al crear la gestión) con `CHECK ((campania_id IS NULL) = (campania_nombre IS NULL))`. `GestionDTO.campania_nombre` y `PrediccionDTO.campania_asignada` salen de esa columna.
2. **Gestión por ciclo.** La gestión pertenece a la membresía, no a la predicción: se ve en todas las listas que contienen ese ciclo. La segunda creación → `409`, también por carrera (el índice único parcial se traduce a `GestionDuplicadaError`); el cierre usa `SELECT … FOR UPDATE` (dos cierres → `200` y `409`).
3. **Contrato.** `PrediccionDTO` añade `gestion_id`; `prioridad` de campaña 1..999; `GestionDTO.fecha_asignacion` = instante de creación. `GET /alertas` y `GET /gestiones?filtro=` siguen en `501` hasta el día 6.
4. **Campañas.** 3 de ejemplo por migración de datos `0007` ("Ejemplo: …", sin duplicar); nombres repetidos permitidos; inactivar es idempotente; no se borran (R-009 tampoco permitía volver a activarlas: **revertido por ADR-009**); editar no cambia `es_ejemplo`.
5. **Fechas.** Rango de seguimiento `[hoy, vencimiento + 30]`; sugerida = `max(vencimiento + 25, hoy)`, calculada en el frontend con la misma regla que el dominio; "hoy" = fecha de negocio de Ecuador.
6. **Resultado.** Reglas de coherencia en el dominio (`422` por regla); Renovó Sí/No cierra la gestión y ya no se edita (`409`).
7. **Excel.** Añade las columnas "Gestión" y "Campaña" para seguir igual a la tabla.

## Alternativas descartadas

- **Leer el nombre actual de la campaña con un JOIN:** un renombrado cambiaría gestiones ya hechas (incumple RN-08.2).
- **Prohibir editar campañas en uso:** impide corregir un nombre y no lo pide CU-06.
- **Gestión por predicción:** permitiría dos gestiones del mismo ciclo desde dos listas.
- **Comprobar duplicados solo en la aplicación:** no resiste dos peticiones simultáneas.
- **Dejar el Excel sin las columnas nuevas:** dejaría de ser igual a la pantalla.

## Consecuencias

- Una gestión muestra el nombre antiguo aunque la campaña se renombre; es lo esperado.
- `gestion_id` viaja en cada ítem de la lista: clientes y dobles de prueba lo incluyen.
- Las reglas de fecha y coherencia están duplicadas en frontend y backend; se mantienen con los mismos casos de prueba y el servidor decide.
- `0007` usa `now()` de la base (no el reloj inyectable), como toda migración de datos de Alembic.
- [03 §15 CU-12](../03-casos-de-uso.md) decía que el Excel no lleva gestión ni campaña; se ajustó en R-010 (DOC-1).
- Detalle: [API_CONTRACT](../docs/API_CONTRACT.md), [09](../docs/backend/09-esquema-base-de-datos.md), [12](../docs/backend/12-modelo-y-listas.md), [frontend/01](../docs/frontend/01-arquitectura.md).
