# Backend · 01 · Arquitectura

Python 3.12 · FastAPI · Pydantic v2 · pydantic-settings · SQLAlchemy 2 · psycopg 3 · PostgreSQL 16. Creado en R-001 (ver [ADR-001](../../adr/ADR-001-fastapi-react-postgresql.md)).

## Capas

```
Backend/app/
  domain/          reglas de negocio, solo librería estándar
  application/     casos de uso (handlers), puertos (Protocol), DTOs (Pydantic)
  infrastructure/  implementaciones de puertos: persistence/ (SQLAlchemy), clock/
  api/             HTTP: routers/, errors.py, dependencies.py (composition root)
  core/            configuración transversal (config.py); no importa ninguna capa
  main.py          create_app(): composition root
```

Dependencias hacia dentro: `api → infrastructure → application → domain`. Se verifica con `import-linter` (`pyproject.toml`, 7 contratos):

| Contrato | Regla |
|---|---|
| `layers` | `api > infrastructure > application > domain` |
| forbidden `domain` | no importa `api`, `application`, `infrastructure`, `core` ni `app.main` |
| forbidden `core` | no importa `api`, `application`, `infrastructure` ni `app.main` |
| forbidden `application` | no importa `api`, `infrastructure` ni `app.main` |
| forbidden `infrastructure` | no importa `api` ni `app.main` |
| forbidden `api` | no importa `infrastructure`, salvo `app.api.dependencies` (ignore explícito, alerta si deja de usarse) |
| forbidden ML (R-002, [ADR-002](../../adr/ADR-002-ml-en-infraestructura.md)) | `domain` y `application` no importan `pandas`, `numpy` ni `sklearn` |

**Dominio común (R-002):** `domain/common/enums.py` define los 12 catálogos como `StrEnum` (`Plan`, `FormaPago`, `EstadoCiclo`, `NivelRiesgo`, `EstadoGestion`, `OrigenMembresia`, `EstadoRegistro`, `TipoCarga`, `EstadoMigracion`, `DisparadorReentrenamiento`, `ResultadoReentrenamiento`, `Respuesta`) y los subconjuntos `PLANES_CAMPANIA` (sin `DIARIO`) y `RESPUESTAS_OFRECIMIENTO`/`_ACEPTACION`/`_RENOVACION`; conversión estricta (`Plan("mensual")` → `ValueError`). Son la única fuente de los `CHECK` de la BD y de los catálogos de los DTOs. `domain/common/predictor.py` declara el puerto `PredictorModel` (`Protocol` `runtime_checkable`: `train(features, labels) -> TrainedModel`, `predict(artefacto, features) -> list[Prediction]`); `float` se admite ahí solo por ser probabilidades del modelo. La implementación con scikit-learn irá en `infrastructure` (día 3).

**Contrato de la API (R-002):** `api/openapi.py` concentra `error_responses(...)`, `success_response(...)` y `raise_not_implemented()`; los routers `sistema`, `cargas`, `listas`, `campanias`, `gestiones` y `dashboard` publican las 18 operaciones con DTOs en `application/{modulo}/dtos.py` y responden `501` hasta tener su caso de uso ([API_CONTRACT](../API_CONTRACT.md)).

**Composition root:** `app/main.py` (crea el engine en el `lifespan`, registra handlers de error y CORS, monta routers bajo `/api/v1`) y `app/api/dependencies.py` (enlaza puertos con implementaciones vía `Depends`). Ningún otro módulo instancia infraestructura. La app **no** crea tablas ni ejecuta migraciones al arrancar.

## Patrón de un caso de uso (ejemplo `health`)

| Capa | Archivo | Rol |
|---|---|---|
| domain | `domain/health/value_objects.py` | `HealthReport.create(database, checked_at)` (frozen, slots); `checked_at` naive → `InvalidHealthReportError` (`DomainError`) |
| domain | `domain/common/clock.py` | puerto `Clock` (`now()` UTC aware) |
| application | `application/health/ports.py` | `DatabaseProbe.is_reachable() -> bool` (no lanza) |
| application | `application/health/queries.py` | `GetHealthQueryHandler`: probe + clock → `HealthReport` → `HealthDTO` |
| application | `application/health/dtos.py` | `HealthDTO` (`status`, `database`, `checked_at`) |
| infrastructure | `infrastructure/clock/system_clock.py` | `SystemClock`: única lectura del reloj del sistema |
| infrastructure | `infrastructure/persistence/database.py` | factory de engine: `pool_pre_ping`, `pool_size`, `max_overflow`, `connect_timeout=2`, `pool_timeout=2` |
| infrastructure | `infrastructure/persistence/database_probe.py` | `SqlAlchemyDatabaseProbe`: `SELECT 1`; ante fallo registra solo el tipo de excepción (sin URL ni credenciales) |
| api | `api/routers/health.py` | `GET /api/v1/health`; 503 si `database == "down"`; `def` síncrono (I/O bloqueante en threadpool) |

El router recibe y devuelve DTOs; nunca entidades de dominio ni ORM.

## Configuración (`core/config.py`)

`Settings` (pydantic-settings), validada al arrancar; si falla, el log nombra la variable sin mostrar el valor.

| Variable | Regla |
|---|---|
| `DATABASE_URL` | obligatoria, `SecretStr`, debe empezar por `postgresql+psycopg://` |
| `CORS_ORIGINS` | lista separada por comas; cada origen `http(s)://host[:port]`; `*` rechazado |
| `APP_ENV` | `development` · `test` · `production` |
| `DEBUG` | `False` por defecto; solo se permite `True` con `APP_ENV` explícito `development` o `test` |

## Errores

Handlers globales en `api/errors.py` con formato único `{"error":{"code","message"}}`. Tabla de códigos en [API_CONTRACT.md](../API_CONTRACT.md#formato-único-de-error). El `500` devuelve un mensaje genérico y registra el traceback solo en el servidor.

**Contrato pendiente (S16):** el mensaje de toda subclase de `DomainError` llega tal cual al cliente en el `422`; debe redactarse apto para el usuario final.

## Pruebas

`Backend/tests/{unit,integration}` espejando `app/`. Unit: dominio y aplicación con dobles, sin FastAPI ni BD. Integration: infraestructura y API contra PostgreSQL real (`TEST_DATABASE_URL` obligatoria; sin ella fallan, no se saltan). 132 pruebas al cierre de R-001. Comandos en `Backend/README.md`.

## Pendiente (fuera de R-001)

- Logging JSON con `correlation_id` (S15).
- Rate limit en `/api/v1/health` (S13).
- Alembic y primeras tablas; con ellas, rol de BD sin superusuario para la app y rol separado para migraciones (S23).
