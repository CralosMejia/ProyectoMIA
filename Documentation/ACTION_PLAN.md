# ACTION PLAN — board vivo

> Board corto. El detalle por producto va en `Documentation/products/P##-*.md` (aún no existe ninguno).
> Estados de tarea: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[!]` bloqueada.

## ACTIVO

_(vacío — siguiente: Día 2, ver PRÓXIMO)_

## TERMINADOS RECIENTEMENTE

### R-002 — Día 1 del cronograma (Cimientos): esquema completo con Alembic y servicio `migrate`, contrato de la API en `501`, dominio común y esqueleto del frontend con MSW · **DONE** 2026-09-28

**Cierre:** security **diferida** a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)) · tests `pass` (Backend 391 pytest, ruff, format, mypy, lint-imports 7 contratos; Frontend 242 Vitest, build, lint 0 avisos; E2E 1/1; stack real verificado). Docs: `docs/backend/09-esquema-base-de-datos.md` (nuevo), `docs/backend/10-docker.md`, `docs/backend/01-arquitectura.md`, `docs/API_CONTRACT.md`, `docs/frontend/01-arquitectura.md`, `Backend/README.md`, `Frontend/README.md`, `README.md` (índice), `05-cronograma-semana.md` (avance y resumen del Día 1).

**Pendientes que pasan a otros días:** `membresias.socio_id` NULL o NOT NULL → día 2 · riesgo pandas 3.x al portar el notebook → día 2 · S23 rol de BD sin superusuario → día 7 · revisión de seguridad de R-002 → día 7 (D7-OP-02) · verificación manual de "[MSW] Mocking enabled" · handler MSW de `GET /gestiones` sin filtro devuelve `[]` (backend: `400`) · errores de `mypy` previos a R-002 en `tests/integration/api/test_error_handlers.py` ~230-233.

**Objetivo:** al cerrar, `docker compose up` crea las tablas antes del backend, `/openapi.json` muestra todos los endpoints de la semana con ejemplos, y el frontend navega entre 5 páginas con la API simulada por MSW.

**Fuente:** [05 §3 Día 1](05-cronograma-semana.md) (D1-OP-01..04, D1-BD-01..04, D1-BE-01..03, D1-FE-01..03) · entidades de [03 §16](03-casos-de-uso.md) · catálogos de 03 CU-01, CU-06, CU-10, CU-11 · [04 §2, §5](04-pendientes-para-iniciar-desarrollo.md).

**Notas de alcance del planner**
- No existe `products/P##-*.md` ni `DEVELOPMENT_GUIDELINES.md` (lo crea DOC-2). El alcance se validó contra [03 §20](03-casos-de-uso.md): nada de este requerimiento cae fuera. **Fuera de R-002:** lógica real de cualquier endpoint (todos responden `501`), CU-00 (middleware de IP, día 6), repositorios, lectores de Excel, entrenamiento, rol de BD sin superusuario (S23, se revisa el día 7).
- **Sin login (RT-12):** la regla "propietario desde el token" y `user_id` de `database.md` **no aplican** (decisión del usuario, 04 §5.2). Las pruebas de aislamiento entre usuarios no aplican; cada test de contrato lo deja escrito en un comentario.
- **Nombres de tabla en plural** (`database.md` §Convenciones) aunque 03 §16 use singular: `socios`, `cargas`, `membresias`, `modelos`, `intentos_reentrenamiento`, `estado_sistema` (fila única), `listas_priorizadas`, `predicciones`, `campanias`, `gestiones_retencion`. Son **10** entidades (05 dice "11" por error de conteo).
- **Convenciones comunes de tablas:** PK `BIGINT GENERATED ALWAYS AS IDENTITY` (salvo `estado_sistema.id SMALLINT` con `CHECK (id = 1)`); `created_at`/`updated_at TIMESTAMPTZ NOT NULL`; fechas de calendario (`fecha_inicio`, `fecha_vencimiento`, `fecha_seguimiento`…) como `DATE`, instantes como `TIMESTAMPTZ`; montos `NUMERIC(19,4)` con `CHECK >= 0`; probabilidades (`score`, `prevalencia`, `umbral_*`, `pr_auc_*`) `NUMERIC(10,8)` con `CHECK` entre 0 y 1; semiestructurados `JSONB`; FKs `ON DELETE RESTRICT`; estados con `CHECK ... IN (...)` generado desde los enums del dominio; naming convention de constraints fijada en el `MetaData`.
- **`deleted_at`** en `socios`, `cargas`, `membresias`, `campanias`, `gestiones_retencion`. **Excepción documentada** (sin `deleted_at`): `modelos`, `listas_priorizadas`, `predicciones` (instantáneas inmutables, RT-07), `intentos_reentrenamiento` (auditoría append-only) y `estado_sistema` (fila única de control). DOC-4 la documenta.
- `membresias.socio_id` admite `NULL` (registros históricos sin identidad utilizable; la decisión final es del día 2). `socios.cedula VARCHAR(20)` (D-14: pasaporte hasta 20).
- Las migraciones Alembic no tienen `Clock`: `0002` usa `CURRENT_TIMESTAMP` en SQL para `created_at`/`updated_at` (excepción documentada).
- Excepción al límite de 4 archivos: los `__init__.py` vacíos y las páginas placeholder de T19 (par `routes.tsx` + `*Page.tsx` sin lógica por feature).
- D1-OP-02/03/04 son de documentación: los hace **doc-agent** (DOC-1..3), no el developer. DOC-1 edita `.claude/CLAUDE.md` (configuración de agentes): requiere aprobación explícita del usuario por el sistema de permisos.

**Tareas**

- [x] **T1** · `infra-deploy` · D1-OP-01 · Ignorar los libros históricos
  - Archivos: `.gitignore` (principal).
  - Docs: `Documentation/04-pendientes-para-iniciar-desarrollo.md` §4.1; `.claude/rules/git.md` §Secretos.
  - Aceptación:
    - Añade la línea explícita `plantillas/Control Gym*.xlsx` (se mantiene aunque `/plantillas` se quite más adelante).
    - `git check-ignore -v "plantillas/Control Gym 2025 (1).xlsx"` y `"plantillas/Control Gym 2026 (2).xlsx"` → ambos coinciden (código 0).
    - `git status --short` no lista ningún `Control Gym*.xlsx`.
  - Pruebas: verificación por comandos.

- [x] **T2** · `infra-deploy` · D1-BE-01 · Dependencias de datos y ML con versiones fijadas
  - Archivos: `Backend/pyproject.toml` (principal).
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas; `.claude/rules/backend.md` §Comandos.
  - Aceptación:
    - `dependencies` añade con `==`: `pandas`, `numpy`, `scikit-learn`, `openpyxl`, `joblib`, `alembic`, `python-multipart` (versiones estables compatibles con Python 3.12; el notebook corrió con Python 3.11.15 y **no** registra versiones de librerías: se anota en DOC-4).
    - `[tool.mypy]` añade overrides `ignore_missing_imports = true` **solo** para `sklearn.*` y `joblib.*`, con comentario de justificación.
    - En venv limpio: `pip install -e ".[dev]"` → código 0; `ruff check .`, `mypy app`, `lint-imports` y `pytest tests/unit` siguen en verde.
    - `docker build -t backend:dev Backend` → código 0; `docker run --rm --entrypoint python backend:dev -c "import pandas, numpy, sklearn, openpyxl, joblib, alembic, multipart"` → código 0.
  - Pruebas: verificación por comandos (sin suite nueva).

- [x] **T3** · `domain` · D1-BE-03 · Enums del dominio común y puerto `PredictorModel`
  - Archivos: `Backend/app/domain/common/enums.py` (principal), `Backend/app/domain/common/predictor.py`, `Backend/tests/unit/domain/common/test_enums.py`, `Backend/tests/unit/domain/common/test_predictor_port.py`.
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas; `Documentation/03-casos-de-uso.md` §4 (tabla de columnas), §9, §13, §16; `Documentation/04-pendientes-para-iniciar-desarrollo.md` §5.4 y §5.7.
  - Aceptación (TDD, test primero):
    - `StrEnum` con estos valores exactos: `Plan` {MENSUAL, TRIMESTRAL, SEMESTRAL, ANUAL, DIARIO, OTRO}; `FormaPago` {EFECTIVO, TRANSFERENCIA, TARJETA_DATAFAST, OTRO, SIN_DATO}; `EstadoCiclo` {EVALUABLE, PENDIENTE, EXCLUIDO}; `NivelRiesgo` {ALTO, MEDIO, BAJO}; `EstadoGestion` {PENDIENTE, CERRADA}; `OrigenMembresia` {HISTORICO, PLANTILLA}; además `EstadoRegistro` {NUEVO, RENOVACION, CONGELAMIENTO, REINGRESO, BAJA}; `TipoCarga` {MIGRACION_HISTORICA, PLANTILLA}; `EstadoMigracion` {PENDIENTE, EN_CURSO, COMPLETADA}; `DisparadorReentrenamiento` {PROGRAMADO, MANUAL, INICIAL}; `ResultadoReentrenamiento` {ENTRENADO, CRITERIOS_NO_CUMPLIDOS, NO_SUPERA_VIGENTE, OMITIDO, FALLIDO}; `Respuesta` {SI, NO, PENDIENTE, NO_APLICA}.
    - Constantes de subconjunto: `PLANES_CAMPANIA` = Plan sin DIARIO; `RESPUESTAS_OFRECIMIENTO` = {SI, NO, NO_APLICA}; `RESPUESTAS_ACEPTACION` = {SI, NO, PENDIENTE, NO_APLICA}; `RESPUESTAS_RENOVACION` = {SI, NO, PENDIENTE}.
    - `Plan("MENSUAL") is Plan.MENSUAL`; `Plan("mensual")` → `ValueError`; `{p.value for p in Plan}` coincide exactamente con el conjunto esperado (un test por enum).
    - `predictor.py`: `PredictorModel` (`typing.Protocol`, `@runtime_checkable`) con `train(features: Sequence[Mapping[str, float | int | str | None]], labels: Sequence[int]) -> TrainedModel` y `predict(artefacto: bytes, features: Sequence[Mapping[...]]) -> list[Prediction]`; `TrainedModel(artefacto: bytes, metadata_tecnica: Mapping[str, str])` y `Prediction(score: float, factores_principales: tuple[str, ...])` como `@dataclass(frozen=True, slots=True)`. Docstring: `float` permitido aquí porque son probabilidades del modelo, no valores exactos (04 §5.7).
    - Un doble mínimo en el test satisface `isinstance(doble, PredictorModel)` y `mypy` lo acepta como `PredictorModel`; un objeto sin `predict` → `isinstance` `False`.
    - El dominio solo importa librería estándar: `lint-imports` y `mypy app` en verde; `grep -r "pandas\|sklearn\|numpy" app/domain` = 0.
  - Pruebas: unitarias.

