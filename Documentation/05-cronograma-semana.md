# 05 · Cronograma de la entrega de una semana

**Fecha:** 28 de septiembre de 2026  
**Base:** [03 · Casos de uso](03-casos-de-uso.md) (v4) y [04 · Decisiones](04-pendientes-para-iniciar-desarrollo.md) (§2 y §6).  
**Punto de partida:** existe el scaffold de R-001 (FastAPI en capas, React por features, PostgreSQL 16 en Docker Compose con `restart: unless-stopped` y el ejemplo `health`). No existen todavía tablas de negocio, Alembic, pandas ni scikit-learn.

---

## 1. Supuestos

| Supuesto | Valor | Si cambia |
|---|---|---|
| Personas | **Dos**: **A** (base de datos y backend) y **B** (frontend, datos de prueba y documentación). | Con una sola persona, este plan necesita **10 a 11 días**. La carga de A (unas 9 h/día) y la de B (unas 6 h/día) no caben juntas en una jornada. |
| Jornada | 8 a 9 horas por persona | Menos horas: se aplica el orden de recorte de §5. |
| Días | 7 días seguidos; el día 7 es de integración y margen, sin trabajo nuevo | — |
| Fechas | Sin fechas de calendario. Día 1 = primer día de trabajo. | Se ponen al fijar el inicio. |
| Proceso de agentes | **Un `/req` por día** con las tareas de ese día. TDD completo solo en las tareas marcadas **TDD**; en el resto, pruebas de los criterios de aceptación de `03`. Una sola revisión de seguridad el día 7. | — |

**Nomenclatura de tareas:** `D<día>-<área>-<n>`. Áreas: **BD** base de datos · **BE** backend · **FE** frontend · **OP** preparación, pruebas y documentación.

---

## 2. Vista general

| Día | Objetivo del día | CU | Hito verificable al cierre |
|---|---|---|---|
| 1 | Cimientos: configuración, esquema completo, contrato de la API y esqueleto del frontend | — | `docker compose up` crea las tablas antes del backend; el OpenAPI muestra todos los endpoints; el frontend navega con datos simulados. |
| 2 | Lectura del histórico, limpieza, identidad, ciclos y etiquetas | CU-03 (lógica) | Con los libros reales, en local: **2.771 / 2.748 / 1.410** y los ciclos evaluables del notebook. |
| 3 | Modelo v1, migración atómica al arrancar, lista y Excel | CU-03, CU-04, CU-05, CU-12 | Arranque en limpio → modelo v1. La lista al 31-08-2026 coincide con la del notebook. |
| 4 | Carga por plantilla y pantallas conectadas a la API real | CU-01, CU-04, CU-12 | Carga, lista y descarga de punta a punta en el navegador. |
| 5 | Campañas, sugerencias y formulario de gestión | CU-06, CU-07, CU-08, CU-10 | Asignar una campaña y cerrar una gestión desde la lista. |
| 6 | Alertas, dashboard, reentrenamiento y acceso por IP | CU-09, CU-11, CU-02, CU-00 | Pruebas con reloj simulado (programado y `OMITIDO`); `403` desde una IP no autorizada. |
| 7 | Integración, seguridad, instalación limpia y demo | Todos | Escenario de `03` §21 completo y ensayado. |

**Ruta crítica:** D1-BD-01 → D2-BE-01 → D2-BE-04 → D3-BE-02 → D3-BE-04 → D3-BE-05. Un retraso en cualquiera de ellas corre todo el plan. El frontend no está en la ruta crítica gracias al contrato de la API del día 1 y a los datos simulados con MSW.

---

## 3. Cronograma por día

### Día 1 · Cimientos

