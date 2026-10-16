# Guía de desarrollo — alcance de la versión actual

**Versión:** entrega de una semana (28-09-2026) · **Fuente de verdad:** [03 · Casos de uso](03-casos-de-uso.md) §1.1, §19 y §20 · decisiones D-01 a D-18 de [04 §2](04-pendientes-para-iniciar-desarrollo.md).
Si esta guía y `03` discrepan, manda `03`; esta guía se corrige.

---

## Alcance

Entran todos los casos de uso, CU-00 a CU-12, varios en versión simplificada ([03 §1.1](03-casos-de-uso.md)):

| CU | Versión de la entrega |
|---|---|
| CU-00 Validar acceso por IP | Simplificado: lista de IP o rangos en variables de entorno (por defecto, solo el propio PC); sin proxy intermedio. |
| CU-01 Cargar nuevos datos | Simplificado: carga todo o nada con la plantilla oficial (máx. 500 filas). |
| CU-02 Reentrenar el modelo | Simplificado: fecha programada cada 6 meses sin recuperar fechas perdidas, comando manual y comparación contra el vigente. |
| CU-03 Migrar el histórico inicial | Completo: automático en el primer arranque con la base vacía, atómico con el modelo v1 ([ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md)). |
| CU-04 Generar priorización | Completo. |
| CU-05 Nivel de riesgo | Completo, cortes fijos del notebook 0,70 / 0,50 (desde M01, R-015; antes, percentiles 20/30/50). |
| CU-06 Parametrizar campañas | Simplificado: reglas solo por nivel de riesgo y tipo de plan. |
| CU-07 Recomendar campañas | Simplificado: filtra por nivel y plan, ordena por prioridad. |
| CU-08 / CU-10 Gestión | Simplificado: un solo formulario; una gestión por ciclo. |
| CU-09 Alertas | Simplificado: vencidos, hoy y próximos 7 días. |
| CU-11 Dashboard | Simplificado: embudo, tabla por campaña, estado del modelo; solo filtro por mes. |
| CU-12 Descargar Excel | Completo. |

### Decisiones de alcance ([03 §19](03-casos-de-uso.md))

1. Sin login; el acceso se restringe por IP (CU-00, RT-12).
2. Alertas solo dentro de la aplicación.
3. Campañas parametrizables por Mtabolic, sugeridas con reglas, no con un segundo modelo.
4. El modelo no toma decisiones comerciales: el personal elige campaña y contacta.
5. Las cifras de campañas son descriptivas; no se atribuye causalidad.
6. La lista se genera solo a pedido del usuario.
7. Se conserva la descarga en Excel.
8. El histórico se migra una sola vez, automáticamente en el primer arranque con la base vacía y de forma atómica con el modelo v1; después, carga solo por plantilla.
9. Reentrenamiento cada 6 meses sin recuperar fechas perdidas, más comando manual; solo si hay datos suficientes y el modelo nuevo no es peor que el vigente ([ADR-003](adr/ADR-003-reentrenamiento-y-versionado.md)).
10. Entrega en una semana ([05 · Cronograma](05-cronograma-semana.md)).
11. Un solo PC con Docker Compose; el sistema se usa desde ese equipo.
12. La lógica del notebook se adapta tal cual (estados del registro y asistencias no se usan; variables del modelo = las del notebook).

---

## Fuera de alcance

No se implementa nada de esta sección. Si un requerimiento lo pide, el planner lo marca fuera de alcance y lo escala al usuario.

### Diferido a una versión posterior

- Cargar solo las filas válidas de un archivo con errores (CU-01).
- Recuperar una fecha de reentrenamiento perdida porque el PC estaba apagado (CU-02).
- Cambiar la lógica del notebook: revisar `inicio_aproximado` y `mes_vencimiento`, usar asistencias o los estados del registro (`BAJA`, `CONGELAMIENTO`, `REINGRESO`) en la etiqueta y la lista. **Excepción ya ejecutada:** la mejora M01 del tutor (R-015, pedida explícitamente por el usuario tras la entrega) cambió las variables (corte T−30, medianas solo de entrenamiento), la partición (márgenes de 30 días) y retiró `forma_pago` e `inicio_aproximado` del modelo ([mejoras/M01](mejoras/M01-modelo-sin-fuga-temporal.md), [ADR-014](adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md)). Lo demás de este punto sigue diferido.
- Días de congelamiento como dato propio.
- Reglas de campaña por antigüedad, ciclos previos y vigencia (CU-06).
- Editar una gestión cerrada o más de una gestión por ciclo (CU-08, CU-10).
- Plazo configurable de "próximos N días" (CU-09).
- Resultados por nivel de riesgo y filtros por nivel y campaña en el dashboard (CU-11).
- Pantalla de revisión manual de enlaces entre socios históricos y de plantilla (CU-01).
- Confianza en cabeceras de proxy para la restricción por IP (CU-00).

