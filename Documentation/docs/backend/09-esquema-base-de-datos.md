# Backend · 09 · Esquema de base de datos

PostgreSQL 16. Creado en R-002 (día 1 del [cronograma](../../05-cronograma-semana.md)). Fuente: entidades de [03 §16](../../03-casos-de-uso.md).

- ORM (descripción del `MetaData`): `Backend/app/infrastructure/persistence/models/{base,historial,modelo,retencion}.py`.
- Migraciones: `Backend/alembic/versions/0001_esquema_inicial.py` (esquema), `0002_estado_sistema_inicial.py` (datos), `0003_membresias_socio_id_not_null.py` (R-003) y `0004_membresias_fecha_actividad.py` (R-004). Las aplica **solo** el servicio `migrate` ([10-docker.md](10-docker.md), [ADR-004](../../adr/ADR-004-migracion-datos-al-arrancar.md)); la aplicación nunca migra al arrancar.

## Convenciones

| Aspecto | Regla |
|---|---|
| Nombres | Tablas en plural `snake_case` (03 §16 usa singular: se sigue `database.md`). Constraints por `naming_convention` del `MetaData`: `pk_<t>`, `fk_<t>_<col>_<ref>`, `uq_<t>_<cols>`, `ck_<t>_<nombre>`, `ix_<t>_<cols>`; únicos parciales `ux_<t>_<...>`. |
| PK | `BIGINT GENERATED ALWAYS AS IDENTITY`. Excepción: `estado_sistema.id SMALLINT` con `CHECK (id = 1)`. |
| Auditoría | `created_at`, `updated_at` `TIMESTAMPTZ NOT NULL`, asignados desde el `Clock`. Excepción: la migración `0002` usa `CURRENT_TIMESTAMP` (Alembic no tiene `Clock`). |
| Fechas | Instantes `TIMESTAMPTZ`; fechas de calendario (`fecha_inicio`, `fecha_vencimiento`, `fecha_seguimiento`…) `DATE`. |
| Montos | `NUMERIC(19,4)` con `CHECK >= 0`. |
| Probabilidades | `score`, `prevalencia`, `umbral_*`, `pr_auc_*`: `NUMERIC(10,8)` con `CHECK BETWEEN 0 AND 1`. Ninguna columna `REAL`/`DOUBLE`. |
| Catálogos | `TEXT` + `CHECK (col IN (...))` generado desde los `StrEnum` de `app/domain/common/enums.py` (cambiar el enum cambia el `CHECK`; `alembic check` detecta la deriva). Arreglos `TEXT[]` con `CHECK` de no vacío y subconjunto (`<@`). |
| Semiestructurados | `JSONB`. |
| FK | `ON DELETE RESTRICT` en todas; ninguna `CASCADE`. |
| Borrado lógico | `deleted_at TIMESTAMPTZ NULL` en `socios`, `cargas`, `membresias`, `campanias`, `gestiones_retencion`. |
| Propietario | Sin `user_id`: no hay login (RT-12, [DEVELOPMENT_GUIDELINES](../../DEVELOPMENT_GUIDELINES.md)). |

**Excepción de `deleted_at`** (sin borrado lógico): `modelos`, `listas_priorizadas`, `predicciones` (instantáneas inmutables, RT-07), `intentos_reentrenamiento` (auditoría append-only) y `estado_sistema` (fila única de control). Ninguna se borra: los repositorios no expondrán `Delete`.

## Tablas (10)

### Historial

