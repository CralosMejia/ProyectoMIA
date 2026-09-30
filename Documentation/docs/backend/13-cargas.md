# Backend · 13 · Carga por plantilla (CU-01)

Creado en R-007 (Día 4). Caso de uso: [03 §4 CU-01](../../03-casos-de-uso.md). Contrato y mensajes exactos: [API_CONTRACT §Cargas](../API_CONTRACT.md#cargas-cu-01-r-007). Esquema: [09](09-esquema-base-de-datos.md) (migración `0005`).

## Flujo

`POST /cargas/vista-previa` y `POST /cargas` comparten el mismo análisis (`_analizar` en `app/application/cargas/procesar_carga.py`): **leer → validar por fila → consultar socios y claves → planificar**. La vista previa no escribe ni hace `commit`. La confirmación revalida el archivo completo en el servidor (no hay estado entre ambas llamadas) y guarda **todo o nada** en una sola transacción. Ninguna de las dos dispara reentrenamiento (RN-01.11).

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Dominio | `app/domain/cargas/fila.py` | `FilaPlantilla` (número real de fila ≥ 2 y valores crudos A..N), `PlantillaLeida` |
| Dominio | `app/domain/cargas/documento.py` | Cédula: normalización y módulo 10; excepción de pasaporte |
| Dominio | `app/domain/cargas/validacion.py` | `validar_fila` → `FilaValida` o todos sus `ErrorFila(fila, columna, motivo)`; una regla por columna A..M |
| Dominio | `app/domain/cargas/enlace.py` | `planificar(...)` → `PlanCarga`: socio por fila, duplicados, avisos. Función pura y determinista (orden de fila) |
| Dominio | `app/domain/cargas/errores.py` | `PlantillaInvalidaError` y sus mensajes (archivo rechazado completo) |
| Aplicación | `app/application/cargas/ports.py` | `LectorPlantilla`, `ConsultasCarga`, `EscrituraCarga`, `ContextoCargas`, `UnidadDeTrabajoCargas` (`Protocol`); `ClaveMembresia` |
| Aplicación | `app/application/cargas/procesar_carga.py` | `PrevisualizarCarga` (query) y `ConfirmarCarga` (command) |
| Infraestructura | `app/infrastructure/cargas/lector_plantilla.py` | `LectorPlantillaOpenpyxl` |
| Infraestructura | `app/infrastructure/persistence/repositories/cargas.py` | `SqlAlchemyConsultasCarga`, `SqlAlchemyEscrituraCarga` (sin `commit`) |
| Infraestructura | `app/infrastructure/persistence/unit_of_work_cargas.py` | Sesión única, bloqueo, `rollback` si no hay `commit` |
| API | `app/api/routers/cargas.py` | Lectura acotada a 5 MB + 1 byte y mapeo de errores |

## Lector

- `openpyxl` con `read_only=True` y `data_only=True`; solo columnas A..N de la hoja `Registros`. O y P (fórmulas hasta la fila 501) se ignoran siempre.
- Títulos de la fila 1, A..N, iguales a los oficiales tras `strip()` (mayúsculas y tildes exactas).
- Sin `Registros` y con alguna hoja cuyo nombre es un mes → formato antiguo. Bytes que no son `.xlsx` → dañado.
- Filas vacías intermedias se saltan conservando su número real. Máximo 500 filas con datos (`MAX_FILAS_PLANTILLA`).

## Validación por fila

- **C (cédula):** texto → sin espacios; celda numérica → `str(int)` y, si quedan 9 dígitos, se antepone `0` (Excel pierde el cero). Válida = 10 dígitos con verificador módulo 10 (coeficientes 2,1,2,…), sin reglas de provincia. **Pasaporte:** si Observaciones contiene la palabra completa `PASAPORTE` (sin distinguir mayúsculas) se acepta 5..20 caracteres `[A-Za-z0-9]`.
- **A, F, I:** catálogos con `strip().upper()`; A vacío es válido. **B:** ≥ 5 letras tras normalizar. **E:** correo opcional bien formado.
- **G, H:** fecha o texto `AAAA-MM-DD`, entre 2024-01-01 y 2035-12-31; H > G; duración 21..400 días salvo `DIARIO` (solo H > G).
- **K, L:** montos `Decimal` ≥ 0 con máximo 2 decimales (punto o coma); L obligatorio. **M:** entero 0..400 (acepta `7.0`).
- Una fila con varios fallos devuelve todos. Ningún motivo contiene el valor de la celda.

## Enlace y duplicados

- **Enlace (RN-01.9 / D-03):** 1) cédula existente → ese socio (la búsqueda de `0XXXXXXXXX` prueba también `XXXXXXXXX`, porque el histórico guardó cédulas de 9 dígitos; no se reescribe la histórica); 2) si no, exactamente un socio **sin cédula** con el mismo `nombre_normalizado` → se enlaza y recibe la cédula (celular y correo solo si estaban vacíos), aunque sus filas resulten duplicadas; 3) dos o más homónimos → socio nuevo y aviso "Fila N: hay varios socios históricos con el mismo nombre; se creó un socio nuevo." (sin el nombre). Varias filas con la misma cédula nueva → un solo socio. Un candidato por nombre ya tomado por otra cédula del archivo no se reutiliza.
- **Duplicado (RN-01.8 / D-04):** `ClaveMembresia` = socio + `fecha_inicio` + `fecha_vencimiento` + `plan`, contra membresías no borradas (históricas o de cargas) y contra filas anteriores del mismo archivo. Las duplicadas cuentan como válidas y no se guardan. No hay índice único de duplicados: D-04 conserva los duplicados exactos del histórico.
- Consultas: una por tipo (sin N+1), SQL parametrizado; el enlace por nombre usa `ix_socios_nombre_normalizado_sin_cedula` (`0005`); los duplicados, `ix_membresias_socio_id_fecha_vencimiento`.