**Preparación (primeras 2 horas, A y B juntos)**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D1-OP-01 | Añadir `plantillas/Control Gym*.xlsx` a `.gitignore`. | A | — | `git status` ya no lista los libros. | Hecho (R-002 T1) |
| D1-OP-02 | Completar `.claude/CLAUDE.md`: nombre y descripción del proyecto, invariantes sin login (acceso por IP) y nota de que la regla `user_id` de `database.md` no aplica. | B | — | Sin marcadores `{{…}}` en el archivo. | Hecho (R-002 DOC-1) |
| D1-OP-03 | Crear `Documentation/DEVELOPMENT_GUIDELINES.md` con el alcance y lo que queda fuera (`03` §19 y §20). | B | — | Existe y `CLAUDE.md` lo enlaza. | Hecho (R-002 DOC-2) |
| D1-OP-04 | Redactar ADR-002 (ML en infraestructura), ADR-003 (reentrenamiento y versionado) y ADR-004 (migración de datos al arrancar). | B | — | Tres ADR en `Documentation/adr/`. | Hecho (R-002 DOC-3) |

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D1-BD-01 | Modelos ORM de las ~~11~~ **10** entidades de `03` §16 (corregido en R-002: la lista siempre tuvo 10): `socio`, `carga`, `membresia`, `modelo`, `intento_reentrenamiento`, `estado_sistema`, `lista_priorizada`, `prediccion`, `campania`, `gestion_retencion`. Montos en `NUMERIC`, fechas con zona horaria y `deleted_at` en `carga`. | A | D1-OP-01 | `mypy` y `lint-imports` en verde. | Hecho (R-002 T4–T5) |
| D1-BD-02 | Alembic: configuración y migración `0001` con todas las tablas, restricciones `CHECK` de los estados, índice único parcial de `socio.cedula`, índice único de `gestion_retencion.membresia_id` e índices de consulta (socio + fechas, estado + fecha de seguimiento). | A | D1-BD-01 | `alembic upgrade head` y `downgrade base` funcionan contra el PostgreSQL de Compose. | Hecho (R-002 T6–T7) |
| D1-BD-03 | Servicio `migrate` en `compose.yaml`: ejecuta `alembic upgrade head` y termina. El backend depende de él (`service_completed_successfully`). Volumen de solo lectura para la carpeta de libros históricos, con la ruta en `.env`. | A | D1-BD-02 | `docker compose up` desde cero deja las tablas creadas antes de que arranque el backend. | Hecho (R-002 T9) |
| D1-BD-04 | Migración de datos `0002`: fila única de `estado_sistema` (`migracion_historica = PENDIENTE`). | A | D1-BD-02 | La fila existe tras `upgrade head`. | Hecho (R-002 T8) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D1-BE-01 | Dependencias con versiones fijadas: pandas, numpy, scikit-learn, openpyxl, joblib, alembic, python-multipart. Las mismas versiones con que se ejecutó el notebook, si se conocen. | A | — | `pip install -e ".[dev]"` e imagen Docker construyen sin errores. | Hecho (R-002 T2); versiones del notebook desconocidas |
| D1-BE-02 | **Contrato de la API**: routers con DTOs, códigos de respuesta y ejemplos en OpenAPI para todos los endpoints de la semana (estado del sistema, carga con vista previa y confirmación, generar y consultar lista, Excel, campañas, sugerencias, gestiones, alertas, dashboard). Por ahora responden `501`. | A | D1-BE-01 | `/openapi.json` muestra todos los endpoints con ejemplos. Se entrega a B a media mañana. | Hecho (R-002 T10–T16): 18 operaciones |
| D1-BE-03 | Dominio común: enums de plan, forma de pago, estado de ciclo, nivel de riesgo, estado de gestión y origen, y los puertos `Clock` (ya existe) y `PredictorModel`. | A | — | Pruebas unitarias de los enums; `lint-imports` en verde. | Hecho (R-002 T3): 12 enums |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D1-FE-01 | Layout y navegación con 5 rutas: Inicio, Carga, Lista, Campañas y Dashboard. | B | — | Se navega entre las 5 páginas vacías. | Hecho (R-002 T17–T18) |
| D1-FE-02 | Componentes base: tabla, insignia de nivel de riesgo, aviso de error, indicador de carga y ventana modal. | B | D1-FE-01 | Pruebas de render de cada componente. | Hecho (R-002 T19–T22) |
| D1-FE-03 | Tipos y servicios `api/` de cada feature según el contrato, más handlers MSW con datos simulados. | B | D1-BE-02 | Cada servicio tiene su prueba contra MSW. | Hecho (R-002 T23–T30) |

#### Avance y resumen del Día 1

**Estado:** cerrado · 15 de 15 tareas hechas en un solo requerimiento (R-002, `DONE`). Hito verificado en el stack real: `migrate` termina con código 0 antes de arrancar `backend`; la base tiene las 10 tablas más `alembic_version` y `estado_sistema` con la fila `(1, PENDIENTE)`; `/openapi.json` publica 18 operaciones de negocio más `health`, todas en `501`; el frontend sirve `/`, `/carga`, `/lista`, `/campanias`, `/dashboard` y `/salud`.

**Realizado**
- Base de datos: esquema completo (10 tablas, `CHECK` generados desde los enums, índices únicos parciales, FKs `RESTRICT`, `deleted_at` en las 5 tablas editables), Alembic con `0001` (esquema) y `0002` (fila de `estado_sistema`), servicio `migrate` y volumen `HISTORICO_DIR` de solo lectura. Detalle: [09-esquema-base-de-datos](docs/backend/09-esquema-base-de-datos.md), [10-docker](docs/backend/10-docker.md).
- Backend: dependencias de datos y ML fijadas ([Backend/README](../Backend/README.md)); 12 enums del dominio y puerto `PredictorModel`; contrato `import-linter` que prohíbe pandas/numpy/sklearn en `domain` y `application` (ADR-002); contrato de la API con ejemplos ([API_CONTRACT](docs/API_CONTRACT.md)).
- Frontend: `AppLayout` con navegación, 5 páginas placeholder, `shared/ui` (`DataTable`, `RiskBadge`, `LoadingIndicator`, `ErrorAlert`, `Modal`), `core/http` con POST/PUT/multipart/Blob, MSW para pruebas y para desarrollo (`VITE_API_MOCKS=true`), y la capa `api/` de las 5 features ([frontend/01-arquitectura](docs/frontend/01-arquitectura.md)).
- Preparación: `.gitignore` de los libros, `CLAUDE.md`, `DEVELOPMENT_GUIDELINES.md`, ADR-002/003/004.
- Pruebas: Backend 391 pytest, `ruff`, `format`, `mypy`, `lint-imports` (7 contratos); Frontend 242 Vitest, `build`, `lint` sin avisos; E2E 1/1.

