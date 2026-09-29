---
paths:
  - "Backend/**/*.py"
  - "Backend/pyproject.toml"
  - "Backend/requirements*.txt"
  - "Backend/alembic.ini"
---

# Reglas — Backend (Python + FastAPI, Clean Architecture + DDD pragmático)

Stack: Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 · PostgreSQL 16 (`psycopg` 3) · Alembic · pytest · ruff · mypy.

Referencia larga: `Documentation/docs/backend/01-arquitectura.md`, `04-api-rest.md`, `05-seguridad.md`.

## Arquitectura en capas — responsabilidades desacopladas

Cuatro capas, cada una con **una sola responsabilidad**. Las dependencias apuntan siempre hacia dentro (`api` → `application` → `domain`; `infrastructure` → `application`/`domain`). Una capa interna nunca conoce a una externa.

| Capa | Paquete | Responsabilidad única | Puede importar | Nunca importa |
|---|---|---|---|---|
| Presentación | `app/api` | HTTP: rutas, autenticación, (de)serialización, códigos de estado, mapeo de errores | `application`, `app/core` | `infrastructure` (salvo en el composition root), modelos ORM, SQL |
| Aplicación | `app/application` | Casos de uso: orquestar dominio y puertos, transacción, DTOs | `domain` | FastAPI, SQLAlchemy, `infrastructure`, `api` |
| Dominio | `app/domain` | Reglas de negocio: entidades, value objects, invariantes, excepciones de dominio | solo librería estándar | Pydantic, FastAPI, SQLAlchemy, cualquier otra capa |
| Infraestructura | `app/infrastructure` | Detalles técnicos: persistencia (SQLAlchemy), reloj, hashing, JWT, servicios externos. Implementa los puertos | `application`, `domain` | `api` |

- **Composition root** único en `app/main.py` + `app/api/dependencies.py`: el único sitio donde se instancian implementaciones de `infrastructure` y se enlazan con los puertos vía `Depends`. Ninguna otra capa instancia clases de infraestructura.
- La comunicación entre capas cruza por **contratos**, no por implementaciones: puertos (`Protocol`) entre aplicación e infraestructura, DTOs entre presentación y aplicación. Un router nunca recibe ni devuelve una entidad de dominio o un modelo ORM.
- Cambiar un detalle de una capa (motor de BD, framework web, proveedor de tokens) no obliga a tocar `domain` ni `application`.
- Estructura por módulo dentro de cada capa: `domain/{modulo}/{entities,value_objects,enums,events,exceptions}.py`, `application/{modulo}/{commands,queries,dtos,ports}.py`, `infrastructure/{persistence,repositories,security,clock}/`, `api/routers/{modulo}.py`.
- Los módulos de negocio no se importan entre sí por dentro: si `A` necesita algo de `B`, lo consume a través de un puerto o caso de uso de `B`.
- Pruebas en `Backend/tests/{unit,integration}/` espejando la estructura de `app/`. `domain` y `application` se prueban sin FastAPI ni BD (dobles de los puertos); `infrastructure` y `api` con BD real.
- La regla de dependencias se verifica automáticamente con `import-linter` (contratos `layers` en `pyproject.toml`); un import que la viola es un defecto bloqueante.
- No introducir una abstracción sin una necesidad real y presente.

## Dominio

- Entidades como clases con factory method (`Entidad.create(...)`) y atributos privados (`_campo`) expuestos por propiedades de solo lectura. Sin mutación directa desde fuera.
- Las invariantes se validan en el factory o en el método de dominio, nunca en el handler.
- Los value objects son inmutables: `@dataclass(frozen=True, slots=True)`.
- Los valores exactos usan `decimal.Decimal`. `float` en cálculos exactos está prohibido.
- Fecha y hora **solo** vía un puerto `Clock` inyectable (UTC, `datetime` con tz). `datetime.now()`, `datetime.utcnow()`, `date.today()` y `time.time()` están prohibidos fuera de su implementación.
- Las violaciones de regla de negocio lanzan una excepción de dominio específica (subclase de `DomainError`), no `Exception` ni `ValueError` genérico.
- Tipado completo; `mypy --strict` sobre `app/`.

## Application

- Un caso de uso = un handler. Commands escriben, Queries leen.
- El handler orquesta: carga el agregado, invoca el método de dominio, persiste. No contiene reglas de negocio.
- Los puertos (`{{Modulo}}Repository`, `Clock`, `UnitOfWork`, …) se declaran como `Protocol` en `application`/`domain`; se implementan en `infrastructure`.
- DTOs de entrada/salida como modelos Pydantic en `application/{modulo}/dtos.py`; nunca se devuelve una entidad de dominio ni un modelo ORM por la API.