| Tabla | Columnas relevantes | Restricciones e índices |
|---|---|---|
| `socios` | `cedula VARCHAR(20) NULL` (cédula o pasaporte, D-14), `nombre`, `nombre_normalizado` `TEXT NOT NULL`, `celular`, `correo` `TEXT NULL` | `ux_socios_cedula` único parcial `WHERE cedula IS NOT NULL AND deleted_at IS NULL`; `ix_socios_nombre_normalizado` |
| `cargas` | `tipo` (`TipoCarga`), `fecha_carga TIMESTAMPTZ`, `nombre_archivo TEXT NOT NULL`, `filas_leidas`, `filas_guardadas`, `filas_duplicadas`, `socios_enlazados` `INTEGER NOT NULL` | conteos `>= 0`; `ux_cargas_migracion_historica` único parcial `(tipo) WHERE tipo = 'MIGRACION_HISTORICA' AND deleted_at IS NULL` (una sola migración histórica) |
| `membresias` | FK `socio_id` **NOT NULL** (migración `0003`, R-003), FK `carga_id` NOT NULL; `plan` (`Plan`), `forma_pago` (`FormaPago`) NOT NULL; `estado_registro` (`EstadoRegistro`) NULL; `origen` (`OrigenMembresia`); `fecha_inicio`, `fecha_vencimiento` `DATE NULL`; `fecha_actividad DATE NOT NULL` (migración `0004`, R-004: fecha de inicio o, si falta, primer día del mes de la hoja; ordena el historial y define "previo" y "ya renovó"); `monto_facturado`, `monto_cobrado` `NUMERIC(19,4) NULL`; `asistencias INTEGER NULL`; `observaciones`; `referencia_origen JSONB NULL` (año, hoja, fila del libro); `plan_original`, `forma_pago_original` `TEXT NULL`; `inicio_aproximado BOOLEAN NOT NULL` | montos `>= 0`; `asistencias BETWEEN 0 AND 400`; `ix_membresias_socio_id_fecha_vencimiento`, `ix_membresias_fecha_vencimiento`, `ix_membresias_socio_id_fecha_actividad` (`0004`) |

### Modelo predictivo

| Tabla | Columnas relevantes | Restricciones e índices |
|---|---|---|
| `modelos` | `version INTEGER UNIQUE NOT NULL`, `vigente BOOLEAN`, `fecha_entrenamiento TIMESTAMPTZ`, `ciclos_entrenamiento`, `periodo_desde`/`periodo_hasta DATE`, `prevalencia`, `umbral_alto`, `umbral_medio` (probabilidad), `porcentajes_umbral JSONB`, `artefacto BYTEA`, `metadata_tecnica JSONB` (parámetros y versiones de librerías) | `ux_modelos_vigente` único parcial `WHERE vigente` (un solo vigente); `ciclos_entrenamiento >= 0` |
| `intentos_reentrenamiento` | `fecha TIMESTAMPTZ`, `fecha_programada DATE NULL`, `disparador` (`DisparadorReentrenamiento`), `resultado` (`ResultadoReentrenamiento`), `motivo`, `ciclos_nuevos`, `pr_auc_candidato`, `pr_auc_vigente` NULL, FK `modelo_id` NULL | `ciclos_nuevos >= 0`; probabilidades 0..1 |
| `estado_sistema` | `id SMALLINT` PK, `migracion_historica` (`EstadoMigracion`), `proxima_fecha_reentrenamiento DATE NULL` | `ck_estado_sistema_fila_unica` (`id = 1`). La crea `0002` con `(1, 'PENDIENTE', NULL)` e `ON CONFLICT (id) DO NOTHING` |

### Retención