### Fuera del proyecto

- Autenticación por usuario, roles o permisos.
- Integración con WhatsApp, SMS o correo.
- Integración con el sistema biométrico.
- Facturación, cobros o aplicación automática de descuentos.
- Aprendizaje automático para elegir campañas, pruebas A/B o inferencia causal.
- Notificaciones push o aplicación móvil.
- Generador de reportes o BI avanzado.
- Reentrenamiento en línea por cada registro o ajuste automático de hiperparámetros.

---

## Excepciones documentadas a las reglas generales

| Regla general | Excepción en este proyecto | Origen |
|---|---|---|
| Propietario del dato desde el token; `user_id NOT NULL` en toda tabla (`.claude/rules/database.md`) | **No aplica.** No hay login ni usuarios; el acceso se controla por IP (CU-00). Las pruebas de aislamiento entre usuarios no aplican. | RT-12 · [04 §5](04-pendientes-para-iniciar-desarrollo.md) (ítem 2) |
| Borrado lógico con `deleted_at` en lo crítico | Llevan `deleted_at`: `socios`, `cargas`, `membresias`, `campanias`, `gestiones_retencion`. **No** lo llevan: `modelos`, `listas_priorizadas`, `predicciones` (instantáneas inmutables, RT-07), `intentos_reentrenamiento` (auditoría de solo inserción) y `estado_sistema` (fila única de control). Ninguna de ellas se borra físicamente. | R-002 (plan) · RT-07 |
| Nada crítico se borra físicamente | **Excepción puntual y única, no cambia la regla:** el 2026-09-30 01:50:06 UTC se borraron físicamente todas las filas de `predicciones` (117) y `listas_priorizadas` (3) de la base de desarrollo del stack de Docker, por ser listas de prueba que dificultaban ver errores (decisión explícita del usuario). Una transacción con precondición `gestiones_retencion = 0`, sin `CASCADE`, `TRUNCATE` ni reinicio de secuencias; el resto de tablas quedó intacto. El código sigue sin exponer borrado de listas. Detalle y SQL: [09 §Convenciones](docs/backend/09-esquema-base-de-datos.md). | R-006 (T4) |
| Nada crítico se borra físicamente | **Reinicio manual de la base principal (no es una función de la aplicación):** los scripts `scripts/reiniciar-base-historica.ps1` / `.sh` hacen `down -v` del stack principal (`-p proyectofinal`) y lo recrean solo con el histórico, borrando cargas por plantilla, socios que estas agregaron, listas, predicciones y todo lo demás del volumen. Solo por decisión explícita del usuario, con confirmación `BORRAR`; nunca toca `mtabolic-e2e`. El código de la app sigue sin exponer borrados. En R-008 no se ejecutó (la base tenía listas del usuario). **Ejecutado el 30-09-2026** en el stack principal con `scripts/reiniciar-base-historica.sh --si`, autorizado por el usuario; resultado: socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0, sistema `LISTO`. → [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md) | R-008 (T5) · R-009 (ejecución) |
| Valores exactos en decimal, nunca coma flotante | Montos y probabilidades se guardan como `Decimal` (`NUMERIC`). La conversión `Decimal → float` (y `float → Decimal` del score) está permitida **solo en el borde del modelo**: el adaptador de infraestructura que implementa `PredictorModel` ([ADR-002](adr/ADR-002-ml-en-infraestructura.md)). Dominio, aplicación, persistencia y API trabajan siempre con `Decimal`. | [04 §5](04-pendientes-para-iniciar-desarrollo.md) (ítem 7) |
| La aplicación nunca ejecuta migraciones al arrancar | Se mantiene para el **esquema** (solo el servicio `migrate`). La única migración de **datos** al arrancar es CU-03. | RT-14 · [ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md) |