- [x] **T4** · `infra` · D1-BD-01 (1/2) · Base ORM y tablas del historial (`socios`, `cargas`, `membresias`)
  - Archivos: `Backend/app/infrastructure/persistence/models/base.py` (principal: `Base(DeclarativeBase)` con `MetaData(naming_convention=...)`, mixin de `id`/`created_at`/`updated_at`, mixin `deleted_at`, helper `check_in(columna, enum_o_valores)`), `Backend/app/infrastructure/persistence/models/historial.py`, `Backend/app/infrastructure/persistence/models/__init__.py` (exporta `Base` y los modelos), `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`.
  - Docs: `.claude/rules/database.md` §Convenciones de esquema, §Reparto de herramientas; `Documentation/03-casos-de-uso.md` §16.
  - Aceptación (unitarias sobre `Base.metadata`, sin BD):
    - `socios`: `cedula VARCHAR(20) NULL` con índice único parcial `WHERE cedula IS NOT NULL AND deleted_at IS NULL`; `nombre`, `nombre_normalizado` `TEXT NOT NULL`; `celular`, `correo` `TEXT NULL`; índice en `nombre_normalizado`.
    - `cargas`: `tipo` con `CHECK` de `TipoCarga`; `fecha_carga TIMESTAMPTZ`; conteos `INTEGER NOT NULL CHECK >= 0`; índice único parcial `(tipo) WHERE tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL`.
    - `membresias`: FKs `socio_id` (NULL) y `carga_id` (NOT NULL) `ON DELETE RESTRICT`; `plan` y `forma_pago` `NOT NULL` con `CHECK` de sus enums; `estado_registro` NULL con `CHECK`; `origen` con `CHECK`; `fecha_inicio`/`fecha_vencimiento` `DATE NULL`; `monto_facturado`/`monto_cobrado` `NUMERIC(19,4) NULL CHECK >= 0`; `asistencias INTEGER NULL CHECK 0..400`; `referencia_origen JSONB NULL`; `plan_original`/`forma_pago_original` `TEXT NULL`; `inicio_aproximado BOOLEAN NOT NULL`; índice de consulta `(socio_id, fecha_vencimiento)` y `(fecha_vencimiento)`.
    - Test: ninguna columna de `Base.metadata` es `Float`/`REAL`/`DOUBLE`; toda columna `DateTime` tiene `timezone=True`; las 3 tablas tienen `deleted_at`; los valores de cada `CHECK` salen del enum (cambiar el enum cambia el `CHECK`).
    - `mypy app` (SQLAlchemy 2 `Mapped[...]`) y `lint-imports` en verde; `infrastructure` importa `domain.common.enums`, nunca al revés.
  - Pruebas: unitarias.

- [x] **T5** · `infra` · D1-BD-01 (2/2) · Tablas de modelo y retención
  - Archivos: `Backend/app/infrastructure/persistence/models/modelo.py` (principal: `modelos`, `intentos_reentrenamiento`, `estado_sistema`), `Backend/app/infrastructure/persistence/models/retencion.py` (`listas_priorizadas`, `predicciones`, `campanias`, `gestiones_retencion`), `Backend/app/infrastructure/persistence/models/__init__.py`, `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`.
  - Docs: `.claude/rules/database.md` §Convenciones de esquema; `Documentation/03-casos-de-uso.md` §9, §11, §13, §16.
  - Aceptación (unitarias sobre `Base.metadata`):
    - `modelos`: `version INTEGER UNIQUE NOT NULL`, `vigente BOOLEAN NOT NULL`, índice único parcial `(vigente) WHERE vigente` (un solo vigente), `artefacto BYTEA NOT NULL`, `metadata_tecnica` y `porcentajes_umbral` `JSONB NOT NULL`, `periodo_desde`/`periodo_hasta DATE`, probabilidades `NUMERIC(10,8)`.
    - `intentos_reentrenamiento`: `disparador` y `resultado` con `CHECK`; `modelo_id` FK NULL; `fecha TIMESTAMPTZ NOT NULL`; `fecha_programada DATE NULL`.
    - `estado_sistema`: `id SMALLINT` PK con `CHECK (id = 1)`; `migracion_historica NOT NULL` con `CHECK` de `EstadoMigracion`; `proxima_fecha_reentrenamiento DATE NULL`.
    - `listas_priorizadas`: `modelo_id` FK NOT NULL; `fecha_generacion DATE`; `horizonte_dias` y `top_k` `INTEGER CHECK > 0`; `creada_en TIMESTAMPTZ`.
    - `predicciones`: FKs `lista_id`, `membresia_id` NOT NULL y `socio_id` NULL; `score NUMERIC(10,8) CHECK 0..1`; `nivel_riesgo` con `CHECK`; `factores_principales JSONB`; `prioridad INTEGER CHECK > 0`; `dentro_top_k BOOLEAN`; único `(lista_id, membresia_id)`; índice `(lista_id, prioridad)`.
    - `campanias`: `niveles_riesgo TEXT[]` y `planes TEXT[]` no vacíos con `CHECK` de subconjunto (`<@`) de `NivelRiesgo` y `PLANES_CAMPANIA`; `prioridad INTEGER CHECK >= 1`; `activa`, `es_ejemplo` `BOOLEAN NOT NULL`; `deleted_at`.
    - `gestiones_retencion`: FKs `prediccion_id`, `membresia_id` NOT NULL, `campania_id` NULL; índice único parcial `(membresia_id) WHERE deleted_at IS NULL` (RN-08.1); `estado` con `CHECK` de `EstadoGestion`; `campania_ofrecida`/`campania_aceptada`/`renovo_declarado` NULL con `CHECK` de `RESPUESTAS_*`; `contactado BOOLEAN NULL`; `fecha_asignacion`/`fecha_seguimiento`/`fecha_contacto DATE`; `cerrada_en TIMESTAMPTZ NULL`; índice `(estado, fecha_seguimiento)`; `deleted_at`.
    - Test: `Base.metadata.tables` contiene exactamente las 10 tablas; `deleted_at` existe en las 5 del listado y **no** en las 5 de la excepción; ninguna FK tiene `ondelete="CASCADE"`.
  - Pruebas: unitarias.

- [x] **T6** · `db` · D1-BD-02 (1/2) · Configuración de Alembic
  - Archivos: `Backend/alembic.ini` (principal: `script_location = %(here)s/alembic`, sin `sqlalchemy.url`), `Backend/alembic/env.py` (URL solo desde `DATABASE_URL` del entorno; `target_metadata = Base.metadata`; `compare_type=True`; error claro sin valores si falta), `Backend/alembic/script.py.mako`.
  - Docs: `.claude/rules/database.md` §Migraciones; `Documentation/docs/backend/10-docker.md` §Variables.
  - Aceptación:
    - Sin `DATABASE_URL` → `alembic current` sale con código ≠ 0 y el mensaje nombra la variable sin mostrar ningún valor.
    - Con `DATABASE_URL` de la BD del compose → `alembic current` sale con código 0.
    - `alembic.ini` no contiene URL ni credenciales (`grep -i "postgresql" alembic.ini` = 0).
    - `ruff check .` en verde (incluye `alembic/`).
  - Pruebas: verificación por comandos (la integración va en T7).

- [x] **T7** · `db` · D1-BD-02 (2/2) · Migración `0001` con todas las tablas, restricciones e índices
  - Archivos: `Backend/alembic/versions/0001_esquema_inicial.py` (principal), `Backend/tests/integration/persistence/test_migrations.py`, `Backend/tests/integration/conftest.py` (fixture `migrated_engine` y guarda de BD de pruebas), `.env.example` (`TEST_DATABASE_URL` → base `app_db_test`).
  - Docs: `.claude/rules/database.md` §Migraciones, §Pruebas.
  - Aceptación (integración contra PostgreSQL 16 del compose, nunca SQLite):
    - `revision = "0001"`, `down_revision = None`; autogenerado revisado a mano; `downgrade()` elimina todo lo creado.
    - Guarda: la fixture **aborta** si el nombre de la base de `TEST_DATABASE_URL` no termina en `_test` (evita borrar la base de desarrollo); crea la base de pruebas si no existe (conexión `AUTOCOMMIT` a la base `postgres`).
    - `alembic upgrade head` → existen las 10 tablas; `alembic check` no detecta diferencias entre `Base.metadata` y la base.
    - Insertar `membresias.plan = 'SEMANAL'` → `IntegrityError` (CHECK). Dos `socios` con la misma `cedula` → `IntegrityError`; dos con `cedula NULL` → OK; el segundo con la misma cédula pero el primero con `deleted_at` → OK.
    - Segunda `carga` `MIGRACION_HISTORICA` → `IntegrityError`; segundo `modelos.vigente = true` → `IntegrityError`; segunda `gestiones_retencion` para la misma `membresia_id` → `IntegrityError`; `campanias.planes = '{DIARIO}'` → `IntegrityError`; `monto_cobrado = -1` → `IntegrityError`.
    - `alembic downgrade base` → solo queda `alembic_version` (sin tablas de negocio); `upgrade head` de nuevo funciona (idempotencia del ciclo).
    - Cada prueba deja la base como la encontró (transacción con rollback; el ciclo upgrade/downgrade al final termina en `base`).
  - Pruebas: integración.

