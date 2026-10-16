# 07 · Cierre de la entrega

Estado al cierre del día 7 (R-013, 2026-10-01). Resume qué se entregó, en qué se aparta del notebook, qué queda diferido con sus riesgos y cómo se opera. El detalle vive en los documentos enlazados; aquí no se repite.

> **Mejora posterior a la entrega (2026-10-15, R-015):** a recomendación del tutor, el notebook y la app eliminaron la posible fuga temporal (variables con corte T−30, medianas solo de entrenamiento, márgenes de 30 días), el modelo usa la variante sin `forma_pago` ni `inicio_aproximado`, los niveles usan los cortes 0,70/0,50 y el stack principal tiene el modelo v2 vigente (v1 conservado). Detalle: [mejoras/M01](mejoras/M01-modelo-sin-fuga-temporal.md), [ADR-014](adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md).

## 1. Qué se entregó

Aplicación web local (FastAPI + PostgreSQL 16 + React) en Docker, accesible solo desde el propio PC, que cubre los casos de uso de [03](03-casos-de-uso.md) dentro del alcance de [DEVELOPMENT_GUIDELINES](DEVELOPMENT_GUIDELINES.md):

| Caso de uso | Qué hace | Referencia |
|---|---|---|
| CU-00 | Acceso por IP (backend detrás de nginx) y protección `Host`/`Origin` | [ADR-010](adr/ADR-010-acceso-por-ip-detras-de-nginx.md), [ADR-013](adr/ADR-013-proteccion-host-y-origin.md) |
| CU-03 | Migración única del histórico al arrancar y modelo v1 | [ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md), [11-historico](docs/backend/11-historico.md) |
| CU-01 | Carga mensual por plantilla con vista previa | [13-cargas](docs/backend/13-cargas.md) |
| CU-04, CU-05, CU-12 | Lista priorizada desde hoy, niveles de riesgo, Excel | [12-modelo-y-listas](docs/backend/12-modelo-y-listas.md), [06](06-como-funciona-la-lista.md) |
| CU-06..CU-10 | Campañas, sugerencias, gestión, alertas de seguimiento y resultado | [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md), [ADR-009](adr/ADR-009-reactivar-campanias-y-gestion-sin-campania-cerrada.md) |
| CU-11 | Dashboard con embudo, resultados por campaña y estado del modelo; impresión del navegador | [03 §14](03-casos-de-uso.md) |
| CU-02 | Reentrenamiento programado (cada 6 meses) y manual | [ADR-011](adr/ADR-011-reglas-del-reentrenamiento.md) |

Día 7: respaldo y restauración con scripts, rol de base de datos sin superusuario (S23, [ADR-012](adr/ADR-012-rol-de-aplicacion-sin-superusuario.md)), instalación limpia equivalente, revisión de seguridad única de R-001..R-012 (0 critical/high abiertos), E2E del escenario principal, ensayo de §21 y rediseño visual. Detalle por tarea: [05 Día 7](05-cronograma-semana.md).

**Pruebas al cierre:** Backend 1.970 pytest con `ruff`, `ruff format`, `mypy app` y `lint-imports` limpios; Frontend 857 Vitest con `lint` y `build` limpios; E2E 5/5 en el stack aislado (8081), sin violaciones de CSP. Esquema en `0008`.

**Instalación limpia (libros reales, stack efímero):** 1.410 socios, 2.748 membresías, v1 con 1.564 ciclos y las mismas métricas y umbrales que el v1 del stack principal; lista del día y Excel generados.

## 2. Diferencias con el notebook

