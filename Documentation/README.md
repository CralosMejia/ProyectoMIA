# Documentación · App web de no renovaciones (Mtabolic)

Registro del paso del notebook `MVP.ipynb` a una aplicación web. Sirve de insumo para el reporte final.

| # | Documento | Contenido | Fecha |
|---|---|---|---|
| 01 | [Análisis: del notebook MVP a una aplicación web](01-analisis-mvp-a-app-web.md) | Alcance, implicaciones técnicas, privacidad, despliegue y puntos por aclarar | 2026-09-28 |
| 02 | [Entorno de desarrollo asistido por IA: harness y agentes](02-entorno-desarrollo-ia.md) | Máquina de estados, agentes, comandos, permisos, hook de commit y gestión de contexto | 2026-09-28 |
| 03 | [Casos de uso del sistema de apoyo a la retención](03-casos-de-uso.md) | v4 · CU-00 a CU-12 con el alcance de la entrega de una semana y las decisiones confirmadas: un solo PC, migración automática y atómica del histórico, reentrenamiento sin recuperar fechas perdidas, lógica del notebook tal cual; modelo conceptual de datos; alcance diferido | 2026-09-28 |
| 04 | [Decisiones y pendientes para iniciar el desarrollo](04-pendientes-para-iniciar-desarrollo.md) | Decisiones D-01 a D-18 confirmadas, implicaciones de la instalación en un solo PC, acciones sobre repositorio y datos, ajustes de configuración y plan resumido de la semana | 2026-09-28 |
| 05 | [Cronograma de la entrega de una semana](05-cronograma-semana.md) | Tareas por día de base de datos, backend, frontend y apoyo, con responsable, dependencias, criterio de "hecho", ruta crítica, carga por persona y orden de recorte | 2026-09-28 |

> `01` se conserva como registro del análisis inicial; el alcance vigente es el de `03`.

## Documentación técnica

| Documento | Contenido |
|---|---|
| [ACTION_PLAN.md](ACTION_PLAN.md) | Board vivo de requerimientos y decisiones |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Endpoints, formato único de error, CORS |
| [docs/backend/01-arquitectura.md](docs/backend/01-arquitectura.md) | Capas del Backend, composition root, configuración, pruebas |
| [docs/backend/09-esquema-base-de-datos.md](docs/backend/09-esquema-base-de-datos.md) | Las 10 tablas, convenciones, restricciones, índices, excepción de `deleted_at`, migraciones |
| [docs/backend/10-docker.md](docs/backend/10-docker.md) | `compose.yaml`, imágenes, variables de entorno, pendientes de seguridad |
| [docs/frontend/01-arquitectura.md](docs/frontend/01-arquitectura.md) | Capas del Frontend, cliente HTTP, feature de referencia, estilos |

## Decisiones de arquitectura (ADR)

| ADR | Decisión |
|---|---|
| [ADR-001](adr/ADR-001-fastapi-react-postgresql.md) | FastAPI + React + PostgreSQL en lugar de Streamlit (cierra P-07) |

Cómo levantar el stack: [README.md de la raíz](../README.md).