- [x] **T8** · `db` · D1-BD-04 · Migración de datos `0002`: fila única de `estado_sistema`
  - Archivos: `Backend/alembic/versions/0002_estado_sistema_inicial.py` (principal), `Backend/tests/integration/persistence/test_migrations.py`.
  - Docs: `.claude/rules/database.md` §Migraciones.
  - Aceptación:
    - `down_revision = "0001"`; `upgrade()` inserta `id = 1, migracion_historica = 'PENDIENTE', proxima_fecha_reentrenamiento = NULL` con `created_at`/`updated_at = CURRENT_TIMESTAMP`, de forma idempotente (`ON CONFLICT (id) DO NOTHING`); SQL con `sa.text`, sin interpolar.
    - Tras `upgrade head` → `SELECT count(*) FROM estado_sistema` = 1 y `migracion_historica = 'PENDIENTE'`.
    - Insertar una segunda fila con `id = 2` → `IntegrityError`.
    - `downgrade` a `0001` borra solo esa fila (tabla vacía, tabla presente); `upgrade head` otra vez → 1 fila.
  - Pruebas: integración.

- [x] **T9** · `infra-deploy` · D1-BD-03 · Servicio `migrate` en Compose y volumen de libros históricos
  - Archivos: `compose.yaml` (principal), `Backend/Dockerfile` (copia `alembic.ini` y `alembic/` a `/srv`), `.env.example` (`HISTORICO_DIR` con valor marcador), `Backend/.dockerignore` (verifica que no excluye `alembic/`).
  - Docs: `Documentation/docs/backend/10-docker.md` §Servicios, §Variables, §Imagen del Backend; `.claude/rules/deploy.md` §Contenedores, §Configuración y secretos.
  - Aceptación:
    - Servicio `migrate`: misma imagen `backend:dev`, `command: ["alembic", "upgrade", "head"]`, `restart: "no"`, `healthcheck: disable: true`, `depends_on: db: condition: service_healthy`, `DATABASE_URL` desde `.env`, sin puertos publicados.
    - `backend.depends_on` incluye `migrate: condition: service_completed_successfully`; el backend **no** ejecuta migraciones (`grep -r "alembic\|create_all" Backend/app` = 0).
    - `backend` monta `${HISTORICO_DIR:?defina HISTORICO_DIR en .env}:/data/historico:ro`; escribir en `/data/historico` desde el contenedor falla (`touch` → "Read-only file system").
    - `docker compose down -v && docker compose up -d --build` → `migrate` sale con código 0 **antes** de que arranque `backend`; `docker compose exec db psql ... -c "\dt"` lista las 10 tablas y `estado_sistema` tiene 1 fila `PENDIENTE`; `backend` y `frontend` quedan `healthy`; `curl http://localhost:8000/api/v1/health` → `200`.
    - Un segundo `docker compose up -d` con la base ya migrada → `migrate` vuelve a terminar con 0 (sin cambios).
    - `compose.yaml` sigue sin contraseñas literales.
  - Pruebas: verificación de stack por comandos.

- [x] **T10** · `api` · D1-BE-02 (base) · Respuesta `501` y catálogo de respuestas de error para OpenAPI
  - Archivos: `Backend/app/api/openapi.py` (principal: `error_responses(*codes) -> dict[int, dict]` con `model` de error y **ejemplo** por código 400/403/404/409/413/422/501; `raise_not_implemented() -> NoReturn`), `Backend/app/api/errors.py` (añade `501 → ("not_implemented", "Esta funcion aun no esta disponible.")`, `413 → ("payload_too_large", ...)` y cambia el mensaje de `403` a uno sin referencia a sesión: "El acceso no esta permitido desde este equipo."), `Backend/tests/integration/api/test_error_handlers.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md` §Formato único de error; `.claude/rules/backend.md` §API.
  - Aceptación:
    - Ruta de prueba que llama `raise_not_implemented()` → `501` `{"error":{"code":"not_implemented","message":"Esta funcion aun no esta disponible."}}`.
    - `error_responses(400, 501)` produce entradas con `content.application/json.example` en el formato único de error.
    - Pruebas existentes de `test_error_handlers.py` siguen en verde (ajustando solo la del mensaje de `403` si la hubiera).
  - Pruebas: integración.

- [x] **T11** · `api` · D1-BE-02 · Contrato `sistema`
  - Archivos: `Backend/app/api/routers/sistema.py` (principal), `Backend/app/application/sistema/dtos.py`, `Backend/app/main.py` (incluye el router bajo `/api/v1`), `Backend/tests/integration/api/test_contract_sistema.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md` §Endpoints; `Documentation/03-casos-de-uso.md` §6 (CU-03, "Inicializando"), §14 punto 3.
  - Aceptación:
    - `GET /api/v1/sistema/estado` → `response_model=EstadoSistemaDTO` {`estado`: `"INICIALIZANDO"|"FALTAN_DATOS_HISTORICOS"|"LISTO"`, `migracion_historica`: `EstadoMigracion`, `modelo_vigente`: {`version`, `fecha_entrenamiento`, `ciclos_entrenamiento`} | null, `ultima_carga_en`: datetime | null, `proxima_fecha_reentrenamiento`: date | null}; `responses` con `200` (ejemplo) y `error_responses(403, 501)`.
    - Llamada real → `501` con `code = "not_implemented"`.
    - `/openapi.json` contiene la ruta con ejemplo en `200`, `403` y `501`, y el schema `EstadoSistemaDTO`.
    - El router no importa `app.infrastructure` (`lint-imports` en verde). Comentario en el test: aislamiento entre usuarios no aplica (sin login, RT-12).
  - Pruebas: integración.

- [x] **T12** · `api` · D1-BE-02 · Contrato `cargas` (CU-01)
  - Archivos: `Backend/app/api/routers/cargas.py` (principal), `Backend/app/application/cargas/dtos.py`, `Backend/app/main.py`, `Backend/tests/integration/api/test_contract_cargas.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §4.
  - Aceptación:
    - `POST /api/v1/cargas/vista-previa` (multipart, campo `archivo: UploadFile`) → `200` `VistaPreviaCargaDTO` {`filas_leidas`, `filas_validas`, `filas_con_error`, `filas_duplicadas`, `vencimiento_desde`, `vencimiento_hasta`, `errores`: [{`fila`, `columna`, `motivo`}], `puede_confirmar`}; errores documentados `400` (no `.xlsx`, sin hoja `Registros`, títulos, > 500 filas), `409` (migración histórica no completada), `413`, `403`, `501`.
    - `POST /api/v1/cargas` (multipart `archivo`, re-valida en servidor; sin estado entre vista previa y confirmación) → `201` `CargaDTO` {`id`, `fecha_carga`, `nombre_archivo`, `filas_leidas`, `filas_guardadas`, `filas_duplicadas`, `socios_enlazados`, `avisos_enlace`: [str]}; errores `400`, `409`, `413`, `422` (el archivo tiene filas con error), `403`, `501`.
    - Sin campo `archivo` → `400 validation_error`; con un archivo cualquiera → `501`.
    - `/openapi.json` muestra ambos con ejemplos de cada respuesta.
  - Pruebas: integración.

- [x] **T13** · `api` · D1-BE-02 · Contrato `listas` y Excel (CU-04, CU-05, CU-12)
  - Archivos: `Backend/app/api/routers/listas.py` (principal), `Backend/app/application/listas/dtos.py`, `Backend/app/main.py`, `Backend/tests/integration/api/test_contract_listas.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §7, §8, §15.
  - Aceptación:
    - `POST /api/v1/listas` body `GenerarListaDTO` {`fecha_referencia`: date | null (null = hoy del reloj), `horizonte_dias`: int 1..365 = 30, `top_k`: int ≥ 1 = 25} con ejemplo → `201` `ListaPriorizadaDTO` {`id`, `modelo_version`, `fecha_generacion`, `horizonte_dias`, `top_k`, `umbral_alto`, `umbral_medio`, `advertencia_datos_antiguos`: bool, `items`: [`PrediccionDTO` {`prediccion_id`, `prioridad`, `socio_nombre`, `celular`, `correo`, `plan`, `fecha_vencimiento`, `dias_para_vencer`, `score` (decimal como string), `nivel_riesgo`, `factores_principales`: [str], `dentro_top_k`, `gestion_estado` | null, `campania_asignada` | null}]}; errores `400`, `409` (sistema no listo / sin modelo vigente), `403`, `501`.
    - `GET /api/v1/listas/ultima` → `200` `ListaPriorizadaDTO` | `404`; `GET /api/v1/listas/{lista_id}` → `200` | `404`; `GET /api/v1/listas/{lista_id}/excel` → `200` con `content` `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` documentado | `404`. Todos con `403` y `501`.
    - `top_k = 0` → `400 validation_error`; `lista_id = "abc"` → `400`; entradas válidas → `501`.
  - Pruebas: integración.