**Desviaciones**
- Son **10** entidades, no 11 (error de conteo de este cronograma; corregido en D1-BD-01).
- `deleted_at` no solo en `carga`: en las 5 tablas editables; las 5 restantes quedan como excepción documentada (instantáneas inmutables, auditoría y fila de control).
- Las versiones del notebook no se conocen (no las registra): se fijaron versiones estables para Python 3.12, entre ellas **pandas 3.0.6**.
- `version` del modelo viaja como texto `"v1"` en la API (entero en la BD).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).
- `health` pasó de `/` a `/salud`; `/` es ahora Inicio.

**Pendientes que pasan a los días siguientes**
- **Día 2:** decidir si `membresias.socio_id` pasa a `NOT NULL`; vigilar diferencias de comportamiento de pandas 3.x al portar el notebook (D2-BE-01 a D2-BE-05). *Resuelto en R-003: `NOT NULL` y pandas 3 se mantiene.*
- **Día 7:** S23 (rol de BD sin superusuario y rol de migraciones) dentro de D7-OP-02; revisión de seguridad de todo lo del día 1.
- Menores: verificar a mano el mensaje "[MSW] Mocking enabled" en el navegador; el handler MSW de `GET /gestiones` devuelve `[]` sin filtro (el backend responde `400`), a alinear al usar ese handler en pantallas; errores de `mypy` previos a R-002 en `tests/integration/api/test_error_handlers.py`.

---

### Día 2 · Histórico: lectura, limpieza, identidad, ciclos y etiquetas (CU-03)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D2-BD-01 | Repositorios de `socio`, `membresia` y `carga` con inserción masiva dentro de una transacción recibida desde fuera (unit of work). | A | D1-BD-02 | Prueba de integración: insertar 3.000 filas y hacer rollback deja la base vacía. | Hecho (R-003 T6–T7); además `membresias.socio_id NOT NULL` (T1, migración `0003`) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D2-BE-01 | Lector de libros históricos (infraestructura): año desde el nombre del archivo, hojas mensuales, detección del encabezado y columnas por nombres equivalentes. Adapta las secciones 2.4 a 3.4 del notebook. | A | D1-BE-01 | Lee los libros sintéticos de D2-OP-01. | Hecho (R-003 T9) |
| D2-BE-02 | **TDD** · Limpieza y normalización (dominio puro): filas no útiles, fechas, montos, nombre, cédula, plan (6 categorías) y forma de pago. Adapta las secciones 3.5 a 4.6. | A | D1-BE-03 | Pruebas con los casos del notebook ("39,50 USD", fecha numérica de Excel, "PROMO 3 MESES", plan con una forma de pago dentro…). | Hecho (R-003 T2–T3) |
| D2-BE-03 | **TDD** · Identidad del socio: cédula de al menos 9 dígitos o nombre normalizado; `inicio_aproximado`. | A | D2-BE-02 | Pruebas unitarias. | Hecho (R-003 T4) |
| D2-BE-04 | **TDD** · Ciclos y etiqueta (dominio puro): estado del ciclo (reglas de la Sección 5.3, fecha de corte), ventana T a T+30 y detección de renovación. | A | D2-BE-03 | Pruebas, incluido el caso del tutor (vence el 20-08 → pendiente). | Hecho (R-003 T5, T10) |
| D2-BE-05 | Verificación local fuera de la suite versionada: script que corre D2-BE-01 a D2-BE-04 con los libros reales e imprime los conteos. | A | D2-BE-04 | Da 2.771 / 2.748 / 1.410 y los ciclos evaluables del notebook. Las diferencias quedan documentadas. | Hecho (R-003 T11): 2.771 / 2.748 / 1.410 / 1.564; 2 diferencias conocidas documentadas |

**Frontend y apoyo**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D2-OP-01 | **Datos sintéticos**: dos libros con la estructura del histórico (hojas mensuales y auxiliares, encabezado en filas distintas, nombres de columna cambiantes, totales, filas vacías, socios sin cédula) y 5 plantillas (1 válida y 4 con errores: cédula, catálogo, fechas y 501 filas). Sin datos reales. | B | — | Archivos en `Backend/tests/fixtures/`. | Hecho (R-003 T8) |
| D2-FE-01 | Página Inicio: estado del sistema (Inicializando / Faltan datos históricos / Listo), con datos simulados. | B | D1-FE-03 | Pruebas de los tres estados. | Hecho (R-003 T12) |
| D2-FE-02 | Página Carga: selección de archivo, vista previa con conteos, tabla de errores por fila y botón Confirmar, deshabilitado si hay errores. | B | D1-FE-03 | Pruebas con vista previa válida y con errores (simuladas). | Hecho (R-003 T13) |

#### Avance y resumen del Día 2

**Estado:** cerrado · 9 de 9 tareas hechas en un solo requerimiento (R-003, `DONE`, 13 tareas de desarrollo + documentación). Hito verificado: con los libros reales, la lógica portada da **2.771 / 2.748 / 1.410** y **1.564 evaluables** (1.098 no renovó / 466 renovó), iguales al notebook.

