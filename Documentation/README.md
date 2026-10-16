# Documentación · App web de no renovaciones (Mtabolic)

Registro del paso del notebook `MVP.ipynb` a una aplicación web. Sirve de insumo para el reporte final.

| # | Documento | Contenido | Fecha |
|---|---|---|---|
| 00 | [Descripción del proyecto](00-descripcion-del-proyecto.md) | Qué es la aplicación, problema que resuelve, objetivo general y específicos, funciones, usuarios, alcance y stack | 2026-09-29 |
| 01 | [Análisis: del notebook MVP a una aplicación web](01-analisis-mvp-a-app-web.md) | Alcance, implicaciones técnicas, privacidad, despliegue y puntos por aclarar | 2026-09-28 |
| 02 | [Entorno de desarrollo asistido por IA: harness y agentes](02-entorno-desarrollo-ia.md) | Máquina de estados, agentes, comandos, permisos, hook de commit y gestión de contexto | 2026-09-28 |
| 03 | [Casos de uso del sistema de apoyo a la retención](03-casos-de-uso.md) | v4 · CU-00 a CU-12 con el alcance de la entrega de una semana y las decisiones confirmadas: un solo PC, migración automática y atómica del histórico, reentrenamiento sin recuperar fechas perdidas, lógica del notebook tal cual; modelo conceptual de datos; alcance diferido | 2026-09-28 |
| 04 | [Decisiones y pendientes para iniciar el desarrollo](04-pendientes-para-iniciar-desarrollo.md) | Decisiones D-01 a D-18 confirmadas, implicaciones de la instalación en un solo PC, acciones sobre repositorio y datos, ajustes de configuración y plan resumido de la semana | 2026-09-28 |
| 05 | [Cronograma de la entrega de una semana](05-cronograma-semana.md) | Tareas por día de base de datos, backend, frontend y apoyo, con responsable, dependencias, criterio de "hecho", ruta crítica, carga por persona y orden de recorte | 2026-09-28 |
| 06 | [¿Cómo funciona la lista de socios por vencer?](06-como-funciona-la-lista.md) | Guía para el personal del gimnasio, sin términos técnicos: fecha y días a revisar, socios prioritarios, nombre de la lista, niveles alto/medio/bajo, motivos, datos mostrados (pantalla y Excel iguales) y casos frecuentes | 2026-09-29 |
| 07 | [Cierre de la entrega](07-cierre.md) | Qué se entregó, diferencias con el notebook, lo diferido y riesgos residuales, cómo operar | 2026-10-01 |

> `01` se conserva como registro del análisis inicial; el alcance vigente es el de `03`.

## Documentación técnica

| Documento | Contenido |
|---|---|
| [ACTION_PLAN.md](ACTION_PLAN.md) | Board vivo de requerimientos y decisiones |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Endpoints, formato único de error, CORS |
| [docs/backend/01-arquitectura.md](docs/backend/01-arquitectura.md) | Capas del Backend, composition root, configuración, pruebas |
| [docs/backend/09-esquema-base-de-datos.md](docs/backend/09-esquema-base-de-datos.md) | Las 10 tablas, convenciones, restricciones, índices, excepción de `deleted_at`, migraciones |
| [docs/backend/10-docker.md](docs/backend/10-docker.md) | `compose.yaml`, imágenes, variables de entorno, pendientes de seguridad |
| [docs/backend/11-historico.md](docs/backend/11-historico.md) | Lectura de libros, limpieza, identidad, ciclos y etiquetas; repositorios del historial; conciliación con el notebook |
| [docs/backend/12-modelo-y-listas.md](docs/backend/12-modelo-y-listas.md) | Modelo v1 (variables, adaptador scikit-learn, factores, umbrales), migración al arrancar con bloqueo y estados, lista priorizada, Excel; conciliación con la lista del notebook |
| [docs/backend/13-cargas.md](docs/backend/13-cargas.md) | Carga por plantilla (CU-01): lector, validación por fila, enlace de socios, duplicados, transacción todo o nada con bloqueo; decisiones de R-007 |
| [docs/frontend/01-arquitectura.md](docs/frontend/01-arquitectura.md) | Capas del Frontend, cliente HTTP, feature de referencia, estilos |

## Comandos

| Documento | Contenido |
|---|---|
| [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md) | Reiniciar la base principal a solo datos históricos (borra cargas mensuales, listas y predicciones; no toca `mtabolic-e2e`) |
| [comandos/respaldo-y-restauracion.md](comandos/respaldo-y-restauracion.md) | Respaldo de solo lectura y restauración en una base nueva con comparación de conteos (R-013) |
| [comandos/ensayo-demo-e2e.md](comandos/ensayo-demo-e2e.md) | Ensayo de la demostración (03 §21) en el stack aislado: adelantar seguimientos y perder la fecha de reentrenamiento (R-013) |

## Decisiones de arquitectura (ADR)

| ADR | Decisión |
|---|---|
| [ADR-001](adr/ADR-001-fastapi-react-postgresql.md) | FastAPI + React + PostgreSQL en lugar de Streamlit (cierra P-07) |
| [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md) | Excel igual a la tabla de la pantalla y nombre editable de la lista (R-008) |
| [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md) | Gestión por ciclo de membresía, nombre de la campaña congelado al asignar y reglas de campañas y gestiones (R-009) |
| [ADR-012](adr/ADR-012-rol-de-aplicacion-sin-superusuario.md) | La app se conecta con un rol sin superusuario ni `DELETE`; migraciones con el propietario (S23, R-013) |
| [ADR-013](adr/ADR-013-proteccion-host-y-origin.md) | Filtro de `Host` y `Origin` contra DNS rebinding y CSRF (S1, R-013) |
| [ADR-014](adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md) | Modelo M01: variante sin `forma_pago`/`inicio_aproximado`, cortes 0,70/0,50, corte de los datos y `adoptar-modelo` (R-015) · mejoras del tutor en [mejoras/](mejoras/README.md) |

Cómo levantar el stack: [README.md de la raíz](../README.md).