- [x] **T14** · `api` · D1-BE-02 · Contrato `campanias` y sugerencias (CU-06, CU-07)
  - Archivos: `Backend/app/api/routers/campanias.py` (principal), `Backend/app/application/campanias/dtos.py`, `Backend/app/main.py`, `Backend/tests/integration/api/test_contract_campanias.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §9, §10.
  - Aceptación:
    - `GET /api/v1/campanias` → `200` [`CampaniaDTO` {`id`, `nombre`, `descripcion`, `activa`, `niveles_riesgo`: [NivelRiesgo], `planes`: [Plan sin DIARIO], `prioridad`, `es_ejemplo`}].
    - `POST /api/v1/campanias` body `CampaniaEntradaDTO` (`nombre` 1..120, `niveles_riesgo` y `planes` listas no vacías de los catálogos, `prioridad ≥ 1`) → `201`; `PUT /api/v1/campanias/{campania_id}` → `200` | `404`; `POST /api/v1/campanias/{campania_id}/inactivar` → `200` | `404` (no existe `DELETE`).
    - `GET /api/v1/predicciones/{prediccion_id}/campanias-sugeridas` → `200` [`CampaniaDTO`] ordenadas por prioridad | `404`.
    - `planes = ["DIARIO"]` o `niveles_riesgo = []` → `400 validation_error`; entradas válidas → `501`. Todos documentan `403` y `501` con ejemplos.
  - Pruebas: integración.

- [x] **T15** · `api` · D1-BE-02 · Contrato `gestiones` y alertas (CU-08, CU-09, CU-10)
  - Archivos: `Backend/app/api/routers/gestiones.py` (principal), `Backend/app/application/gestiones/dtos.py`, `Backend/app/main.py`, `Backend/tests/integration/api/test_contract_gestiones.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §11, §12, §13.
  - Aceptación:
    - `POST /api/v1/gestiones` body {`prediccion_id`, `campania_id` | null, `fecha_seguimiento`: date, `responsable`: str ≤ 120 | null} → `201` `GestionDTO`; errores `400`, `404` (predicción o campaña), `409` (ya existe gestión para el ciclo), `422` (fecha fuera de hoy..vencimiento+30), `403`, `501`.
    - `GET /api/v1/gestiones/{gestion_id}` → `200` | `404`. `PUT /api/v1/gestiones/{gestion_id}/resultado` body {`contactado`: bool, `campania_ofrecida`: SI/NO/NO_APLICA, `campania_aceptada`: SI/NO/PENDIENTE/NO_APLICA, `renovo_declarado`: SI/NO/PENDIENTE, `fecha_contacto`: date | null, `observaciones` ≤ 500 | null, `responsable` | null, `fecha_seguimiento` | null} → `200` | `404` | `409` (gestión cerrada) | `422`.
    - `GET /api/v1/gestiones?filtro=vencidas|hoy|proximas` → `200` [`GestionResumenDTO`]; `filtro` fuera de la lista blanca → `400`.
    - `GET /api/v1/alertas` → `200` `AlertasDTO` {`vencidas`, `hoy`, `proximos_7_dias`} (enteros ≥ 0).
    - `campania_ofrecida = "PENDIENTE"` → `400`; entradas válidas → `501`. Todos con ejemplos, `403` y `501`.
  - Pruebas: integración.

- [x] **T16** · `api` · D1-BE-02 · Contrato `dashboard` (CU-11)
  - Archivos: `Backend/app/api/routers/dashboard.py` (principal), `Backend/app/application/dashboard/dtos.py`, `Backend/app/main.py`, `Backend/tests/integration/api/test_contract_dashboard.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §14.
  - Aceptación:
    - `GET /api/v1/dashboard?mes=YYYY-MM` (opcional; por defecto mes actual del reloj) → `200` `DashboardDTO` {`mes`, `embudo`: {`asignadas`, `contactadas`, `ofrecidas`, `aceptadas`, `renovaron`}, `por_campania`: [{`campania_id` | null, `nombre`, `gestiones`, `contactados`, `renovaciones`, `gestiones_cerradas`, `tasa_renovacion`: decimal string | null, `casos_insuficientes`: bool}], `estado_modelo`: {`version`, `fecha_entrenamiento`, `ciclos_entrenamiento`, `proxima_fecha_reentrenamiento`, `ciclos_nuevos_evaluables`} | null}.
    - `mes=2026-13` o `mes=abc` → `400 validation_error`; válido o ausente → `501`.
    - Test final del contrato: `/openapi.json` contiene **las 18 operaciones** de T11–T16 (sistema 1, cargas 2, listas 4, campañas 5, gestiones/alertas 5, dashboard 1) más `GET /api/v1/health`, y cada operación de negocio declara ejemplo en su respuesta de éxito y en `501`.
  - Pruebas: integración.

- [x] **T17** · `frontend` · D1-FE-01 (1/2) · Layout con navegación y router anidado
  - Archivos: `Frontend/src/core/layout/AppLayout.tsx` (principal: `<header>` + `<nav>` con `NavLink` a Inicio `/`, Carga `/carga`, Lista `/lista`, Campañas `/campanias`, Dashboard `/dashboard`; `<main>` con `<Outlet/>` y `Suspense`), `Frontend/src/app/router.tsx` (ruta raíz con `AppLayout` y rutas hijas de cada feature; `health` pasa a `/salud`), `Frontend/src/features/health/routes.tsx`, `Frontend/src/core/layout/AppLayout.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura, §Feature `health`; `.claude/rules/frontend.md` §Estructura.
  - Aceptación:
    - Render con `createMemoryRouter` → `navigation` con 5 enlaces con esos textos; el enlace de la ruta actual tiene `aria-current="page"`.
    - Clic en "Campañas" → la URL pasa a `/campanias` y el `<main>` muestra el contenido de esa ruta.
    - `/salud` renderiza `HealthPage` (sus pruebas siguen en verde); `Frontend/e2e/health.spec.ts` se ajusta a `/salud` (cuarto archivo tolerado: 1 línea).
    - Estilos solo con tokens de `index.css`.
  - Pruebas: frontend (Vitest + Testing Library).

- [x] **T18** · `frontend` · D1-FE-01 (2/2) · Cinco features con página placeholder y ruta lazy
  - Archivos (excepción de scaffold, sin lógica): `Frontend/src/features/{inicio,carga,lista,campanias,dashboard}/routes.tsx` (principal: `features/inicio/routes.tsx`) y `.../pages/{Inicio,Carga,Lista,Campanias,Dashboard}Page.tsx`; `Frontend/src/app/router.tsx`; `Frontend/src/app/router.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura; `.claude/rules/frontend.md` §Estructura.
  - Aceptación:
    - Cada página renderiza un `<h1>` con su nombre ("Inicio", "Carga de datos", "Lista priorizada", "Campañas", "Dashboard"); cada `routes.tsx` usa `React.lazy`.
    - Test parametrizado: navegar a cada una de las 5 rutas muestra su `<h1>` dentro del layout; una ruta inexistente muestra "Página no encontrada".
    - `npm run build`, `npm run lint` y `npm test` en verde.
  - Pruebas: frontend.

- [x] **T19** · `frontend` · D1-FE-02 · Componente `DataTable`
  - Archivos: `Frontend/src/shared/ui/DataTable.tsx` (principal: genérico `<T>` con `columns: {key, header, render?}[]`, `rows`, `getRowKey`, `emptyMessage`, `caption`), `Frontend/src/shared/ui/DataTable.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estilos; `.claude/rules/frontend.md` §Estilos, §Pruebas.
  - Aceptación: 3 filas → `getAllByRole("row")` = 4 (cabecera + 3) y `columnheader` con los títulos; `rows = []` → muestra `emptyMessage`; `render` personalizado se usa en su celda; sin `any`.
  - Pruebas: frontend.

- [x] **T20** · `frontend` · D1-FE-02 · Componente `RiskBadge` y tokens de riesgo
  - Archivos: `Frontend/src/shared/ui/RiskBadge.tsx` (principal: prop `nivel: "ALTO" | "MEDIO" | "BAJO"`), `Frontend/src/index.css` (tokens `--color-risk-high`, `--color-risk-medium`, `--color-risk-low` en `@theme`), `Frontend/src/shared/ui/RiskBadge.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estilos.
  - Aceptación: cada nivel muestra su texto ("Alto", "Medio", "Bajo") y una clase distinta basada en el token; no importa nada de `features/`; los colores no se escriben en el componente (solo nombres de token).
  - Pruebas: frontend.

- [x] **T21** · `frontend` · D1-FE-02 · Componentes `LoadingIndicator` y `ErrorAlert`
  - Archivos: `Frontend/src/shared/ui/LoadingIndicator.tsx` (principal: `role="status"`, texto accesible configurable), `Frontend/src/shared/ui/ErrorAlert.tsx` (`role="alert"`, `message`, `onRetry?` → botón "Reintentar"), `Frontend/src/shared/ui/LoadingIndicator.test.tsx`, `Frontend/src/shared/ui/ErrorAlert.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estilos, §Pruebas.
  - Aceptación: `LoadingIndicator` → `getByRole("status")` con el texto; `ErrorAlert` → `getByRole("alert")` con el mensaje; con `onRetry` el clic en "Reintentar" lo llama 1 vez; sin `onRetry` no hay botón.
  - Pruebas: frontend.