**Realizado**
- Base de datos: `membresias.socio_id` pasa a `NOT NULL` (migración `0003`; falla si hubiera membresías sin socio; `downgrade` vuelve a `NULL`). Repositorios de socios, membresías y cargas con inserción masiva sin `commit` propio: 1 carga + 1.000 socios + 3.000 membresías y `rollback` deja la base vacía en < 5 s. Detalle: [09-esquema-base-de-datos](docs/backend/09-esquema-base-de-datos.md).
- Backend: dominio `historico` sin pandas (conversiones de fecha y monto con `Decimal`, normalización, identidad, registro y limpieza con conteos, ciclos y etiqueta T..T+30 con el caso del tutor), puertos y servicio `ProcesarHistorico` con informe solo de conteos, lector de libros con pandas y script de verificación local. Detalle: [11-historico](docs/backend/11-historico.md).
- Datos sintéticos: generador determinista, 2 libros y 5 plantillas en `Backend/tests/fixtures/`, validados ejecutando el código del notebook (39 leídas, 25 útiles, 14 socios, 15 evaluables, prevalencia 0,6).
- Frontend: páginas Inicio (tres estados del sistema) y Carga (selección, vista previa, errores, confirmación sin doble envío) con MSW ([frontend/01-arquitectura](docs/frontend/01-arquitectura.md)).
- Pruebas: Backend 729 pytest, `ruff`, `format`, `mypy app` (67 archivos), `lint-imports` (7 contratos); Frontend 270 Vitest, `lint` 0 avisos, `build`.

**Conciliación con el notebook (libros reales)**
- Iguales: útiles 2.771, con identidad 2.748, socios 1.410, corte 2026-08-31, evaluables 1.564, no renovó 1.098, renovó 466, vencimiento posterior al corte 160, ventana incompleta 96, duración implausible 49, pase diario 16.
- Diferencias conocidas: `SIN_VENCIMIENTO` 857 frente a 855 y `FECHA_FUERA_DE_RANGO` 6 frente a 8. Causa: 2 celdas basura en la fecha de vencimiento que pandas 3 convierte en los años 1114 y 1; la app no las toma como fecha. Ambos ciclos quedan excluidos igual: sin efecto en evaluables ni etiquetas.
- Corregido durante la conciliación: fechas con separador doble (`dd//mm/aaaa`) que se perdían (evaluables de 1.562 a 1.564).

**Desviaciones**
- No se replica la conversión de pandas de las 2 celdas basura (podría convertir basura como `2026` en una fecha válida).
- Montos negativos se guardan como `None` y se cuentan (la BD exige `>= 0`); el notebook los conserva.
- Se mantiene **pandas 3.0.6**: el notebook corrió con pandas 3 (con 2.x su propia lógica no da 855/8); no hizo falta el plan B de fijar pandas 2.x.
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Pendientes que pasan a los días siguientes**
- **Día 3:** conectar `ProcesarHistorico` con los repositorios en la migración atómica al arrancar (D3-BE-04).
- **Día 7:** S23 y revisión de seguridad de lo hecho el día 2 (D7-OP-02).
- Menores: `mypy` sobre `tests/` (stubs de `openpyxl`, `generar_fixtures.py:836`, `type: ignore` sin uso en `test_procesar_historico.py:33`); el resumen de carga no muestra `filasLeidas` ni `fechaCarga` (no lo exige el criterio).

---

### Día 3 · Modelo v1, migración al arrancar, lista y Excel (CU-03, CU-04, CU-05, CU-12)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D3-BD-01 | Repositorios de `modelo` (guarda el artefacto en `bytea`; solo uno vigente), `estado_sistema` (con bloqueo consultivo de PostgreSQL) y `lista_priorizada` + `prediccion`. | A | D1-BD-02 | Pruebas de integración: un solo modelo vigente; el bloqueo impide una segunda migración simultánea. | Hecho (R-004 T2–T5); además `membresias.fecha_actividad NOT NULL` (T1, migración `0004`) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D3-BE-01 | **TDD** · Variables en T−30 (Sección 7.2 a 7.4): historial previo, antigüedad, monto histórico, días desde la última membresía, imputaciones y `mes_vencimiento`. | A | D2-BE-04 | Pruebas con historiales pequeños conocidos. | Hecho (R-004 T6) |
| D3-BE-02 | Adaptador de scikit-learn que implementa `PredictorModel`: pipeline y parámetros del notebook, entrenamiento, `predict_proba`, factores principales (Sección 13.3) y serialización. | A | D3-BE-01 | Prueba: entrenar con datos sintéticos, serializar, deserializar y obtener los mismos scores. | Hecho (R-004 T9, T10) |
| D3-BE-03 | Umbrales por percentiles (20 / 30 / 50 sobre los últimos 3 meses con resultado conocido). | A | D3-BE-02 | Prueba unitaria. | Hecho (R-004 T8, T10) |
| D3-BE-04 | Migración atómica al arrancar: en segundo plano, con bloqueo y en una sola transacción (datos + modelo v1 + próxima fecha de reentrenamiento + informe). Si falla, se revierte todo. Endpoint de estado del sistema. | A | D2-BD-01, D3-BD-01, D3-BE-03 | Arranque en limpio con datos sintéticos → `COMPLETADA`; un fallo forzado del entrenamiento → base vacía; `/health` responde durante la migración. | Hecho (R-004 T11–T14) |
| D3-BE-05 | CU-04 · Generar lista: cartera en el horizonte, exclusión de renovados y `DIARIO`, score, factores, orden, una fila por socio, top K y nivel. Se guarda con su versión de modelo. Advertencia si la última carga tiene más de 30 días. | A | D3-BE-04 | Con los libros reales y la fecha 31-08-2026, coincide con la lista de septiembre del notebook. | Hecho (R-004 T7, T15, T16, T19): 25/25 iguales al notebook |
| D3-BE-06 | CU-12 · Excel en memoria (`top_K`, `cartera_completa`, `resumen`) con neutralización de fórmulas. | A | D3-BE-05 | Prueba: un nombre que empieza por `=` queda como texto. | Hecho (R-004 T17–T18) |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D3-FE-01 | Página Lista: parámetros (fecha, horizonte, K), botón Generar, tabla (prioridad, contacto, plan, vencimiento, días, score, nivel, factores, top K) y advertencia de datos antiguos. | B | D1-FE-03 | Pruebas con datos simulados. | Hecho (R-004 T20–T21); verificada también contra la API real (T25) |
| D3-FE-02 | Botón de descarga del Excel de la lista. | B | D3-FE-01 | Prueba: llama al endpoint con el id de la lista. | Hecho (R-004 T22) |
| D3-FE-03 | Historial de listas generadas (selector de listas anteriores). | B | D3-FE-01 | Prueba con dos listas simuladas. | Hecho (R-004 T23) |