| Diferencia | Motivo | Referencia |
|---|---|---|
| ~~Niveles de riesgo por percentiles 20/30/50, no umbrales fijos 0,70/0,50~~ — ya no es diferencia desde M01: la app usa 0,70/0,50 | CU-05 · R-015 | [ADR-014](adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) |
| Referencia de factores fija (desde M01: vencimientos ≤ 01-12-2025, el `X_train` del notebook) | Igualar los factores del notebook | ADR-005, ADR-014 |
| La lista se genera desde **hoy** (fecha de Ecuador), horizonte ≤ 31 días; no se puede generar al 31-08-2026 desde la app | Lista operativa | [ADR-006](adr/ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md) |
| Cédula en lugar de correo; socios sin cédula fuera de la cartera | Identificación por el personal | ADR-006 |
| 2 celdas basura de vencimiento no se convierten en fechas (pandas sí); monto negativo → sin monto | Robustez; sin efecto en evaluables ni etiquetas | [11-historico](docs/backend/11-historico.md) |
| Reentrenamiento con criterios y comparación PR-AUC (el notebook entrena una vez) | CU-02 | ADR-011 |

La conciliación con el notebook se hace con `Backend/scripts/verificar_lista.py --fecha 2026-08-31`: resultado idéntico al cierre (cartera 59, 57 a priorizar, 0 diferencias de probabilidad u orden).

## 3. Diferido y riesgos residuales

Fuera de alcance de la versión (no son defectos): [03 §20](03-casos-de-uso.md) y [DEVELOPMENT_GUIDELINES §Fuera de alcance](DEVELOPMENT_GUIDELINES.md).

| Id | Qué queda | Riesgo | Referencia |
|---|---|---|---|
| S5 | El filtro por IP solo es efectivo con los puertos en `127.0.0.1`; abrir la app a otro PC no está implementado (exigiría filtrar en nginx) | Publicar los puertos en la red anula CU-00 | ADR-010, [10-docker](docs/backend/10-docker.md) |
| S23 residual | El rol propietario sigue siendo superusuario del clúster (imagen oficial) | Quien obtenga esas credenciales controla el clúster; la app ya no las usa | ADR-012 |
| S18 / TLS | Sin TLS ni HSTS; con TLS delante habrá que propagar `X-Forwarded-Proto` y que el filtro de `Origin` vea `https` | Solo relevante si se sale de `localhost` | ADR-013 |
| S19 | Comprobar que el build no publica sourcemaps | Bajo | 10-docker |
| S21 | Imágenes base fijadas por versión, no por digest | Bajo | 10-docker |
| S24 | Si la base no responde al arrancar, el frontend no arranca | Disponibilidad | 10-docker |
| S10 | Dependencias de Python sin lockfile; `pip-audit`/`npm audit` no ejecutados en R-013 (sin red) | Vulnerabilidades conocidas no revisadas al cierre | 10-docker |
| S26 | En operación `CORS_ORIGINS` debe listar solo el origen del frontend | Ampliarla debilita la protección CSRF | ADR-013 |
| T10-OBS-1 | El script de ensayo muestra la salida propia de `docker compose restart` | Cosmético | [comandos/ensayo-demo-e2e.md](comandos/ensayo-demo-e2e.md) |
| D7-FE-01 | Revisión visual del rediseño por el usuario | Ajustes estéticos | [frontend/01 §Estilos](docs/frontend/01-arquitectura.md) |
| — | Referencia de factores fija en 2025: revisar cuando exista un v2 | Factores menos representativos | ADR-005 |
| — | Cédula (dato personal) en la API, el Excel y los respaldos | Mitigado por el acceso local, `respaldos/` no versionado y sin datos en logs | ADR-006 |

## 4. Cómo operar

- Instalación, variables, rol de la app (S23), `HOSTS_PERMITIDOS`, reentrenamiento manual: [Backend/README §Operación](../Backend/README.md).
- Respaldo y restauración: [comandos/respaldo-y-restauracion.md](comandos/respaldo-y-restauracion.md). Haga un respaldo antes de cualquier cambio de configuración o de un reinicio de la base.
- Reiniciar la base a solo histórico (borra datos): [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md).
- Ensayo de la demostración (solo stack aislado): [comandos/ensayo-demo-e2e.md](comandos/ensayo-demo-e2e.md).
- Stacks: principal `proyectofinal` (8080, datos reales), aislado `mtabolic-e2e` (8081, datos sintéticos), instalación limpia `mtabolic-limpia` (8082, efímero): [10-docker](docs/backend/10-docker.md).
- Uso funcional de la lista, gestión, seguimiento y dashboard: [06](06-como-funciona-la-lista.md).