| Tabla | Columnas relevantes | Restricciones e índices |
|---|---|---|
| `listas_priorizadas` | FK `modelo_id` NOT NULL, `fecha_generacion DATE`, `horizonte_dias`, `top_k`, `creada_en TIMESTAMPTZ` | `horizonte_dias > 0`, `top_k > 0` |
| `predicciones` | FK `lista_id`, `membresia_id` NOT NULL, FK `socio_id` NULL; `score`; `nivel_riesgo` (`NivelRiesgo`); `factores_principales JSONB`; `prioridad`; `dentro_top_k BOOLEAN` | `prioridad > 0`; único `(lista_id, membresia_id)`; `ix_predicciones_lista_id_prioridad` |
| `campanias` | `nombre TEXT`, `descripcion TEXT NULL`, `activa`, `es_ejemplo` `BOOLEAN`, `niveles_riesgo TEXT[]`, `planes TEXT[]`, `prioridad` | arreglos no vacíos y contenidos en `NivelRiesgo` y `PLANES_CAMPANIA` (sin `DIARIO`); `prioridad >= 1` |
| `gestiones_retencion` | FK `prediccion_id`, `membresia_id` NOT NULL, FK `campania_id` NULL; `fecha_asignacion`, `fecha_seguimiento` `DATE`; `estado` (`EstadoGestion`); `responsable`; `contactado BOOLEAN NULL`; `campania_ofrecida`, `campania_aceptada`, `renovo_declarado` NULL; `fecha_contacto DATE NULL`; `observaciones`; `cerrada_en TIMESTAMPTZ NULL` | respuestas con `CHECK` de `RESPUESTAS_OFRECIMIENTO` {SI, NO, NO_APLICA}, `RESPUESTAS_ACEPTACION` {SI, NO, PENDIENTE, NO_APLICA}, `RESPUESTAS_RENOVACION` {SI, NO, PENDIENTE}; `ux_gestiones_retencion_membresia_id` único parcial `WHERE deleted_at IS NULL` (RN-08.1: una gestión por ciclo); `ix_gestiones_retencion_estado_fecha_seguimiento` |

**`membresias.socio_id NOT NULL`** (decisión del usuario, día 2): toda membresía pertenece a un socio. Coherente con el notebook: los registros del histórico sin identidad utilizable (sin cédula válida y nombre normalizado de menos de 5 caracteres; 23 en los libros reales) se descartan antes de guardar y solo cuentan en el informe de la migración. `predicciones.socio_id` sigue `NULL`.

`modelos.version` se guarda como entero; la API la expone como texto `"v<n>"` (p. ej. `"v1"`, ver [API_CONTRACT](../API_CONTRACT.md)).

## Migraciones y pruebas

- `Backend/alembic.ini` sin URL; `alembic/env.py` lee `DATABASE_URL` del entorno y, si falta, termina con un error que nombra la variable sin mostrar valores. `compare_type=True`.
- Pruebas de integración (`tests/integration/persistence/test_migrations.py`) contra la base `app_db_test` (`TEST_DATABASE_URL`). La fixture **aborta** si el nombre de la base no termina en `_test` (el `downgrade base` vaciaría la de desarrollo) y crea la base si no existe. Cubren: 10 tablas, `alembic check` sin diferencias, cada `CHECK` e índice único, ciclo `upgrade head` → `downgrade base` → `upgrade head`.
- `0003` (`down_revision = "0002"`): `upgrade` hace `ALTER COLUMN socio_id SET NOT NULL` y **falla** si ya existen membresías sin socio (hoy ninguna base las tiene); `downgrade` lo devuelve a `NULL`. Las pruebas verifican `IntegrityError` con `socio_id NULL` tras `upgrade head`, aceptación tras `downgrade 0002` y `alembic current` → `0003`.
- `0004` (`down_revision = "0003"`): añade `fecha_actividad DATE NULL`, la rellena con `fecha_inicio` donde exista, hace `SET NOT NULL` (falla si queda alguna fila sin valor) y crea `ix_membresias_socio_id_fecha_actividad`; `downgrade` elimina índice y columna. Las pruebas verifican `IntegrityError` sin `fecha_actividad`, el ciclo `downgrade 0003` → `upgrade head` y `alembic current` → `0004 (head)`.
- Fixture `db_session` (`tests/integration/conftest.py`): `Session` sobre una conexión con transacción externa que termina en `rollback`; la usan las pruebas de repositorios ([11-historico.md](11-historico.md)).

## Pendientes

- **S23**: rol de BD sin superusuario para la app y rol separado para migraciones (día 7).