#### Avance y resumen del Día 3

**Estado:** cerrado · 10 de 10 tareas hechas en un solo requerimiento (R-004, `DONE`, 25 tareas de desarrollo + documentación). Hito verificado: `docker compose down -v && up -d --build` con los libros reales → `migrate` 0 → estado `INICIALIZANDO` → `LISTO` en unos 5 s (`/health` 200 todo el tiempo), modelo v1 vigente con 1.564 ciclos de entrenamiento, 2.748 membresías y 1.410 socios; en http://localhost:8080 (sin MSW) la lista al 31-08-2026 da 57 socios y el top 25 igual al del notebook; el Excel se descarga con sus 3 hojas.

**Realizado**
- Base de datos: migración `0004` (`membresias.fecha_actividad DATE NOT NULL` + índice `(socio_id, fecha_actividad)`); repositorios de modelo, intentos, `estado_sistema` con bloqueo consultivo, listas y predicciones; unidades de trabajo. Detalle: [09-esquema-base-de-datos](docs/backend/09-esquema-base-de-datos.md).
- Backend: variables en T−30 (TDD), cartera y top K, umbrales por percentiles, adaptador scikit-learn (pipeline §9.5, factores §13.3, artefacto joblib en `bytea`, scores `Decimal` de 8 decimales), `EntrenarModeloInicial`, `MigrarHistorico` atómico en segundo plano al arrancar, `GET /sistema/estado` real, `POST /listas`, `GET /listas` (nuevo), `/listas/ultima`, `/listas/{id}` y `/listas/{id}/excel` (Excel en memoria, fórmulas neutralizadas). Detalle: [12-modelo-y-listas](docs/backend/12-modelo-y-listas.md); contrato: [API_CONTRACT](docs/API_CONTRACT.md).
- Frontend: página Lista (parámetros, Generar, tabla con `RiskBadge`, advertencia de datos antiguos, `409` si el sistema no está listo), botón Excel, historial de listas e Inicio que vuelve a consultar cada 5 s mientras inicializa ([frontend/01-arquitectura](docs/frontend/01-arquitectura.md)).
- Despliegue: `compose.yaml` pasa `HISTORICO_PATH=/data/historico` al backend; `Backend/README.md` §Primer arranque.
- Pruebas: Backend 1.082 pytest, `ruff`, `format` (198 archivos), `mypy app` (92), `lint-imports` (7 contratos); Frontend 323 Vitest, `lint` 0; E2E Playwright 1/1.

**Conciliación con el notebook (libros reales, `scripts/verificar_lista.py`)**
- Salida `0` con scikit-learn 1.8.0: cartera 59, ya renovaron 2, a priorizar 57 (57 socios), 1.564 ciclos de entrenamiento; top 25 con probabilidades, orden y factores iguales al notebook. El empate en el corte (posición 25) se acepta como conjunto.
- Con scikit-learn 1.9.1 el bosque cambiaba (24/25 del top iguales, probabilidades ±0,001–0,016): se fija 1.8.0, la versión del notebook.
- Corregido durante la conciliación: la referencia de los factores pasa de "todo el entrenamiento" a los evaluables con vencimiento en 2025, como `X_train` del notebook (con la primera no coincidían los factores).

