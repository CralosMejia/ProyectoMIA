---
paths:
  - "Backend/alembic/**"
  - "Backend/app/infrastructure/persistence/**"
  - "Backend/app/infrastructure/repositories/**"
  - "**/*.sql"
---

# Reglas — Base de datos

Motor: **PostgreSQL 16** · SQLAlchemy 2 (ORM para escrituras, Core/`text()` para lecturas complejas) · driver `psycopg` 3 (`postgresql+psycopg://`) · Alembic para migraciones.

Referencia larga: `Documentation/docs/backend/03-acceso-a-datos.md` y `09-esquema-base-de-datos.md`.

## Reparto de herramientas

- **SQLAlchemy ORM** para escrituras: comandos, agregados, transacciones. Mapeo en `infrastructure/persistence`; el dominio no conoce los modelos ORM.
- **SQLAlchemy Core / `text()` con parámetros enlazados** para lecturas complejas: listados, reportes, consultas con varios joins.
- **Alembic** para migraciones.
- La misma consulta no se implementa con ambas sin una razón explícita y anotada.
- Los repositorios exponen métodos con semántica de negocio. Nada de `save(obj)` ni `get_all()` genéricos.
- Una sesión por request (unit of work); el `commit` ocurre una sola vez al final del caso de uso.
- Tipos del dialecto PostgreSQL desde `sqlalchemy.dialects.postgresql` cuando aplique (`UUID`, `JSONB`, `ENUM`).
- `Numeric(19, 4)` con `asdecimal=True` para valores exactos.
- Pool de conexiones configurado explícitamente (`pool_size`, `max_overflow`, `pool_pre_ping=True`).

## Convenciones de esquema

- Tablas y columnas en `snake_case`; tablas en plural.
- Claves primarias `UUID` (generadas por la aplicación o con `gen_random_uuid()`) o `BIGINT GENERATED ALWAYS AS IDENTITY`; nunca `SERIAL`.
- Valores exactos: `NUMERIC` con precisión declarada (p. ej. `NUMERIC(19,4)`). Nunca `REAL`, `DOUBLE PRECISION` ni el tipo `MONEY`.
- Texto: `TEXT`, o `VARCHAR(n)` solo si el límite es una regla de negocio. Datos semiestructurados en `JSONB`, nunca `JSON`.
- Toda tabla lleva `created_at` y `updated_at` de tipo `TIMESTAMPTZ` (nunca `TIMESTAMP` sin zona), con valor en UTC asignado por la aplicación desde el `Clock`.
- **Toda tabla editable por el usuario lleva `deleted_at`** (`TIMESTAMPTZ NULL`, borrado lógico) con filtro aplicado en todas las consultas del repositorio. Las unicidades de negocio se declaran como índice único parcial `WHERE deleted_at IS NULL`. Excepciones explícitas: tablas de auditoría append-only y tablas de sesión/tokens.
- Toda tabla con un valor mutable sensible a concurrencia lleva un token de concurrencia optimista (`version`, con `version_id_col` de SQLAlchemy).
- Toda tabla de datos de usuario lleva `user_id` (o el identificador de tenant) `NOT NULL` e indexado; los índices de consulta empiezan por él.
- Estados cerrados con `CHECK` o tipo `ENUM` de PostgreSQL; invariantes simples de columna también con `CHECK` (p. ej. `amount >= 0`).
- Claves foráneas explícitas con el `ON DELETE` correcto — nunca cascada sobre datos críticos.

## Reglas innegociables

- **Ningún registro crítico se elimina físicamente.** Se anula por estado; opcionalmente recibe `deleted_at` para ocultarlo. Su repositorio no expone `Delete`.
- **Las escrituras que deben ser consistentes entre sí ocurren en la misma transacción.** Si una parte falla, no se persiste nada.
- Toda consulta filtra por el identificador de propietario. Una consulta sin ese `WHERE` es un defecto bloqueante.
- SQL siempre parametrizado. Interpolación o concatenación de entrada del usuario está prohibida.
- Orden y filtro dinámicos se validan contra una lista blanca de columnas.

## Migraciones

- Una migración de Alembic por cambio lógico, con mensaje descriptivo: `alembic revision --autogenerate -m "add_deleted_at_to_{{tabla}}"`.
- El autogenerado se revisa y corrige a mano, y se revisa el SQL (`alembic upgrade head --sql`) antes de aceptar la migración.
- Los `ENUM` de PostgreSQL no se autogeneran bien: crear o alterar el tipo explícitamente en la migración (`ALTER TYPE ... ADD VALUE`).
- Índices sobre tablas grandes con `CREATE INDEX CONCURRENTLY` (dentro de `op.get_context().autocommit_block()`).
- Toda migración implementa `downgrade()`.
- **La aplicación nunca ejecuta las migraciones al arrancar.** Son un paso separado del despliegue, anterior al de la nueva versión.
- Migración destructiva (drop de columna o tabla con datos): prohibida sin ADR y sin plan de migración de datos en dos fases.
- Toda migración debe poder ejecutarse sobre una base con datos, no solo sobre una vacía.

## Pruebas

- Los repositorios se prueban contra **PostgreSQL real en contenedor** (misma versión mayor que producción; imagen `postgres:16` fijada) (efímera en CI, la de `docker compose` en desarrollo). Nunca con una implementación en memoria.
- Se prueban: la migración aplica limpia, la transacción es atómica, la concurrencia optimista lanza el conflicto, y el filtro por propietario aísla usuarios.
- Cada prueba de integración deja la base como la encontró.

## Finalización

La migración aplica sobre una base con datos, las pruebas de integración pasan, el documento de esquema refleja la tabla o columna nueva, y el filtro de borrado lógico (`deleted_at IS NULL`) se aplica en todas las consultas del repositorio.