## Transacción y concurrencia

`ConfirmarCarga` toma `pg_advisory_xact_lock(7_310_004)` (`bloquear()`) **antes** de consultar duplicados; crea socios, asigna cédulas, inserta membresías y la fila de `cargas`, y hace **un** `commit`. Si algo falla antes, la unidad de trabajo hace `rollback` y no queda nada. Dos confirmaciones del mismo archivo en paralelo: la segunda espera y ve todo duplicado → `422`.

Membresía guardada: `origen=PLANTILLA`, `fecha_actividad = fecha_inicio`, `inicio_aproximado=False`, `estado_registro` informativo (RN-01.7), `plan_original`/`forma_pago_original` = texto de la celda. Carga: `tipo=PLANTILLA`, `fecha_carga = clock.now()`, `nombre_archivo` = nombre base recortado a 255.

**Efecto en la lista:** la advertencia de datos antiguos usa la fecha de la última carga, y las membresías nuevas entran en la cartera de `POST /listas` ([12](12-modelo-y-listas.md)).

## Decisiones de R-007 (reversibles)

| | Decisión |
|---|---|
| (a) | `filas_validas` incluye duplicadas; `puede_confirmar` = sin errores y al menos una fila nueva |
| (b), (c) | Clave de duplicado y reglas de enlace de arriba |
| (d), (e) | Cédula con y sin cero inicial; 10 dígitos módulo 10 sin provincia; celda numérica de 9 dígitos → antepone `0` |
| (f) | Títulos A..N exactos; formato antiguo detectado por nombres de mes |
| (g) | 5 MB máximo → `413`; nombre de archivo = nombre base ≤ 255 |
| (h) | Montos `Decimal` con máximo 2 decimales; nunca `float` fuera del lector |
| (i) | Valores de la membresía guardada, de arriba |
| (j) | Bloqueo consultivo de transacción; sin índice único de duplicados |
| (k) | Mapeo de códigos de [API_CONTRACT §Cargas](../API_CONTRACT.md#cargas-cu-01-r-007) |
| (l) | Confirmaciones de prueba y E2E solo en el stack aislado `mtabolic-e2e` ([10](10-docker.md)) |

Fuera de R-007: anular cargas (RN-01.3), alerta de datos del mes (D6-BE-06 / D6-FE-04).

## Pruebas

Unitarias: `tests/unit/domain/cargas/` (TDD en `test_documento.py` y `test_validacion.py`), `tests/unit/application/cargas/` (dobles), `tests/unit/infrastructure/cargas/test_lector_plantilla.py`. Integración (PostgreSQL `app_db_test`): `test_cargas_repository.py`, `test_unit_of_work_cargas.py`, `test_cargas_api.py`, `test_cargas_api_bordes.py`, `test_cargas_lista_api.py` (la carga alimenta la lista), `test_contract_cargas.py`. Solo fixtures sintéticos o libros construidos en `tmp_path`. Sin login (RT-12): sin pruebas de aislamiento entre usuarios.