**Desviaciones**
- Niveles de riesgo por percentiles 20/30/50 (CU-05) en lugar de los umbrales fijos 0,70/0,50 del notebook: el score y el orden coinciden, el nivel puede diferir (por diseño).
- Cambio de contrato: `GET /listas` nuevo; `fecha_generacion` pasa a `date`, se añaden `creada_en` y `monto_cobrado`.
- Un fallo de la migración deja `FALTAN_DATOS_HISTORICOS` (sin estado nuevo) y se reintenta al reiniciar el backend; el motivo solo va al log.
- El localizador lee solo `*Control*Gym*.xlsx` e ignora la plantilla de carga de la misma carpeta.
- Adelanto del día 4: Inicio y Lista ya funcionan contra la API real en el stack de Compose (parte de D4-FE-01).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Qué puede probar el usuario**
1. En `.env`, `HISTORICO_DIR` apunta a la carpeta con los `Control Gym*.xlsx`; `docker compose up -d --build` y abrir http://localhost:8080: Inicio muestra "Sistema listo" con el modelo v1.
2. Lista: fecha 2026-08-31, horizonte 30, K 25 → "Generar lista" → 57 socios, top 25 marcados, con nivel y factores. "Descargar Excel" → libro con `top_25`, `cartera_completa` y `resumen`. El historial permite volver a listas anteriores.
3. Desde `Backend/`: `python scripts/verificar_lista.py ../plantillas` y `python scripts/verificar_historico.py ../plantillas` → conciliación con el notebook (salida `0`).
4. `docker compose down -v && docker compose up -d --build` → vuelve a migrar solo y llega a `LISTO`.

**Pendientes que pasan a los días siguientes**
- **Día 5:** `gestion_estado` y `campania_asignada` de la lista salen siempre `null` hasta CU-08.
- **Día 7:** S23 y revisión de seguridad de lo hecho el día 3 (D7-OP-02).
- Menores: dos `POST /listas` simultáneos sin probar; `mypy` sobre `tests/` con errores de tipado estricto en dobles; el motivo de un fallo de migración vive solo en memoria.

#### Ajustes posteriores al Día 3 (R-005)

Petición del usuario tras revisar la lista. **Estado:** `DONE` (12 tareas de desarrollo + 2 de documentación). No se reentrena ni se recargan datos: el modelo v1 no cambia.

- **Fecha y horizonte:** la lista solo se genera desde hoy (fecha de Ecuador, UTC−5) hacia adelante; una fecha pasada → `422` "La fecha de la lista debe ser hoy o posterior."; por defecto, hoy. Horizonte de 1 a 31 días (`400` fuera de rango). Las listas antiguas se conservan tal cual.
- **Socios sin cédula:** se excluyen de la lista antes de predecir y del top K; siguen en la base y en el entrenamiento.
- **Cédula en lugar de correo:** en la API, en el Excel (columna "Cédula", texto con el cero inicial) y en el repositorio de listas; el correo sigue solo en la base. El Excel conserva score y aportes.
- **Pantalla para usuario no técnico:** fecha por defecto hoy (`min` = hoy), días máx. 31, dos tablas ("Socios prioritarios a contactar" y "Otros socios por vencer"), sin score ni columna Top, motivos sin el aporte, etiquetas amigables; Inicio muestra "Modelo de predicción: activo desde <fecha>". Detalle: [frontend/01-arquitectura](docs/frontend/01-arquitectura.md), [12-modelo-y-listas](docs/backend/12-modelo-y-listas.md), [API_CONTRACT](docs/API_CONTRACT.md).
- **Guía funcional** para el personal: [06-como-funciona-la-lista](06-como-funciona-la-lista.md).
- **Conciliación:** la fecha 31-08-2026 ya no se puede pedir en la aplicación; `scripts/verificar_lista.py` sigue saliendo con `0` (su propia ventana, todos "con cédula"). Sustituye al paso 2 de "Qué puede probar el usuario": ahora se genera la lista con la fecha de hoy.
- Pruebas: Backend 1.122 pytest, `ruff`, `mypy app` (92), `lint-imports` (7); Frontend 347 Vitest, `build`, `lint` 0.
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1); incluye la exposición de la cédula en la API y el Excel.
- **Registrado para días siguientes (no implementado):** D4-FE-03 (botón de ayuda en la Lista) y D6-BE-06 / D6-FE-04 (alerta de datos del mes).

#### Ajustes posteriores (R-006)

Continuación de R-005, a petición del usuario. **Estado:** `DONE` (5 tareas + documentación). Sin cambios en el backend ni en la API.

- **Listas de prueba borradas:** borrado físico puntual de `predicciones` (117) y `listas_priorizadas` (3) en la base de Docker, 2026-09-30 01:50:06 UTC; resto de tablas intacto. Excepción única: [DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md), [09](docs/backend/09-esquema-base-de-datos.md).
- **Pantalla Lista:** resumen de dos líneas ("Rango de fechas: 29 sep – 29 oct 2026" y "Socios priorizados para campañas: 25"); sin columna Celular (sigue en la API y el Excel); "Listas anteriores" con nombres cortos ("29 sep 2026 · 25 prioritarios"). Detalle: [frontend/01-arquitectura](docs/frontend/01-arquitectura.md).
- Pruebas: Frontend 375 Vitest, `lint` 0, `build`; E2E 1/1. Verificado en Docker (lista del 2026-09-29, 30 días, 25; Excel de 3 hojas con Celular y Cédula).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).
- **Registrado para el día 7 (no implementado):** D7-FE-01 (mejora del diseño visual).

---

