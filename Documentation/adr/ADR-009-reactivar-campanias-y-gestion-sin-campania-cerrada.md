# ADR-009 · Las campañas se pueden volver a activar y la gestión sin campaña nace cerrada

- **Estado:** aceptada · 2026-09-30 · R-010 (arreglos tras el día 5)
- **Origen:** pedido del usuario tras R-009 · [03 §9, §11, §13](../03-casos-de-uso.md) (CU-06, CU-08, CU-10)
- **Se aparta de:** [ADR-008](ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md) punto 4 ("no se reactivan"), la decisión (e) de R-009, y el contrato de R-009 (`fecha_seguimiento` obligatoria; toda gestión nace `PENDIENTE`). El resto de ADR-008 sigue vigente.

## Contexto

Tras R-009 una campaña inactivada por error no se podía recuperar: había que crear otra igual. Y elegir "No asignar campaña" dejaba una gestión `PENDIENTE` con fecha de seguimiento y un formulario de resultado en el que casi todo era "No aplica": trabajo sin sentido para el personal y un seguimiento que aparecería en las alertas del día 6 sin nada que revisar.

## Decisión

1. **Activar campañas.** `POST /api/v1/campanias/{id}/activar`: `200` con `activa: true`; idempotente (ya activa → `200` sin cambios); `404` si no existe o está borrada; `400` con id inválido. No cambia `es_ejemplo` ni otros datos. La campaña vuelve a sugerirse y a poder asignarse. Las gestiones ya creadas no cambian (nombre congelado, ADR-008). En la pantalla, botón "Activar" en las filas inactivas, **sin confirmación** (no quita nada y se revierte con "Inactivar").
2. **Gestión sin campaña = cerrada al crearla.** `POST /gestiones` con `campania_id: null` guarda en una transacción `estado = CERRADA`, `cerrada_en` = instante de creación, `fecha_seguimiento` = hoy, `responsable` y los seis campos de resultado en `NULL`. `fecha_seguimiento` pasa a opcional en el contrato: obligatoria solo con campaña (`400` si falta); sin campaña, fecha y responsable enviados se ignoran y el plazo de seguimiento terminado no bloquea. `PUT /gestiones/{id}/resultado` sobre ella → `409` (regla de gestión cerrada, ya existente).
3. **Sin migración.** El esquema queda en `0008`. "Sin campaña" se reconoce por `campania_id IS NULL`.
4. **La regla de la fecha de contacto no cambia** (entre el día en que se creó la gestión y hoy); solo se explica en la ayuda y en la guía 06.

## Alternativas descartadas

- **Seguir sin reactivar (crear una campaña nueva):** duplica campañas y separa sus cifras en el dashboard.
- **Activar mediante `PUT /campanias/{id}` con `activa`:** mezcla editar con cambiar el estado; `PUT` sigue rechazando `activa`.
- **Guardar `NO_APLICA` en los campos de resultado:** el `CHECK` de `renovo_declarado` solo admite `SI/NO/PENDIENTE`; exigiría una migración. Nulo expresa mejor "no hubo resultado que registrar".
- **Hacer `fecha_seguimiento` nula en la base:** exigiría migración; se guarda el día de creación y no se muestra.
- **No crear gestión cuando no hay campaña:** se perdería el registro de que el socio ya fue revisado y la fila volvería a ofrecer "Gestionar".
- **Migrar las gestiones pendientes sin campaña anteriores:** solo pueden existir en el stack E2E (el principal tiene 0 gestiones); se conserva la rama "sin campaña" de la validación del resultado para ellas.

## Consecuencias

- Una gestión `CERRADA` ya no implica "renovó Sí o No": puede tener `renovo_declarado` nulo. **Alertas y dashboard del día 6** deben filtrar por `estado` y tratar `renovo_declarado` nulo como "sin resultado"; si no, inflarían cifras. Las alertas cuentan solo `PENDIENTE`, así que estas gestiones quedan fuera por construcción.
- En una gestión sin campaña, `fecha_seguimiento` no tiene significado; ninguna pantalla ni informe debe usarla.
- La lista y el Excel muestran "Cerrada" / "Sin campaña"; la fila solo ofrece "Ver gestión" y la ventana solo dice "No se le asignó campaña".
- Una gestión sin campaña no se puede reabrir ni completar después (editar una gestión cerrada sigue fuera de alcance).
- Detalle: [API_CONTRACT](../docs/API_CONTRACT.md), [09](../docs/backend/09-esquema-base-de-datos.md), [frontend/01](../docs/frontend/01-arquitectura.md), [06](../06-como-funciona-la-lista.md).
