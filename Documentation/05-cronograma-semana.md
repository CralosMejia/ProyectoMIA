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

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D4-BD-01 | Consulta de duplicados por la clave de D-04 y búsqueda de socios históricos sin cédula por nombre normalizado (con índice). | A | D2-BD-01 | Pruebas de integración de ambas consultas. | Hecho (R-007 T1, migración `0005`; T3) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D4-BE-01 | Lector de la plantilla: hoja `Registros`, títulos exactos, máximo 500 filas; rechazo del formato antiguo. | A | D1-BE-01 | Pruebas con las plantillas de D2-OP-01. | Hecho (R-007 T2, T4) |
| D4-BE-02 | **TDD** · Validación por fila: cédula con módulo 10, excepción de pasaporte, catálogos, fechas, montos, duración y nombre. | A | D4-BE-01 | Una prueba por regla de la tabla de CU-01. | Hecho (R-007 T5, T6; TDD) |
| D4-BE-03 | Duplicados y enlace con el histórico (D-03): enlace único, homónimos informados en el resumen. | A | D4-BD-01, D4-BE-02 | Pruebas de los criterios de aceptación de CU-01. | Hecho (R-007 T7, T8) |
| D4-BE-04 | Endpoints: vista previa (valida sin guardar) y confirmación (vuelve a recibir el archivo, revalida y guarda en una transacción; todo o nada). | A | D4-BE-03 | Cargar dos veces el mismo archivo no duplica; un archivo con una fila inválida no se puede confirmar. | Hecho (R-007 T9, T10) |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D4-FE-01 | Conectar Inicio, Carga y Lista a la API real (MSW solo en pruebas). Estados "Inicializando" y "Faltan datos". | B | D3-BE-04, D4-BE-04 | Recorrido en el navegador con el stack de Compose. | Hecho (Inicio y Lista desde R-004; Carga en R-007 T11; recorrido en T15) |
| D4-FE-02 | Resumen posterior a la carga: guardadas, duplicadas y socios enlazados u homónimos. | B | D4-FE-01 | Prueba con respuesta simulada. | Hecho (R-007 T11) |
| D4-OP-01 | E2E Playwright: carga válida → generar lista → descargar Excel (con datos sintéticos). | B | D4-FE-01 | Prueba en verde contra el stack local. | Hecho (R-007 T13 stack aislado, T14 E2E) |
| D4-FE-03 | Botón de ayuda "¿Cómo funciona esta lista?" en la pantalla Lista, con la explicación de [06-como-funciona-la-lista](06-como-funciona-la-lista.md) (añadida por R-005). | B | D3-FE-01 | Prueba: el botón abre la explicación sin términos técnicos. | Hecho (R-007 T12) |

#### Avance y resumen del Día 4