### Día 4 · Carga por plantilla e integración real (CU-01)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D4-BD-01 | Consulta de duplicados por la clave de D-04 y búsqueda de socios históricos sin cédula por nombre normalizado (con índice). | A | D2-BD-01 | Pruebas de integración de ambas consultas. |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D4-BE-01 | Lector de la plantilla: hoja `Registros`, títulos exactos, máximo 500 filas; rechazo del formato antiguo. | A | D1-BE-01 | Pruebas con las plantillas de D2-OP-01. |
| D4-BE-02 | **TDD** · Validación por fila: cédula con módulo 10, excepción de pasaporte, catálogos, fechas, montos, duración y nombre. | A | D4-BE-01 | Una prueba por regla de la tabla de CU-01. |
| D4-BE-03 | Duplicados y enlace con el histórico (D-03): enlace único, homónimos informados en el resumen. | A | D4-BD-01, D4-BE-02 | Pruebas de los criterios de aceptación de CU-01. |
| D4-BE-04 | Endpoints: vista previa (valida sin guardar) y confirmación (vuelve a recibir el archivo, revalida y guarda en una transacción; todo o nada). | A | D4-BE-03 | Cargar dos veces el mismo archivo no duplica; un archivo con una fila inválida no se puede confirmar. |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D4-FE-01 | Conectar Inicio, Carga y Lista a la API real (MSW solo en pruebas). Estados "Inicializando" y "Faltan datos". | B | D3-BE-04, D4-BE-04 | Recorrido en el navegador con el stack de Compose. |
| D4-FE-02 | Resumen posterior a la carga: guardadas, duplicadas y socios enlazados u homónimos. | B | D4-FE-01 | Prueba con respuesta simulada. |
| D4-OP-01 | E2E Playwright: carga válida → generar lista → descargar Excel (con datos sintéticos). | B | D4-FE-01 | Prueba en verde contra el stack local. |
| D4-FE-03 | Botón de ayuda "¿Cómo funciona esta lista?" en la pantalla Lista, con la explicación de [06-como-funciona-la-lista](06-como-funciona-la-lista.md) (añadida por R-005; pendiente). | B | D3-FE-01 | Prueba: el botón abre la explicación sin términos técnicos. |

---

### Día 5 · Campañas y gestión (CU-06, CU-07, CU-08, CU-10)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D5-BD-01 | Repositorios de `campania` (sin borrado; inactivar) y `gestion_retencion` (una por ciclo). | A | D1-BD-02 | Pruebas de integración; una segunda gestión para el mismo ciclo falla. |
| D5-BD-02 | Migración de datos `0003`: 3 campañas de ejemplo marcadas `es_ejemplo` (D-17). | A | D5-BD-01 | Aparecen tras `upgrade head`. |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D5-BE-01 | CU-06 · Crear, editar e inactivar campañas; validaciones. | A | D5-BD-01 | Criterios de aceptación de CU-06. |
| D5-BE-02 | CU-07 · Sugerencias por nivel y plan, ordenadas por prioridad y nombre, más "No asignar". | A | D5-BE-01 | Criterios de aceptación de CU-07. |
| D5-BE-03 | CU-08 · Crear gestión: fecha sugerida (vencimiento + 25), rango permitido, responsable y referencia a la predicción, el modelo y la campaña. | A | D5-BD-01 | Criterios de aceptación de CU-08. |
| D5-BE-04 | CU-10 · Registrar resultado: reglas de coherencia, cierre con Sí o No, bloqueo de edición de una gestión cerrada. | A | D5-BE-03 | Criterios de aceptación de CU-10. |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D5-FE-01 | Página Campañas: lista, formulario de alta y edición, inactivar e indicador "ejemplo". | B | D1-FE-03 | Pruebas del formulario y del flujo de inactivar. |
| D5-FE-02 | Formulario de gestión (ventana modal desde la Lista): parte 1 (campaña sugerida o "No asignar", fecha de seguimiento, responsable) y parte 2 (resultado). | B | D3-FE-01 | Pruebas de validación: fecha fuera de rango y combinaciones incoherentes. |
| D5-FE-03 | Columna de estado de gestión y campaña en la tabla de la Lista. | B | D5-FE-02 | Prueba con una gestión pendiente y una cerrada. |

---