- [x] **T22** · `frontend` · D1-FE-02 · Componente `Modal`
  - Archivos: `Frontend/src/shared/ui/Modal.tsx` (principal: `open`, `title`, `onClose`, `children`; `role="dialog"`, `aria-modal="true"`, `aria-labelledby`), `Frontend/src/shared/ui/Modal.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estilos.
  - Aceptación: `open=false` → no hay `dialog`; `open=true` → `getByRole("dialog", { name: title })`; `Escape` y el botón "Cerrar" llaman `onClose`; el foco pasa al diálogo al abrir.
  - Pruebas: frontend.

- [x] **T23** · `frontend` · D1-FE-03 (base 1/3) · `core/http`: POST, PUT, multipart y descarga
  - Archivos: `Frontend/src/core/http/http-client.ts` (principal: `httpPost<T>(path, body, opts)`, `httpPut<T>`, `httpPostForm<T>(path, FormData, opts)` sin fijar `Content-Type`, `httpGetBlob(path, opts) -> Blob`), `Frontend/src/core/http/http-client.test.ts`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §`core/http`.
  - Aceptación (TDD, red mockeada): `httpPost` envía JSON con `Content-Type: application/json` y devuelve el cuerpo en `201`; `501` con formato de error → `ApiError{status:501, message:"Esta funcion aun no esta disponible."}`; `httpPostForm` envía `multipart/form-data` con el archivo; `httpGetBlob` devuelve `Blob` con el tipo de la respuesta; abortar → `AbortError`. Las pruebas existentes de `httpGet` siguen en verde.
  - Pruebas: unitarias Vitest.

- [x] **T24** · `frontend` · D1-FE-03 (base 2/3) · Servidor MSW para pruebas con autodescubrimiento de handlers
  - Archivos: `Frontend/src/mocks/handlers.ts` (principal: agrega con `import.meta.glob("../features/*/api/*.handlers.ts", { eager: true })` todos los `handlers` exportados), `Frontend/src/mocks/server.ts` (`setupServer`), `Frontend/src/test/setup.ts` (`beforeAll listen({ onUnhandledRequest: "error" })`, `afterEach resetHandlers`, `afterAll close`), `Frontend/src/mocks/handlers.test.ts`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Pruebas; `.claude/rules/frontend.md` §Pruebas.
  - Aceptación: con 0 archivos `*.handlers.ts` la lista es vacía y la suite existente (96 tests) sigue en verde; un handler de prueba registrado con `server.use` responde; una petición sin handler hace fallar el test (`onUnhandledRequest: "error"`).
  - Pruebas: frontend.

- [x] **T25** · `frontend` · D1-FE-03 (base 3/3) · MSW en el navegador en desarrollo
  - Archivos: `Frontend/src/mocks/browser.ts` (principal: `setupWorker(...handlers)`), `Frontend/src/main.tsx` (arranca el worker solo si `import.meta.env.DEV && import.meta.env.VITE_API_MOCKS === "true"`, antes de montar), `Frontend/public/mockServiceWorker.js` (generado con `npx msw init public`), `Frontend/src/core/config.ts` (expone `apiMocks: boolean`).
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Desarrollo local.
  - Aceptación: `VITE_API_MOCKS=true npm run dev` → la consola del navegador muestra "[MSW] Mocking enabled" y las rutas de la API responden con datos simulados; `npm run build` → el bundle de `dist/assets` no contiene `setupWorker` (`grep` = 0; import dinámico bajo la condición `DEV`); sin la variable, no se registra el worker.
  - Pruebas: verificación manual + build.
  - Cierre: build sin `setupWorker` y condición de arranque cubiertos por pruebas (`config.test.ts`, `msw-wiring.test.ts`); **la comprobación manual del mensaje "[MSW] Mocking enabled" en el navegador no se hizo** (pendiente menor).

- [x] **T26** · `frontend` · D1-FE-03 · Feature `inicio`: estado del sistema y alertas
  - Archivos: `Frontend/src/features/inicio/api/inicio-api.ts` (principal: `getEstadoSistema(signal)`, `getAlertas(signal)`), `Frontend/src/features/inicio/types.ts`, `Frontend/src/features/inicio/api/inicio-api.handlers.ts` (datos simulados coherentes con los ejemplos de T11 y T15), `Frontend/src/features/inicio/api/inicio-api.test.ts`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Feature `health` (patrón); `Documentation/docs/API_CONTRACT.md`.
  - Aceptación (contra MSW): `GET /api/v1/sistema/estado` simulado → `{ estado: "LISTO", migracionHistorica: "COMPLETADA", modeloVigente: { version: "v1" (string; corregido al cerrar: el texto original decía número), fechaEntrenamiento: Date, ... }, ultimaCargaEn: Date | null, proximaFechaReentrenamiento: string | null }` (snake_case → camelCase solo en `api/`); `GET /api/v1/alertas` → `{ vencidas, hoy, proximos7Dias }`; respuesta `501` (vía `server.use`) → `ApiError` con `status 501`; no usa `fetch` directo.
  - Pruebas: unitarias Vitest + MSW.

- [x] **T27** · `frontend` · D1-FE-03 · Feature `carga`: vista previa y confirmación
  - Archivos: `Frontend/src/features/carga/api/carga-api.ts` (principal: `previsualizarCarga(file, signal)`, `confirmarCarga(file, signal)`), `Frontend/src/features/carga/types.ts`, `Frontend/src/features/carga/api/carga-api.handlers.ts` (una vista previa válida y una con errores según el nombre del archivo), `Frontend/src/features/carga/api/carga-api.test.ts`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §4.
  - Aceptación: archivo `valida.xlsx` → `puedeConfirmar: true`, `errores: []`; `con-errores.xlsx` → `puedeConfirmar: false` y `errores[0]` con `{ fila, columna, motivo }`; `confirmarCarga` → `CargaResumen` con `filasGuardadas`; `422` simulado → `ApiError status 422`; el archivo viaja como `FormData` campo `archivo`.
  - Pruebas: unitarias Vitest + MSW.

- [x] **T28** · `frontend` · D1-FE-03 · Feature `lista`: lista, Excel, sugerencias y gestiones
  - Archivos: `Frontend/src/features/lista/api/lista-api.ts` (principal: `generarLista`, `getUltimaLista`, `getLista`, `descargarExcel`, `getCampaniasSugeridas`, `crearGestion`, `registrarResultado`, `getGestiones(filtro)`), `Frontend/src/features/lista/types.ts`, `Frontend/src/features/lista/api/lista-api.handlers.ts` (lista de ≥ 30 socios ficticios con los tres niveles), `Frontend/src/features/lista/api/lista-api.test.ts`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §7, §10, §11, §13, §15.
  - Aceptación: `generarLista({ horizonteDias: 30, topK: 25 })` envía `{"fecha_referencia":null,"horizonte_dias":30,"top_k":25}` y devuelve `items` con `score` como `string` decimal (nunca `parseFloat`) y `nivelRiesgo` tipado; `getUltimaLista` con `404` → `null`; `descargarExcel` → `Blob` con tipo xlsx; `crearGestion` con `409` → `ApiError 409`; `getGestiones("vencidas")` envía `?filtro=vencidas`. Los datos simulados son ficticios (sin cédulas reales).
  - Pruebas: unitarias Vitest + MSW.

- [x] **T29** · `frontend` · D1-FE-03 · Feature `campanias`
  - Archivos: `Frontend/src/features/campanias/api/campanias-api.ts` (principal: `listarCampanias`, `crearCampania`, `editarCampania`, `inactivarCampania`), `Frontend/src/features/campanias/types.ts`, `Frontend/src/features/campanias/api/campanias-api.handlers.ts` (dos campañas `esEjemplo: true`), `Frontend/src/features/campanias/api/campanias-api.test.ts`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §9.
  - Aceptación: `listarCampanias` → 2 campañas con `esEjemplo: true`; `crearCampania` envía snake_case y devuelve la creada (`201`); `inactivarCampania(id)` hace `POST /api/v1/campanias/{id}/inactivar` y devuelve `activa: false`; `400` simulado → `ApiError 400` con el mensaje del servidor. Los tipos no admiten `"DIARIO"` en `planes`.
  - Pruebas: unitarias Vitest + MSW.

- [x] **T30** · `frontend` · D1-FE-03 · Feature `dashboard`
  - Archivos: `Frontend/src/features/dashboard/api/dashboard-api.ts` (principal: `getDashboard(mes, signal)`), `Frontend/src/features/dashboard/types.ts`, `Frontend/src/features/dashboard/api/dashboard-api.handlers.ts` (una campaña con ≥ 10 cerradas y otra con `casosInsuficientes: true`), `Frontend/src/features/dashboard/api/dashboard-api.test.ts`.
  - Docs: `Documentation/docs/API_CONTRACT.md`; `Documentation/03-casos-de-uso.md` §14.
  - Aceptación: `getDashboard("2026-09")` envía `?mes=2026-09` y devuelve `embudo`, `porCampania` (con `tasaRenovacion: string | null`) y `estadoModelo`; sin mes no envía el parámetro; `501` simulado → `ApiError 501`.
  - Pruebas: unitarias Vitest + MSW.

- [x] **DOC-1** · (doc-agent) · D1-OP-02 · Completar `.claude/CLAUDE.md` **(requiere aprobación del usuario)**: nombre "Mtabolic — apoyo a la retención", descripción de una línea, sustituir la invariante "propietario desde el token" por "sin login; acceso por IP (CU-00); la regla `user_id` de `database.md` no aplica", `{{INVARIANTE_PROPIA_DEL_DOMINIO}}` → "el esquema lo migra solo el servicio `migrate`; la única migración de datos al arrancar es CU-03 (ADR-004)", enlace a `DEVELOPMENT_GUIDELINES.md`. Aceptación: `grep "{{" .claude/CLAUDE.md` = 0.
- [x] **DOC-2** · (doc-agent) · D1-OP-03 · Crear `Documentation/DEVELOPMENT_GUIDELINES.md` con alcance (03 §1.1, §19) y §"fuera de alcance" (03 §20), más la excepción de `deleted_at` y la conversión `Decimal → float` permitida solo en el borde del modelo (04 §5.7).
- [x] **DOC-3** · (doc-agent) · D1-OP-04 · ADR-002 (ML en infraestructura detrás de `PredictorModel`), ADR-003 (reentrenamiento y versionado en BD), ADR-004 (migración de datos al arrancar; el esquema solo por `migrate`) en `Documentation/adr/`; enlazarlos en §DECISIONES.
- [x] **DOC-4** · (doc-agent) · Documentar R-002: `docs/backend/09-esquema-base-de-datos.md` (nuevo: tablas, restricciones, índices, excepciones; nombre corregido desde `02-esquema-bd.md` para coincidir con la referencia de `.claude/rules/database.md`), `docs/backend/10-docker.md` (servicio `migrate`, `HISTORICO_DIR`, `app_db_test`), `docs/API_CONTRACT.md` (18 operaciones en `501`), `docs/frontend/01-arquitectura.md` (layout, `shared/ui`, MSW), versiones fijadas en `Backend/README.md`; actualizar `05-cronograma-semana.md` con el avance del Día 1 y el resumen de lo realizado.

**Dependencias**
- Backend: T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9. T10 → T11 → T12 → T13 → T14 → T15 → T16 (todas tocan `main.py`: en serie). La rama T10–T16 requiere T2 (`python-multipart`) y T3 (enums en DTOs); puede ir en paralelo a T4–T9 (archivos disjuntos).
- Frontend: T17 → T18 → T19..T22 (en cualquier orden) ; T23 → T24 → T25 → T26..T30. T26–T30 requieren el contrato de T11–T16 (los tipos siguen los DTOs; con el contrato de este plan pueden empezar antes y ajustarse).
- T1 primero (antes de cualquier `git add`). DOC-1..3 pueden ir en paralelo al código; DOC-4 al final, con T1–T30 cerradas.
- Externas: Docker Desktop con Compose v2; PostgreSQL del compose en marcha para T6–T9; `.env` local con `HISTORICO_DIR` y `TEST_DATABASE_URL` apuntando a `app_db_test`.

**Riesgos**
1. **Borrado de la base de desarrollo por las pruebas de migración:** hoy `TEST_DATABASE_URL` apunta a `app_db`; el `downgrade base` de T7/T8 la vaciaría. Mitigación obligatoria: base `app_db_test` y guarda que aborta si el nombre no termina en `_test`.
2. **Deriva entre ORM, migración `0001` y enums:** un `CHECK` escrito a mano que no coincida con el enum rompe el día 2 en silencio. Mitigación: `CHECK` generados desde los enums y `alembic check` sin diferencias en T7.
3. **Orden de arranque en Compose:** si `migrate` falla o el backend no espera `service_completed_successfully`, el backend arranca sin tablas; y dos servicios con `build` e `image: backend:dev` pueden reconstruir o buscar la imagen en un registro. Verificar `docker compose down -v && up --build` desde cero (T9).

### R-001 — Scaffold Backend (FastAPI en capas) + Frontend (React en capas) con Docker + PostgreSQL 16 y ejemplo `health` end-to-end (TDD) · **DONE** 2026-09-28

**Cierre:** security `clean` · tests `pass` (Backend 132 pytest unit+integration; Frontend 96 Vitest + 1 E2E Playwright). Docs: `docs/backend/01-arquitectura.md`, `docs/backend/10-docker.md`, `docs/frontend/01-arquitectura.md`, `docs/API_CONTRACT.md`, `README.md` (raíz, `Backend/`, `Frontend/`), ADR-001. No se creó `products/P00-*.md` (P00 no se mantiene como producto aparte).

**Seguimientos de seguridad no bloqueantes (para requerimientos futuros):** S13 rate limit en `/api/v1/health` · S15 logging JSON con `correlation_id` · S16 mensajes de `DomainError` aptos para el usuario · S18 `X-Forwarded-Proto` con TLS delante · S19 CSP/HSTS y verificar ausencia de sourcemaps · S21 imágenes base por digest · S23 rol de BD sin superusuario + rol de migraciones (con la primera tarea de Alembic) · S24 el frontend no arranca si la BD no está disponible al inicio.

**Objetivo:** dejar ambos proyectos arrancando con `docker compose up`, con un endpoint `GET /api/v1/health` que verifica la BD recorriendo api → application → domain ← infrastructure, y una página React que lo consume recorriendo pages → hooks → api → core/http.

**Producto:** P00 — Fundaciones técnicas (sin `products/P00-*.md`; lo crea doc-agent si se decide mantenerlo).

**Notas de alcance del planner**
- No existe `Documentation/DEVELOPMENT_GUIDELINES.md` ni `Documentation/docs/**`: no hay §"fuera de alcance" contra el que validar. Las tareas citan `.claude/rules/*.md` como documento técnico hasta que doc-agent cree `docs/`.
- El requerimiento resuelve de facto la pregunta abierta **P-07** de `Documentation/01-analisis-mvp-a-app-web.md` (FastAPI + React en lugar de Streamlit). Doc-agent debe reflejarlo (candidato a ADR).
- **Fuera de R-001** (no planificar ni implementar aquí): autenticación/JWT, tablas de negocio y migraciones Alembic (no hay tablas; solo se deja preparado el paquete `persistence`), logging JSON con `correlation_id`, CI/CD, lógica del modelo del notebook, inicialización de submódulos git.
- Excepción al límite de 4 archivos: los `__init__.py` vacíos que marcan paquetes no cuentan.
- `GET /api/v1/health` es público y no maneja datos de usuario: la prueba de aislamiento entre usuarios **no aplica** (se deja explícito en el test del router con un comentario).

**Tareas**

- [x] **T1** · `infra-deploy` · Esqueleto y tooling del Backend
  - Archivos: `Backend/pyproject.toml` (principal), `Backend/app/**/__init__.py` (paquetes `api`, `api/routers`, `application`, `application/health`, `domain`, `domain/common`, `domain/health`, `infrastructure`, `infrastructure/persistence`, `infrastructure/clock`, `core`), `Backend/tests/{unit,integration}/**/__init__.py`, `Backend/.gitignore`.
  - Docs: `.claude/rules/backend.md` §Arquitectura en capas, §Comandos.
  - Aceptación:
    - `pip install -e ".[dev]"` en venv Python 3.12 instala FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2, psycopg 3 (binary), uvicorn; dev: pytest, httpx, ruff, mypy, import-linter.
    - `ruff check .`, `ruff format --check .`, `mypy app` (strict) y `lint-imports` terminan con código 0.
    - `pyproject.toml` declara contratos import-linter: `domain` no importa ninguna otra capa; `application` no importa `api` ni `infrastructure`; `infrastructure` no importa `api`; `api` no importa `infrastructure` salvo `app.api.dependencies` y `app.main` (ignore explícito).
    - Un import prohibido de prueba (p. ej. `app.domain` → `app.infrastructure`) hace fallar `lint-imports` (verificado manualmente y revertido).
    - `pytest` configurado con markers `unit`/`integration` y `asyncio_mode` si aplica; `pytest` sin tests sale sin error de configuración.
  - Pruebas: ninguna de comportamiento; verificación por comandos de lint/tipos/capas.

- [x] **T2** · `domain` · Dominio `health` y puerto `Clock`
  - Archivos: `Backend/app/domain/health/value_objects.py` (principal), `Backend/app/domain/common/exceptions.py` (`DomainError`), `Backend/app/domain/common/clock.py` (`Clock` Protocol, `now() -> datetime` UTC aware), `Backend/tests/unit/domain/health/test_health_report.py`.
  - Docs: `.claude/rules/backend.md` §Dominio.
  - Aceptación (TDD, test primero):
    - `HealthReport.create(database=ComponentStatus.UP, checked_at=<aware UTC>)` → `status == OverallStatus.OK`.
    - `database=ComponentStatus.DOWN` → `status == OverallStatus.DEGRADED`.
    - `checked_at` naive (sin tz) → lanza `InvalidHealthReportError` (subclase de `DomainError`).
    - `HealthReport` es `@dataclass(frozen=True, slots=True)`; asignar un atributo lanza `FrozenInstanceError`.
    - El dominio solo importa librería estándar (`lint-imports` y `mypy app` en verde).
  - Pruebas: unitarias (`test_create_database_up_returns_ok`, `test_create_database_down_returns_degraded`, `test_create_naive_datetime_raises_invalid_health_report_error`).

- [x] **T3** · `application` · Query `GetHealth` con puertos
  - Archivos: `Backend/app/application/health/queries.py` (principal, `GetHealthQueryHandler`), `Backend/app/application/health/ports.py` (`DatabaseProbe` Protocol: `is_reachable() -> bool`, no lanza), `Backend/app/application/health/dtos.py` (`HealthDTO` Pydantic: `status: Literal["ok","degraded"]`, `database: Literal["up","down"]`, `checked_at: datetime`), `Backend/tests/unit/application/health/test_get_health_query.py`.
  - Docs: `.claude/rules/backend.md` §Application.
  - Aceptación (TDD, con dobles de `DatabaseProbe` y `Clock`, sin FastAPI ni BD):
    - probe `True` + reloj fijo `2026-01-01T00:00:00Z` → `HealthDTO(status="ok", database="up", checked_at=2026-01-01T00:00:00Z)`.
    - probe `False` → `status="degraded"`, `database="down"`.
    - La hora sale solo del `Clock` inyectado (no hay `datetime.now` en `application/`: `grep` = 0).
    - El handler no devuelve la entidad de dominio, solo el DTO.
  - Pruebas: unitarias.

- [x] **T4** · `infra` · Configuración y reloj del sistema
  - Archivos: `Backend/app/core/config.py` (principal, `Settings` con pydantic-settings: `DATABASE_URL` obligatorio, `CORS_ORIGINS` lista, `APP_ENV`, `DEBUG=False` por defecto), `Backend/app/infrastructure/clock/system_clock.py`, `Backend/tests/unit/core/test_config.py`, `Backend/tests/unit/infrastructure/test_system_clock.py`.
  - Docs: `.claude/rules/backend.md` §Seguridad; `.claude/rules/deploy.md` §Configuración y secretos.
  - Aceptación (TDD):
    - Sin `DATABASE_URL` en el entorno → `Settings()` lanza error de validación cuyo mensaje nombra la variable y **no** incluye ningún valor.
    - `CORS_ORIGINS="http://localhost:5173,http://localhost:8080"` → lista de 2 orígenes; `"*"` es rechazado.
    - `repr(settings)` / `str(settings)` no muestra la contraseña de `DATABASE_URL` (tipo `SecretStr` o equivalente).
    - `SystemClock().now()` devuelve `datetime` con `tzinfo == UTC`; es la única implementación que llama a `datetime.now(UTC)`.
  - Pruebas: unitarias (con `monkeypatch` de variables de entorno).

- [x] **T5** · `infra` · Engine SQLAlchemy y `SqlAlchemyDatabaseProbe`
  - Archivos: `Backend/app/infrastructure/persistence/database_probe.py` (principal), `Backend/app/infrastructure/persistence/database.py` (factory de engine con `pool_size`, `max_overflow`, `pool_pre_ping=True`, `connect_timeout` corto; driver `postgresql+psycopg://`), `Backend/tests/integration/conftest.py` (fixture de engine desde `TEST_DATABASE_URL`), `Backend/tests/integration/infrastructure/test_database_probe.py`.
  - Docs: `.claude/rules/database.md` §Reparto de herramientas, §Pruebas.
  - Aceptación (TDD contra PostgreSQL 16 real del compose, nunca SQLite):
    - Engine hacia la BD levantada → `is_reachable()` devuelve `True` (ejecuta `SELECT 1` con `text()`).
    - Engine hacia `127.0.0.1:<puerto sin servicio>` → `is_reachable()` devuelve `False` en < 5 s, no propaga excepción, y registra el fallo en log **sin** la URL ni credenciales.
    - Sin `TEST_DATABASE_URL` → los tests de integración fallan con mensaje claro (no se saltan en silencio).
    - La app no crea tablas ni ejecuta migraciones al arrancar (`create_all`/`alembic upgrade` ausentes: `grep` = 0).
  - Pruebas: integración.