**Estado:** cerrado · 8 de 8 tareas hechas en un solo requerimiento (R-007, `DONE`, 15 tareas de desarrollo + documentación). Hito verificado: en el stack aislado (http://localhost:8081, datos sintéticos) el recorrido carga → confirmar → lista → Excel funciona en el navegador y en el E2E; en el stack principal (http://localhost:8080) la base quedó en `0005`, `LISTO`, con los datos intactos (socios 1.410, membresías 2.748, cargas 1).

**Realizado**
- Base de datos: migración `0005` con el índice parcial `ix_socios_nombre_normalizado_sin_cedula`; repositorio de cargas (búsqueda de cédula con y sin cero inicial, candidatos sin cédula por nombre, claves de duplicado) y unidad de trabajo con bloqueo consultivo de transacción. Detalle: [09](docs/backend/09-esquema-base-de-datos.md).
- Backend: lector de la plantilla (hoja `Registros`, títulos A..N exactos, máximo 500 filas, O y P ignoradas, formato antiguo y archivos dañados rechazados); validación por fila con una regla por columna (cédula módulo 10 y pasaporte por TDD); enlace por cédula o por nombre único, homónimos → socio nuevo con aviso; duplicados por la clave de D-04; `POST /cargas/vista-previa` y `POST /cargas` reales (todo o nada, un solo `commit`). La carga alimenta la lista: el aviso de datos antiguos usa la nueva fecha de carga y las membresías nuevas entran en la cartera. Detalle: [13-cargas](docs/backend/13-cargas.md); contrato: [API_CONTRACT §Cargas](docs/API_CONTRACT.md#cargas-cu-01-r-007).
- Frontend: Carga contra la API real con vista previa (conteos, rango de vencimientos, errores por fila y columna) y resumen tras confirmar (guardadas, duplicadas, socios enlazados, "Para revisar", enlace a la Lista); botón "¿Cómo funciona esta lista?" ([frontend/01](docs/frontend/01-arquitectura.md)).
- Despliegue: puertos e `IMAGE_TAG` configurables en `compose.yaml` y stack aislado `mtabolic-e2e` con `.env.e2e` ([10-docker](docs/backend/10-docker.md)).
- Pruebas: Backend 1.409 pytest, `ruff`, `format` (226 archivos), `mypy app` (104), `lint-imports` (7 contratos); Frontend 404 Vitest, `build`, `lint` 0; E2E `health` en 8080 y 8081, `carga-lista-excel` en verde en 8081 (unos 10 s) y saltado a propósito en 8080.

**Desviaciones**
- Las confirmaciones de prueba y el E2E se hacen solo en el stack aislado (8081): confirmar en el principal dejaría socios ficticios que no se pueden borrar. En el principal solo se verificó la vista previa (`plantilla_valida` 6/6 con "Confirmar" habilitado sin confirmar; `plantilla_cedula_invalida` 5 válidas y 1 error con "Confirmar" deshabilitado), la ayuda y la lista (30 filas) con su Excel.
- Las filas duplicadas cuentan como válidas; confirmar exige ninguna fila con error y al menos una fila nueva.
- Cédula: 10 dígitos con módulo 10, sin reglas de provincia; una celda numérica de 9 dígitos recupera el `0`; la búsqueda prueba la cédula con y sin cero inicial (el histórico guardó algunas con 9 dígitos). Un socio enlazado por nombre recibe la cédula aunque sus filas resulten duplicadas.
- Límites propios: 5 MB (`413`), 500 filas, montos con máximo 2 decimales. Sin índice único de duplicados (D-04 conserva duplicados del histórico); la concurrencia se resuelve con bloqueo consultivo.
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Qué puede probar el usuario**
1. En http://localhost:8080 → Carga: subir la plantilla real del mes (formato oficial `Plantilla_Carga_Datos_Mtabolic.xlsx`) → revisar la vista previa y los errores por fila → "Confirmar" → ver el resumen → ir a Lista y generar: los socios nuevos aparecen y el aviso de datos antiguos desaparece. (Confirmar guarda de verdad en la base: hacerlo solo con datos reales del mes.)
2. Lista → botón "¿Cómo funciona esta lista?": abre la explicación y cierra con "Cerrar" o `Escape`.
3. Para probar sin tocar los datos reales: levantar el stack aislado ([10-docker §Stack E2E aislado](docs/backend/10-docker.md)), abrir http://localhost:8081 y cargar una plantilla sintética, o ejecutar el E2E (`Frontend/README.md`).

**Pendientes que pasan a los días siguientes**
- **Día 6:** D6-BE-06 / D6-FE-04 (alerta de datos del mes).
- **Día 7:** revisión de seguridad de lo hecho el día 4 y S23 (D7-OP-02); `npm audit` con 2 avisos moderados por `uuid` < 11.1.1 vía `exceljs` (solo `devDependency` del E2E); D7-FE-01 (diseño).
- Menor: el aviso de enlace del contrato va con tildes ("históricos", "creó"), a diferencia de otros mensajes del backend sin tildes.

#### Correcciones posteriores al Día 4 (R-008)

A petición del usuario. **Estado:** `DONE` (14 tareas + documentación).

- **Excel igual a la tabla:** hojas "Socios prioritarios a contactar", "Otros socios por vencer" y "Resumen", con las columnas de la pantalla (sin celular, score ni monto; motivos sin aporte). Revierte R-005 (e) y el celular en el Excel de R-006; la API conserva esos campos. Detalle: [12 §Excel](docs/backend/12-modelo-y-listas.md), [03 §15](03-casos-de-uso.md).
- **Carga en tres pasos:** "Seleccionar archivo de carga (.xlsx)" (elegir no llama a la API) → "Revisar archivo" → "Confirmar carga" ([frontend/01](docs/frontend/01-arquitectura.md)).
- **Ayuda de la lista** con 4 secciones (sin "Qué datos se muestran" ni "Casos frecuentes") ([06](06-como-funciona-la-lista.md)).
- **Nombre editable de la lista:** migración `0006` (`listas_priorizadas.nombre`, 1..80), `nombre` opcional en `POST /listas` (por defecto "Lista del 29 sep 2026") y en las respuestas; título, "Listas anteriores" y hoja "Resumen" → [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md), [09](docs/backend/09-esquema-base-de-datos.md), [API_CONTRACT](docs/API_CONTRACT.md).
- **Reinicio de la base principal a solo histórico** con scripts versionados → [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md). No se ejecutó en esta sesión (la base tenía 2 listas del usuario).
- Pruebas: Backend 1.463 pytest, `ruff`, `format` (231), `mypy app` (106), `lint-imports` (7), `verificar_lista.py` salida 0; Frontend 448 Vitest, `build`, `lint` 0; E2E 2/2 en el stack aislado. Stack principal en `0006` con datos intactos (socios 1.410, membresías 2.748, cargas 1, listas 2).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

---

### Día 5 · Campañas y gestión (CU-06, CU-07, CU-08, CU-10)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D5-BD-01 | Repositorios de `campania` (sin borrado; inactivar) y `gestion_retencion` (una por ciclo). | A | D1-BD-02 | Pruebas de integración; una segunda gestión para el mismo ciclo falla. | Hecho (R-009 T7, T11; migración `0008`, T4) |
| D5-BD-02 | Migración de datos `0003`: 3 campañas de ejemplo marcadas `es_ejemplo` (D-17). | A | D5-BD-01 | Aparecen tras `upgrade head`. | Hecho (R-009 T3; la migración es la `0007`, no la `0003`) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D5-BE-01 | CU-06 · Crear, editar e inactivar campañas; validaciones. | A | D5-BD-01 | Criterios de aceptación de CU-06. | Hecho (R-009 T1, T5, T8) |
| D5-BE-02 | CU-07 · Sugerencias por nivel y plan, ordenadas por prioridad y nombre, más "No asignar". | A | D5-BE-01 | Criterios de aceptación de CU-07. | Hecho (R-009 T6, T8) |
| D5-BE-03 | CU-08 · Crear gestión: fecha sugerida (vencimiento + 25), rango permitido, responsable y referencia a la predicción, el modelo y la campaña. | A | D5-BD-01 | Criterios de aceptación de CU-08. | Hecho (R-009 T2, T9, T12) |
| D5-BE-04 | CU-10 · Registrar resultado: reglas de coherencia, cierre con Sí o No, bloqueo de edición de una gestión cerrada. | A | D5-BE-03 | Criterios de aceptación de CU-10. | Hecho (R-009 T2, T10, T12) |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D5-FE-01 | Página Campañas: lista, formulario de alta y edición, inactivar e indicador "ejemplo". | B | D1-FE-03 | Pruebas del formulario y del flujo de inactivar. | Hecho (R-009 T16, T17) |
| D5-FE-02 | Formulario de gestión (ventana modal desde la Lista): parte 1 (campaña sugerida o "No asignar", fecha de seguimiento, responsable) y parte 2 (resultado). | B | D3-FE-01 | Pruebas de validación: fecha fuera de rango y combinaciones incoherentes. | Hecho (R-009 T18, T19, T20) |
| D5-FE-03 | Columna de estado de gestión y campaña en la tabla de la Lista. | B | D5-FE-02 | Prueba con una gestión pendiente y una cerrada. | Hecho (R-009 T13, T14, T15, T21) |

#### Avance y resumen del Día 5

**Estado:** cerrado · 9 de 9 tareas hechas en un solo requerimiento (R-009, `DONE`, 22 tareas de desarrollo + documentación). Hito verificado: en el stack aislado (http://localhost:8081, datos sintéticos) el recorrido campaña → lista → gestión → resultado → Excel funciona en el navegador y en el E2E; en el stack principal (http://localhost:8080) la base quedó en `0008`, `LISTO`, con socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0, las 3 campañas de ejemplo y 0 gestiones.

**Realizado**
- Base de datos: migración de datos `0007` (3 campañas "Ejemplo: …", sin duplicar si ya existen) y de esquema `0008` (`gestiones_retencion.campania_nombre`: el nombre de la campaña queda congelado al asignarla, RN-08.2); repositorios de campañas y gestiones sin borrado y unidad de trabajo de retención. Detalle: [09](docs/backend/09-esquema-base-de-datos.md), [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md).
- Backend: campañas (listar, crear, editar, inactivar; sin borrar; volver a activarlas llegó en R-010), sugerencias por nivel y plan, crear gestión (una por ciclo, rango de fecha de seguimiento), consultar gestión y registrar resultado (reglas de coherencia; Renovó Sí/No la cierra y ya no se edita). La lista y el Excel traen la gestión y la campaña de cada socio. Contrato: [API_CONTRACT §Campañas y gestiones](docs/API_CONTRACT.md#campañas-y-gestiones-cu-06-cu-07-cu-08-cu-10-r-009); Excel: [12 §Excel](docs/backend/12-modelo-y-listas.md).
- Frontend: página Campañas (tabla, alta y edición en ventana, inactivar con confirmación, etiqueta "Ejemplo") y formulario de gestión desde la Lista, con columnas "Gestión", "Campaña" y botón de acción ([frontend/01](docs/frontend/01-arquitectura.md)). Guía para el personal: [06 §7](06-como-funciona-la-lista.md).
- Pruebas: Backend 1.671 pytest, `ruff`, `format` (267 archivos), `mypy app` (121), `lint-imports` (7 contratos), `verificar_lista.py` salida 0; Frontend 570 Vitest, `build`, `lint` 0; E2E en el stack aislado 8081: 3 en verde (`health`, `carga-lista-excel`, `campanias-gestion`); contra 8080: 1 en verde y 2 saltados a propósito. Carreras probadas: dos creaciones simultáneas → `201` y `409`; dos cierres → `200` y `409`.

**Desviaciones**
- La migración de las campañas de ejemplo es la `0007` (el cronograma decía `0003`, número ya usado) y se añadió la `0008` para congelar el nombre de la campaña en la gestión.
- `GET /alertas` y `GET /gestiones?filtro=` siguen en `501`: son del día 6 (CU-09). Implementados en R-011.
- Fecha de seguimiento sugerida = el mayor entre vencimiento + 25 y hoy (el cronograma decía solo vencimiento + 25, que puede quedar en el pasado). La gestión es por ciclo de membresía: se ve en todas las listas que contienen ese ciclo.
- El Excel incluye las columnas "Gestión" y "Campaña", para seguir igual a la tabla; revierte el criterio de R-008 que las excluía. [03 §15 CU-12](03-casos-de-uso.md) se ajustó en R-010.
- Nombres de campaña repetidos permitidos; prioridad 1..999. En R-009 una campaña inactiva no se podía volver a activar: **cambiado en R-010** (ver abajo).
- Reinicio de la base principal ejecutado el 30-09-2026 con `scripts/reiniciar-base-historica.sh --si`, autorizado por el usuario ([DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md)).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Qué puede probar el usuario**
1. En http://localhost:8080 → Campañas: ver las 3 de ejemplo, crear una nueva (nombre, niveles, planes, prioridad), editarla e inactivarla.
2. Lista: generar una lista → columnas "Gestión" y "Campaña" → "Gestionar" un socio → elegir una campaña sugerida o "No asignar campaña", la fecha de seguimiento y el responsable → "Crear gestión" → registrar el resultado ("¿Renovó?" Sí o No cierra la gestión) → la fila muestra "Pendiente" o "Cerrada". (Crear campañas y gestiones guarda de verdad en la base.)
3. "Descargar Excel": incluye "Gestión" y "Campaña".
4. Para probar sin tocar los datos reales: stack aislado y E2E ([10-docker §Stack E2E aislado](docs/backend/10-docker.md), `Frontend/README.md`); para volver a solo histórico: [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md).

**Pendientes que pasan a los días siguientes**
- **Día 6:** alertas (CU-09), dashboard (CU-11), reentrenamiento (CU-02), acceso por IP (CU-00) y alerta de datos del mes (D6-BE-06 / D6-FE-04).
- **Día 7:** revisión de seguridad de lo hecho el día 5 (incluido R-010) y S23 (D7-OP-02); diseño visual (D7-FE-01).
- Menor: con datos simulados en el navegador (`VITE_API_MOCKS`), las gestiones creadas no se recuerdan (solo afecta a pruebas). No hay prueba automática de "sin f-strings en `0007`" ni de `alembic check` tras `0008` (queda a la revisión de código).

#### Arreglos posteriores al Día 5 (R-010)

A petición del usuario. **Estado:** `DONE` (15 tareas + documentación). Sin migración: el esquema sigue en `0008`.

- **Las campañas se pueden volver a activar:** `POST /api/v1/campanias/{id}/activar` (idempotente; no cambia `es_ejemplo`; la campaña vuelve a sugerirse) y botón "Activar" en las filas inactivas de la página Campañas, sin confirmación. Revierte la decisión (e) de R-009 → [ADR-009](adr/ADR-009-reactivar-campanias-y-gestion-sin-campania-cerrada.md), [API_CONTRACT](docs/API_CONTRACT.md).
- **"No asignar campaña" deja la gestión cerrada al crearla:** no se piden fecha de seguimiento ni responsable, no hay resultado que registrar (`PUT …/resultado` → `409`) y la fila muestra "Cerrada" / "Sin campaña" con "Ver gestión" como única acción; el Excel, los mismos textos. `fecha_seguimiento` pasa a opcional en `POST /gestiones` (obligatoria solo con campaña) → [ADR-009](adr/ADR-009-reactivar-campanias-y-gestion-sin-campania-cerrada.md), [09 §Retención](docs/backend/09-esquema-base-de-datos.md), [frontend/01](docs/frontend/01-arquitectura.md), [03 §11, §13](03-casos-de-uso.md).
- **La regla de la fecha de contacto no cambió** (entre el día en que se creó la gestión y hoy); ahora se explica en la ayuda y en [06 §7](06-como-funciona-la-lista.md).
- **Ayuda "¿Cómo funciona esta lista?":** secciones nuevas "Campañas" y "Gestionar a un socio" ([06 §7–§8](06-como-funciona-la-lista.md)).
- Documentación pendiente de R-009 cerrada: [03 §15 CU-12](03-casos-de-uso.md) ya dice que el Excel lleva "Gestión" y "Campaña".
- Pruebas: Backend 1.710 pytest; Frontend 597 Vitest; E2E 3/3 en el stack aislado 8081. Las gestiones pendientes sin campaña anteriores a R-010 no se migraron (solo pueden existir en el stack E2E).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Aviso para el día 6.** Desde R-010 una gestión `CERRADA` puede no tener resultado (gestión sin campaña: `renovo_declarado` y el resto de campos de resultado nulos, `fecha_seguimiento` sin significado). Las consultas de alertas (D6-BD-01, D6-BE-01) y del dashboard (D6-BE-02) deben **filtrar por `estado`** (las alertas cuentan solo `PENDIENTE`) y tratar `renovo_declarado` nulo como **"sin resultado"**, ni renovación ni no renovación; si no, inflarían las cifras.

---

### Día 6 · Alertas, dashboard, reentrenamiento y acceso (CU-09, CU-11, CU-02, CU-00)

**Base de datos**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D6-BD-01 | Consultas de lectura (SQLAlchemy Core con parámetros): contadores de alertas, embudo del mes y tabla por campaña. | A | D5-BD-01 | Pruebas de integración con datos conocidos. | Hecho (R-011 T2, T15) |
| D6-BD-02 | Repositorio de `intento_reentrenamiento`. | A | D1-BD-02 | Prueba de integración. | Hecho (R-011 T9) |

**Backend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D6-BE-01 | CU-09 · Endpoint de alertas: vencidos, hoy, próximos 7 días y la lista de cada categoría. | A | D6-BD-01 | Criterios de aceptación con reloj fijado. | Hecho (R-011 T1, T3, T4) |
| D6-BE-02 | CU-11 · Endpoint del dashboard: embudo, tabla por campaña (tasa desde 10 casos) y estado del modelo. | A | D6-BD-01 | Criterios de aceptación de CU-11. | Hecho (R-011 T16, T17) |
| D6-BE-03 | **TDD** · CU-02 · Servicio de reentrenamiento: criterios, conjunto de comparación de 3 meses, PR-AUC del candidato contra la del vigente, reentrenamiento completo, `OMITIDO` y cálculo de la próxima fecha. | A | D3-BE-02, D6-BD-02 | Pruebas de todos los flujos alternativos de CU-02 con reloj simulado. | Hecho (R-011 T5–T8) |
| D6-BE-04 | Planificador dentro del backend (revisa al arrancar y una vez al día si hoy es la fecha programada; si ya pasó, registra `OMITIDO`) y comando `python -m app.cli reentrenar`. | A | D6-BE-03 | Arranque con fecha pasada → `OMITIDO`; el comando crea v2 con datos sintéticos suficientes. | Hecho (R-011 T10, T11) |
| D6-BE-05 | CU-00 · Filtro de IP: lista en `.env` (por defecto `127.0.0.1`), IP tomada de la conexión, sin `X-Forwarded-For`, `/health` exento, `403` con el formato único de error. | A | — | Criterios de aceptación de CU-00. | Hecho (R-011 T12–T14) |
| D6-BE-06 | Exponer a Inicio (el endpoint lo decide el planner del día 6) si no hay ninguna carga (CU-01) con `fecha_carga` dentro del mes actual (fecha de negocio, reloj inyectable) (añadida por R-005). | A | D4-BE-04 | Pruebas con reloj fijo: con y sin carga en el mes. | Hecho (R-011 T18, T19) |

**Frontend**

| ID | Tarea | Resp. | Depende de | Hecho cuando | Estado |
|---|---|---|---|---|---|
| D6-FE-01 | Contadores de alertas en Inicio; al pulsar, lista de gestiones que abre el formulario. | B | D5-FE-02 | Prueba de los tres contadores y la navegación. | Hecho (R-011 T22–T25) |
| D6-FE-02 | Página Dashboard: filtro por mes, embudo (barras), tabla por campaña ("casos insuficientes" bajo 10) y tarjeta del estado del modelo. | B | D1-FE-03 | Pruebas con datos simulados. | Hecho (R-011 T26–T28) |
| D6-FE-03 | Página de acceso denegado para respuestas `403`. | B | D1-FE-02 | Prueba de render. | Hecho (R-011 T20, T21) |
| D6-FE-04 | Alerta en Inicio "Aún no se han cargado los datos de este mes" cuando D6-BE-06 lo indique (añadida por R-005). | B | D6-BE-06 | Prueba con respuesta simulada con y sin carga del mes. | Hecho (R-011 T22, T23) |
| D6-OP-01 | `Backend/README.md`: instalación en el PC, dónde poner los libros, comando manual de reentrenamiento y cómo hacer y restaurar un respaldo. | B | D6-BE-04 | Documento revisado por A. | Hecho (R-011 T30); revisión de A pendiente |

#### Avance y resumen del Día 6

**Estado:** cerrado · 13 de 13 tareas hechas en un solo requerimiento (R-011, `DONE`, 31 tareas de desarrollo + documentación). Sin migración: el esquema sigue en `0008`. Hito verificado: en el stack aislado (http://localhost:8081) alertas → Seguimiento → resultado → Dashboard funciona en el E2E, una IP no autorizada recibe `403` (y `/health` `200`), un `OMITIDO` forzado se registra una sola vez y el comando manual responde `CRITERIOS_NO_CUMPLIDOS` con código 0. El stack principal (http://localhost:8080) se reconstruyó y solo se consultó: `LISTO`, aviso de datos del mes visible (`datos_mes_cargados: false`), alertas 0/0/0, dashboard `200`, puerto 8000 → `403` salvo `/health`; base intacta (mismos conteos que tras R-010, 1 modelo, 1 intento de reentrenamiento: el inicial).

**Realizado**
- Alertas (CU-09): `GET /alertas` y `GET /gestiones?filtro=` (solo gestiones pendientes; "hoy" en Ecuador). En Inicio, bloque "Seguimientos pendientes" con Vencidos / Para hoy / Próximos 7 días, que lleva a la página Seguimiento; allí "Abrir gestión" abre la ventana de gestión → [API_CONTRACT §Alertas y dashboard](docs/API_CONTRACT.md#alertas-y-dashboard-cu-09-cu-11-r-011), [06 §9](06-como-funciona-la-lista.md).
- Datos del mes (D6-BE-06/D6-FE-04): `datos_mes_cargados` en `/sistema/estado` (solo cargas por plantilla); Inicio avisa "Aún no se han cargado los datos de este mes." con enlace "Ir a Carga".
- Dashboard (CU-11): `GET /dashboard?mes=` y página con filtro por mes, embudo (solo gestiones con campaña), tabla por campaña (tasa desde 10 cerradas con resultado; "Sin campaña" al final), tarjeta del modelo y aviso de que las cifras son observadas, no causales.
- Reentrenamiento (CU-02): servicio programado y manual, PR-AUC en el dominio, planificador en hilo (al arrancar y cada hora) y comando `docker compose exec backend python -m app.cli reentrenar` → [12 §Reentrenamiento](docs/backend/12-modelo-y-listas.md#reentrenamiento-cu-02-r-011), [ADR-011](adr/ADR-011-reglas-del-reentrenamiento.md).
- Acceso por IP (CU-00): middleware en el backend, red interna con IP fija del frontend, página "Acceso no permitido" → [10-docker §Red interna](docs/backend/10-docker.md), [ADR-010](adr/ADR-010-acceso-por-ip-detras-de-nginx.md).
- Operación: guía en `Backend/README.md` §Operación en el PC del gimnasio (instalación, libros, variables, reentrenamiento manual, respaldo y restauración).
- Pruebas: Backend 1.904 pytest, `ruff`, `format`, `mypy app`, `lint-imports` limpios; Frontend 665 Vitest, `lint`, `build`; E2E 4/4 en el stack aislado 8081.

**Desviaciones**
- El planificador revisa cada hora (el cronograma decía una vez al día) y solo actúa cuando cambia el día de negocio.
- Si se pierden varias fechas seguidas se registra un `OMITIDO` por cada una ([ADR-011](adr/ADR-011-reglas-del-reentrenamiento.md)); el manual solo mueve la próxima fecha si entrena.
- El criterio de D6-BE-04 "el comando crea v2 con datos sintéticos suficientes" se probó en la suite de integración; en el stack aislado el comando respondió `CRITERIOS_NO_CUMPLIDOS` (sin datos nuevos suficientes), como se esperaba.
- La tasa del dashboard exige 10 gestiones **cerradas con resultado** (Sí/No); las cerradas sin campaña no cuentan.
- Por el filtro de IP, el backend publicado en 8000/8001 solo atiende `/health`; todo se usa por 8080/8081. Abrir la app a otro PC no está implementado (exigiría filtrar también en nginx).
- No hubo revisión en el navegador del stack principal (extensión de Chrome no disponible); la verificación fue por API y E2E en el aislado.
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

**Qué puede probar el usuario**
1. En http://localhost:8080 → Inicio: aviso "Aún no se han cargado los datos de este mes" y "Seguimientos pendientes" con los tres contadores (en 0 mientras no haya gestiones pendientes).
2. Gestionar un socio con campaña y fecha de seguimiento hoy desde la Lista → el contador "Para hoy" sube → pulsarlo → "Abrir gestión" → registrar "¿Renovó?" → la fila desaparece. (Guarda de verdad en la base.)
3. Dashboard: elegir el mes y ver embudo, tabla por campaña y estado del modelo.
4. `curl http://localhost:8000/api/v1/sistema/estado` → `403`; por 8080 → `200`.
5. Reentrenamiento manual: `docker compose exec backend python -m app.cli reentrenar` (en la base real cambiaría el modelo si se cumplen los criterios; probar primero en el stack aislado).

**Aviso para el día 7**
- D7-OP-02: la revisión de seguridad única cubre R-007 a R-012; en R-011 conviene mirar en especial el middleware de IP (`403` en todas las rutas salvo `/health`, IP solo de la conexión), la red fija de compose, el comando `app.cli` (salida sin datos personales) y el hilo del planificador (logs solo con el tipo de excepción). S23 sigue abierto.
- D7-OP-04: el ensayo de CU-02 y CU-09 con reloj simulado se hace en el stack aislado; en el principal no se ejecuta `reentrenar` sin decisión del usuario.
- D6-OP-01 queda pendiente de revisión por A; D7-BD-01 (script de respaldo) sigue pendiente: la guía actual usa `pg_dump`/`pg_restore` a mano.
- D7-OP-03 puede partir del E2E `alertas-dashboard` ya existente.

#### Arreglos posteriores al Día 6 (R-012)

A petición del usuario. **Estado:** `DONE` (12 tareas + documentación). Solo frontend: sin cambios de backend, API ni esquema (sigue en `0008`).

- **La ventana de gestión se cierra al guardar** (Lista y Seguimiento): al crear con éxito (con o sin campaña) y al registrar el resultado, la ventana se cierra y la lista se recarga; con error queda abierta con el mensaje. El resultado se anota después con "Registrar resultado" de la fila → [06 §7](06-como-funciona-la-lista.md), [03 §11, §13](03-casos-de-uso.md), [frontend/01](docs/frontend/01-arquitectura.md).
- **Ayudas nuevas:** "¿Cómo funciona el inicio?" y "¿Cómo funciona el dashboard?", con el componente compartido `shared/ui/Ayuda.tsx` (también lo usa la ayuda de la lista) → [06 §9–§10](06-como-funciona-la-lista.md).
- **Dashboard:** "Resultados de <mes en palabras>", embudo en barras con número y % sobre asignadas, dona "Resultado de las gestiones del mes" (Renovaron / No renovaron / Sin resultado), tablas equivalentes accesibles; SVG/CSS propios con tokens (`--color-brand`), sin librerías nuevas → [03 §14](03-casos-de-uso.md).
- **Imprimir / Guardar PDF** del dashboard con la impresión del navegador; RN-11.2 precisada → [03 §14](03-casos-de-uso.md).
- Pruebas: Frontend 742 Vitest, `lint` y `build` limpios; E2E 4/4 en el stack aislado 8081. Stack principal reconstruido y verificado solo leyendo; sin revisión en el navegador (extensión de Chrome sin conectar).
- Revisión de seguridad no ejecutada: diferida a la revisión única del día 7 (§1).

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