### Día 6 · Alertas, dashboard, reentrenamiento y acceso (CU-09, CU-11, CU-02, CU-00)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D6-BD-01 | Consultas de lectura (SQLAlchemy Core con parámetros): contadores de alertas, embudo del mes y tabla por campaña. | A | D5-BD-01 | Pruebas de integración con datos conocidos. |
| D6-BD-02 | Repositorio de `intento_reentrenamiento`. | A | D1-BD-02 | Prueba de integración. |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D6-BE-01 | CU-09 · Endpoint de alertas: vencidos, hoy, próximos 7 días y la lista de cada categoría. | A | D6-BD-01 | Criterios de aceptación con reloj fijado. |
| D6-BE-02 | CU-11 · Endpoint del dashboard: embudo, tabla por campaña (tasa desde 10 casos) y estado del modelo. | A | D6-BD-01 | Criterios de aceptación de CU-11. |
| D6-BE-03 | **TDD** · CU-02 · Servicio de reentrenamiento: criterios, conjunto de comparación de 3 meses, PR-AUC del candidato contra la del vigente, reentrenamiento completo, `OMITIDO` y cálculo de la próxima fecha. | A | D3-BE-02, D6-BD-02 | Pruebas de todos los flujos alternativos de CU-02 con reloj simulado. |
| D6-BE-04 | Planificador dentro del backend (revisa al arrancar y una vez al día si hoy es la fecha programada; si ya pasó, registra `OMITIDO`) y comando `python -m app.cli reentrenar`. | A | D6-BE-03 | Arranque con fecha pasada → `OMITIDO`; el comando crea v2 con datos sintéticos suficientes. |
| D6-BE-05 | CU-00 · Filtro de IP: lista en `.env` (por defecto `127.0.0.1`), IP tomada de la conexión, sin `X-Forwarded-For`, `/health` exento, `403` con el formato único de error. | A | — | Criterios de aceptación de CU-00. |
| D6-BE-06 | Exponer a Inicio (el endpoint lo decide el planner del día 6) si no hay ninguna carga (CU-01) con `fecha_carga` dentro del mes actual (fecha de negocio, reloj inyectable) (añadida por R-005; pendiente). | A | D4-BE-04 | Pruebas con reloj fijo: con y sin carga en el mes. |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D6-FE-01 | Contadores de alertas en Inicio; al pulsar, lista de gestiones que abre el formulario. | B | D5-FE-02 | Prueba de los tres contadores y la navegación. |
| D6-FE-02 | Página Dashboard: filtro por mes, embudo (barras), tabla por campaña ("casos insuficientes" bajo 10) y tarjeta del estado del modelo. | B | D1-FE-03 | Pruebas con datos simulados. |
| D6-FE-03 | Página de acceso denegado para respuestas `403`. | B | D1-FE-02 | Prueba de render. |
| D6-FE-04 | Alerta en Inicio "Aún no se han cargado los datos de este mes" cuando D6-BE-06 lo indique (añadida por R-005; pendiente). | B | D6-BE-06 | Prueba con respuesta simulada con y sin carga del mes. |
| D6-OP-01 | `Backend/README.md`: instalación en el PC, dónde poner los libros, comando manual de reentrenamiento y cómo hacer y restaurar un respaldo. | B | D6-BE-04 | Documento revisado por A. |

---

### Día 7 · Integración, seguridad y demostración

| ID | Tarea | Resp. | Depende de | Hecho cuando |
|---|---|---|---|---|
| D7-BD-01 | Script de respaldo (`pg_dump`) y restauración, probado una vez en limpio. | A | — | Restauración en una base nueva con los mismos conteos. |
| D7-OP-01 | Instalación limpia en el PC de destino (o uno equivalente): `docker compose up` con base vacía y libros reales → migración → lista. | A | Todo | Informe de migración correcto y lista generada. |
| D7-OP-02 | Revisión de seguridad única (agente `security-reviewer` sobre todo el código de la semana) y corrección de hallazgos críticos o altos. | A | Todo | Sin hallazgos críticos ni altos abiertos. |
| D7-OP-03 | E2E Playwright del escenario principal: carga → lista → gestión → cierre → dashboard. | B | Todo | Prueba en verde. |
| D7-OP-04 | Ensayo del escenario de demostración de `03` §21, con reloj simulado para CU-02 y CU-09. | A y B | D7-OP-01 | Ensayo completo sin fallos. |
| D7-OP-05 | Documentación de cierre: `ACTION_PLAN.md`, ajustes en `03` si algo cambió, diferencias con el notebook y lista de lo diferido. | B | Todo | Documentos actualizados. |
| D7-FE-01 | Mejora del diseño visual de la aplicación (jerarquía, espaciado, tipografía y color con los tokens de `shared/ui`, sin cambiar comportamiento) (añadida por R-006, a pedido del usuario; pendiente). | B | Todo el frontend | Revisión visual con el usuario y suites en verde. |

---

## 4. Carga estimada por persona (horas)

| Día | A · BD + backend | B · frontend + apoyo |
|---|---|---|
| 1 | 9 | 8 |
| 2 | 9 | 7 |
| 3 | 10 | 6 |
| 4 | 8 | 6 |
| 5 | 8 | 7 |
| 6 | 10 | 7 |
| 7 | 7 | 6 |
| **Total** | **≈ 61** | **≈ 47** |

A tiene más carga. Si B termina antes, lo primero que puede tomar es **D6-BE-05** (filtro de IP), **D2-BE-05** (script de verificación) y **D7-BD-01** (respaldo).

---

## 5. Riesgos y orden de recorte

| Riesgo | Señal | Acción |
|---|---|---|
| La migración no reproduce las cifras del notebook | D2-BE-05 no cuadra al cierre del día 2 | Se documenta la diferencia y se sigue; como máximo medio día extra del día 3. |
| El día 3 no termina (tiene la ruta crítica más cargada) | D3-BE-05 sin terminar | D3-FE-03 (historial de listas) y D3-BE-06 (Excel) pasan al día 4. |
| Atraso acumulado en los días 5 o 6 | CU-08/CU-10 sin cerrar al final del día 5 | Recortar en este orden: 1) gráfico del embudo (queda como tabla); 2) tabla por campaña del dashboard; 3) comparación PR-AUC de CU-02 (queda solo la cantidad de ciclos); 4) E2E del día 4. |
| Una sola persona disponible | — | No cabe en 7 días: 10 a 11 días con este mismo orden. |