- [x] **T6** · `api` · Router `GET /api/v1/health` y composition root
  - Archivos: `Backend/app/api/routers/health.py` (principal), `Backend/app/api/dependencies.py` (enlaza `SqlAlchemyDatabaseProbe`, `SystemClock`, `GetHealthQueryHandler` vía `Depends`), `Backend/app/main.py` (`create_app()`, monta router bajo `/api/v1`, `debug` desde settings, sin migraciones en `lifespan`, dispose del engine al cerrar), `Backend/tests/integration/api/test_health_endpoint.py`.
  - Docs: `.claude/rules/backend.md` §API (FastAPI).
  - Aceptación (TDD, `TestClient`/`httpx`; BD real; `dependency_overrides` solo para reloj y, en el caso "down", para el probe):
    - BD arriba → `200` `{"status":"ok","database":"up","checked_at":"<ISO-8601 UTC>"}`; con reloj sobrescrito, `checked_at == "2026-01-01T00:00:00Z"`.
    - Probe sobrescrito devolviendo `False` → `503` `{"status":"degraded","database":"down","checked_at":...}`.
    - `/openapi.json` contiene `/api/v1/health` con `response_model`, respuestas `200` y `503` y **ejemplos** para ambas.
    - El router no importa `app.infrastructure` ni SQLAlchemy (`lint-imports` en verde).
  - Pruebas: integración.