## API (FastAPI)

- Un `APIRouter` por módulo en `app/api/routers/{modulo}.py`, montado bajo `/api/v1/...`.
- Todo endpoint privado declara la dependencia de autenticación explícitamente (`Depends(get_current_user)`).
- Todo endpoint declara `response_model`, `status_code`, `responses={...}` con cada código de error y **ejemplos reales** (`json_schema_extra` / `openapi_examples`) de request y de cada respuesta, para que el OpenAPI generado sea el spec público.
- Códigos: `400` validación de entrada · `401` sin autenticar · `403` recurso de otro usuario · `404` no existe · `409` conflicto de concurrencia o regla de negocio · `422` regla de negocio violada.
- FastAPI devuelve `422` por defecto en errores de validación de Pydantic: se sobrescribe el handler de `RequestValidationError` para devolver `400` con el formato único.
- Los errores se devuelven con un formato único desde los exception handlers globales. Los mensajes son comprensibles para el usuario final.
- Validación de entrada en el borde (modelos Pydantic con restricciones) antes de tocar la lógica.
- Endpoints `async def` solo si toda la cadena de I/O es asíncrona; no mezclar llamadas bloqueantes dentro de `async def`.

## Seguridad

- El identificador de propietario se lee **siempre** del claim de identidad del token (`sub`) vía la dependencia de autenticación. Un id en body, query o ruta se ignora.
- **Toda** consulta y comando filtra por él, incluidas las consultas SQL crudas.
- Ningún secreto en código ni en configuración versionada. Variables de entorno cargadas con `pydantic-settings`; se validan al arrancar y se falla rápido si faltan.
- Contraseñas con hash adaptativo (argon2 o bcrypt). JWT firmados con secreto de ≥32 caracteres y expiración corta.
- Nunca registrar en logs: tokens, contraseñas, hashes, cabeceras de autorización, datos personales.
- Las respuestas de error no exponen tracebacks, SQL ni rutas del sistema. `debug=False` fuera de desarrollo.

## Errores y logging

- Excepción de dominio → respuesta de error con el código correcto, mapeada en un único exception handler.
- Log estructurado (JSON) con `correlation_id` propagado por middleware. Detalle en el servidor, mensaje seguro al cliente.
- Nunca un `except: pass` ni un `except Exception` que se traga el error sin registrarlo.

## Pruebas

- TDD para dominio, casos de uso, comportamiento crítico, autorización y aislamiento por usuario.
- Sin TDD para getters triviales ni configuración generada por el framework.
- pytest. Nombre: `test_{metodo}_{escenario}_{resultado_esperado}`.
- Endpoints con `httpx.AsyncClient`/`TestClient` y `app.dependency_overrides` solo para auth y reloj; la base de datos es real.
- Integración con PostgreSQL real en contenedor (nunca SQLite como sustituto); cada prueba limpia su estado (transacción con rollback o truncado).
- Cada endpoint nuevo tiene una prueba que demuestra que un usuario no accede a datos de otro.

## Comandos (desde `Backend/`, con el entorno virtual activo)

- Lint: `ruff check .` · Formato: `ruff format --check .`
- Tipos: `mypy app`
- Capas: `lint-imports`
- Pruebas: `pytest` (acota con `pytest tests/unit/{modulo}` o `-k`)
- Arranque local: `uvicorn app.main:app --reload`

## Finalización

Una tarea de backend está terminada cuando: `ruff check`, `ruff format --check`, `mypy` y `lint-imports` pasan sin errores, la suite está en verde, el endpoint está documentado en el OpenAPI con su contrato y ejemplos, y no hay hallazgos `critical`/`high`.

## Prohibido

- Ejecutar migraciones automáticamente al arrancar la aplicación (ni `alembic upgrade` ni `Base.metadata.create_all` en el `lifespan`).
- Borrado físico de datos marcados como no borrables.
- SQL construido por concatenación, f-strings o `%` con entrada del usuario.
- Lógica de negocio en routers, dependencias o repositorios.
- `save(obj)` genérico en repositorios: solo métodos con semántica de negocio.
- Implementar la misma consulta con dos mecanismos de acceso a datos sin razón explícita.
- `# type: ignore` o `# noqa` sin justificación en la misma línea.
