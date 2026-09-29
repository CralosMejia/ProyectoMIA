# Documentación · App web de no renovaciones (Mtabolic)

Registro del paso del notebook `MVP.ipynb` a una aplicación web. Sirve de insumo para el reporte final.

| # | Documento | Contenido | Fecha |
|---|---|---|---|
| 01 | [Análisis: del notebook MVP a una aplicación web](01-analisis-mvp-a-app-web.md) | Alcance, implicaciones técnicas, privacidad, despliegue y puntos por aclarar | 2026-09-28 |
| 02 | [Entorno de desarrollo asistido por IA: harness y agentes](02-entorno-desarrollo-ia.md) | Máquina de estados, agentes, comandos, permisos, hook de commit y gestión de contexto | 2026-09-28 |
| 03 | [Casos de uso de la aplicación](03-casos-de-uso.md) | Carga de datos, entrenamiento con advertencia semestral, predicción y descarga del Excel; impacto en el análisis 01 | 2026-09-28 |

## Documentación técnica

| Documento | Contenido |
|---|---|
| [ACTION_PLAN.md](ACTION_PLAN.md) | Board vivo de requerimientos y decisiones |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Endpoints, formato único de error, CORS |
| [docs/backend/01-arquitectura.md](docs/backend/01-arquitectura.md) | Capas del Backend, composition root, configuración, pruebas |
| [docs/backend/10-docker.md](docs/backend/10-docker.md) | `compose.yaml`, imágenes, variables de entorno, pendientes de seguridad |
| [docs/frontend/01-arquitectura.md](docs/frontend/01-arquitectura.md) | Capas del Frontend, cliente HTTP, feature de referencia, estilos |

## Decisiones de arquitectura (ADR)

| ADR | Decisión |
|---|---|
| [ADR-001](adr/ADR-001-fastapi-react-postgresql.md) | FastAPI + React + PostgreSQL en lugar de Streamlit (cierra P-07) |

Cómo levantar el stack: [README.md de la raíz](../README.md).