- [x] **T7** · `api` · Formato único de error y CORS
  - Archivos: `Backend/app/api/errors.py` (principal: handlers de `RequestValidationError` → `400`, `HTTPException`, `DomainError` → `422`, `Exception` → `500`, todos con `{"error":{"code":"...","message":"..."}}`), `Backend/app/main.py` (registro de handlers y `CORSMiddleware` con `CORS_ORIGINS` explícitos), `Backend/tests/integration/api/test_error_handlers.py`.
  - Docs: `.claude/rules/backend.md` §API, §Errores y logging; `.claude/rules/deploy.md` §Red.
  - Aceptación (TDD):
    - `GET /api/v1/no-existe` → `404` con `{"error":{"code":"not_found","message":...}}`.
    - Ruta de prueba registrada solo en el test que lanza `RuntimeError` → `500` con mensaje genérico; el cuerpo no contiene `Traceback`, rutas de archivo ni SQL; el error queda registrado en log.
    - Preflight `OPTIONS` desde origen permitido → cabecera `access-control-allow-origin` con ese origen; desde origen no listado → sin la cabecera.
    - No hay `allow_origins=["*"]` con `allow_credentials=True`.
  - Pruebas: integración.

- [x] **T8** · `infra-deploy` · Imagen Docker del Backend
  - Archivos: `Backend/Dockerfile` (principal, multi-stage, `python:3.12-slim` con versión fijada, usuario no root, `uvicorn` sin `--reload`, `HEALTHCHECK` contra `/api/v1/health`), `Backend/.dockerignore` (excluye `.venv`, `__pycache__`, `tests`, `.git`, `.env`).
  - Docs: `.claude/rules/deploy.md` §Contenedores.
  - Aceptación:
    - `docker build -t backend:dev Backend` termina sin error; la imagen final no contiene `pytest`, `ruff`, `mypy` ni compiladores.
    - `docker run` con `DATABASE_URL` → `whoami` dentro del contenedor ≠ `root`.
    - `docker run` sin `DATABASE_URL` → el proceso sale con código ≠ 0 y el log nombra la variable faltante sin valores.
  - Pruebas: verificación manual por comandos (sin suite nueva).

- [x] **T9** · `frontend` · Tooling del Frontend (Vite + React + TS estricto)
  - Archivos: `Frontend/package.json` (principal: react, react-dom, react-router-dom, tailwindcss v4 + `@tailwindcss/vite`; dev: vite, typescript, vitest, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom, jsdom, msw, eslint, @playwright/test; scripts `dev`, `build` = `tsc -b && vite build`, `lint`, `test` = `vitest run`), `Frontend/tsconfig.json` (`strict: true`), `Frontend/vite.config.ts` (plugin React y Tailwind, `test.environment = "jsdom"`, proxy dev `/api` → `http://localhost:8000`), `Frontend/eslint.config.js`.
  - Docs: `.claude/rules/frontend.md` §Stack, §Comandos.
  - Aceptación: `npm install` sin errores; `npm run lint` y `npx tsc -b` en verde; `npm test` ejecuta Vitest (0 tests no es error de configuración, `passWithNoTests`).
  - Pruebas: ninguna de comportamiento.

- [x] **T10** · `frontend` · Bootstrap de la app y router con rutas lazy
  - Archivos: `Frontend/src/main.tsx` (principal), `Frontend/index.html`, `Frontend/src/app/router.tsx` (`createBrowserRouter`, monta rutas de features con `React.lazy` + `Suspense`), `Frontend/src/index.css` (`@import "tailwindcss"` + tokens de diseño en `@theme`: colores `ok`, `degraded`, tipografía, radios).
  - Docs: `.claude/rules/frontend.md` §Estructura, §Estilos.
  - Aceptación: `npm run build` genera `dist/` sin errores TS; los tokens de diseño existen en un único punto (`index.css`); no hay CSS custom fuera de `index.css`.
  - Pruebas: cubiertas en T14 (render de la ruta).

- [x] **T11** · `frontend` · Cliente HTTP único `core/http`
  - Archivos: `Frontend/src/core/http/http-client.ts` (principal: `httpGet<T>(path, { signal })`, base URL desde `import.meta.env.VITE_API_BASE_URL` con fallback `""`), `Frontend/src/core/http/api-error.ts` (`ApiError` con `status`, `message`, `body: unknown`), `Frontend/src/core/config.ts`, `Frontend/src/core/http/http-client.test.ts`.
  - Docs: `.claude/rules/frontend.md` §Capas y responsabilidades, §Seguridad.
  - Aceptación (TDD, `fetch` mockeado/MSW):
    - `200` con JSON → resuelve el cuerpo parseado.
    - `404` con `{"error":{"code":"not_found","message":"X"}}` → lanza `ApiError{status:404, message:"X", body:<json>}`.
    - `503` con cuerpo JSON → `ApiError` con `status:503` y `body` accesible.
    - Error de red → `ApiError{status:0}` con mensaje genérico.
    - `AbortSignal` abortado → la promesa rechaza con `AbortError` (no `ApiError`).
    - No usa `localStorage`/`sessionStorage`; no hace `console.log` de respuestas.
  - Pruebas: unitarias Vitest.

- [x] **T12** · `frontend` · Feature `health`: tipos y servicio `api/`
  - Archivos: `Frontend/src/features/health/api/health-api.ts` (principal: `getHealth(signal)`), `Frontend/src/features/health/types.ts` (`Health = { status: "ok" | "degraded"; database: "up" | "down"; checkedAt: Date }`), `Frontend/src/features/health/api/health-api.test.ts`.
  - Docs: `.claude/rules/frontend.md` §Capas y responsabilidades, §Pruebas.
  - Aceptación (TDD, red mockeada):
    - `200 {"status":"ok","database":"up","checked_at":"2026-01-01T00:00:00Z"}` → `{status:"ok", database:"up", checkedAt: Date(2026-01-01T00:00:00Z)}` (snake_case mapeado a camelCase aquí y solo aquí).
    - `503` con cuerpo de health válido → devuelve `{status:"degraded", database:"down", ...}` (no lanza).
    - `500` u otro error → propaga `ApiError`.
    - Llama a `core/http`, nunca a `fetch` directamente (`grep fetch` en `features/` = 0).
  - Pruebas: unitarias Vitest.

- [x] **T13** · `frontend` · Hook `useHealth`
  - Archivos: `Frontend/src/features/health/hooks/useHealth.ts` (principal: `{ data, error, isLoading, refetch }`), `Frontend/src/features/health/hooks/useHealth.test.tsx`.
  - Docs: `.claude/rules/frontend.md` §Estado y asincronía.
  - Aceptación (TDD, `renderHook` con `health-api` mockeado):
    - Montaje → `isLoading=true`; resolución → `data` poblado, `isLoading=false`.
    - Servicio lanza `ApiError` → `error` con el mensaje, `data=null`.
    - Desmontar antes de resolver → se llama `abort()` y no se actualiza estado (sin warning de act).
    - `refetch()` vuelve a llamar al servicio.
  - Pruebas: unitarias Vitest.

- [x] **T14** · `frontend` · Página `HealthPage`, componente presentacional y rutas del feature
  - Archivos: `Frontend/src/features/health/pages/HealthPage.tsx` (principal), `Frontend/src/features/health/components/HealthStatusCard.tsx` (solo props), `Frontend/src/features/health/routes.tsx` (lazy, ruta `/`), `Frontend/src/features/health/pages/HealthPage.test.tsx`.
  - Docs: `.claude/rules/frontend.md` §Capas y responsabilidades, §Pruebas.
  - Aceptación (TDD, Testing Library por roles/textos, red mockeada con MSW):
    - Cargando → se ve un indicador con `role="status"`.
    - API `200` ok → texto "Sistema operativo" y "Base de datos: conectada".
    - API `503` → texto "Servicio degradado" y "Base de datos: sin conexión".
    - API `500` → banner `role="alert"` con el mensaje de error y botón "Reintentar" que dispara `refetch`.
    - `HealthStatusCard` no importa hooks ni `api/`; `HealthPage` no importa `api/` ni `core/http`.
  - Pruebas: frontend (Vitest + Testing Library).

- [x] **T15** · `infra-deploy` · Imagen Docker del Frontend
  - Archivos: `Frontend/Dockerfile` (principal, multi-stage: `node:<versión fijada>-alpine` para build, `nginxinc/nginx-unprivileged:<versión fijada>-alpine` para runtime), `Frontend/nginx.conf` (sirve `dist/`, fallback SPA a `index.html`, proxy `/api/` → `http://backend:8000`), `Frontend/.dockerignore`.
  - Docs: `.claude/rules/deploy.md` §Contenedores.
  - Aceptación: `docker build Frontend` sin error; la imagen final no contiene `node_modules` ni `src/`; corre como usuario no root en el puerto 8080; ninguna variable `VITE_*` contiene secretos.
  - Pruebas: verificación manual por comandos.

- [x] **T16** · `infra-deploy` · `compose.yaml` raíz con backend, frontend y PostgreSQL 16
  - Archivos: `compose.yaml` (principal: servicio `db` `postgres:16-alpine` fijado, volumen nombrado, healthcheck `pg_isready`, puerto publicado solo en `127.0.0.1:5432`; `backend` con `depends_on: db: condition: service_healthy`, puerto 8000; `frontend` puerto 8080), `.env.example` (cada variable con valor marcador: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `TEST_DATABASE_URL`, `CORS_ORIGINS`, `APP_ENV`), `.gitignore` raíz (incluye `.env`).
  - Docs: `.claude/rules/deploy.md` §Contenedores, §Configuración y secretos.
  - Aceptación:
    - `compose.yaml` no contiene contraseñas literales: usa `${POSTGRES_PASSWORD:?...}` desde `.env` no versionado.
    - `cp .env.example .env` + valores locales + `docker compose up -d --build` → los 3 servicios `healthy`/`running`.
    - `curl http://localhost:8000/api/v1/health` → `200` con `"database":"up"`; `curl http://localhost:8080/api/v1/health` (vía nginx) → mismo resultado.
    - `docker compose stop db` → `curl .../api/v1/health` → `503` con `"database":"down"`; el backend sigue vivo.
    - `pytest` del Backend (unit + integration) en verde contra la BD del compose con `TEST_DATABASE_URL`.
  - Pruebas: verificación de stack completa por comandos.

- [x] **T17** · `frontend` · E2E Playwright del flujo health
  - Archivos: `Frontend/e2e/health.spec.ts` (principal), `Frontend/playwright.config.ts` (`baseURL` desde `E2E_BASE_URL`, por defecto `http://localhost:8080`).
  - Docs: `.claude/rules/frontend.md` §Pruebas.
  - Aceptación: con el stack de T16 arriba, `npx playwright test` → abre `/`, ve "Sistema operativo" y "Base de datos: conectada"; test en verde.
  - Pruebas: e2e.

- [x] **DOC** · (doc-agent, no developer) · Documentar R-001: crear `Documentation/docs/backend/01-arquitectura.md`, `docs/backend/10-docker.md`, `docs/frontend/01-arquitectura.md`, `docs/API_CONTRACT.md` (contrato de `/api/v1/health` y formato de error), `Backend/README.md` y `Frontend/README.md` (comandos), actualizar el índice de `Documentation/README.md` y cerrar P-07 en `01-analisis-mvp-a-app-web.md` (evaluar ADR-001 "FastAPI + React + PostgreSQL en lugar de Streamlit").

**Dependencias**
- Backend: T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8.
- Frontend: T9 → T10 → T11 → T12 → T13 → T14 → T15 (independiente del Backend hasta T15; puede intercalarse tras T1).
- T16 requiere T8 y T15. T17 requiere T16. DOC requiere T1–T17 cerradas.
- Externas: Docker Desktop con Compose v2, Python 3.12, Node LTS; T5/T6/T7 necesitan PostgreSQL 16 en marcha (se puede levantar solo `db` con un `docker run postgres:16-alpine` temporal o adelantar el servicio `db` de T16).

**Riesgos**
1. Pruebas de integración (T5–T7) dependen de un PostgreSQL disponible antes de existir `compose.yaml`: si `TEST_DATABASE_URL` no está, deben fallar explícitamente, nunca saltarse ni caer a SQLite.
2. Fuga de credenciales: `DATABASE_URL` contiene la contraseña; riesgo de aparecer en logs del probe, en `repr(Settings)`, en `compose.yaml` o en `.env` versionado.
3. Contratos de import-linter mal definidos (T1) dejarían pasar violaciones de capa en todo el resto del requerimiento; verificarlos con un import prohibido deliberado.

## DECISIONES IMPORTANTES

- 2026-09-28 · R-001 · Stack FastAPI + React + PostgreSQL 16 en Docker en lugar de Streamlit; cierra P-07 → [ADR-001](adr/ADR-001-fastapi-react-postgresql.md).
- 2026-09-28 · R-001 · `GET /api/v1/health` responde `503` con cuerpo de health válido (no formato de error) cuando la BD no responde; el frontend lo muestra como `degraded`.
- 2026-09-28 · R-001 · Errores de validación de entrada → `400 validation_error` (no el `422` de FastAPI); `422` queda para `domain_rule_violated`.
- 2026-09-28 · R-001 · Puertos publicados solo en `127.0.0.1`; la contraseña de PostgreSQL debe ser URL-safe.
- 2026-09-28 · Alcance · El histórico 2025–2026 (`plantillas/Control Gym *.xlsx`) se migra una sola vez al generar la base, y en el mismo proceso se entrena el modelo v1 (CU-03). Después, la carga es solo por plantilla (CU-01) → [03](03-casos-de-uso.md).
- 2026-09-28 · Alcance · El despliegue no está confirmado; el desarrollo no debe depender del lugar de instalación → [04 §3](04-pendientes-para-iniciar-desarrollo.md).

- 2026-09-28 · Alcance · Todo el proyecto (CU-00 a CU-12) se entrega en **una semana**, con alcance simplificado ([03 §1.1](03-casos-de-uso.md)). Se adoptan las recomendaciones D-01 a D-18 ([04 §2](04-pendientes-para-iniciar-desarrollo.md)). Instalación local con Docker Compose.

- 2026-09-28 · Alcance · Decisiones D-01 a D-18 confirmadas por el usuario ([04 §2](04-pendientes-para-iniciar-desarrollo.md)): un solo PC; migración del histórico automática en el primer arranque con la base vacía y atómica con el modelo v1; reentrenamiento sin recuperar fechas perdidas y con comando manual documentado; lógica del notebook adaptada tal cual; ML en infraestructura (ADR-002, por redactar); la regla `user_id` de `database.md` no aplica.

- 2026-09-28 · R-002 · Alcance, fuera de alcance y excepciones (`deleted_at`, `Decimal → float` solo en el borde del modelo, sin `user_id`) → [DEVELOPMENT_GUIDELINES](DEVELOPMENT_GUIDELINES.md); `.claude/CLAUDE.md` completado (sin login, acceso por IP).
- 2026-09-28 · R-002 · ML en infraestructura detrás de `PredictorModel` → [ADR-002](adr/ADR-002-ml-en-infraestructura.md).
- 2026-09-28 · R-002 · Reentrenamiento programado en el backend sin recuperar fechas, comando manual y modelos versionados en la BD → [ADR-003](adr/ADR-003-reentrenamiento-y-versionado.md).
- 2026-09-28 · R-002 · Esquema solo por el servicio `migrate`; única migración de datos al arrancar = CU-03, atómica y en segundo plano → [ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md).
- 2026-09-28 · R-002 · Esquema de 10 tablas en plural (05 decía 11); `deleted_at` en 5 tablas editables y excepción para instantáneas, auditoría y fila de control; `CHECK` generados desde los enums; `cargas.nombre_archivo` NOT NULL, `campanias.descripcion` NULL; `membresias.socio_id` NULL provisional hasta el día 2 → [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-28 · R-002 · La `version` del modelo es `INTEGER` en BD y string `"v<n>"` en la API; decimales como string en los DTOs; `descripcion` de campaña ≤ 500 (límite propio) → [API_CONTRACT](docs/API_CONTRACT.md).
- 2026-09-28 · R-002 · Dependencias de datos/ML fijadas a versiones estables para Python 3.12 (pandas 3.0.6…), no a las del notebook, que no las registra → [Backend/README](../Backend/README.md).
- 2026-09-28 · R-002 · La revisión de seguridad de R-002 se difiere a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)).
- 2026-09-28 · R-002 · `health` se mueve de `/` a `/salud`; `/` es la página Inicio. MSW en el navegador solo con `DEV` y `VITE_API_MOCKS=true` → [frontend/01](docs/frontend/01-arquitectura.md).

## PRÓXIMO

Día 2 del [cronograma](05-cronograma-semana.md) (histórico: lectura, limpieza, identidad, ciclos y etiquetas). Arrastra de R-002: decidir `membresias.socio_id` NOT NULL y vigilar pandas 3.x.
