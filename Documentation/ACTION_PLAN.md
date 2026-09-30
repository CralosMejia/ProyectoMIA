# ACTION PLAN — board vivo

> Board corto. El detalle por producto va en `Documentation/products/P##-*.md` (aún no existe ninguno).
> Estados de tarea: `[ ]` pendiente · `[~]` en curso · `[x]` hecha · `[!]` bloqueada.

## ACTIVO

_(ninguno)_

## TERMINADOS RECIENTEMENTE

### R-009 — Día 5 del cronograma: campañas (CU-06, CU-07) y gestión de retención (CU-08, CU-10) desde la Lista · **DONE** 2026-09-30

**Cierre:** Backend 1.671 pytest, `ruff`, `format` (267), `mypy app` (121), `lint-imports` (7), `verificar_lista.py` salida 0; Frontend 570 Vitest, `build`, `lint` 0; E2E 3/3 en el stack aislado 8081 (`health`, `carga-lista-excel`, `campanias-gestion`); contra 8080, 1 en verde y 2 saltados a propósito. Stack principal en `0008`, `LISTO`: socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0, campañas 3 (de ejemplo), gestiones 0; navegador: Campañas con las 3 "Ejemplo" y formulario; Lista con formulario de gestión. Reinicio de la base principal ejecutado el 30-09-2026 (autorizado por el usuario). Seguridad diferida al día 7 (05 §1). Contrato y esquema → [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md). **Escalado al usuario:** [03 §15 CU-12](03-casos-de-uso.md) aún dice que el Excel no lleva gestión ni campaña; no se creó `docs/backend/14-campanias-y-gestiones.md` (el detalle está en API_CONTRACT, 09, 12 y ADR-008); la excepción de `now()` en `0007` no se añadió a DEVELOPMENT_GUIDELINES.

**Objetivo:** el personal parametriza campañas (crear, editar, inactivar; 3 de ejemplo), ve las sugeridas para un socio de la lista, crea la gestión (campaña o "No asignar", fecha de seguimiento, responsable), registra el resultado hasta cerrarla con Renovó Sí/No, y ve el estado de la gestión y la campaña en la tabla de la Lista y en su Excel.

**Fuente:** [05 §3 Día 5](05-cronograma-semana.md) (D5-BD-01..02, D5-BE-01..04, D5-FE-01..03) · [03 §9–§11, §13](03-casos-de-uso.md) (CU-06, CU-07, CU-08, CU-10; RN-06.x, RN-07.x, RN-08.x, RN-10.x) y §16 (entidades `campania`, `gestion_retencion`) · [04 §2 D-16, D-17, D-18](04-pendientes-para-iniciar-desarrollo.md) · [06](06-como-funciona-la-lista.md) · `docs/API_CONTRACT.md` §Operaciones de negocio · `docs/backend/09-esquema-base-de-datos.md` §Retención.

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Nada cae en `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance (editar una gestión cerrada y más de una gestión por ciclo siguen fuera: se **rechazan**). Sin reactivar campañas (CU-06 solo pide crear, editar e inactivar; el contrato no tiene `activar`).
- **Fuera de R-009 (día 6):** `GET /alertas` y `GET /gestiones?filtro=` (CU-09, D6-BD-01/D6-BE-01/D6-FE-01) **siguen en `501`**; el requerimiento los nombra entre los endpoints en `501`, pero pertenecen al día 6 y su pantalla (Inicio) también. Se avisa al usuario (decisión (a), reversible).
- **Proceso (05 §1):** el día 5 no tiene tareas marcadas **TDD** → pruebas de los criterios de aceptación en todas. Revisión de seguridad diferida a la revisión única del día 7. Sin login (RT-12): no hay pruebas de aislamiento entre usuarios. Datos de prueba ficticios; ni logs ni mensajes de error llevan nombres, cédulas ni celulares.
- **Stacks:** confirmaciones de prueba y E2E solo en `mtabolic-e2e` (8081). En el principal (8080) solo verificación: se aplican `0007` (3 campañas de ejemplo) y `0008`; **no** se crean campañas ni gestiones.
- **Decisiones del planner (reversibles; se avisan al usuario):**
  - (a) Alcance de endpoints: se implementan `GET/POST /campanias`, `PUT /campanias/{id}`, `POST /campanias/{id}/inactivar`, `GET /predicciones/{id}/campanias-sugeridas`, `POST /gestiones`, `GET /gestiones/{id}`, `PUT /gestiones/{id}/resultado`. `GET /alertas` y `GET /gestiones?filtro` quedan en `501` hasta el día 6.
  - (b) **Contrato:** se mantiene salvo: `PrediccionDTO` **añade** `gestion_id: int | null` (para abrir la gestión desde la lista); `CampaniaEntradaDTO.prioridad` pasa a `1..999` (evita desbordar `INTEGER` → 500). `GestionDTO.fecha_asignacion` (datetime) = `created_at` de la gestión (instante UTC); la columna `fecha_asignacion DATE` guarda la fecha de negocio (Ecuador) y la usará el dashboard del día 6. `gestion_estado` y `campania_asignada` de `PrediccionDTO` dejan de ser siempre `null`.
  - (c) **RN-08.2 (la campaña queda como estaba al asignarla):** migración de esquema `0008`: `gestiones_retencion.campania_nombre TEXT NULL` (instantánea del nombre al crear la gestión) con `CHECK ((campania_id IS NULL) = (campania_nombre IS NULL))` (`campania_nombre_coherente`); relleno desde `campanias.nombre` para filas existentes (hoy 0). `GestionDTO.campania_nombre` y `PrediccionDTO.campania_asignada` salen de esa columna: editar o inactivar la campaña no cambia gestiones ya creadas.
  - (d) **Campañas de ejemplo (`0007`, D-17):** migración de **datos** en Alembic (la ejecuta el servicio `migrate`, como `0002`; no es una migración al arrancar). Inserta con `es_ejemplo = true`, `activa = true`, `created_at = updated_at = now()` de la base (excepción al `Clock`, solo en migraciones), **solo si no existe** ya una campaña no borrada con ese nombre:
    1. "Ejemplo: Llamada personal antes del vencimiento" — "Llamar al socio antes de que venza su plan para recordarle sus avances y resolver dudas." — `ALTO` — `MENSUAL, TRIMESTRAL, SEMESTRAL, ANUAL, OTRO` — prioridad 1.
    2. "Ejemplo: Renovación anticipada" — "Ofrecer renovar antes del vencimiento con el beneficio que Mtabolic defina." — `ALTO, MEDIO` — `MENSUAL, TRIMESTRAL` — prioridad 2.
    3. "Ejemplo: Recordatorio de renovación" — "Enviar un recordatorio amable de la fecha de vencimiento." — `MEDIO, BAJO` — todos los planes de campaña — prioridad 3.
    `downgrade` borra solo esas 3 filas `es_ejemplo` y **falla con mensaje claro** si alguna gestión las referencia (solo desarrollo). La aplicación no calcula descuentos (RN-06.1).
  - (e) **Campañas (CU-06):** nombre recortado 1..120; descripción recortada ≤ 500 (vacía → `null`); `niveles_riesgo` y `planes` no vacíos, sin `DIARIO`, **deduplicados** y guardados en orden canónico (`ALTO, MEDIO, BAJO`; `MENSUAL, TRIMESTRAL, SEMESTRAL, ANUAL, OTRO`); prioridad 1..999. Se permiten nombres repetidos. Editar no cambia `activa` ni `es_ejemplo` (el indicador "ejemplo" marca el origen). Inactivar una ya inactiva → `200` sin cambios (idempotente). Editar una inactiva se permite. `GET /campanias`: sin `deleted_at`, ordenadas `activa DESC, prioridad, lower(nombre), id`. No hay `DELETE` ni borrado físico.
  - (f) **Sugerencias (CU-07):** nivel = `predicciones.nivel_riesgo` (el de esa lista); plan = `membresias.plan` del ciclo. Campañas `activa AND deleted_at IS NULL AND nivel = ANY(niveles_riesgo) AND plan = ANY(planes)`, orden `prioridad, lower(nombre), id`. Plan `DIARIO` → `[]`. La opción "No asignar campaña" la pinta el frontend (`campania_id = null` en `POST /gestiones`); el backend devuelve solo campañas.
  - (g) **Gestión (CU-08):** "hoy" = `hoy_en_negocio(clock.now())` (Ecuador). Rango permitido `[hoy, vencimiento + 30]`; fuera → `422` "La fecha de seguimiento debe estar entre AAAA-MM-DD y AAAA-MM-DD."; si `vencimiento + 30 < hoy` → `422` "El plazo de seguimiento de este ciclo ya termino." Fecha sugerida (la calcula el frontend con la misma regla, probada con los mismos casos) = `max(vencimiento + 25, hoy)`. Una gestión por **ciclo** (`membresia_id`), aunque la membresía esté en varias listas: la segunda → `409` "El ciclo de membresia ya tiene una gestion." (también si llega por carrera: la violación de `ux_gestiones_retencion_membresia_id` se traduce a `409`). Campaña inexistente o borrada → `404`; inactiva o incompatible con el nivel/plan de la predicción → `422` "La campana no esta activa o no aplica a este socio." Se guarda: `prediccion_id`, `membresia_id` (de la predicción), `campania_id`, `campania_nombre` (instantánea), `fecha_asignacion = hoy`, `estado = PENDIENTE`, `responsable` recortado. Score, nivel y versión del modelo se leen por la predicción (RT-07). Todo en una transacción.
  - (h) **Resultado (CU-10), `PUT` reemplaza los campos del resultado** (`contactado`, `campania_ofrecida`, `campania_aceptada`, `renovo_declarado`, `fecha_contacto`, `observaciones`, `responsable`); `fecha_seguimiento` `null` = se conserva. Coherencia (`422` con mensaje propio de cada regla):
    - sin campaña → ofrecida y aceptada = `NO_APLICA`;
    - con campaña y `contactado = false` → ofrecida y aceptada = `NO_APLICA`;
    - con campaña y `contactado = true` → ofrecida ∈ {`SI`, `NO`}; ofrecida `NO` → aceptada `NO_APLICA`; ofrecida `SI` → aceptada ∈ {`SI`, `NO`, `PENDIENTE`};
    - `contactado = true` → `fecha_contacto` obligatoria con `fecha_asignacion ≤ fecha_contacto ≤ hoy`; `contactado = false` → `fecha_contacto` debe ser `null`.
    - `renovo_declarado` `SI`/`NO` → `CERRADA`, `cerrada_en = clock.now()` (`fecha_seguimiento` recibida se ignora); `PENDIENTE` → sigue `PENDIENTE` y, si llega `fecha_seguimiento`, se valida con el rango de (g).
    - Gestión `CERRADA` → `409` "La gestion esta cerrada y no se puede modificar." (se comprueba con `SELECT … FOR UPDATE` dentro de la transacción). El resultado no toca membresías ni etiquetas (RN-10.2).
  - (i) **Lista (D5-FE-03):** la gestión de un ítem se busca por `membresia_id` (no por `prediccion_id`), con `deleted_at IS NULL`, en la misma consulta de `obtener` (LEFT JOIN, sin N+1). Tabla: columnas nuevas **"Gestión"** (`Sin gestión` / `Pendiente` / `Cerrada`) y **"Campaña"** (nombre de la instantánea; `Sin campaña` si la gestión no tiene; `—` si no hay gestión) y columna de acción con botón **"Gestionar"** (sin gestión), **"Registrar resultado"** (pendiente) o **"Ver gestión"** (cerrada, solo lectura), con nombre accesible que incluye la prioridad (p. ej. "Gestionar prioridad 3"), no el nombre del socio.
  - (j) **Excel (D5-FE-03, "Excel igual a la tabla", ADR-007):** se añaden las columnas I "Gestión" y J "Campaña" con los mismos textos que la pantalla, con el estado **al momento de descargar**. El botón de acción no va al Excel. Sustituye el criterio de R-008 T1 que prohibía estado de gestión y campaña en el Excel.
  - (k) **Frontend:** el formulario de gestión vive en el feature `lista` (su API ya está en `lista-api.ts`); la página Campañas en el feature `campanias`. Ventana modal con `Modal` de `shared/ui`. Parte 1 (solo al crear): radios con las campañas sugeridas (nombre + descripción) y "No asignar campaña" (seleccionada por defecto si no hay sugerencias; si hay, ninguna preseleccionada y se exige elegir); "Fecha de seguimiento" con la sugerida y `min`/`max` del rango; "Responsable (opcional)" `maxLength` 120. Parte 2 (gestión pendiente): "¿Se contactó al socio?" Sí/No; "¿Se ofreció la campaña?" Sí/No/No aplica; "¿Aceptó la campaña?" Sí/No/Pendiente/No aplica; "¿Renovó?" Sí/No/Pendiente; "Fecha del contacto"; "Observaciones" (`maxLength` 500); "Responsable"; "Fecha de seguimiento" solo si Renovó = Pendiente. Las opciones incoherentes se **deshabilitan** y se valida también al guardar (mensaje local), y los `422`/`409` del servidor se muestran con `ErrorAlert`. Tras guardar se recarga la lista para ver la columna actualizada. "Hoy" en el navegador = fecha local (el PC está en Ecuador).
- **Excepción al límite de 4 archivos:** `__init__.py` vacíos; `"0006 (head)"` → `"0008 (head)"` en `test_migrations_robustness.py` (T3/T4); añadir `gestion_id`/`gestion_estado`/`campania_asignada` a constructores de dobles y datos de prueba (`tests/unit/application/listas/dobles.py`, `tests/integration/api/listas_datos.py`, `scripts/verificar_lista.py` si construye `ItemLista`) (T13); ajuste de la expectativa `501` en `test_contract_campanias.py` / `test_contract_gestiones.py` (T8, T12); `Frontend/src/features/lista/components/TablaLista.test.tsx` y fixtures de `Prediccion` con `gestionId` (T17).

**Tareas**

- [x] **T1** · `domain` · Reglas de una campaña (validación, normalización y compatibilidad)
  - Archivos: `Backend/app/domain/campanias/campania.py` (principal, nuevo: `DatosCampania` frozen con factory `crear(...)`, `CampaniaInvalidaError(DomainError)`, `es_compatible(activa, niveles, planes, nivel, plan) -> bool`, `clave_orden(prioridad, nombre, id)`), `Backend/app/domain/campanias/__init__.py`, `Backend/tests/unit/domain/campanias/test_campania.py` (nuevo).
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas; `03-casos-de-uso.md` §9–§10; decisiones (e), (f).
  - Aceptación:
    - `crear(nombre="  Renovación  ", descripcion="  ", niveles=[MEDIO, ALTO, MEDIO], planes=[TRIMESTRAL, MENSUAL], prioridad=1)` → nombre `"Renovación"`, descripción `None`, niveles `(ALTO, MEDIO)`, planes `(MENSUAL, TRIMESTRAL)`.
    - Nombre vacío tras recortar o > 120, descripción > 500, niveles o planes vacíos, plan `DIARIO`, prioridad 0 o 1000 → `CampaniaInvalidaError` con mensaje sin datos del socio.
    - `es_compatible`: campaña solo `BAJO` + socio `ALTO` → `False`; solo `MENSUAL` + socio `ANUAL` → `False`; inactiva → `False`; `ALTO`+`MENSUAL` en una campaña `[ALTO,MEDIO]`/`[MENSUAL]` activa → `True`; plan `DIARIO` → `False`.
    - Orden: prioridades `[2,1,1]` con nombres `["b","Zeta","alfa"]` → `alfa, Zeta, b` (sin distinguir mayúsculas; empate final por id). Solo librería estándar; `lint-imports` en verde.
  - Pruebas: unitarias.

- [x] **T2** · `domain` · Reglas de una gestión (rango de fecha, coherencia del resultado y cierre)
  - Archivos: `Backend/app/domain/gestiones/reglas.py` (principal, nuevo: `rango_seguimiento(hoy, vencimiento) -> (desde, hasta)`, `fecha_sugerida(hoy, vencimiento)`, `validar_fecha_seguimiento(...)`, `validar_resultado(con_campania, contactado, ofrecida, aceptada, fecha_contacto, fecha_asignacion, hoy)`, `estado_tras_resultado(renovo) -> EstadoGestion`), `Backend/app/domain/gestiones/errores.py` (nuevo: `FechaSeguimientoFueraDeRangoError`, `PlazoSeguimientoTerminadoError`, `ResultadoIncoherenteError`, `GestionCerradaError`, `GestionDuplicadaError`, `CampaniaNoAplicableError`, todas `DomainError`), `Backend/app/domain/gestiones/__init__.py`, `Backend/tests/unit/domain/gestiones/test_reglas.py` (nuevo).
  - Docs: `03-casos-de-uso.md` §11, §13; decisiones (g), (h).
  - Aceptación (sin reloj: `hoy` llega como parámetro):
    - hoy 2026-09-29, vencimiento 2026-10-05 → rango `2026-09-29..2026-11-04`, sugerida `2026-10-30`. Vencimiento 2026-09-01 → rango `2026-09-29..2026-10-01`, sugerida `2026-09-29`. Vencimiento 2026-08-29 (venc+30 = 2026-09-28 < hoy) → `PlazoSeguimientoTerminadoError`.
    - `validar_fecha_seguimiento`: 2026-09-28 o 2026-11-05 (con venc 2026-10-05) → `FechaSeguimientoFueraDeRangoError` cuyo mensaje contiene `2026-09-29` y `2026-11-04`; los extremos son válidos.
    - `validar_resultado` (parametrizada con cada fila de (h)): no contactado + ofrecida `SI` → error; sin campaña + ofrecida `NO` → error; contactado + ofrecida `NO` + aceptada `SI` → error; contactado + ofrecida `SI` + aceptada `NO_APLICA` → error; contactado sin `fecha_contacto` → error; `fecha_contacto` futura o anterior a `fecha_asignacion` → error; no contactado con `fecha_contacto` → error; combinaciones coherentes de (h) → sin error.
    - `estado_tras_resultado`: `SI`/`NO` → `CERRADA`; `PENDIENTE` → `PENDIENTE`.
  - Pruebas: unitarias.

- [x] **T3** · `db` · Migración de datos `0007`: 3 campañas de ejemplo (D5-BD-02, D-17)
  - Archivos: `Backend/alembic/versions/0007_campanias_ejemplo.py` (principal), `Backend/tests/integration/persistence/test_migrations.py`, `Backend/tests/integration/persistence/test_migrations_robustness.py` (línea de `head`, excepción mecánica).
  - Docs: `.claude/rules/database.md` §Migraciones; `docs/backend/09-esquema-base-de-datos.md` §Retención, §Migraciones y pruebas; decisión (d).
  - Aceptación (`app_db_test`):
    - `revision="0007"`, `down_revision="0006"`. Tras `upgrade 0007` hay exactamente 3 filas en `campanias` con los nombres, niveles, planes, prioridades y descripciones de (d), `es_ejemplo = true`, `activa = true`, `deleted_at IS NULL`.
    - Base con una campaña previa llamada "Ejemplo: Renovación anticipada" → `upgrade` no la duplica (quedan 3 con ese conjunto de nombres). Sin SQL construido con f-strings; valores enlazados o literales fijos.
    - `downgrade 0006` elimina solo esas 3 filas (una campaña creada a mano sigue); con una gestión que referencia una de ejemplo → `downgrade` falla con mensaje claro y no borra nada. Otras tablas con conteos iguales antes/después.
  - Pruebas: integración.

- [x] **T4** · `db` · Migración de esquema `0008`: instantánea `gestiones_retencion.campania_nombre` (RN-08.2)
  - Archivos: `Backend/alembic/versions/0008_gestiones_campania_nombre.py` (principal), `Backend/app/infrastructure/persistence/models/retencion.py` (`GestionRetencion.campania_nombre` + `CheckConstraint` `campania_nombre_coherente`), `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`, `Backend/tests/integration/persistence/test_migrations.py`.
  - Docs: `.claude/rules/database.md` §Migraciones; `docs/backend/09-esquema-base-de-datos.md` §Retención; decisión (c).
  - Aceptación:
    - `revision="0008"`, `down_revision="0007"`. Sobre una base en `0007` con una gestión con campaña y otra sin campaña → `upgrade` rellena `campania_nombre` con el nombre de la campaña y deja `NULL` la otra; luego añade el `CHECK`.
    - Tras `upgrade head`: insertar `campania_id` con `campania_nombre NULL` o al revés → `IntegrityError` (`campania_nombre_coherente`). `alembic check` sin diferencias; `alembic current` → `0008 (head)`; ciclo `downgrade 0007` → `upgrade head` funciona; base vacía también aplica.
  - Pruebas: unitaria (metadatos) + integración.

- [x] **T5** · `application` · CU-06: listar, crear, editar e inactivar campañas
  - Archivos: `Backend/app/application/campanias/gestionar_campanias.py` (principal, nuevo: `ListarCampanias`, `CrearCampania`, `EditarCampania`, `InactivarCampania`, `CampaniaNoExisteError`), `Backend/app/application/campanias/ports.py` (nuevo: `CampaniaGuardada`, `CampaniaRepository` con `listar()`, `obtener(id)`, `crear(datos)`, `actualizar(id, datos)`, `inactivar(id)`, `compatibles(nivel, plan)`; `ContextoCampanias`, `UnidadDeTrabajoCampanias`), `Backend/app/application/campanias/dtos.py` (`prioridad` `le=999`, ejemplos), `Backend/tests/unit/application/campanias/test_gestionar_campanias.py` (nuevo, con dobles en memoria).
  - Docs: `.claude/rules/backend.md` §Application, §API; `docs/API_CONTRACT.md` §Operaciones de negocio; decisiones (b), (e).
  - Aceptación:
    - Crear con los datos de T1 → el repositorio recibe `DatosCampania` normalizado, `activa=True`, `es_ejemplo=False`; se hace **un** `commit`; devuelve `CampaniaDTO`.
    - Editar id inexistente → `CampaniaNoExisteError` sin `commit`; editar conserva `activa` y `es_ejemplo`.
    - Inactivar activa → `activa=False`, un `commit`; inactivar ya inactiva → devuelve la campaña igual (idempotente). Inactivar inexistente → `CampaniaNoExisteError`.
    - Datos inválidos que pasen el DTO pero no el dominio → `CampaniaInvalidaError`, sin `commit`. `CampaniaEntradaDTO(prioridad=1000)` → `ValidationError`. El puerto no expone borrado. `mypy app` en verde.
  - Pruebas: unitarias.

- [x] **T6** · `application` · CU-07: sugerencias para una predicción
  - Archivos: `Backend/app/application/campanias/sugerir_campanias.py` (principal, nuevo: `SugerirCampanias`, `PrediccionNoExisteError`), `Backend/app/application/campanias/ports.py` (puerto `PerfilPrediccion.obtener(prediccion_id) -> (nivel, plan) | None` dentro de `ContextoCampanias`), `Backend/tests/unit/application/campanias/test_sugerir_campanias.py` (nuevo).
  - Docs: `03-casos-de-uso.md` §10; decisión (f).
  - Aceptación:
    - Predicción `ALTO`/`MENSUAL` → pide `compatibles(ALTO, MENSUAL)` y devuelve las campañas en el orden del repositorio como `list[CampaniaDTO]`; sin compatibles → `[]`.
    - Predicción inexistente → `PrediccionNoExisteError`. Plan `DIARIO` → `[]` sin consultar campañas. Solo lectura (sin `commit`).
  - Pruebas: unitarias.

- [x] **T7** · `infra` · Repositorio de campañas y unidad de trabajo de retención (D5-BD-01)
  - Archivos: `Backend/app/infrastructure/persistence/repositories/campanias.py` (principal, nuevo: `SqlAlchemyCampaniaRepository`, `SqlAlchemyPerfilPrediccion`), `Backend/app/infrastructure/persistence/unit_of_work_retencion.py` (nuevo: `SqlAlchemyUnidadDeTrabajoRetencion`, mismo patrón que `unit_of_work_listas.py`; implementa `UnidadDeTrabajoCampanias` y, en T11, la de gestiones), `Backend/tests/integration/persistence/test_campanias_repository.py` (nuevo).
  - Docs: `.claude/rules/database.md` §Reparto de herramientas, §Reglas innegociables; `docs/backend/09-esquema-base-de-datos.md` §Retención; decisiones (e), (f).
  - Aceptación (PostgreSQL `app_db_test`, fixture `db_session`, reloj fijo):
    - `crear` → fila con `created_at`/`updated_at` del `Clock`; `actualizar` cambia `updated_at`; `inactivar` pone `activa=false` y **no** `deleted_at`; ninguna fila desaparece (conteo igual). No existe método de borrado.
    - `listar` excluye `deleted_at` y ordena `activa DESC, prioridad, lower(nombre), id`.
    - `compatibles(ALTO, MENSUAL)` con campañas {solo `BAJO`; solo `ANUAL`; inactiva compatible; borrada compatible; dos compatibles con prioridad 1 "beta"/"Alfa" y una con prioridad 2} → exactamente `Alfa, beta, <prioridad 2>`.
    - `SqlAlchemyPerfilPrediccion.obtener` → `(nivel_riesgo de la predicción, plan de la membresía)`; id inexistente → `None`. SQL parametrizado (`ANY(:param)` o `.any()`), sin `commit` en el repositorio.
  - Pruebas: integración.

- [x] **T8** · `api` · Router de campañas real (D5-BE-01, D5-BE-02)
  - Archivos: `Backend/app/api/routers/campanias.py` (principal: quita `501`, mapea `CampaniaNoExisteError`/`PrediccionNoExisteError` → `404`, `CampaniaInvalidaError` → `400 validation_error`; ejemplos con campañas de ejemplo), `Backend/app/api/dependencies.py` (fábricas de los casos de uso con `SqlAlchemyUnidadDeTrabajoRetencion`), `Backend/tests/integration/api/test_campanias_api.py` (nuevo), `Backend/tests/integration/api/test_contract_campanias.py` (quita la expectativa `501`).
  - Docs: `docs/API_CONTRACT.md` §Operaciones de negocio; `.claude/rules/backend.md` §API; decisiones (b), (e), (f).
  - Aceptación (PostgreSQL de pruebas en `head`):
    - `GET /api/v1/campanias` → `200` con las 3 de ejemplo (`es_ejemplo: true`) en orden de prioridad.
    - `POST /campanias` válido → `201` y aparece en `GET`; `{"nombre":"   ", …}`, `niveles_riesgo: []`, `planes: ["DIARIO"]`, `prioridad: 0` o campo extra → `400 validation_error` sin guardar (conteo igual).
    - `PUT /campanias/{id}` → `200` con los datos nuevos; id inexistente → `404` "La campana no existe."; id `0` → `400`.
    - `POST /campanias/{id}/inactivar` → `200` `activa:false`; repetir → `200` igual; la fila sigue en la base (`SELECT count(*)` igual).
    - `GET /predicciones/{id}/campanias-sugeridas` (predicción ficticia `ALTO`/`MENSUAL`) → las compatibles activas por prioridad; tras inactivar una, ya no aparece; predicción inexistente → `404` "La prediccion no existe.".
    - `/openapi.json`: ningún endpoint de campañas documenta ya `501`; `prioridad` con `maximum` 999; ejemplos de request y de cada respuesta.
  - Pruebas: integración (API).

- [x] **T9** · `application` · CU-08: crear la gestión (D5-BE-03)
  - Archivos: `Backend/app/application/gestiones/crear_gestion.py` (principal, nuevo: `CrearGestion`), `Backend/app/application/gestiones/ports.py` (nuevo: `DatosPrediccionGestion` (membresía, vencimiento, nivel, plan, score, versión, nombre del socio), `NuevaGestion`, `GestionDetalle`, `GestionRepository` con `datos_prediccion(id)`, `existe_para_membresia(id)`, `crear(nueva)`, `obtener(id)`, `obtener_para_actualizar(id)`, `guardar_resultado(...)`; `ContextoGestiones` con `gestiones` y `campanias`; `UnidadDeTrabajoGestiones`), `Backend/tests/unit/application/gestiones/test_crear_gestion.py` (nuevo, dobles en memoria, reloj fijo).
  - Docs: `03-casos-de-uso.md` §11; `.claude/rules/backend.md` §Application; decisiones (b), (c), (g).
  - Aceptación (reloj `2026-09-29T15:00Z`; predicción `ALTO`/`MENSUAL`, vencimiento 2026-10-05):
    - Con campaña compatible y fecha 2026-10-30 → guarda `NuevaGestion(membresia_id de la predicción, campania_nombre="<nombre actual>", fecha_asignacion=2026-09-29, estado=PENDIENTE)`, un `commit`, devuelve `GestionDTO` con `score`, `nivel_riesgo`, `modelo_version` de la predicción.
    - `campania_id=None` → `campania_nombre=None`. Responsable `"  Andrea "` → `"Andrea"` (lo recorta el DTO).
    - Fecha 2026-09-28 o 2026-11-05 → `FechaSeguimientoFueraDeRangoError`; vencimiento 2026-08-29 → `PlazoSeguimientoTerminadoError`; campaña inactiva o solo `BAJO` → `CampaniaNoAplicableError`; campaña inexistente → `CampaniaNoExisteError`; predicción inexistente → `PrediccionNoExisteError`; membresía con gestión → `GestionDuplicadaError`. En todos, **sin** `commit`.
    - Reloj `2026-09-30T03:00Z` (aún 29 en Ecuador) → hoy = 2026-09-29 (acepta 2026-09-29).
  - Pruebas: unitarias.

- [x] **T10** · `application` · CU-10: registrar el resultado y consultar la gestión (D5-BE-04)
  - Archivos: `Backend/app/application/gestiones/registrar_resultado.py` (principal, nuevo: `RegistrarResultado`, `GestionNoExisteError`), `Backend/app/application/gestiones/consultar_gestion.py` (nuevo: `ConsultarGestion`), `Backend/tests/unit/application/gestiones/test_registrar_resultado.py` (nuevo), `Backend/tests/unit/application/gestiones/test_consultar_gestion.py` (nuevo).
  - Docs: `03-casos-de-uso.md` §13; decisión (h).
  - Aceptación (reloj fijo; gestión pendiente creada 2026-09-29 con campaña, vencimiento 2026-10-05):
    - Contactado Sí, ofrecida Sí, aceptada Sí, renovó `PENDIENTE`, fecha contacto 2026-09-29, fecha seguimiento 2026-10-27 → sigue `PENDIENTE`, `fecha_seguimiento` actualizada, un `commit`.
    - Renovó `NO` → `CERRADA` con `cerrada_en = clock.now()`; `fecha_seguimiento` recibida ignorada.
    - Sobre `CERRADA` → `GestionCerradaError` sin `commit`. No contactado + ofrecida `SI` → `ResultadoIncoherenteError`; gestión sin campaña + ofrecida `NO` → error; fecha de seguimiento fuera de rango con renovó `PENDIENTE` → `FechaSeguimientoFueraDeRangoError`. Inexistente → `GestionNoExisteError`.
    - `ConsultarGestion(id)` → `GestionDTO` con `campania_nombre` de la instantánea y score/nivel/versión originales; inexistente → `GestionNoExisteError`. Usa `obtener_para_actualizar` (bloqueo) solo en `RegistrarResultado`.
  - Pruebas: unitarias.

- [x] **T11** · `infra` · Repositorio de gestiones (D5-BD-01)
  - Archivos: `Backend/app/infrastructure/persistence/repositories/gestiones.py` (principal, nuevo: `SqlAlchemyGestionRepository`), `Backend/app/infrastructure/persistence/unit_of_work_retencion.py` (contexto con `gestiones` y `campanias`; traduce `IntegrityError` de `ux_gestiones_retencion_membresia_id` a `GestionDuplicadaError`), `Backend/tests/integration/persistence/test_gestiones_repository.py` (nuevo).
  - Docs: `.claude/rules/database.md` §Reglas innegociables; `docs/backend/09-esquema-base-de-datos.md` §Retención; decisiones (c), (g), (h).
  - Aceptación (PostgreSQL `app_db_test`; datos ficticios: modelo, lista, 2 predicciones de la **misma** membresía en 2 listas):
    - `crear` → fila con `created_at` del `Clock`; `obtener` devuelve socio, plan, vencimiento, score, nivel, versión `"v<n>"`, `campania_nombre`, estado.
    - Segunda gestión para la misma membresía (desde la otra predicción) → `GestionDuplicadaError` (índice único parcial); la primera sigue intacta. `existe_para_membresia` → `True`.
    - Tras renombrar e inactivar la campaña, `obtener` sigue mostrando el nombre original (RN-08.2) y la campaña inactiva.
    - `obtener_para_actualizar` emite `FOR UPDATE`; `guardar_resultado` actualiza campos, `estado`, `cerrada_en`, `updated_at`. Todas las lecturas filtran `deleted_at IS NULL`. Sin método de borrado; sin `commit` en el repositorio.
  - Pruebas: integración.

- [x] **T12** · `api` · Router de gestiones real (`POST /gestiones`, `GET /gestiones/{id}`, `PUT /gestiones/{id}/resultado`)
  - Archivos: `Backend/app/api/routers/gestiones.py` (principal: mapeo `404` predicción/campaña/gestión, `409` duplicada o cerrada, `422` reglas de dominio; `GET /gestiones?filtro` y `GET /alertas` siguen `501`), `Backend/app/api/dependencies.py`, `Backend/tests/integration/api/test_gestiones_api.py` (nuevo), `Backend/tests/integration/api/test_contract_gestiones.py`.
  - Docs: `docs/API_CONTRACT.md` §Operaciones de negocio; `.claude/rules/backend.md` §API; decisiones (a), (b), (g), (h).
  - Aceptación (PostgreSQL de pruebas, `get_clock` fijo `2026-09-29T15:00Z`, predicción ficticia con vencimiento 2026-10-05):
    - `POST /gestiones {prediccion_id, campania_id: <ejemplo compatible>, fecha_seguimiento: "2026-10-30", responsable: "Andrea"}` → `201`, `estado: "PENDIENTE"`, `campania_nombre` correcto, `score`/`nivel_riesgo`/`modelo_version` de la predicción. Repetir (o desde otra lista con la misma membresía) → `409` y 1 sola fila.
    - Fecha `2026-09-28` → `422 domain_rule_violated` con el rango en el mensaje; campaña inactiva → `422`; campaña inexistente → `404`; predicción inexistente → `404`; `campania_id: null` → `201` con `campania_nombre: null`; cuerpo sin `fecha_seguimiento` → `400`. Nada guardado en los errores.
    - `GET /gestiones/{id}` → `200`; inexistente → `404`.
    - `PUT …/resultado` coherente con renovó `PENDIENTE` → `200` `PENDIENTE`; con renovó `NO` → `200` `CERRADA` y `fecha_cierre` no nula; otro `PUT` → `409` "La gestion esta cerrada y no se puede modificar." y datos sin cambios; "No se contactó" + ofrecida `SI` → `422`.
    - `GET /alertas` y `GET /gestiones?filtro=hoy` → siguen `501`. OpenAPI con ejemplos de request y de cada respuesta.
  - Pruebas: integración (API).

- [x] **T13** · `application` · La lista trae la gestión de cada ítem (`gestion_id`, `gestion_estado`, `campania_asignada`)
  - Archivos: `Backend/app/application/listas/ports.py` (principal: `ItemLista` con `gestion_id`, `gestion_estado`, `campania_asignada` opcionales), `Backend/app/application/listas/dtos.py` (`PrediccionDTO.gestion_id: int | None`), `Backend/app/application/listas/consultar_listas.py` (`a_dto`), `Backend/tests/unit/application/listas/test_consultar_listas.py`.
  - Docs: `docs/backend/12-modelo-y-listas.md` §Lista priorizada; `docs/API_CONTRACT.md` §Operaciones de negocio (listas); decisiones (b), (i).
  - Aceptación: ítem con gestión pendiente (id 9, campaña "Ejemplo: Renovación anticipada") → DTO `gestion_id: 9`, `gestion_estado: "PENDIENTE"`, `campania_asignada: "Ejemplo: Renovación anticipada"`; ítem sin gestión → los tres `null`; gestión sin campaña → `campania_asignada: null`, `gestion_estado` presente. Dobles y datos de prueba actualizados (excepción mecánica); `mypy app` en verde.
  - Pruebas: unitarias.

- [x] **T14** · `infra` · Repositorio de listas: LEFT JOIN con la gestión del ciclo
  - Archivos: `Backend/app/infrastructure/persistence/repositories/listas.py` (principal), `Backend/tests/integration/persistence/test_listas_repository.py`, `Backend/tests/integration/api/test_listas_api.py`.
  - Docs: `.claude/rules/database.md` §Reparto de herramientas; decisión (i).
  - Aceptación: con 2 listas que contienen la misma membresía y una gestión creada desde la lista 1 → `obtener(lista 1)` y `obtener(lista 2)` muestran esa gestión en ese ítem; gestión con `deleted_at` → no se muestra; sigue siendo **una** consulta para los ítems (sin N+1). `GET /listas/{id}` y `/ultima` devuelven `gestion_id`, `gestion_estado`, `campania_asignada`.
  - Pruebas: integración.

- [x] **T15** · `infra` · Excel: columnas "Gestión" y "Campaña"
  - Archivos: `Backend/app/infrastructure/exportacion/excel_lista.py` (principal), `Backend/tests/unit/infrastructure/exportacion/test_excel_lista.py`, `Backend/tests/integration/api/test_listas_excel_api.py`.
  - Docs: `docs/backend/12-modelo-y-listas.md` §Excel (CU-12); [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md); decisiones (i), (j).
  - Aceptación: encabezados de ambas hojas = `Prioridad, Nombre, Cédula, Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales, Gestión, Campaña`; ítem sin gestión → "Sin gestión" y "—"; pendiente con campaña → "Pendiente" y el nombre; cerrada sin campaña → "Cerrada" y "Sin campaña". Nombre de campaña `"=SUM(1)"` → texto `"'=SUM(1)"`. Siguen sin aparecer celular, score ni monto; `Resumen` sin cambios; mismo libro dos veces → bytes idénticos. Se actualiza la aserción de R-008 T1 que prohibía estas columnas.
  - Pruebas: unitaria + integración (API).

- [x] **T16** · `frontend` · Campañas: hook y datos simulados
  - Archivos: `Frontend/src/features/campanias/hooks/useCampanias.ts` (principal, nuevo: carga, `crear`, `editar`, `inactivar`, error, `AbortController`), `Frontend/src/features/campanias/api/campanias-api.handlers.ts` (MSW: 3 de ejemplo, `400` con nombre vacío, `404`), `Frontend/src/features/campanias/types.ts` (si falta algo), `Frontend/src/features/campanias/hooks/useCampanias.test.ts` (nuevo).
  - Docs: `docs/frontend/01-arquitectura.md` §Estructura, §MSW; `.claude/rules/frontend.md` §Estado y asincronía; decisión (e).
  - Aceptación: al montar carga la lista (1 petición); `crear` exitoso añade la campaña y recarga; `400` → `error` con el mensaje del servidor y sin cambios; `inactivar` actualiza `activa:false` en el estado; desmontar aborta la petición en curso. Datos del handler ficticios.
  - Pruebas: frontend.

- [x] **T17** · `frontend` · Página Campañas: tabla, formulario de alta/edición, inactivar e indicador "Ejemplo" (D5-FE-01)
  - Archivos: `Frontend/src/features/campanias/pages/CampaniasPage.tsx` (principal), `Frontend/src/features/campanias/components/FormularioCampania.tsx` (nuevo, presentacional), `Frontend/src/features/campanias/components/TablaCampanias.tsx` (nuevo, usa `DataTable` de `shared/ui`), `Frontend/src/features/campanias/pages/CampaniasPage.test.tsx` (nuevo).
  - Docs: `docs/frontend/01-arquitectura.md` §`shared/ui`, §Estilos; `.claude/rules/frontend.md` §Formularios, §Estilos; `03-casos-de-uso.md` §9; decisión (e).
  - Aceptación (Vitest + MSW + `user-event`):
    - La tabla muestra Nombre, Descripción, Niveles, Planes, Prioridad, Estado ("Activa"/"Inactiva") y una etiqueta "Ejemplo" en las `esEjemplo`.
    - "Nueva campaña" abre el formulario: campos con `label` ("Nombre", "Descripción", casillas de "Niveles de riesgo" Alto/Medio/Bajo y "Planes" Mensual/Trimestral/Semestral/Anual/Otro —sin Diario—, "Prioridad"). Guardar sin nombre → "Escriba un nombre para la campaña."; sin nivel → "Elija al menos un nivel de riesgo."; sin plan → "Elija al menos un plan."; prioridad fuera de 1..999 → "La prioridad debe ser un número entre 1 y 999." — sin llamar a la API. Válido → aparece en la tabla.
    - "Editar" precarga los datos y guarda con `PUT`. "Inactivar" pide confirmación en `Modal` ("La campaña dejará de sugerirse; las gestiones que ya la usan la conservan.") y tras confirmar el estado pasa a "Inactiva" y el botón desaparece; no hay botón "Eliminar".
    - Error del servidor → `ErrorAlert` con el mensaje. Sin CSS nuevo; solo tokens existentes.
  - Pruebas: frontend.

- [x] **T18** · `frontend` · Lista: tipos, cliente y MSW de gestiones (`gestionId`)
  - Archivos: `Frontend/src/features/lista/api/lista-api.ts` (principal: mapea `gestion_id`), `Frontend/src/features/lista/types.ts` (`Prediccion.gestionId: number | null`), `Frontend/src/features/lista/api/lista-api.handlers.ts` (MSW: sugeridas, `POST /gestiones` con `409`/`422`, `GET /gestiones/:id`, `PUT …/resultado` con `409` si cerrada), `Frontend/src/features/lista/api/lista-api.test.ts`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada, §MSW; decisión (b).
  - Aceptación: `obtenerLista` mapea `gestion_id` → `gestionId` (y `null`); `crearGestion` con `422` → `ApiError` 422 con el mensaje del servidor; `registrarResultado` con `409` → `ApiError` 409. Fixtures de `Prediccion` en pruebas existentes con `gestionId` (excepción mecánica). Datos ficticios.
  - Pruebas: frontend.

- [x] **T19** · `frontend` · Reglas del formulario de gestión y hook `useGestion`
  - Archivos: `Frontend/src/features/lista/hooks/useGestion.ts` (principal, nuevo: abre con `prediccion` → carga sugeridas o la gestión existente; `crear`, `registrar`, estados `cargando/listo/enviando/error`, cancelación), `Frontend/src/features/lista/hooks/reglasGestion.ts` (nuevo, funciones puras: `rangoSeguimiento`, `fechaSugerida`, `opcionesPermitidas`, `validarResultado`), `Frontend/src/features/lista/hooks/reglasGestion.test.ts` (nuevo), `Frontend/src/features/lista/hooks/useGestion.test.ts` (nuevo).
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada; `.claude/rules/frontend.md` §Estado y asincronía, §Formularios; decisiones (g), (h), (k).
  - Aceptación:
    - `reglasGestion` con los **mismos casos** de T2 (hoy 2026-09-29: venc 2026-10-05 → rango 29-09..04-11, sugerida 30-10; venc 2026-09-01 → sugerida 29-09; venc 2026-08-29 → sin rango, "El plazo de seguimiento de este ciclo ya terminó.") y cada fila de coherencia de (h).
    - `opcionesPermitidas`: sin campaña → ofrecida y aceptada solo "No aplica"; no contactado → idem; ofrecida No → aceptada solo "No aplica"; ofrecida Sí → aceptada Sí/No/Pendiente.
    - `useGestion` sin gestión → 1 petición a sugeridas; con `gestionId` → 1 petición a `GET /gestiones/{id}`; `crear` exitoso → devuelve la gestión; `422`/`409` → `error` con el mensaje del servidor; no hay doble envío mientras `enviando`.
  - Pruebas: frontend.

- [x] **T20** · `frontend` · Formulario de gestión en ventana modal (D5-FE-02)
  - Archivos: `Frontend/src/features/lista/components/FormularioGestion.tsx` (principal, nuevo, presentacional: parte 1 y contenedor), `Frontend/src/features/lista/components/ResultadoGestion.tsx` (nuevo, parte 2), `Frontend/src/features/lista/components/FormularioGestion.test.tsx` (nuevo).
  - Docs: `docs/frontend/01-arquitectura.md` §`shared/ui` (`Modal`, `ErrorAlert`, `RiskBadge`); `.claude/rules/frontend.md` §Formularios, §Estilos; `03-casos-de-uso.md` §11, §13; decisión (k).
  - Aceptación (Vitest + `user-event`, fecha simulada 2026-09-29):
    - Parte 1: título con prioridad, plan, vencimiento y nivel (`RiskBadge`); radios de las sugeridas en orden + "No asignar campaña"; sin sugerencias → solo "No asignar campaña", marcada. "Fecha de seguimiento" = 2026-10-30 con `min` 2026-09-29 y `max` 2026-11-04; escribir 2026-11-05 → "La fecha de seguimiento debe estar entre el 29/09/2026 y el 04/11/2026." sin enviar; plazo terminado → mensaje y botón "Crear gestión" deshabilitado.
    - Parte 2 (gestión pendiente): elegir "No" en "¿Se contactó al socio?" deja "¿Se ofreció…?" y "¿Aceptó…?" en "No aplica" y deshabilita las demás opciones; gestión sin campaña → las mismas en "No aplica" y deshabilitadas. "Fecha de seguimiento" solo visible con "¿Renovó?" = Pendiente. Guardar con Renovó = No → emite el resultado; con contactado Sí sin fecha de contacto → "Indique la fecha del contacto." sin enviar.
    - Gestión cerrada → todos los campos de solo lectura y sin botón de guardar, con el texto "Gestión cerrada: no se puede modificar.".
    - Accesibilidad: cada grupo de radios en `fieldset` con `legend`; errores enlazados con `aria-describedby`; foco al primer campo al abrir y de vuelta al botón al cerrar (`Modal`). Sin CSS nuevo.
  - Pruebas: frontend.

- [x] **T21** · `frontend` · Tabla de la Lista con columnas "Gestión" y "Campaña" y botón de acción (D5-FE-03)
  - Archivos: `Frontend/src/features/lista/components/TablaLista.tsx` (principal: columnas y botón; emite `onGestionar(prediccion)`), `Frontend/src/features/lista/pages/ListaPage.tsx` (abre `FormularioGestion` con `useGestion`, recarga la lista tras guardar), `Frontend/src/features/lista/components/TablaLista.test.tsx`, `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada; decisiones (i), (k).
  - Aceptación (Vitest + MSW):
    - Con un ítem sin gestión, uno `PENDIENTE` con campaña "Ejemplo: Renovación anticipada" y uno `CERRADA` sin campaña → celdas "Sin gestión"/"—", "Pendiente"/"Ejemplo: Renovación anticipada", "Cerrada"/"Sin campaña"; botones "Gestionar prioridad N", "Registrar resultado prioridad N", "Ver gestión prioridad N" (sin el nombre del socio en el nombre accesible).
    - "Gestionar" → modal con sugeridas → "Crear gestión" → el modal pasa a la parte 2 y, al cerrar, la fila muestra "Pendiente" (lista recargada). `409` del servidor → `ErrorAlert` "El ciclo de membresia ya tiene una gestion.".
    - Ambas tablas (prioritarios y otros) tienen las columnas. Las pruebas existentes siguen en verde.
  - Pruebas: frontend.

- [x] **T22** · `infra-deploy` · Suites, E2E en el stack aislado, stacks reconstruidos y verificación en el navegador
  - Archivos: `Frontend/e2e/campanias-gestion.spec.ts` (principal, nuevo; se salta en 8080 como `carga-lista-excel`).
  - Docs: `docs/backend/10-docker.md` §Uso, §Stack E2E aislado; `.claude/rules/deploy.md`; decisión (a) y nota de stacks.
  - Aceptación (el developer pega solo estados, códigos y conteos, sin datos personales):
    1. Backend `pytest`, `ruff check`, `ruff format --check`, `mypy app`, `lint-imports`; Frontend `npm test`, `npm run lint`, `npm run build` en verde.
    2. Stack E2E (8081) reconstruido (aplica `0007`, `0008`): E2E `health`, `carga-lista-excel` y `campanias-gestion` en verde. `campanias-gestion`: Campañas muestra 3 con "Ejemplo" → crear "Campaña E2E <timestamp>" (ALTO/MEDIO, todos los planes, prioridad 1) → generar lista → "Gestionar" en un ítem → aparece la campaña creada → crear con la fecha sugerida → registrar resultado contactado Sí, ofrecida Sí, aceptada Sí, renovó No → fila "Cerrada" → "Ver gestión" sin botón de guardar → descargar Excel con "Cerrada" en la columna "Gestión".
    3. Stack principal (8080): `docker compose up -d --build` **sin** `down -v`; `alembic current` → `0008 (head)`; `campanias` = 3 (`es_ejemplo`), `gestiones_retencion` = 0; `socios`, `membresias`, `cargas`, `listas_priorizadas`, `predicciones` iguales antes y después; sistema `LISTO`.
    4. Navegador 8080 (solo mirar, sin crear): Campañas lista las 3 de ejemplo con "Ejemplo"; el formulario "Nueva campaña" abre y se cancela; la tabla de la Lista (si el usuario tiene una) muestra "Gestión"/"Campaña" y el botón "Gestionar" abre el modal con las sugeridas (se cierra sin crear). Si no hay listas, se verifica en 8081.
  - Pruebas: E2E + verificación del stack y navegador.

- [x] **DOC-1** · (doc-agent) · Documentación
  - `docs/API_CONTRACT.md`: marcar **(real)** los endpoints de (a); `gestion_id` en `PrediccionDTO`; `prioridad` 1..999; `fecha_asignacion` = instante de creación; códigos y mensajes de (g)–(h); `GET /alertas` y `GET /gestiones?filtro` siguen `501` (día 6).
  - `docs/backend/09-esquema-base-de-datos.md`: `0007` (datos de ejemplo, idempotencia, `downgrade`) y `0008` (`campania_nombre`, CHECK, relleno). Nuevo `docs/backend/14-campanias-y-gestiones.md` (reglas de (e)–(i), unidad de trabajo de retención, concurrencia) enlazado desde `Documentation/README.md`.
  - `docs/backend/12-modelo-y-listas.md` §Excel y `03-casos-de-uso.md` §15 CU-12: columnas "Gestión" y "Campaña" (decisión (j)); valorar si ADR-007 necesita una nota o un ADR nuevo por la instantánea (c).
  - `docs/frontend/01-arquitectura.md`: página Campañas, formulario de gestión (partes, reglas, accesibilidad), columnas nuevas de la tabla. `06-como-funciona-la-lista.md`: cómo gestionar un socio desde la lista.
  - `DEVELOPMENT_GUIDELINES.md` §Excepciones (fila del reinicio): **ejecutado** el 30-09-2026 en el stack principal; conteos tras el reinicio: socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0. Y la excepción de `now()` de la base en la migración de datos `0007` (decisión (d)).
  - `05-cronograma-semana.md`: "Avance y resumen del Día 5" (estado, realizado, desviaciones —`0007` en lugar de `0003`, `0008`, alertas al día 6—, qué puede probar el usuario, pendientes). `ACTION_PLAN.md`: decisiones a DECISIONES IMPORTANTES, R-009 a TERMINADOS.

**Dependencias**
- Backend: T1 → T5 → T6; T1, T5 → T7 → T8. T2 → T9 → T10; T4 → T11 (columna `campania_nombre`); T7, T9, T10 → T11 → T12. T3 → T4 (orden de revisiones). T11 → T13 → T14 → T15.
- Frontend: T16 → T17 (contra MSW; T8 manda el contrato). T18 → T19 → T20 → T21 (T18 puede empezar con MSW; T12 y T13 mandan el contrato).
- Todo (T1–T21) → T22 → DOC-1.
- Orden sugerido: T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22.
- Externas: PostgreSQL con `app_db_test` (T3, T4, T7, T8, T11, T12, T14, T15); Docker Desktop, `.env` y `.env.e2e` (T22); stack `mtabolic-e2e` para todo lo que crea campañas o gestiones.

**Riesgos**
1. **Dos gestiones para el mismo ciclo o edición de una cerrada por carrera** (doble clic, dos pestañas, la misma membresía en dos listas). Mitigación: índice único parcial existente + traducción de `IntegrityError` a `409` (T11), comprobación previa en la transacción, `SELECT … FOR UPDATE` al registrar el resultado (T10–T11), botón deshabilitado mientras envía (T19) y prueba con dos listas que comparten membresía (T11, T12, T14).
2. **Migraciones sobre la base con datos reales.** `0007` podría duplicar campañas o su `downgrade` borrar datos del usuario; `0008` fallaría con filas que no cumplan el CHECK. Mitigación: inserción condicionada por nombre, `downgrade` limitado a las 3 de ejemplo y bloqueado si hay gestiones que las usan (T3), relleno antes del CHECK y prueba sobre base con datos (T4); en el stack principal, `up --build` sin `down -v` y conteos antes/después (T22).
3. **"Hoy" y reglas duplicadas entre backend y frontend.** Usar la fecha UTC en el servidor o una regla distinta en el navegador daría fechas sugeridas aceptadas por uno y rechazadas por el otro (sobre todo después de las 19:00 en Ecuador). Mitigación: `hoy_en_negocio(clock.now())` con prueba a `03:00Z` (T9), mismos casos de prueba en T2 y T19, y el servidor siempre decide (el frontend muestra su `422`).

### R-008 — Correcciones tras el Día 4: Excel igual a la tabla, selector de archivo claro en Carga, ayuda sin dos secciones, reinicio por comandos de la base principal y nombre editable de la lista · **DONE** 2026-09-29

**Cierre:** Backend 1.463 pytest, `ruff`, `format` (231), `mypy app` (106), `lint-imports` (7), `verificar_lista.py` salida 0; Frontend 448 Vitest, `build`, `lint` 0; E2E 2/2 en el stack aislado 8081 (Excel de "Campaña prueba" con las hojas y columnas esperadas). Stack principal reconstruido en `0006` sin `down -v`, datos intactos (socios 1.410, membresías 2.748, cargas 1, listas 2 del usuario); navegador: Carga en tres pasos sin confirmar, nombre sugerido, ayuda con 4 secciones. **Reinicio (T14 paso 2) no ejecutado** para no borrar las 2 listas del usuario: scripts verificados solo por sintaxis y cancelación. Seguridad diferida al día 7 (05 §1). Contrato y esquema → [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md); comando → [comandos/reiniciar-base-historica.md](comandos/reiniciar-base-historica.md).

**Objetivo:** el Excel muestra exactamente lo que ve el personal en pantalla, la carga se hace con pasos explícitos (elegir → revisar → confirmar), la ayuda es más corta, existe un proceso versionado y documentado para dejar la base principal solo con el histórico, y cada lista tiene un nombre editable que se guarda y se ve en pantalla, historial y Excel.

**Fuente:** petición del usuario tras el Día 4 · [03 §15 CU-12](03-casos-de-uso.md) (columnas del Excel) · `docs/backend/12-modelo-y-listas.md` §Excel (CU-12) · `docs/frontend/01-arquitectura.md` §Inicio y Carga, §Lista priorizada · [06 §5–§6](06-como-funciona-la-lista.md) · `docs/backend/10-docker.md` §Uso · `compose.yaml` (`name: proyectofinal`; stack E2E `-p mtabolic-e2e`).

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Nada cae en `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance. **Puntos 1–4 sin cambios de API ni de esquema:** `PrediccionDTO` sigue con `celular`, `score`, `monto_cobrado`, etc. **Punto 5 (ampliación del usuario)** sí cambia contrato y esquema: `nombre` en `GenerarListaDTO` (opcional), `ListaPriorizadaDTO` y `ListaResumenDTO`; migración `0006`. No se reentrena desde el código.
- **Proceso (05 §1):** sin TDD; pruebas de los criterios de aceptación. Revisión de seguridad diferida a la revisión única del día 7. Sin login: no hay pruebas de aislamiento.
- **Cambia decisiones anteriores (las registra DOC-1):** R-005 (e) "el Excel conserva score y aportes" y R-006 "el celular se mantiene en el Excel" quedan **revertidas** por el usuario; CU-12 §15 (03, línea de **Columnas**) se ajusta. El doc-agent decide si merece ADR (afecta a ADR-006 solo en el Excel).
- **Reinicio de la base = borrado físico** de todo el volumen del stack principal (cargas por plantilla, listas, predicciones y, en el futuro, campañas y gestiones). Es una **operación manual y explícita del usuario**, no una función de la aplicación; se registra en `DEVELOPMENT_GUIDELINES.md` §Excepciones (DOC-1). El código de la app sigue sin exponer borrados.
- **Decisiones del planner (reversibles; se avisan al usuario):**
  - (a) **Hojas del Excel:** `Socios prioritarios a contactar` (31 caracteres, el máximo de Excel) = ítems con `dentro_top_k`; `Otros socios por vencer` = el resto (si no hay, la hoja queda solo con encabezados; en pantalla la tabla se oculta); `Resumen` con términos amigables. Ambas por `prioridad` ascendente. Desaparecen `top_{K}` y `cartera_completa`.
  - (b) **Columnas (A..H):** Prioridad (número), Nombre, Cédula (texto, cero inicial, `null` → vacía), Plan, Vence el (celda fecha, formato `dd/mm/yyyy`), Días para vencer (número), Nivel de riesgo (`Alto`/`Medio`/`Bajo`, como `RiskBadge`), Motivos principales (unidos con `"; "`, cada uno **sin** el aporte final entre paréntesis, misma regla que `APORTE_FINAL` de `TablaLista.tsx`: `\s*\([^()]*\)\s*$`; sin motivos → "Sin factores de riesgo destacados").
  - (c) **Resumen:** filas "Nombre de la lista" (punto 5, decisión (j)), "Fecha de la lista", "Vencen hasta" (fecha + horizonte), "Socios prioritarios a contactar", "Otros socios por vencer", "Total de socios por vencer", "Riesgo alto", "Riesgo medio", "Riesgo bajo". Sin versión del modelo, umbrales, "Top K", score ni horizonte. Fechas como celda fecha `dd/mm/yyyy`.
  - (d) **Carga en tres pasos:** elegir archivo **no** llama a la API (nuevo estado `seleccionado`); "Revisar archivo" lanza la vista previa; "Confirmar carga" guarda. Cambiar de archivo limpia vista previa, resumen y errores y cancela la petición en curso. El `<input type="file">` queda oculto (`hidden`, fuera del orden de tabulación) y sigue asociado a la etiqueta "Archivo de la plantilla (.xlsx)" (lo usan pruebas y E2E); el control visible y enfocable es un `<button type="button">` "Seleccionar archivo de carga (.xlsx)" que abre el diálogo del sistema. Componente en `features/carga/components/` (un solo uso: no sube a `shared/ui`), con los tokens existentes, sin CSS nuevo.
  - (e) **Scripts de reinicio** en `scripts/` de la raíz: fijan `-p proyectofinal` y `--env-file <raíz>/.env` (resueltos desde la ubicación del script, sin depender del directorio actual) y se niegan a continuar si no existen `compose.yaml` o `.env`; nunca aceptan otro nombre de proyecto. Confirmación escribiendo literalmente `BORRAR`; flag `-Si` / `--si` para uso no interactivo (documentado con advertencia). Espera `GET http://localhost:${BACKEND_PORT:-8000}/api/v1/sistema/estado` cada 5 s hasta `LISTO` (máx. 15 min; `FALTAN_DATOS_HISTORICOS` o tiempo agotado → salida ≠ 0). Conteos con `docker compose -p proyectofinal exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" …'` (credenciales dentro del contenedor, nunca en la línea de comandos ni en la salida). `.gitattributes` fija `*.sh text eol=lf`.
  - (f) **Ejecución del reinicio en el stack principal (T14):** solo con confirmación explícita del usuario transmitida por el orquestador. La verificación del Excel en el navegador se hace en el stack E2E (8081, datos sintéticos) para que la base principal quede, tras el reinicio, en 0 listas; si el usuario prefiere, también en 8080.
  - (g) **Nombre por defecto** = `"Lista del <d> <mmm> <aaaa>"` con la fecha de la lista (`fecha_generacion` efectiva) y la tabla fija de meses de R-006 (`ene feb mar abr may jun jul ago sep oct nov dic`, sin punto, día sin cero): `2026-09-29` → `"Lista del 29 sep 2026"`, `2027-01-05` → `"Lista del 5 ene 2027"`. El mismo formato en backend (dominio, sin `locale`), en la migración (SQL con `ARRAY[...]`) y en el frontend (`fechaCorta` de `formatoFechas.ts`).
  - (h) **Validación del nombre:** se recorta (`strip`); tras recortar, 1..80 caracteres; sin caracteres de control (`\x00-\x1f`, `\x7f`). Ausente o `null` → nombre por defecto. Vacío tras recortar, > 80 o con caracteres de control → `400 validation_error` (entrada inválida, no regla de negocio). Se permiten nombres repetidos (no hay unicidad). Guardado tal cual (recortado); la neutralización `= + - @` ocurre **solo** al escribir el Excel (y React escapa en pantalla).
  - (i) **Esquema (`0006`):** `listas_priorizadas.nombre TEXT NOT NULL` con `CHECK (char_length(nombre) BETWEEN 1 AND 80)` (`nombre_longitud`). `upgrade` en tres pasos: añade la columna `NULL` → rellena las filas existentes con el nombre por defecto de su `fecha_generacion` → `SET NOT NULL` + `CHECK`. `downgrade` elimina la columna (solo en desarrollo). Sin índice (no se busca por nombre). La lista sigue inmutable (RN-04.5): el nombre no se edita después de generarla.
  - (j) **Dónde se ve:** título de la lista = `nombre` (sustituye a "Lista del 29 de septiembre de 2026", R-006 (d)); "Listas anteriores" = `"<nombre> · <N> prioritarios"`; Excel = primera fila de la hoja `Resumen` "Nombre de la lista". Campo "Nombre de la lista" en el formulario, primero de los parámetros; la sugerencia sigue a la fecha mientras el valor coincida con la sugerencia de la fecha anterior (no editado a mano); si el usuario lo cambia, se respeta aunque cambie la fecha.
- **Excepción al límite de 4 archivos:** ajuste mecánico de selectores en `Frontend/e2e/carga-lista-excel.spec.ts` (T14); añadir `nombre` a los constructores de dobles y datos de prueba (`tests/unit/application/listas/dobles.py`, `tests/unit/application/listas/test_ports.py`, `tests/unit/infrastructure/exportacion/test_excel_lista.py`, `tests/integration/api/listas_datos.py`, `scripts/verificar_lista.py`) y la línea `"0005 (head)"` → `"0006 (head)"` en `test_migrations_robustness.py` (T7); `__init__.py` vacíos.

**Tareas**

- [x] **T1** · `infra` · Excel con las columnas y las dos tablas de la pantalla
  - Archivos: `Backend/app/infrastructure/exportacion/excel_lista.py` (principal), `Backend/tests/unit/infrastructure/exportacion/test_excel_lista.py`, `Backend/tests/integration/api/test_listas_excel_api.py`.
  - Docs: `Documentation/docs/backend/12-modelo-y-listas.md` §Excel (CU-12); `Frontend/src/features/lista/components/TablaLista.tsx` (regla `APORTE_FINAL`, solo lectura); decisiones (a), (b), (c), (j). Requiere `ListaDetalle.nombre` (T8).
  - Aceptación (lista ficticia: 3 ítems, `top_k` 2, uno con factores `["Plan: TRIMESTRAL (+0,09)", "Membresías previas: 1 (-0,02)"]`, otro sin factores, uno con cédula `"0912345678"` y nombre `"=HYPERLINK(...)"`):
    - `sheetnames == ["Socios prioritarios a contactar", "Otros socios por vencer", "Resumen"]`; la primera tiene 2 filas de datos (las `dentro_top_k`), la segunda 1; con todos dentro del top, la segunda solo tiene la fila de encabezados.
    - Fila 1 de ambas hojas = exactamente `Prioridad, Nombre, Cédula, Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales`. Ninguna celda de ninguna hoja contiene "Celular", "Score", "Monto", "Estado de la gestion", "Campania", "Top K", "Umbral", "Version del modelo"; ni el celular ni el score del ítem aparecen en ningún valor.
    - Motivos → `"Plan: TRIMESTRAL; Membresías previas: 1"` (sin paréntesis ni números de aporte); sin factores → "Sin factores de riesgo destacados". Nivel → "Alto"/"Medio"/"Bajo".
    - Cédula en celda de tipo texto con valor `"0912345678"`; el nombre con `=` queda `"'=HYPERLINK(...)"` (sin fórmulas en todo el libro). Vence el es fecha con formato `dd/mm/yyyy`; Días para vencer = vencimiento − `fecha_generacion`.
    - Resumen con las 9 etiquetas de (c) y sus valores (nombre, 2, 1, 3 y los conteos por nivel). Con `nombre="=SUM(1)"` la celda es texto `"'=SUM(1)"`; con `"Campaña octubre"` sale igual.
    - `generar(lista)` dos veces → bytes idénticos; sin archivos temporales (RN-12.1 intacto).
    - API: `GET /api/v1/listas/{id}/excel` → `200`, `Content-Type` de xlsx, nombre `lista_<id>_<fecha>.xlsx`, hojas y encabezados anteriores; `GET /api/v1/listas/{id}` sigue devolviendo `celular`, `score` y `monto_cobrado` (contrato sin cambios); id inexistente → `404`.
  - Pruebas: unitaria + integración (API).

- [x] **T2** · `frontend` · Hook de carga en tres pasos (elegir → revisar → confirmar)
  - Archivos: `Frontend/src/features/carga/hooks/useCarga.ts` (principal), `Frontend/src/features/carga/hooks/useCarga.test.ts` (nuevo, `renderHook` + MSW).
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Inicio y Carga; `.claude/rules/frontend.md` §Estado y asincronía; decisión (d).
  - Aceptación:
    - `EstadoCarga` añade `seleccionado`; se expone `archivoSeleccionado: string | null` (solo el nombre) y `revisar()`.
    - `seleccionarArchivo(xlsx)` → estado `seleccionado`, nombre expuesto y **cero** peticiones a `/cargas/vista-previa` (contador del handler MSW = 0). `.csv` → `errorArchivo` "Seleccione un archivo .xlsx con la plantilla oficial.", estado `inicial`, sin petición. `null` → `inicial`.
    - `revisar()` en `seleccionado` → `validando` → `vista-previa` (1 petición). `revisar()` sin archivo o mientras valida/envía → no hace nada. Error de la API → mensaje y vuelve a `seleccionado` (se puede reintentar); `413` → "El archivo supera el tamaño máximo permitido.".
    - Elegir otro archivo durante `validando` aborta la petición anterior y limpia vista previa, resumen y errores. `confirmar()` sin cambios (sin doble envío; `422` → vuelve a `vista-previa`).
  - Pruebas: frontend.

- [x] **T3** · `frontend` · Selector de archivo visible y botones "Revisar archivo" / "Confirmar carga"
  - Archivos: `Frontend/src/features/carga/components/SelectorArchivo.tsx` (principal, nuevo, presentacional), `Frontend/src/features/carga/pages/CargaPage.tsx`, `Frontend/src/features/carga/components/VistaPreviaCarga.tsx` (texto del botón), `Frontend/src/features/carga/pages/CargaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Inicio y Carga, §`shared/ui`, §Estilos; `.claude/rules/frontend.md` §Estilos; decisión (d).
  - Aceptación (Vitest + MSW + `user-event`):
    - Se ve un botón con nombre accesible "Seleccionar archivo de carga (.xlsx)", el texto de ayuda "Suba la plantilla oficial del mes." (enlazado con `aria-describedby`) y "Ningún archivo seleccionado"; tras elegir `plantilla.xlsx` → "Archivo elegido: plantilla.xlsx" y **no** aparece la vista previa.
    - Botón "Revisar archivo": deshabilitado sin archivo; habilitado tras elegir; al pulsarlo → "Validando archivo..." y luego la vista previa. Deshabilitados ambos botones mientras valida o envía.
    - Botón "Confirmar carga" (antes "Confirmar") con las mismas reglas de habilitación; confirmar → resumen.
    - Teclado: `Tab` llega al botón de selección y a "Revisar archivo" (el `input` oculto no recibe foco); `Enter`/`Espacio` en el botón de selección dispara el `click` del `input` (espía). `getByLabelText('Archivo de la plantilla (.xlsx)')` sigue encontrando el `input` con `accept=".xlsx"`.
    - Error de extensión se muestra junto al selector (`aria-describedby`). Las pruebas existentes de `CargaPage.test.tsx` se adaptan al nuevo paso "Revisar archivo" y siguen en verde. Sin CSS nuevo; solo tokens de Tailwind existentes.
  - Pruebas: frontend.

- [x] **T4** · `frontend` · Ayuda de la lista sin "Qué datos se muestran" ni "Casos frecuentes"
  - Archivos: `Frontend/src/features/lista/components/AyudaLista.tsx` (principal), `Frontend/src/features/lista/components/AyudaLista.test.tsx`.
  - Docs: `Documentation/06-como-funciona-la-lista.md` §1–§4; `docs/frontend/01-arquitectura.md` §Lista priorizada (párrafo "Ayuda de la lista").
  - Aceptación:
    - El diálogo tiene exactamente 4 encabezados de sección: "Qué hace la lista", "Socios prioritarios a contactar", "Niveles de riesgo: alto, medio y bajo", "Motivos". No contiene "Qué datos se muestran", "Casos frecuentes" ni la palabra "celular".
    - Si la sección "Motivos" dice que el Excel incluye los números, se corrige (el Excel ya no los incluye, T1).
    - Siguen en verde: apertura/cierre con "Cerrar" y `Escape`, foco de vuelta al botón y la prueba de términos prohibidos ("score", "Top K", "top", "horizonte", "percentil", "modelo v1").
  - Pruebas: frontend.

- [x] **T5** · `infra-deploy` · Scripts de reinicio de la base principal solo con el histórico
  - Archivos: `scripts/reiniciar-base-historica.ps1` (principal, nuevo), `scripts/reiniciar-base-historica.sh` (nuevo, `#!/usr/bin/env bash`, `set -euo pipefail`), `.gitattributes` (nuevo o ampliado: `*.sh text eol=lf`).
  - Docs: `Documentation/docs/backend/10-docker.md` §Uso; `compose.yaml` (cabecera: stack E2E y advertencia de `down -v`); `.claude/rules/deploy.md` §Configuración y secretos; decisión (e).
  - Aceptación:
    - Ambos muestran qué se borrará (cargas por plantilla, listas, predicciones y todo lo demás del volumen principal; se reentrena el modelo v1 idéntico) y piden escribir `BORRAR`; cualquier otra respuesta → "Cancelado", salida `0`, **ningún** comando `docker` ejecutado.
    - Tras confirmar ejecutan en orden: `docker compose -p proyectofinal --env-file <raíz>/.env down -v` → `docker compose -p proyectofinal --env-file <raíz>/.env up -d` → espera `LISTO` → imprime conteos `socios`, `membresias`, `cargas`, `listas_priorizadas`, `predicciones`. Todos los comandos llevan `-p proyectofinal`; la cadena `mtabolic-e2e` no aparece salvo en un comentario que explica que no se toca.
    - Sin `.env` o sin `compose.yaml` en la raíz → mensaje claro y salida ≠ 0 antes de cualquier `docker`. Un comando fallido → se detiene con salida ≠ 0 (`$ErrorActionPreference='Stop'` y comprobación de `$LASTEXITCODE`; `set -e` en bash). Estado `FALTAN_DATOS_HISTORICOS` o más de 15 min → salida ≠ 0 con el último estado.
    - Ninguna contraseña, `DATABASE_URL` ni dato personal en el script ni en su salida (solo estados y conteos). Funcionan desde cualquier directorio actual.
    - Comprobación estática: `bash -n scripts/reiniciar-base-historica.sh` y el parser de PowerShell (`[System.Management.Automation.Language.Parser]::ParseFile`) sin errores; ejecución con respuesta distinta de `BORRAR` → cancelado sin tocar Docker (verificable con `docker compose -p proyectofinal ps` antes/después idéntico).
  - Pruebas: verificación por comandos (sin ejecutar el borrado en esta tarea).

- [x] **T6** · `domain` · Punto 5 · Nombre por defecto de una lista
  - Archivos: `Backend/app/domain/listas/nombre.py` (principal, nuevo: `MESES_CORTOS`, `LONGITUD_MAXIMA_NOMBRE = 80`, `nombre_por_defecto(fecha: date) -> str`), `Backend/tests/unit/domain/listas/test_nombre.py` (nuevo).
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas; `docs/frontend/01-arquitectura.md` §Lista priorizada (fila `formatoFechas.ts`, mismo formato); decisión (g).
  - Aceptación:
    - `date(2026,9,29)` → `"Lista del 29 sep 2026"`; `date(2027,1,5)` → `"Lista del 5 ene 2027"`; los 12 meses dan `ene … dic` (parametrizada). Nunca supera 80 caracteres.
    - Solo librería estándar; no usa `locale`, `strftime('%b')` ni el reloj. `lint-imports` en verde.
  - Pruebas: unitarias.

- [x] **T7** · `db` · Punto 5 · Migración `0006`: `listas_priorizadas.nombre`
  - Archivos: `Backend/alembic/versions/0006_listas_nombre.py` (principal), `Backend/app/infrastructure/persistence/models/retencion.py` (`ListaPriorizada.nombre` + `CheckConstraint`), `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`, `Backend/tests/integration/persistence/test_migrations.py`.
  - Docs: `.claude/rules/database.md` §Migraciones; `Documentation/docs/backend/09-esquema-base-de-datos.md` §Retención; decisión (i).
  - Aceptación:
    - `revision="0006"`, `down_revision="0005"`. Sobre una base en `0005` con 2 listas ficticias (`fecha_generacion` 2026-09-29 y 2027-01-05) → `upgrade` deja `nombre` = `"Lista del 29 sep 2026"` y `"Lista del 5 ene 2027"`; columna `NOT NULL`; insertar `nombre=''` o de 81 caracteres → `IntegrityError` (CHECK `nombre_longitud`).
    - Sobre una base vacía también aplica. `alembic check` sin diferencias; `alembic current` → `0006 (head)`; ciclo `downgrade 0005` → `upgrade head` funciona. `predicciones` y demás tablas no cambian (conteos iguales).
  - Pruebas: unitaria (metadatos) + integración.

- [x] **T8** · `application` · Punto 5 · Contrato y caso de uso con `nombre`
  - Archivos: `Backend/app/application/listas/dtos.py` (principal: `GenerarListaDTO.nombre: str | None = None` con recorte y (h), ejemplo con `"nombre": "Campaña octubre"`; `nombre: str` en `ListaPriorizadaDTO` y `ListaResumenDTO`), `Backend/app/application/listas/ports.py` (`nombre` en `NuevaLista` —`ValueError` si vacío o > 80—, `ListaDetalle`, `ListaResumen`), `Backend/app/application/listas/generar_lista.py` (usa el nombre recibido o `nombre_por_defecto(fecha efectiva)`), `Backend/tests/unit/application/listas/test_generar_lista.py`.
  - Docs: `docs/backend/12-modelo-y-listas.md` §Lista priorizada; `docs/API_CONTRACT.md` §Operaciones de negocio (listas); `.claude/rules/backend.md` §API, §Application; decisiones (g), (h).
  - Aceptación:
    - `GenerarListaDTO(nombre="  Campaña octubre  ")` → `"Campaña octubre"`; `None`/ausente → `None`; `"   "`, 81 caracteres o `"a\x07b"` → `ValidationError`; 80 caracteres → válido.
    - Caso de uso sin nombre y sin fecha, reloj `2026-09-29T15:00Z` → guarda `NuevaLista(nombre="Lista del 29 sep 2026")`; con `fecha_referencia=2026-10-02` → `"Lista del 2 oct 2026"`; con nombre → lo guarda tal cual. El DTO devuelto lleva `nombre`.
    - Fecha pasada → `422` como antes y sin guardar (el nombre no altera las reglas existentes). Dobles y datos de prueba actualizados (excepción mecánica); `mypy app` en verde.
  - Pruebas: unitarias.

- [x] **T9** · `infra` · Punto 5 · Repositorio de listas guarda y lee `nombre`
  - Archivos: `Backend/app/infrastructure/persistence/repositories/listas.py` (principal), `Backend/tests/integration/persistence/test_listas_repository.py`.
  - Docs: `.claude/rules/database.md` §Reparto de herramientas; `docs/backend/09-esquema-base-de-datos.md` §Retención; decisión (i).
  - Aceptación (PostgreSQL `app_db_test`):
    - `crear(NuevaLista(nombre="Campaña octubre", …))` → `obtener` y `listar` devuelven ese `nombre`; `ultima()` también. SQL parametrizado; sigue siendo una consulta por método (sin N+1); sin `commit`.
  - Pruebas: integración.

- [x] **T10** · `api` · Punto 5 · `nombre` en `POST /listas`, `GET /listas`, `GET /listas/{id}` y `/ultima`
  - Archivos: `Backend/app/api/routers/listas.py` (principal: ejemplos de request/response con `nombre` y ejemplo `400` de nombre inválido), `Backend/app/application/listas/consultar_listas.py` (`a_dto`, `_a_resumen`), `Backend/tests/integration/api/test_listas_api.py`.
  - Docs: `docs/API_CONTRACT.md` §Operaciones de negocio; `.claude/rules/backend.md` §API; decisiones (h), (j).
  - Aceptación (PostgreSQL de pruebas, `get_clock` fijo `2026-09-29T15:00Z`):
    - `POST /listas {}` → `201` con `"nombre": "Lista del 29 sep 2026"`; `POST {"nombre": "  Campaña octubre  "}` → `201` `"nombre": "Campaña octubre"`; `GET /listas/{id}`, `GET /listas/ultima` y `GET /listas` devuelven el mismo `nombre`.
    - `{"nombre": "   "}`, 81 caracteres, con carácter de control o `{"nombre": 5}` → `400 validation_error` con el formato único y **nada** guardado (conteo de `listas_priorizadas` igual).
    - `/openapi.json`: `GenerarListaDTO.nombre` opcional (`maxLength` 80), `nombre` requerido en `ListaPriorizadaDTO` y `ListaResumenDTO`, con ejemplos.
  - Pruebas: integración (API).

- [x] **T11** · `frontend` · Punto 5 · Cliente API y tipos con `nombre`
  - Archivos: `Frontend/src/features/lista/api/lista-api.ts` (principal: envía `nombre` si llega; mapea `nombre` en detalle y resumen), `Frontend/src/features/lista/types.ts`, `Frontend/src/features/lista/api/lista-api.handlers.ts` (MSW: nombre por defecto con el mismo formato y `400` para nombre vacío o > 80), `Frontend/src/features/lista/api/lista-api.test.ts`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada (fila `lista` · API), §MSW; decisiones (g), (h).
  - Aceptación:
    - `generarLista({ …, nombre: 'Campaña octubre' })` envía `"nombre":"Campaña octubre"` en el cuerpo; sin `nombre` no envía la clave (o `null`). `ListaPriorizada.nombre` y `ListaResumen.nombre` mapeados desde la respuesta.
    - `400` del servidor → `ApiError` con el mensaje del servidor. Los datos del handler son ficticios.
  - Pruebas: frontend.

- [x] **T12** · `frontend` · Punto 5 · Campo "Nombre de la lista" con sugerencia que sigue a la fecha
  - Archivos: `Frontend/src/features/lista/hooks/useLista.ts` (principal: `ParametrosLista.nombre`, `nombreSugerido(fechaIso)` con `fechaCorta`, regla de edición manual (j), validación local (h)), `Frontend/src/features/lista/pages/ListaPage.tsx` (campo con `label`, `maxLength` 80, error con `aria-describedby`), `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada (fila `lista` · página), `formatoFechas.ts`; `.claude/rules/frontend.md` §Formularios; decisiones (g), (h), (j).
  - Aceptación (Vitest + MSW, fecha del sistema simulada 2026-09-29):
    - Al entrar, "Nombre de la lista" = "Lista del 29 sep 2026". Cambiar la fecha a 2026-10-02 sin tocar el nombre → "Lista del 2 oct 2026".
    - Escribir "Campaña octubre" y luego cambiar la fecha → sigue "Campaña octubre". Si el usuario vuelve a escribir exactamente la sugerencia de la fecha actual, vuelve a seguir a la fecha.
    - Vacío o solo espacios → error local "Escriba un nombre para la lista." sin llamar a la API; > 80 no se puede escribir (`maxLength`) y, si llegara, error "El nombre puede tener hasta 80 caracteres.".
    - "Generar lista" envía el nombre recortado; la lista generada muestra ese nombre como título. `400` del servidor → `ErrorAlert` con el mensaje.
  - Pruebas: frontend.

- [x] **T13** · `frontend` · Punto 5 · Nombre como título y en "Listas anteriores"
  - Archivos: `Frontend/src/features/lista/components/TablaLista.tsx` (principal: título `h2` = `lista.nombre`), `Frontend/src/features/lista/components/HistorialListas.tsx` (`etiquetaLista` = `"<nombre> · <N> prioritarios"`), `Frontend/src/features/lista/components/TablaLista.test.tsx`, `Frontend/src/features/lista/components/HistorialListas.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada (resumen R-006, fila historial); decisión (j).
  - Aceptación:
    - Lista con `nombre` "Campaña octubre" → encabezado "Campaña octubre"; ya no aparece "Lista del 29 de septiembre de 2026". Las líneas "Rango de fechas: …" y "Socios priorizados para campañas: n" no cambian.
    - Nombre `"<b>x</b>"` se muestra como texto literal (sin HTML). Historial con `nombre` "Lista del 29 sep 2026", `topK` 25, `totalItems` 30 → opción "Lista del 29 sep 2026 · 25 prioritarios"; singular "1 prioritario" se mantiene.
  - Pruebas: frontend.

- [x] **T14** · `infra-deploy` · Suites, E2E, stack reconstruido y verificación en el navegador
  - Archivos: `Frontend/e2e/carga-lista-excel.spec.ts` (selectores: elegir archivo → "Revisar archivo" → "Confirmar carga"; si comprueba hojas del Excel, usar los nombres nuevos).
  - Docs: `docs/backend/10-docker.md` §Uso; `.claude/rules/deploy.md`; decisiones (e), (f).
  - Aceptación (el developer pega solo estados, códigos y conteos, sin datos personales):
    1. Backend `pytest`, `ruff check`, `ruff format --check`, `mypy app`, `lint-imports`; Frontend `npm test`, `npm run lint`, `npm run build`; E2E `carga-lista-excel` y `health` en verde contra el stack E2E (8081) reconstruido (aplica `0006`).
    2. **Solo si el usuario lo confirma** (decisión (f)): `scripts/reiniciar-base-historica.ps1` en el stack principal (tras `docker compose build`, para que `migrate` aplique `0006`) → `LISTO` y conteos socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0; el stack E2E (`docker compose -p mtabolic-e2e ps`) sigue igual antes y después. Si no lo confirma: `docker compose up -d --build` sin `down -v` (aplica `0006` sobre las listas existentes, que reciben su nombre por defecto) y conteos de `socios`, `membresias`, `cargas`, `listas_priorizadas`, `predicciones` antes/después idénticos. En ambos casos `alembic current` → `0006 (head)`.
    3. http://localhost:8080 → Carga: botón "Seleccionar archivo de carga (.xlsx)", ayuda "Suba la plantilla oficial del mes.", nombre del archivo tras elegir `plantilla_valida.xlsx`, "Revisar archivo" muestra la vista previa; **no** se confirma (R-007 (l)). Lista → campo "Nombre de la lista" con "Lista del <hoy corto>" que cambia al mover la fecha; "¿Cómo funciona esta lista?" con 4 secciones.
    4. http://localhost:8081 (stack E2E) → generar una lista con nombre "Prueba R-008" → título "Prueba R-008", aparece en "Listas anteriores" como "Prueba R-008 · N prioritarios" → descargar Excel: hojas "Socios prioritarios a contactar", "Otros socios por vencer", "Resumen" (primera fila "Nombre de la lista" = "Prueba R-008"); columnas de la tabla; sin Celular ni Score; motivos sin paréntesis.
  - Pruebas: E2E + verificación del stack y navegador.

- [x] **DOC-1** · (doc-agent) · Documentación
  - **Nueva carpeta** `Documentation/comandos/reiniciar-base-historica.md`: qué hace (paso a paso), cuándo usarlo, advertencias (borra cargas por plantilla, listas y predicciones y todo lo demás del volumen principal, sin vuelta atrás; reentrena el modelo v1 idéntico; nunca toca `mtabolic-e2e`), cómo ejecutarlo en Windows (PowerShell, incl. `-ExecutionPolicy Bypass -File` si hace falta) y en bash, flag `-Si`/`--si`, resultado esperado (1.410 socios, 2.748 membresías, 1 carga, 0 listas, 0 predicciones) y qué hacer si termina en `FALTAN_DATOS_HISTORICOS`. Enlace desde `Documentation/README.md` (nueva sección "Comandos"); **no** en el README raíz.
  - `DEVELOPMENT_GUIDELINES.md` §Excepciones: el reinicio manual del stack principal como borrado físico explícito del usuario (no una función de la app); si se ejecutó en T14, fecha/hora y conteos.
  - **Punto 5:** `docs/backend/09-esquema-base-de-datos.md` (columna `nombre`, CHECK, migración `0006` y su relleno); `docs/API_CONTRACT.md` (`nombre` en `POST /listas`, respuestas de listas y `400`); `docs/backend/12-modelo-y-listas.md` §Lista priorizada (nombre por defecto, decisiones (g)–(i)); `03-casos-de-uso.md` CU-04/CU-05 (nombre de la lista) si el doc-agent lo considera necesario; `06-como-funciona-la-lista.md` (cómo nombrar una lista). Nota breve en `docs/backend/10-docker.md` §Uso enlazando el nuevo documento.
  - `docs/backend/12-modelo-y-listas.md` §Excel: hojas, columnas, motivos sin aporte, resumen amigable (decisiones (a)–(c)); marcar como sustituido el párrafo de R-005 sobre score/aportes. `03-casos-de-uso.md` §15 CU-12 **Columnas** y la mención de hojas.
  - `06-como-funciona-la-lista.md`: §2 (hojas del Excel), §4 (el Excel ya no incluye los números), §5 (el Excel tiene las mismas columnas que la pantalla; sin celular ni monto); indicar que §5–§6 ya no están en la ayuda de la aplicación.
  - `docs/frontend/01-arquitectura.md`: §Inicio y Carga (estado `seleccionado`, `SelectorArchivo`, "Revisar archivo", "Confirmar carga", accesibilidad), párrafo de la ayuda (4 secciones) y §Lista priorizada (campo "Nombre de la lista", sugerencia que sigue a la fecha, título y opciones del historial con el nombre; sustituye R-006 (d)).
  - `05-cronograma-semana.md`: nota "Ajustes posteriores al Día 4 (R-008)". `ACTION_PLAN.md`: decisiones en DECISIONES IMPORTANTES (incluida la reversión de R-005 (e) y del celular en el Excel), R-008 a TERMINADOS. El doc-agent decide si hace falta ADR.

**Dependencias**
- Backend: T6 → T8 (usa `nombre_por_defecto`); T7 → T9; T8 → T9 → T10; **T8 → T1** (el Excel lee `ListaDetalle.nombre`). T6 y T7 pueden ir en paralelo.
- Frontend: T2 → T3; T4 independiente; T11 → T12 y T13 (T11 puede empezar ya con MSW; el contrato de T10 manda).
- T5 independiente. Todo (T1–T13) → T14 → DOC-1 (DOC-1 necesita la hora y los conteos de T14 si se ejecutó el reinicio).
- Orden sugerido: T6, T7, T8, T9, T10, T1, T2, T3, T4, T11, T12, T13, T5, T14.
- Externas: PostgreSQL con `app_db_test` (T1, T7, T9, T10); Docker Desktop y el `.env` local (T5, T14); stack E2E `mtabolic-e2e` con `.env.e2e` (T14); **confirmación explícita del usuario** para ejecutar el reinicio en T14.

**Riesgos**
1. **Borrado irreversible del stack equivocado o de datos útiles.** Un `down -v` sin `-p` o con el `.env` de otro stack borraría el volumen incorrecto; en el principal se pierden cargas confirmadas y listas. Mitigación: `-p proyectofinal` y `--env-file` fijos resueltos desde el script, confirmación con `BORRAR`, precondiciones antes de cualquier `docker`, ejecución real solo con confirmación del usuario (T5, T14) y advertencias en el documento.
2. **Migración `0006` sobre una base con listas y cambio de contrato en cadena.** Un `NOT NULL` sin relleno fallaría con listas existentes, y un relleno SQL con otro formato distinto al del dominio/frontend dejaría nombres incoherentes; añadir `nombre` a los dataclass sin valor por defecto rompe dobles, `verificar_lista.py` y fixtures. Mitigación: migración en tres pasos probada sobre datos (T7) con el mismo caso de fechas que T6 y T12, excepción mecánica declarada para dobles, `mypy`/suite completa en T8 y T14.
3. **Regresiones de accesibilidad y de pruebas en Carga (y quitar el celular del Excel).** Ocultar el `input` puede dejarlo sin foco o romper `getByLabel`/`setInputFiles` del E2E, y las 50+ aserciones de `CargaPage.test.tsx` asumen la vista previa automática. Mitigación: botón nativo enfocable que dispara el `input`, `input` etiquetado y oculto (T3), pruebas de teclado y E2E actualizado en T14. Quitar el celular deja al personal sin el contacto en el Excel (CU-12 lo listaba): decisión explícita del usuario; la API lo conserva y DOC-1 registra la reversión.

### R-007 — Día 4 del cronograma: carga por plantilla (CU-01) de punta a punta, integración real y ayuda de la lista · **DONE** 2026-09-29

**Cierre:** Backend 1.409 pytest, `ruff`, `format` (226), `mypy app` (104), `lint-imports` (7); Frontend 404 Vitest, `build`, `lint` 0; E2E `health` en 8080 y 8081, `carga-lista-excel` en verde en el stack aislado 8081 y saltado a propósito en 8080. Stack principal en `0005`, `LISTO`, datos intactos (socios 1.410, membresías 2.748, cargas 1); solo vista previa, sin confirmar. Seguridad diferida al día 7 (05 §1). Sin ADR: el contrato de cargas no cambia de forma (solo se retira el `501`), el modelo de datos solo gana un índice y (l) es una práctica operativa → [13-cargas](docs/backend/13-cargas.md), [10-docker](docs/backend/10-docker.md).

**Objetivo:** el personal sube la plantilla oficial, ve la vista previa con errores por fila y duplicados, confirma (todo o nada, sin duplicar) y la carga alimenta la lista (sin aviso de datos antiguos y con las membresías nuevas en la cartera); E2E carga → lista → Excel con datos sintéticos.

**Fuente:** [05 §3 Día 4](05-cronograma-semana.md) (D4-BD-01, D4-BE-01..04, D4-FE-01..03, D4-OP-01) · [03 §4 CU-01](03-casos-de-uso.md) (formato, flujo, excepciones, RN-01.1..11, criterios) · [04 §2 D-03, D-04](04-pendientes-para-iniciar-desarrollo.md) · `docs/API_CONTRACT.md` (`POST /cargas/vista-previa`, `POST /cargas`) · `Backend/tests/fixtures/generar_fixtures.py` (`TITULOS_REGISTROS`, `fila_plantilla`, `cedula_valida`) y `tests/fixtures/esperado.py` (`FILAS_CON_DATOS`, `FILAS_CON_ERROR`) · plantilla oficial `plantillas/Plantilla_Carga_Datos_Mtabolic.xlsx` **solo para comprobar estructura** (hojas y títulos; nunca se copian filas).

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Nada cae en `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance. **Fuera de R-007:** anular cargas (RN-01.3, sin endpoint en el contrato), reentrenar tras la carga (RN-01.11: la carga no dispara nada), alerta de datos del mes (D6-BE-06/D6-FE-04), CU-00, revisión de seguridad (día 7), D7-FE-01.
- **Proceso (05 §1):** TDD **solo en T5 y T6** (D4-BE-02: test en rojo primero). El resto, pruebas de sus criterios. Seguridad diferida a la revisión única del día 7. Sin login (RT-12): no hay pruebas de aislamiento entre usuarios; cada archivo nuevo de prueba de API/repositorio lo deja escrito en un comentario.
- **Sin datos personales reales:** pruebas solo con los fixtures sintéticos o libros construidos en el test (`tmp_path`) con nombres y cédulas ficticios (`cedula_valida`). Ni logs ni mensajes de error contienen nombres, cédulas, celulares ni correos: los errores citan fila y columna, nunca el valor.
- **Contrato:** se mantienen `VistaPreviaCargaDTO`, `ErrorFilaDTO` y `CargaDTO` de `app/application/cargas/dtos.py` (publicados el día 1); solo cambian los ejemplos y se retira el `501`.
- **Decisiones del planner (reversibles; se avisan al usuario):**
  - (a) **Conteos:** `filas_leidas` = filas con algún valor en A..N (O y P se ignoran siempre); `filas_validas` = sin error (incluye duplicadas); `filas_duplicadas` ⊆ válidas; nuevas = válidas − duplicadas = `filas_guardadas`. `puede_confirmar` = `filas_con_error == 0 and nuevas > 0`. `vencimiento_desde/hasta` = mín./máx. de H entre las válidas (`null` si no hay).
  - (b) **Duplicado (RN-01.8 / D-04):** misma identidad resuelta (socio existente) + `fecha_inicio` + `fecha_vencimiento` + `plan`, contra membresías no borradas (históricas o de cargas) **y** contra filas anteriores del mismo archivo. Una fila de un socio nuevo solo puede ser duplicada de otra fila del mismo archivo.
  - (c) **Enlace (RN-01.9 / D-03):** 1) cédula existente → ese socio (se cuenta como enlazado); 2) si no, exactamente un socio **sin cédula** con el mismo `nombre_normalizado` → se enlaza y se le asigna la cédula (celular y correo solo si estaban vacíos); 3) dos o más → socio nuevo y aviso `"Fila N: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."` (sin el nombre). Varias filas con la misma cédula nueva → un solo socio. Un candidato por nombre enlazado con una cédula ya no está disponible para otra cédula distinta del mismo archivo. `socios_enlazados` = socios existentes distintos a los que se asoció al menos una fila **nueva**.
  - (d) **Cédula histórica sin cero inicial:** el histórico guardó la cédula como dígitos (≥ 9, `normalizar_cedula`), así que las que empezaban por 0 quedaron con 9 dígitos. La búsqueda por cédula `0XXXXXXXXX` prueba también `XXXXXXXXX`; no se reescribe la cédula histórica.
  - (e) **Cédula en la celda:** texto → se quitan espacios; número (Excel pierde el cero) → `str(int)` y, si quedan 9 dígitos, se antepone `0`. Validación: 10 dígitos y verificador módulo 10 (coeficientes 2,1,2,…, como `cedula_valida`), **sin** reglas de provincia (CU-01 no las pide). Pasaporte: Observaciones contiene la palabra `PASAPORTE` (sin distinguir mayúsculas) → 5..20 caracteres `[A-Za-z0-9]`.
  - (f) **Títulos:** fila 1, columnas A..N, iguales a `TITULOS_REGISTROS[:14]` tras `strip()` (mayúsculas y tildes exactas). O y P no se validan. **Formato antiguo:** sin hoja `Registros` y con alguna hoja cuyo nombre es un mes (`MESES` de `alias_columnas.py`) → mensaje "El archivo tiene el formato antiguo de hojas mensuales; use la plantilla oficial de carga.".
  - (g) **Tamaño máximo:** 5 MB (`MAX_BYTES_PLANTILLA`); mayor → `413`. Nombre de archivo guardado = solo el nombre base, recortado a 255.
  - (h) **Catálogos y montos:** A, F, I se aceptan con `strip().upper()`; montos numéricos o texto con punto o coma decimal, ≥ 0 y con **máximo 2 decimales**, como `Decimal` (nunca `float` fuera del lector); asistencias entero 0..400 (acepta `7.0`). Fechas: celda fecha/fecha-hora o texto `AAAA-MM-DD`; G y H entre 2024-01-01 y 2035-12-31. Duración = H − G: `DIARIO` solo exige H > G; el resto 21..400.
  - (i) **Membresía guardada:** `origen=PLANTILLA`, `fecha_actividad = fecha_inicio`, `inicio_aproximado=False`, `estado_registro` informativo (RN-01.7), `plan_original`/`forma_pago_original` = texto de la celda, `referencia_origen=None`. Carga `tipo=PLANTILLA`, `fecha_carga = clock.now()`.
  - (j) **Concurrencia:** la confirmación toma `pg_advisory_xact_lock` (clave fija de cargas) antes de revalidar duplicados dentro de su transacción; dos confirmaciones del mismo archivo en paralelo → la segunda ve todo duplicado → `422`. No se añade índice único de duplicados (D-04 conserva duplicados exactos del histórico).
  - (k) **Códigos:** archivo no `.xlsx`/dañado, sin `Registros`, títulos distintos, formato antiguo, > 500 filas o sin campo `archivo` → `400 validation_error`; > 5 MB → `413`; migración no `COMPLETADA` → `409`; confirmar con filas con error → `422 domain_rule_violated` "Hay filas con error; corrija el archivo y vuelva a subirlo."; confirmar vacío o todo duplicado → `422` "El archivo no tiene filas nuevas para guardar.".
  - (l) **E2E y verificación con datos sintéticos en un stack aparte** (proyecto de Compose `mtabolic-e2e`, volumen propio, puertos 8081/8001/5433, `HISTORICO_DIR=./Backend/tests/fixtures/historico`). Motivo: confirmar una carga en el stack principal metería socios ficticios en la base con datos reales, y no se pueden borrar físicamente. **En el stack principal solo se hace la vista previa (no guarda) y la lista/Excel; confirmar allí queda a decisión del usuario.** La plantilla del E2E se genera en el test con fechas relativas a hoy y cédulas únicas por ejecución (devDependency `exceljs`, solo en `e2e/`).
  - (m) **Ayuda de la lista (D4-FE-03):** botón "¿Cómo funciona esta lista?" que abre el `Modal` de `shared/ui` con un resumen de 06 §1–§6 en texto estático del componente (no se carga el `.md` en tiempo de ejecución).
- **Excepción al límite de 4 archivos:** `__init__.py` vacíos; la línea `"0004 (head)"` → `"0005 (head)"` en `test_migrations_robustness.py` (T1); el registro del router en `main.py` si hiciera falta (ya está montado).

**Tareas**

- [x] **T1** · `db` · D4-BD-01 (1/2) · Índice de socios sin cédula por nombre (migración `0005`)
  - Archivos: `Backend/alembic/versions/0005_socios_nombre_sin_cedula.py` (principal), `Backend/app/infrastructure/persistence/models/historial.py`, `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`, `Backend/tests/integration/persistence/test_migrations.py`.
  - Docs: `.claude/rules/database.md` §Migraciones; `Documentation/docs/backend/09-esquema-base-de-datos.md` §Historial.
  - Aceptación:
    - `revision="0005"`, `down_revision="0004"`. `upgrade` crea `ix_socios_nombre_normalizado_sin_cedula` sobre `socios(nombre_normalizado)` `WHERE cedula IS NULL AND deleted_at IS NULL`; `downgrade` lo elimina. Aplica sobre una base con datos.
    - ORM declara el mismo índice parcial; `alembic check` sin diferencias; `alembic current` → `0005 (head)`; ciclo `downgrade 0004` → `upgrade head` funciona.
    - La consulta de duplicados reutiliza `ix_membresias_socio_id_fecha_vencimiento` (sin índice nuevo; lo deja escrito en el docstring de la migración).
  - Pruebas: unitaria (metadatos) + integración.

- [x] **T2** · `application` · Puertos y DTOs internos de cargas
  - Archivos: `Backend/app/application/cargas/ports.py` (principal), `Backend/app/domain/cargas/fila.py` (nuevo: `FilaPlantilla(fila: int, valores crudos A..N)`, `PlantillaLeida(filas: tuple[FilaPlantilla, ...])`), `Backend/tests/unit/application/cargas/test_ports.py`.
  - Contenido: `LectorPlantilla.leer(contenido: bytes) -> PlantillaLeida`; `ConsultasCarga`: `socios_por_cedulas(cedulas) -> dict[str, int]`, `socios_sin_cedula_por_nombres(nombres) -> dict[str, list[int]]`, `claves_existentes(socio_ids) -> set[ClaveMembresia]`; `EscrituraCarga`: `crear_socios(Sequence[NuevoSocio]) -> list[int]`, `asignar_cedula(socio_id, cedula, celular, correo)`, `insertar_membresias(...)`, `crear_carga(NuevaCarga) -> int` (reutiliza `NuevoSocio`/`NuevaMembresia`/`NuevaCarga` de `historial/ports.py`); `ContextoCargas` (`consultas`, `escritura`, `estado`, `bloquear()`, `commit()`) y `UnidadDeTrabajoCargas`. `ClaveMembresia` = `(socio_id, fecha_inicio, fecha_vencimiento, plan)` frozen.
  - Docs: `docs/backend/01-arquitectura.md` §Capas, §Patrón de un caso de uso; `docs/backend/11-historico.md` §Aplicación.
  - Aceptación:
    - Todos `Protocol` `runtime_checkable`; un doble en memoria pasa `isinstance` y `mypy`. Docstring: ningún repositorio hace `commit`/`rollback` ni expone `delete`.
    - `FilaPlantilla.fila < 2` → `ValueError`. `lint-imports` en verde (sin `openpyxl`, `sqlalchemy`, `pandas` en `domain`/`application`).
  - Pruebas: unitarias.

- [x] **T3** · `infra` · D4-BD-01 (2/2) · Repositorio de cargas: consultas de duplicados y de enlace, escritura
  - Archivos: `Backend/app/infrastructure/persistence/repositories/cargas.py` (principal: `SqlAlchemyConsultasCarga`, `SqlAlchemyEscrituraCarga` con `(session, clock)`), `Backend/tests/integration/persistence/test_cargas_repository.py`.
  - Docs: `.claude/rules/database.md` §Reparto de herramientas, §Pruebas; `docs/backend/09-esquema-base-de-datos.md` §Historial; decisiones (b), (c), (d).
  - Aceptación (PostgreSQL `app_db_test`, datos ficticios insertados en el test):
    - `socios_por_cedulas({"0912345678"})` encuentra un socio con cédula `"0912345678"` y otro con `"912345678"` (d); excluye `deleted_at`.
    - `socios_sin_cedula_por_nombres({"ANA PEREZ LOPEZ"})`: 1 socio sin cédula → `[id]`; 2 homónimos → 2 ids; un socio con cédula o borrado con ese nombre no aparece. `EXPLAIN` de la consulta usa `ix_socios_nombre_normalizado_sin_cedula` (con `SET enable_seqscan=off`).
    - `claves_existentes([s])` devuelve las claves de membresías no borradas de `s` (históricas y de plantilla); una borrada no aparece. Una sola consulta por método (sin N+1), SQL parametrizado.
    - `asignar_cedula` actualiza cédula, `updated_at` desde el reloj y solo rellena celular/correo vacíos; ninguna escritura hace `commit`.
  - Pruebas: integración.

- [x] **T4** · `infra` · D4-BE-01 · Lector de la plantilla
  - Archivos: `Backend/app/infrastructure/cargas/lector_plantilla.py` (principal: `LectorPlantillaOpenpyxl`, `read_only=True`, `data_only=True`, solo A..N, `MAX_FILAS_PLANTILLA = 500`), `Backend/app/domain/cargas/errores.py` (nuevo: `PlantillaInvalidaError(DomainError)` con motivos: dañado, sin `Registros`, títulos, formato antiguo, demasiadas filas), `Backend/tests/unit/infrastructure/cargas/test_lector_plantilla.py`.
  - Docs: `03-casos-de-uso.md` §4 Formato de entrada, Flujos alternativos; decisión (f); `tests/fixtures/esperado.py`.
  - Aceptación:
    - `plantilla_valida.xlsx` → 6 filas, con `fila` 2..7 y valores crudos (fechas como `date`/`datetime`); las fórmulas de O/P hasta la fila 501 no cuentan. Cada fixture da `FILAS_CON_DATOS`.
    - `plantilla_501_filas.xlsx` → `PlantillaInvalidaError` "El archivo tiene más de 500 filas con datos; divídalo en varios archivos." Uno de exactamente 500 (construido en `tmp_path`) se lee.
    - `Control Gym 2025 sintetico.xlsx` → mensaje de formato antiguo (f). Libro sin `Registros` y sin meses → "El archivo no tiene la hoja Registros.". Un título de A..N cambiado → "Los títulos de la hoja Registros no coinciden con la plantilla oficial.". Bytes que no son xlsx → "El archivo está dañado o no es un .xlsx válido.".
    - Filas vacías intermedias se saltan conservando el número de fila real. Ningún mensaje contiene valores de celdas.
  - Pruebas: unitarias con fixtures sintéticos y libros en `tmp_path`.

- [x] **T5** · `domain` · D4-BE-02 (1/2) · **TDD** · Cédula (módulo 10) y excepción de pasaporte
  - Archivos: `Backend/app/domain/cargas/documento.py` (principal: `normalizar_documento(valor) -> str`, `cedula_valida(texto) -> bool`, `documento_valido(texto, observaciones) -> bool`), `Backend/tests/unit/domain/cargas/test_documento.py` (se escribe **primero**, en rojo).
  - Docs: `03-casos-de-uso.md` §4 (columna C, criterios 3 y 4); decisión (e).
  - Aceptación:
    - `cedula_valida_fixture(1)` (generada como en `generar_fixtures.cedula_valida`) → `True`; mismo número con el verificador +1 → `False`; 9 u 11 dígitos, letras o vacío → `False`.
    - Celda numérica `912345678` → `"0912345678"`; `" 1700000019 "` → sin espacios.
    - `"AB12345"` con Observaciones `"pasaporte colombiano"` → válido; sin `PASAPORTE` → inválido; `"AB1"` o 21 caracteres o con `-` con `PASAPORTE` → inválido. Solo librería estándar.
  - Pruebas: unitarias (TDD).

- [x] **T6** · `domain` · D4-BE-02 (2/2) · **TDD** · Validación por fila
  - Archivos: `Backend/app/domain/cargas/validacion.py` (principal: `validar_fila(FilaPlantilla) -> FilaValida | tuple[ErrorFila, ...]`; `FilaValida` y `ErrorFila(fila, columna, motivo)` frozen), `Backend/tests/unit/domain/cargas/test_validacion.py` (primero, en rojo).
  - Docs: `03-casos-de-uso.md` §4 tabla de columnas A..P y RN-01.1, RN-01.7; decisiones (e), (h).
  - Aceptación — **una prueba por regla**, cada una con su columna y motivo:
    - A fuera del catálogo → error `A`; vacío → válido (`estado_registro=None`). B vacío o con menos de 5 letras tras `normalizar_nombre` → `B`. C (T5) → `C` "La cédula no tiene un dígito verificador válido." / "Falta la cédula.". E con correo mal formado → `E`; vacío → válido. F fuera de catálogo (`SEMANAL`) → `F`. G vacía, no fecha o fuera de 2024-01-01..2035-12-31 → `G`. H ≤ G → `H` "La fecha de vencimiento debe ser posterior a la de inicio.". Duración < 21 (no `DIARIO`) o > 400 → `H`; `DIARIO` de 1 día → válido. I fuera de catálogo → `I`. K negativo o con 3 decimales → `K`; vacío → válido. L vacío, negativo o no numérico → `L`. M `401`, `-1` o `2.5` → `M`; `7.0` → 7.
    - Una fila con varios fallos devuelve todos sus errores. Montos como `Decimal` (`40.5` → `Decimal("40.50")` o `Decimal("40.5")`, nunca `float`). Ningún motivo incluye el valor de la celda.
    - Cada fila de los fixtures: `FILAS_CON_ERROR` coincide (fila y campo).
  - Pruebas: unitarias (TDD).

- [x] **T7** · `domain` · D4-BE-03 (1/2) · Plan de carga: enlace y duplicados
  - Archivos: `Backend/app/domain/cargas/enlace.py` (principal: función pura `planificar(filas_validas, socios_por_cedula, candidatos_por_nombre, claves_existentes) -> PlanCarga` con, por fila, socio existente o nuevo, `duplicada`, `enlazado_por_nombre` y avisos), `Backend/tests/unit/domain/cargas/test_enlace.py`.
  - Docs: `03-casos-de-uso.md` §4 RN-01.8, RN-01.9 y criterios 1, 5, 6; `04` D-03, D-04; decisiones (b), (c).
  - Aceptación:
    - Cédula existente → socio existente, `socios_enlazados` 1. Nombre con 1 candidato sin cédula → enlazado y marcado para `asignar_cedula`. 2 candidatos → socio nuevo y aviso "Fila N: hay varios socios históricos con el mismo nombre; se creó un socio nuevo." (sin el nombre).
    - Clave existente en el histórico → `duplicada`. Dos filas idénticas del archivo → la segunda `duplicada`. Dos filas de la misma cédula nueva → un solo socio nuevo.
    - Candidato por nombre ya tomado por otra cédula del mismo archivo → la segunda crea socio nuevo. Resultado determinista (orden de fila).
  - Pruebas: unitarias.

- [x] **T8** · `application` · D4-BE-03 (2/2) · Casos de uso `PrevisualizarCarga` y `ConfirmarCarga`
  - Archivos: `Backend/app/application/cargas/procesar_carga.py` (principal: ambos handlers comparten `_analizar` = leer → validar → consultar → planificar; `CargaConErroresError`, `CargaSinFilasNuevasError`, `MigracionNoCompletadaError`), `Backend/tests/unit/application/cargas/test_procesar_carga.py`, `Backend/tests/unit/application/cargas/dobles.py`.
  - Docs: `03-casos-de-uso.md` §4 Flujo principal (pasos 1–8), RN-01.11; `docs/backend/01-arquitectura.md` §Patrón de un caso de uso; decisiones (a), (i), (j), (k).
  - Aceptación (dobles, reloj fijo `2026-09-29T15:00Z`):
    - Vista previa de 6 filas válidas nuevas → `filas_leidas 6, filas_validas 6, filas_con_error 0, filas_duplicadas 0, puede_confirmar True`, vencimientos mín./máx.; **no** llama a la escritura ni a `commit`.
    - Con 1 fila con error → `filas_con_error 1`, `errores` con fila/columna/motivo, `puede_confirmar False`. Confirmar ese archivo → `CargaConErroresError` y nada escrito.
    - Confirmar: `bloquear()` antes de consultar duplicados; crea socios nuevos, asigna cédulas, inserta membresías (`origen PLANTILLA`, decisión (i)) y la carga con conteos y `fecha_carga` del reloj, y hace **un** `commit`. Si la escritura falla a mitad → sin `commit`.
    - Confirmar dos veces el mismo contenido (el doble conserva lo escrito) → la segunda lanza `CargaSinFilasNuevasError`. Archivo vacío → vista previa `puede_confirmar False`; confirmar → `CargaSinFilasNuevasError`.
    - Migración ≠ `COMPLETADA` → `MigracionNoCompletadaError` en ambos. No se invoca ningún entrenamiento (RN-01.11). Ningún log con datos personales.
  - Pruebas: unitarias.

- [x] **T9** · `infra` · Unidad de trabajo de cargas y composición
  - Archivos: `Backend/app/infrastructure/persistence/unit_of_work_cargas.py` (principal: sesión única, `bloquear()` = `pg_advisory_xact_lock(<clave fija>)`, rollback si no hay `commit`), `Backend/app/api/dependencies.py` (`get_previsualizar_carga`, `get_confirmar_carga`, lector), `Backend/tests/integration/persistence/test_unit_of_work_cargas.py`.
  - Docs: `docs/backend/01-arquitectura.md` §Composition root; `unit_of_work_listas.py` como patrón; decisión (j).
  - Aceptación:
    - Salir sin `commit` o con excepción → no queda ninguna fila en `socios`, `membresias` ni `cargas`.
    - Con dos sesiones, la segunda `bloquear()` espera hasta que la primera confirma (prueba con hilo y `lock_timeout` corto → la segunda espera o expira, nunca pasan a la vez).
  - Pruebas: integración.

- [x] **T10** · `api` · D4-BE-04 · Endpoints `POST /cargas/vista-previa` y `POST /cargas`
  - Archivos: `Backend/app/api/routers/cargas.py` (principal: lectura acotada a 5 MB + 1 byte, mapeo de errores (k), ejemplos reales de `200`/`201`/`400`/`409`/`413`/`422`, sin `501`), `Backend/tests/integration/api/test_cargas_api.py` (nuevo), `Backend/tests/integration/api/test_contract_cargas.py` (quita `501`, comprueba ejemplos), `Backend/tests/integration/api/test_cargas_lista_api.py` (nuevo: la carga alimenta la lista).
  - Docs: `docs/API_CONTRACT.md` §Operaciones de negocio; `.claude/rules/backend.md` §API; decisiones (a), (g), (k).
  - Aceptación (PostgreSQL de pruebas, migración sintética completada, `get_clock` fijo):
    - `vista-previa` con `plantilla_valida.xlsx` → `200` `{filas_leidas:6, filas_validas:6, filas_con_error:0, filas_duplicadas:0, puede_confirmar:true}`; los conteos de `socios`/`membresias`/`cargas` no cambian.
    - `plantilla_cedula_invalida.xlsx` → `200` con `errores:[{fila:3, columna:"C", …}]`, `puede_confirmar:false`; `POST /cargas` → `422 domain_rule_violated` y nada guardado.
    - `POST /cargas` con la válida → `201` `{filas_guardadas:6, filas_duplicadas:0}`; repetir → vista previa `filas_duplicadas:6, puede_confirmar:false` y `POST` → `422`; `membresias` no crece.
    - Un socio histórico sin cédula con nombre único igual al de una fila → `socios_enlazados ≥ 1` y ahora tiene la cédula; con dos homónimos → socio nuevo y `avisos_enlace` con "Fila N". Una fila igual a una membresía migrada → duplicada.
    - `plantilla_501_filas.xlsx`, libro histórico sintético, `.txt` renombrado y sin campo `archivo` → `400` con el formato único; 5 MB + 1 → `413`; estado `PENDIENTE` → `409`.
    - **Alimenta la lista:** con el reloj a 45 días de la última carga, `POST /listas` → `advertencia_datos_antiguos: true`; tras `POST /cargas` con filas que vencen dentro del horizonte → `POST /listas` da `false` y incluye esas membresías (por cédula ficticia).
    - `/openapi.json`: ambos endpoints sin `501`, con los códigos y ejemplos anteriores.
  - Pruebas: integración (API).

- [x] **T11** · `frontend` · D4-FE-01 + D4-FE-02 · Carga contra la API real y resumen posterior
  - Archivos: `Frontend/src/features/carga/components/VistaPreviaCarga.tsx` (principal: `ResumenCarga` con "Filas leídas", "Filas guardadas", "Filas duplicadas (no se guardaron)", "Socios enlazados con su historia", sección "Para revisar" con `avisosEnlace` y enlace "Ver la lista de socios por vencer" a `/lista`), `Frontend/src/features/carga/api/carga-api.handlers.ts` (respuestas y mensajes iguales a los del backend: `400`, `409`, `413`, `422`), `Frontend/src/features/carga/pages/CargaPage.test.tsx`, `Frontend/src/features/carga/api/carga-api.test.ts`.
  - Docs: `docs/frontend/01-arquitectura.md` §Inicio y Carga, §MSW, §`shared/ui`.
  - Aceptación (Vitest + MSW):
    - Respuesta simulada `{filas_leidas:6, filas_guardadas:4, filas_duplicadas:2, socios_enlazados:1, avisos_enlace:["Fila 5: …"]}` → se ven los cuatro números, la sección "Para revisar" con el aviso y el enlace a `/lista`. Sin avisos → no aparece "Para revisar".
    - `413` → `ErrorAlert` "El archivo supera el tamaño máximo permitido."; `422` al confirmar → mensaje del servidor y vuelve a la vista previa.
    - MSW sigue solo en pruebas y con `VITE_API_MOCKS=true` en `dev` (sin cambios en `main.tsx`); ningún dato del handler es real.
  - Pruebas: frontend.

- [x] **T12** · `frontend` · D4-FE-03 · Botón de ayuda "¿Cómo funciona esta lista?"
  - Archivos: `Frontend/src/features/lista/components/AyudaLista.tsx` (principal, nuevo: botón + `Modal`), `Frontend/src/features/lista/components/AyudaLista.test.tsx` (nuevo), `Frontend/src/features/lista/pages/ListaPage.tsx`, `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `Documentation/06-como-funciona-la-lista.md` §1–§6; `docs/frontend/01-arquitectura.md` §`shared/ui` (`Modal`); decisión (m).
  - Aceptación:
    - En la página Lista (con o sin lista generada) hay un botón "¿Cómo funciona esta lista?"; al pulsarlo se abre un `role="dialog"` con título y secciones: qué hace la lista, socios prioritarios, niveles alto/medio/bajo, motivos, qué datos se muestran (celular solo en el Excel) y casos frecuentes (cargar datos cada mes, socios sin cédula, fecha pasada).
    - Cierra con "Cerrar" y con `Escape`; el foco vuelve al botón.
    - El texto no contiene "score", "Top K", "top", "horizonte", "percentil" ni "modelo v1" (prueba que recorre el contenido del diálogo).
  - Pruebas: frontend.

- [x] **T13** · `infra-deploy` · Stack E2E aislado con datos sintéticos
  - Archivos: `compose.yaml` (principal: puertos publicados con variables y valores por defecto actuales `DB_PORT:-5432`, `BACKEND_PORT:-8000`, `FRONTEND_PORT:-8080`), `.env.e2e.example` (nuevo: marcadores, puertos 5433/8001/8081, `CORS_ORIGINS=http://localhost:8081`, `HISTORICO_DIR=./Backend/tests/fixtures/historico`), `.env.example` (documenta las variables de puerto), `.gitignore` (`.env.e2e`).
  - Docs: `docs/backend/10-docker.md` §Uso; `.claude/rules/deploy.md` §Configuración y secretos; decisión (l).
  - Aceptación:
    - `docker compose up -d --build` con el `.env` actual sigue publicando 5432/8000/8080 solo en `127.0.0.1` (sin cambio para el usuario, sin `down -v`).
    - `docker compose -p mtabolic-e2e --env-file .env.e2e up -d --build` levanta un segundo stack con su propio volumen; `GET http://localhost:8001/api/v1/sistema/estado` → `LISTO` (migración sintética y modelo v1). Ninguna contraseña versionada.
  - Pruebas: verificación por comandos.

- [x] **T14** · `frontend` · D4-OP-01 · E2E Playwright: carga válida → generar lista → descargar Excel
  - Archivos: `Frontend/e2e/carga-lista-excel.spec.ts` (principal), `Frontend/e2e/plantilla-sintetica.ts` (nuevo: genera la plantilla en `test.info().outputPath` con `exceljs`: hoja `Registros`, títulos A..N exactos, 3 filas MENSUAL con inicio = hoy − 20 y vencimiento = hoy + 10, nombres "SOCIO PRUEBA E2E …" y cédulas módulo 10 únicas por ejecución), `Frontend/package.json` (`exceljs` en `devDependencies`), `Frontend/README.md` (cómo correrlo contra el stack E2E).
  - Docs: `docs/frontend/01-arquitectura.md` §Pruebas; `.claude/rules/frontend.md` §Pruebas; decisión (l).
  - Aceptación (`E2E_BASE_URL=http://localhost:8081`):
    - Carga → subir el archivo → vista previa "3" válidas y 0 errores → "Confirmar" → resumen con 3 guardadas.
    - Lista → "Generar lista" con los valores por defecto → sin aviso de datos antiguos; aparece al menos uno de los socios "SOCIO PRUEBA E2E".
    - "Descargar Excel" → `download.suggestedFilename()` termina en `.xlsx` y el archivo no está vacío.
    - Pasa dos veces seguidas sin `down -v`. `health.spec.ts` sigue en verde.
  - Pruebas: E2E.

- [x] **T15** · `infra-deploy` · Stack principal reconstruido y verificación en el navegador
  - Archivos: ninguno (salvo que falle algo del stack).
  - Docs: `docs/backend/10-docker.md` §Uso; `.claude/rules/deploy.md`; decisión (l).
  - Aceptación (el developer pega solo estados, códigos y conteos, sin datos personales):
    1. Suites: Backend `pytest`, `ruff check`, `ruff format --check`, `mypy app`, `lint-imports`; Frontend `npm test`, `npm run lint`, `npm run build`; E2E (T14) en verde contra el stack E2E.
    2. Stack principal: `docker compose run --rm migrate` (aplica `0005`) y `docker compose up -d --build` (sin `down -v`) → `LISTO`, modelo v1; conteos de `socios`, `membresias`, `cargas` antes/después idénticos.
    3. En http://localhost:8080: Carga con `plantilla_valida.xlsx` → vista previa sin errores; **no** se confirma (decisión (l), salvo que el usuario diga lo contrario). Lista → generar → botón de ayuda abre la explicación → Excel descargado.
    4. En http://localhost:8081 (stack E2E): recorrido completo carga → confirmar → lista → Excel en el navegador.
  - Pruebas: verificación del stack y navegador.

- [x] **DOC-1** · (doc-agent) · Documentación
  - `docs/backend/13-cargas.md` (nuevo: lector, validación, enlace, duplicados, transacción y bloqueo, decisiones (a)–(k)) + índice en `Documentation/README.md`; `docs/backend/09-esquema-base-de-datos.md` (índice `0005`); `docs/API_CONTRACT.md` (códigos y mensajes reales de cargas, 5 MB); `docs/backend/10-docker.md` (stack E2E y variables de puerto); `docs/frontend/01-arquitectura.md` (resumen de carga, ayuda de la lista, E2E y `exceljs`); `03-casos-de-uso.md` §4 solo si una decisión lo precisa (d), (e), (h).
  - `05-cronograma-semana.md`: columna/nota de avance del Día 4 (estado por ID), pruebas, desviaciones, "Qué puede probar el usuario" y pendientes; `ACTION_PLAN.md`: decisiones en DECISIONES IMPORTANTES, R-007 a TERMINADOS, PRÓXIMO = Día 5. El doc-agent decide si (l) o (d) merecen ADR.

**Dependencias**
- Backend: T1 → T3. T2 → T3, T4, T8. T5 → T6 → T7 → T8. T3 y T8 → T9 → T10. T4 → T8 (el doble del lector no depende, pero T10 sí de T4).
- Frontend: T11 y T12 pueden empezar ya (MSW). T13 es independiente. T10, T11 y T13 → T14. Todo → T15 → DOC-1.
- Externas: PostgreSQL con `app_db_test` (T1, T3, T9, T10); Docker Desktop (T13–T15); red para instalar `exceljs` (T14); la plantilla oficial solo para cotejar títulos en T4.

**Riesgos**
1. **Duplicados por concurrencia o por cédula sin cero.** Dos confirmaciones simultáneas o la cédula histórica de 9 dígitos podrían duplicar socios o membresías. Mitigación: bloqueo consultivo de transacción y revalidación dentro de ella (T9, T10), búsqueda con ambas variantes (T3), prueba de "cargar dos veces no duplica" (T8, T10, T14).
2. **Datos sintéticos en la base con datos reales.** Confirmar cargas de prueba en el stack principal deja socios ficticios que no se pueden borrar físicamente. Mitigación: E2E y confirmación solo en el stack `mtabolic-e2e` (T13–T15); en el principal, solo vista previa.
3. **Fugas de datos personales y archivos hostiles.** Mensajes de error o logs con cédulas/nombres, o un xlsx enorme o dañado. Mitigación: motivos sin valores de celda (T4, T6), lectura acotada a 5 MB y `read_only` solo A..N (T4, T10), `400` controlado ante archivos dañados; revisión completa el día 7.

### R-006 — Ajustes de presentación de la lista (continuación de R-005): borrado de las listas de prueba, nombres cortos en "Listas anteriores", resumen con rango de fechas, sin columna Celular en pantalla · **DONE** 2026-09-29

**Cierre:** Frontend 375 Vitest, `lint` 0, `build`; E2E 1/1; stack Docker verificado en el navegador (lista del 2026-09-29, 30 días, 25; Excel de 3 hojas con Celular y Cédula). Borrado de T4: 2026-09-30 01:50:06 UTC, `predicciones` 117 y `listas_priorizadas` 3, resto intacto ([09](docs/backend/09-esquema-base-de-datos.md)). Seguridad diferida al día 7 (05 §1). Sin ADR: operación puntual que no cambia la regla, registrada en [DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md).

**Objetivo:** la base de Docker queda sin listas de prueba (borrado físico puntual y documentado) y la pantalla Lista se lee con nombres cortos, un resumen claro por rango de fechas y sin el celular.

**Fuente:** petición del usuario (continuación de R-005) · `docs/frontend/01-arquitectura.md` §Lista priorizada, Excel e historial · `06-como-funciona-la-lista.md` §5 · `DEVELOPMENT_GUIDELINES.md` §Excepciones · `docs/backend/09-esquema-base-de-datos.md` §Retención.

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Nada cae en `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance. **Sin cambios en el backend ni en la API** (el celular sigue en la API y en el Excel). No se reentrena ni se recargan datos.
- **Proceso (05 §1):** pruebas de los criterios de aceptación; sin TDD; revisión de seguridad diferida a la revisión única del día 7. Sin login: no hay pruebas de aislamiento.
- **Excepción puntual a "nada crítico se borra físicamente"** (decisión explícita del usuario, 2026-09-29): son datos de prueba. Se borran **solo** `predicciones` y `listas_priorizadas` en la base del stack de Docker; **no** se tocan `socios`, `membresias`, `cargas`, `modelos`, `intentos_reentrenamiento`, `estado_sistema`, `campanias` ni `gestiones_retencion`. No es una regla nueva: el código sigue sin exponer `delete` sobre listas. No se crea ningún script versionado reutilizable; el SQL exacto queda escrito en la documentación (DOC-1).
- **(B) Registrado, NO se implementa en R-006** (lo añade DOC-1 al cronograma): **D7-FE-01** · Mejora del diseño visual de la aplicación (jerarquía, espaciado, tipografía y color con los tokens de `shared/ui`, sin cambiar comportamiento).
- **Decisiones del planner (reversibles; se avisan al usuario):**
  - (a) Meses abreviados con una tabla fija `ene feb mar abr may jun jul ago sep oct nov dic` (no `Intl` `month: 'short'`, que en es-EC da "sept." y depende del ICU del navegador). Sin punto final.
  - (b) Rango = `fechaGeneracion` … `fechaGeneracion + horizonteDias` (aritmética en UTC). Mismo año → "29 sep – 29 oct 2026"; distinto año → "20 dic 2026 – 10 ene 2027". Mismo mes → "1 oct – 15 oct 2026" (sin compactar). Separador " – " (en dash con espacios).
  - (c) En "Listas anteriores" el número de prioritarios es `min(topK, totalItems)` (`GET /listas` no trae el conteo de `dentro_top_k`; con la priorización actual coinciden). Sin cambio de contrato.
  - (d) El título "Lista del 29 de septiembre de 2026" no cambia. Los títulos de las dos tablas ("Socios prioritarios a contactar" / "Otros socios por vencer") tampoco.

**Tareas**

- [x] **T1** · `frontend` · Formato corto de fechas y rango
  - Archivos: `Frontend/src/features/lista/components/formatoFechas.ts` (principal, nuevo: `fechaCorta(iso)`, `rangoFechas(isoDesde, dias)`), `Frontend/src/features/lista/components/formatoFechas.test.ts` (nuevo).
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Lista priorizada, Excel e historial; decisiones (a), (b).
  - Aceptación:
    - `fechaCorta("2026-09-29")` → `"29 sep 2026"`; `"2026-01-05"` → `"5 ene 2026"`.
    - `rangoFechas("2026-09-29", 30)` → `"29 sep – 29 oct 2026"`; `("2026-12-20", 21)` → `"20 dic 2026 – 10 ene 2027"`; `("2026-10-01", 14)` → `"1 oct – 15 oct 2026"`; `("2026-02-28", 1)` → `"28 feb – 1 mar 2026"`.
    - Mismo resultado con la zona del proceso en `America/Guayaquil` y en `UTC` (sin desplazamiento de día). Funciones puras, sin `Date.now()`.
  - Pruebas: frontend (unitarias Vitest).

- [x] **T2** · `frontend` · Nombres cortos en "Listas anteriores"
  - Archivos: `Frontend/src/features/lista/components/HistorialListas.tsx` (principal: `etiquetaLista` usa `fechaCorta`), `Frontend/src/features/lista/components/HistorialListas.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada, Excel e historial; decisión (c).
  - Aceptación:
    - Lista del 2026-09-29 con `topK` 25 y `totalItems` 30 → opción `"29 sep 2026 · 25 prioritarios"`. `topK` 1 → `"… · 1 prioritario"`. `topK` 25 y `totalItems` 3 → `"… · 3 prioritarios"`; `totalItems` 0 → `"… · 0 prioritarios"`.
    - Las opciones no contienen "Lista del" ni "socios"; siguen de la más reciente a la más antigua; la etiqueta "Listas anteriores" se mantiene. Sin listas, el selector no se muestra (comportamiento actual).
  - Pruebas: frontend.

- [x] **T3** · `frontend` · Resumen con rango de fechas y sin columna Celular
  - Archivos: `Frontend/src/features/lista/components/TablaLista.tsx` (principal), `Frontend/src/features/lista/components/TablaLista.test.tsx`, `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada, Excel e historial, §`shared/ui` (sin estilos nuevos); decisiones (b), (d).
  - Aceptación (lista del 2026-09-29, horizonte 30, 30 ítems, 25 `dentroTopK`):
    - Título "Lista del 29 de septiembre de 2026" (sin cambios).
    - Resumen de exactamente dos líneas: "Rango de fechas: 29 sep – 29 oct 2026" y "Socios priorizados para campañas: 25" (= filas `dentroTopK`). Con 0 ítems → "Socios priorizados para campañas: 0".
    - Ya **no** aparecen los textos "Socios por vencer en los próximos" ni "Socios prioritarios a contactar: " en el resumen (se elimina `textoPorVencer`).
    - Columnas de ambas tablas: Prioridad, Nombre, Cédula, Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales. No existe el encabezado "Celular" ni se renderiza ningún número de celular de los datos simulados.
    - `Prediccion.celular` y el cliente API no cambian (`lista-api.test.ts` sigue en verde).
  - Pruebas: frontend.

- [x] **T4** · `infra-deploy` · Borrado físico puntual de las listas de prueba en el stack de Docker
  - Archivos: ninguno de código. Operación manual sobre el servicio `db` (el developer pega solo comandos, conteos y códigos, sin datos personales).
  - Docs: `docs/backend/10-docker.md` §Uso; `docs/backend/09-esquema-base-de-datos.md` §Retención; `.claude/rules/deploy.md`.
  - Procedimiento: `docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1` con **una sola transacción**: `BEGIN;` → conteos previos → comprobar `SELECT count(*) FROM gestiones_retencion` = 0 (si no, `ROLLBACK` y `BLOCKED`) → `DELETE FROM predicciones;` → `DELETE FROM listas_priorizadas;` → conteos posteriores → `COMMIT;`. Credenciales tomadas del `.env` local, nunca escritas en el comando pegado ni en la documentación. Sin `TRUNCATE ... CASCADE`, sin `down -v`, sin reiniciar secuencias.
  - Aceptación:
    - Antes y después se registran los conteos de `socios`, `membresias`, `cargas`, `modelos`, `intentos_reentrenamiento`, `campanias`, `gestiones_retencion`, `estado_sistema`: **idénticos**.
    - Después: `listas_priorizadas` = 0 y `predicciones` = 0. Se anotan cuántas filas se borraron de cada una y la fecha y hora.
    - `GET /api/v1/sistema/estado` → `200` `LISTO`, modelo v1. `GET /api/v1/listas` → `200 []`. `GET /api/v1/listas/ultima` → `404`.
  - Pruebas: verificación manual por comandos.

- [x] **T5** · `infra-deploy` · Frontend reconstruido y verificación en el navegador
  - Archivos: ninguno (salvo que falle algo del stack).
  - Docs: `docs/backend/10-docker.md` §Uso; `.claude/rules/deploy.md`.
  - Aceptación:
    1. Suites: Frontend `npm test`, `npm run lint`, `npm run build` en verde; E2E Playwright en verde (si alguna aserción usa los textos antiguos, se ajusta en la misma tarea).
    2. `docker compose up -d --build frontend` (sin `down -v`) → http://localhost:8080 carga; la pantalla Lista sin listas se muestra sin error y sin selector "Listas anteriores".
    3. Generar la lista con los valores por defecto (hoy, 30 días, 25) → `201`; se ve "Lista del <hoy largo>", "Rango de fechas: <hoy corto> – <hoy+30 corto>", "Socios priorizados para campañas: <n>", sin columna Celular; "Listas anteriores" muestra "<d mmm aaaa> · <n> prioritarios".
    4. El Excel de esa lista sigue teniendo la columna Celular y Cédula (hoja `top_{K}`).
  - Pruebas: verificación del stack y navegador.

- [x] **DOC-1** · (doc-agent) · Documentación
  - **Registro del borrado** (qué: todas las filas de `listas_priorizadas` y `predicciones` del stack de Docker, con los conteos de T4; cuándo: fecha y hora de T4; por qué: datos de prueba, decisión explícita del usuario; cómo: el SQL exacto de T4 sin credenciales; qué no se tocó): nueva fila/nota en `DEVELOPMENT_GUIDELINES.md` §Excepciones como **excepción puntual y única** (no cambia la regla), nota en `docs/backend/09-esquema-base-de-datos.md` junto a la excepción de `deleted_at` ("Ninguna se borra" salvo la operación puntual de R-006), y línea en `ACTION_PLAN.md` §DECISIONES IMPORTANTES. El doc-agent decide si además merece ADR.
  - `docs/frontend/01-arquitectura.md` §Lista priorizada: resumen (rango + priorizados), columnas sin Celular, opciones del historial "<d mmm aaaa> · <n> prioritarios", helper `formatoFechas.ts`, decisiones (a)–(d).
  - `06-como-funciona-la-lista.md` §5 (qué datos se muestran: sin celular en pantalla, sí en el Excel; rango de fechas; socios priorizados para campañas) y §2 si nombra el resumen antiguo.
  - `05-cronograma-semana.md`: nota "Ajustes posteriores (R-006)" tras la de R-005; añadir **D7-FE-01** (mejora del diseño visual, B, depende de todo el frontend, "Hecho cuando: revisión visual con el usuario y suites en verde") como pendiente en el Día 7.
  - `ACTION_PLAN.md`: D7-FE-01 en PRÓXIMO; mover R-006 a TERMINADOS.

**Dependencias**
- T1 → T2 y T3 (T2 y T3 independientes entre sí). T4 es independiente del código y puede ir en cualquier momento antes de T5. T5 requiere T1–T4. DOC-1 al final, con los conteos y la hora de T4 y la salida de T5.
- Externas: Docker Desktop con el stack levantado y el `.env` local (T4, T5).

**Riesgos**
1. **Borrado destructivo irreversible.** Un `DELETE` mal dirigido (otra tabla, otra base, `CASCADE`) perdería datos reales. Mitigación: una transacción con `ON_ERROR_STOP`, solo dos `DELETE` explícitos sin `CASCADE`, precondición `gestiones_retencion = 0` (además la FK bloquearía), conteos antes/después de las tablas que no se tocan y `COMMIT` solo si coinciden.
2. **Desfase de día en el rango.** Construir fechas con `new Date('AAAA-MM-DD')` en hora local puede mostrar el día anterior en Ecuador. Mitigación: aritmética en UTC y pruebas con dos zonas (T1).
3. **Pruebas con textos antiguos.** `ListaPage.test.tsx`, `TablaLista.test.tsx`, `HistorialListas.test.tsx` y posiblemente el E2E aseveran "Socios por vencer…", "Celular" y "Lista del … socios prioritarios". Mitigación: se actualizan en T2/T3 y se revisa el E2E en T5.

### R-005 — Ajustes de la lista priorizada tras el Día 3 (fecha ≥ hoy, horizonte ≤ 31, cédula en lugar de correo, sin socios sin cédula, pantalla para usuario no técnico) y guía funcional · **DONE** 2026-09-29

**Cierre:** Backend 1.122 pytest, `ruff`, `mypy app` (92), `lint-imports` (7); Frontend 347 Vitest, `build`, `lint` 0; `verificar_lista.py` salida `0`. Seguridad diferida al día 7 (05 §1). Decisión de contrato → [ADR-006](adr/ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md).

**Objetivo:** la lista solo se genera desde hoy hacia adelante (máx. 31 días), muestra la cédula y no el correo, excluye a los socios sin cédula y se lee sin términos técnicos; queda documentado cómo funciona para el personal del gimnasio.

**Fuente:** petición del usuario tras el Día 3 · [03 §7 CU-04, §15 CU-12](03-casos-de-uso.md) · `docs/backend/12-modelo-y-listas.md` §Lista priorizada, §Excel · `docs/API_CONTRACT.md` §Operaciones de negocio · `docs/frontend/01-arquitectura.md` §Lista priorizada, Excel e historial.

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Nada cae en `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance. No se reentrena ni se recargan datos: el modelo v1 no cambia.
- **Proceso (05 §1):** sin TDD; pruebas de los criterios de aceptación. Revisión de seguridad diferida a la revisión única del día 7. Sin login (RT-12): no hay pruebas de aislamiento entre usuarios.
- **(B) Registrado, NO se implementa en R-005** (lo añade DOC-2 al cronograma):
  - **D4-FE-03** · Botón de ayuda "¿Cómo funciona esta lista?" en la pantalla Lista, con el texto de la guía funcional (DOC-1).
  - **D6-BE-06 / D6-FE-04** · Alerta en Inicio cuando no hay ninguna carga (CU-01) con `fecha_carga` dentro del mes actual (fecha de negocio): "Aún no se han cargado los datos de este mes".
- **Decisiones del planner (reversibles; se avisan al usuario):**
  - (a) **"Hoy" = fecha de negocio en Ecuador** (UTC−5 fijo, sin horario de verano): `hoy_en_negocio(clock.now())`. Evita que entre las 19:00 y las 24:00 el backend (UTC) considere "mañana" y rechace la fecha que el navegador propone como hoy. La fecha por defecto del `POST` pasa a ser también esa.
  - (b) Fecha anterior a hoy → `422 domain_rule_violated` "La fecha de la lista debe ser hoy o posterior." (depende del reloj: es regla de negocio). Horizonte fuera de 1..31 → `400 validation_error` (validación de entrada).
  - (c) **Scripts de verificación:** `verificar_lista.py` sigue usando fechas pasadas por su propio camino (reloj fijo = la fecha pedida, sin API) y marca a todas las membresías como "con cédula" para seguir comparando con el notebook. Consecuencia: la lista de la app puede diferir del top 25 del notebook si en él hay socios sin cédula; es por diseño.
  - (d) Las listas ya guardadas son inmutables (RN-04.5): pueden contener socios sin cédula (se muestran con "—") y horizontes > 31; los DTOs de **respuesta** mantienen `horizonte_dias` 1..365. Ninguna respuesta vuelve a incluir `correo`.
  - (e) El Excel cambia solo la columna Correo → Cédula; conserva el score y los factores con su aporte (la petición de quitarlos es solo para la pantalla).
  - (f) Socios prioritarios frente al resto: dos tablas con título propio ("Socios prioritarios a contactar" y "Otros socios por vencer"), sin columna Top ni depender del color.
  - (g) El campo fecha viene relleno con hoy; si el usuario lo vacía, se muestra un error local (ya no se envía `null`).
- **Excepción al límite de 4 archivos:** actualizar constructores en dobles y datos de prueba existentes (`tests/unit/application/listas/dobles.py`, `tests/unit/application/historial/test_ports.py`, `tests/unit/application/listas/test_ports.py`, `tests/integration/api/listas_datos.py`, `tests/integration/api/test_listas_excel_api.py`) es mecánico y no cuenta.

**Tareas**

- [x] **T1** · `domain` · Fecha de negocio ("hoy" en Ecuador)
  - Archivos: `Backend/app/domain/common/fechas.py` (principal: `ZONA_NEGOCIO = timezone(timedelta(hours=-5))` y `hoy_en_negocio(instante: datetime) -> date`), `Backend/tests/unit/domain/common/test_fechas.py`.
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas; `.claude/rules/backend.md` §Dominio (reloj inyectable).
  - Aceptación:
    - `2026-09-30T03:30Z` → `2026-09-29`; `2026-09-29T05:00Z` → `2026-09-29`; `2026-09-29T04:59Z` → `2026-09-28`.
    - Un `datetime` sin zona → `ValueError`. Solo librería estándar; no llama a `datetime.now()`/`date.today()`.
    - Las pruebas de `sumar_meses` siguen en verde.
  - Pruebas: unitarias.

- [x] **T2** · `infra` · Las membresías para predecir indican si el socio tiene cédula
  - Archivos: `Backend/app/application/historial/ports.py` (principal: `MembresiaParaPrediccion.socio_con_cedula: bool`, sin valor por defecto), `Backend/app/infrastructure/persistence/repositories/historial.py` (`listar_para_prediccion` lo rellena con `socios.cedula IS NOT NULL`), `Backend/tests/integration/persistence/test_historial_repositories.py`, `Backend/scripts/verificar_lista.py` (`_membresias` pone `socio_con_cedula=True`, con comentario de la decisión (c)).
  - Docs: `docs/backend/11-historico.md` §Aplicación, §Infraestructura; `docs/backend/09-esquema-base-de-datos.md` §Historial.
  - Aceptación:
    - Socio con cédula → `True`; socio con `cedula NULL` → `False`. Sigue siendo **una** consulta (sin N+1) y excluye `deleted_at`.
    - `python scripts/verificar_lista.py ../plantillas` (libros reales, local) sigue saliendo con `0`; `tests/unit/scripts/test_verificar_lista.py` en verde.
  - Pruebas: integración + unitaria del script.

- [x] **T3** · `application` · `GenerarLista`: fecha ≥ hoy, horizonte ≤ 31 y sin socios sin cédula
  - Archivos: `Backend/app/application/listas/generar_lista.py` (principal: `FechaReferenciaPasadaError(DomainError)`; fecha por defecto `hoy_en_negocio(clock.now())`; filtro de la cartera por `socio_con_cedula` **después** de quitar a los que ya renovaron y **antes** de predecir y priorizar), `Backend/app/application/listas/dtos.py` (solo `GenerarListaDTO.horizonte_dias` `le=31` y su ejemplo), `Backend/tests/unit/application/listas/test_generar_lista.py`, `Backend/tests/unit/application/listas/dobles.py`.
  - Docs: `03-casos-de-uso.md` §7 (flujo, RN-04.x); `docs/backend/12-modelo-y-listas.md` §Lista priorizada; decisiones (a), (b), (c).
  - Aceptación (dobles, reloj en `2026-09-29T15:00Z`):
    - `fecha_referencia=2026-09-28` → `FechaReferenciaPasadaError` y **no** se guarda nada ni se llama al predictor. `2026-09-29` y `2026-10-15` → lista guardada. Sin fecha → `fecha_generacion = 2026-09-29`; con el reloj en `2026-09-30T02:00Z` → `2026-09-29`.
    - `GenerarListaDTO(horizonte_dias=31)` válido; `32` y `0` → `ValidationError`.
    - Cartera de 5 socios, 2 sin cédula, `top_k=2`: la lista tiene 3 ítems, ninguno de los sin cédula; `prioridad` 1..3 sin huecos, en orden de score; `dentro_top_k` en exactamente 2 filas. El predictor recibe solo 3 filas. Las variables de los que quedan siguen usando el historial completo del socio.
    - Todos sin cédula → lista válida con 0 ítems.
    - Ningún log ni mensaje de error contiene cédulas ni nombres.
  - Pruebas: unitarias.

- [x] **T4** · `application` · Ítem de la lista con cédula y sin correo
  - Archivos: `Backend/app/application/listas/ports.py` (principal: `ItemLista.correo` → `cedula: str | None`), `Backend/app/application/listas/dtos.py` (`PrediccionDTO`: se elimina `correo`, se añade `cedula: str | None`), `Backend/app/application/listas/consultar_listas.py` (`a_dto`), `Backend/tests/unit/application/listas/test_consultar_listas.py`.
  - Docs: `docs/API_CONTRACT.md` §Convenciones de los DTOs; decisión (d).
  - Aceptación:
    - `PrediccionDTO.model_json_schema()` no tiene `correo` y sí `cedula` (string o null). Serializar un ítem con cédula `"0912345678"` conserva el cero inicial (string).
    - `a_dto` copia la cédula; con `None` → `null`.
  - Pruebas: unitarias. **Se entrega junto con T5** (hasta entonces `mypy` marca el repositorio).

- [x] **T5** · `infra` · Repositorio de listas lee la cédula
  - Archivos: `Backend/app/infrastructure/persistence/repositories/listas.py` (principal: `obtener` selecciona `Socio.cedula` en lugar de `Socio.correo`), `Backend/tests/integration/persistence/test_listas_repository.py`.
  - Docs: `docs/backend/09-esquema-base-de-datos.md` §Retención.
  - Aceptación:
    - `obtener(id)` devuelve la cédula del socio en cada ítem; ninguna consulta del repositorio lee `socios.correo` (se comprueba con `grep` en el test).
    - Una lista antigua con un socio sin cédula → `cedula=None` (la lista sigue inmutable). `mypy app` en verde.
  - Pruebas: integración.

- [x] **T6** · `infra` · Excel: columna Cédula en lugar de Correo
  - Archivos: `Backend/app/infrastructure/exportacion/excel_lista.py` (principal), `Backend/tests/unit/infrastructure/exportacion/test_excel_lista.py`.
  - Docs: `03-casos-de-uso.md` §15 (columnas, RN-12.x); `docs/backend/12-modelo-y-listas.md` §Excel; decisión (e).
  - Aceptación (leyendo el archivo con openpyxl):
    - Las hojas `top_{K}` y `cartera_completa` tienen la columna "Cédula" en la posición de "Correo"; no existe ninguna columna ni celda con correo.
    - La cédula `"0912345678"` se guarda como **texto** con el cero inicial; `None` → celda vacía. Una cédula que empieza por `=`, `+`, `-` o `@` lleva el prefijo `'` y no hay ningún `<f>` en el XML.
    - Mismos bytes para la misma lista (determinismo de R-004 intacto).
  - Pruebas: unitarias.

- [x] **T7** · `api` · Contrato de `POST /listas` y ejemplos
  - Archivos: `Backend/app/api/routers/listas.py` (principal: ejemplos con `cedula` y sin `correo`; `responses` de `POST` con `422` y el mensaje real; descripción del `400` "Horizonte fuera de 1..31, K menor que 1 o fecha inválida"), `Backend/tests/integration/api/test_listas_api.py`, `Backend/tests/integration/api/test_contract_listas.py`, `Backend/tests/integration/api/test_listas_api_migracion.py`.
  - Docs: `docs/API_CONTRACT.md` §Operaciones de negocio; `.claude/rules/backend.md` §API; decisión (b).
  - Aceptación (PostgreSQL de pruebas, `get_clock` sobrescrito con un reloj fijo; los tests que usaban `2026-08-31` fijan el reloj en esa fecha y el horizonte 120 pasa a ≤ 31):
    - Reloj en 2026-08-31: `POST /api/v1/listas {"fecha_referencia":"2026-08-31","horizonte_dias":30,"top_k":25}` → `201`; ningún ítem tiene la clave `correo`; todos tienen `cedula` no nula.
    - `{"fecha_referencia":"2026-08-30"}` → `422 {"error":{"code":"domain_rule_violated","message":"La fecha de la lista debe ser hoy o posterior."}}`.
    - `horizonte_dias` 32 → `400 validation_error`; 31 → `201`.
    - Con la migración sintética más un socio sin cédula insertado en el test (membresía que vence dentro del horizonte), ese socio no aparece en la respuesta.
    - `/openapi.json`: `PrediccionDTO` sin `correo`; `POST /listas` documenta `201`, `400`, `403`, `409` y `422` con ejemplo.
  - Pruebas: integración (API).

- [x] **T8** · `frontend` · Tipos, cliente y datos simulados con cédula
  - Archivos: `Frontend/src/features/lista/api/lista-api.ts` (principal: `cedula` en lugar de `correo`), `Frontend/src/features/lista/types.ts`, `Frontend/src/features/lista/api/lista-api.handlers.ts` (cédulas **ficticias**, algunas con cero inicial; ningún correo; `422` para fecha pasada), `Frontend/src/features/lista/api/lista-api.test.ts`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura, §MSW; `API_CONTRACT.md`.
  - Aceptación:
    - `Prediccion` no tiene `correo`; `cedula: string | null` se mapea de `cedula`. Un `422` llega como error tipado con el mensaje del servidor.
    - Los handlers no devuelven ninguna clave `correo`.
  - Pruebas: frontend.

- [x] **T9** · `frontend` · Parámetros: fecha por defecto hoy y no anterior, horizonte ≤ 31, etiquetas amigables
  - Archivos: `Frontend/src/features/lista/hooks/useLista.ts` (principal: fecha inicial = hoy local `AAAA-MM-DD`; error si está vacía o es anterior a hoy; horizonte 1..31), `Frontend/src/features/lista/pages/ListaPage.tsx`, `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Lista priorizada; `.claude/rules/frontend.md` §Formularios; decisiones (a), (g).
  - Aceptación (Vitest + MSW, `vi.setSystemTime` en 2026-09-29 12:00 local):
    - Al abrir, el campo "Fecha de la lista" vale `2026-09-29` y tiene `min="2026-09-29"`. Fecha `2026-09-28` → "La fecha debe ser hoy o posterior." y **no** llama a la API. Vacía → "Indique la fecha de la lista." y no llama.
    - "Buscar socios que vencen en los próximos (días)": por defecto 30, `max=31`; 32 → "Entre 1 y 31 días." y no llama; 31 → `POST` con `horizonte_dias: 31`.
    - "Socios prioritarios a contactar": por defecto 25; 0 → mensaje local.
    - Un `422` del servidor se muestra con su mensaje en `ErrorAlert`.
    - El aviso de datos antiguos dice, sin tecnicismos, que la última carga tiene más de 30 días y que faltan los datos del mes.
    - La página no muestra las palabras "Top K", "Horizonte", "score" ni "Versión del modelo".
  - Pruebas: frontend.

- [x] **T10** · `frontend` · Tabla: prioritarios separados, cédula, sin score ni columna Top, factores sin puntajes
  - Archivos: `Frontend/src/features/lista/components/TablaLista.tsx` (principal), `Frontend/src/features/lista/components/TablaLista.test.tsx` (nuevo), `Frontend/src/features/lista/pages/ListaPage.test.tsx` (ajusta las aserciones de la tabla).
  - Docs: `docs/frontend/01-arquitectura.md` §`shared/ui` (reutiliza `DataTable` y `RiskBadge`, sin estilos nuevos); decisión (f).
  - Aceptación (lista de 5 ítems, `topK` 2):
    - Encabezado "Lista del 29 de septiembre de 2026". Resumen: "Socios por vencer en los próximos 30 días: 5" y "Socios prioritarios a contactar: 2" (= filas con `dentroTopK`). No aparece la versión del modelo.
    - Dos tablas: "Socios prioritarios a contactar" con las 2 filas `dentroTopK` y "Otros socios por vencer" con las 3 restantes, ambas en orden de prioridad. Con 0 fuera del top, la segunda no se muestra.
    - Columnas: Prioridad, Nombre, Cédula, Celular, Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales. No hay columnas "Correo", "Indicador de prioridad" ni "Top".
    - `"Plan: TRIMESTRAL (+0,09)"` → "Plan: TRIMESTRAL"; `"Ciclos previos: 1.234 (+0,12)"` → "Ciclos previos: 1.234"; un texto sin paréntesis final queda igual; `[]` → "Sin factores de riesgo destacados".
    - Cédula `null` → "—". El score no se renderiza en ningún lugar de la página.
  - Pruebas: frontend.

- [x] **T11** · `frontend` · Etiquetas amigables en el historial de listas y en Inicio
  - Archivos: `Frontend/src/features/lista/components/HistorialListas.tsx` (principal: opción "Lista del 31 de agosto de 2026 · 25 socios prioritarios", sin "Modelo v1" ni "K"; etiqueta "Listas anteriores"), `Frontend/src/features/lista/components/HistorialListas.test.tsx`, `Frontend/src/features/inicio/components/EstadoSistemaPanel.tsx` ("Modelo de predicción: activo desde <fecha>" en lugar de "Versión del modelo" y "Fecha de entrenamiento"; sin modelo → "El modelo de predicción aún no está disponible"), `Frontend/src/features/inicio/pages/InicioPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Inicio y Carga, §Lista priorizada.
  - Aceptación:
    - Con dos listas simuladas, las opciones son `Lista del <fecha larga es-EC> · <K> socios prioritarios`, de la más reciente a la más antigua.
    - Inicio `LISTO` con modelo → muestra "Modelo de predicción" y no "Versión del modelo" ni "v1". Los tres estados de Inicio siguen probados.
  - Pruebas: frontend.

- [x] **T12** · `infra-deploy` · Stack en Docker con una lista regenerada (marcada al cerrar; la verificación en Docker la confirma el orquestador)
  - Archivos: `Backend/README.md` (principal: §Primer arranque — la lista se genera con la fecha de hoy; la conciliación con el 31-08-2026 se hace con `scripts/verificar_lista.py`).
  - Docs: `docs/backend/10-docker.md` §Uso; `.claude/rules/deploy.md`.
  - Aceptación (manual; el developer pega solo estados, códigos y conteos, sin datos personales):
    1. `docker compose up -d --build` (sin `down -v`: no se recarga ni se reentrena) → `/sistema/estado` `LISTO`, modelo v1.
    2. `POST /api/v1/listas {"horizonte_dias":30,"top_k":25}` → `201` con `fecha_generacion` = hoy; `grep -c '"correo"'` = 0; ningún ítem con `cedula` nula; número de ítems y de `dentro_top_k`.
    3. Fecha de ayer → `422`; horizonte 32 → `400`.
    4. En http://localhost:8080 la lista nueva se ve con las dos tablas y sin score; el Excel tiene la columna Cédula y no Correo.
    5. `python scripts/verificar_lista.py ../plantillas` → salida `0`.
    6. Suites: Backend `pytest`, `ruff`, `format`, `mypy app`, `lint-imports`; Frontend `npm test`, `lint`, `build`; E2E Playwright.
  - Pruebas: verificación del stack por comandos y navegador.

- [x] **DOC-1** · (doc-agent) · Guía funcional, **no técnica**, `Documentation/06-como-funciona-la-lista.md` (nueva) + entrada en `Documentation/README.md`:
  - Qué es la fecha de la lista (desde ese día se buscan los socios cuya membresía vence en los próximos N días y se estima la probabilidad de que no renueven), qué son "los próximos N días" (máx. 31), qué son los socios prioritarios a contactar (los K primeros) y cómo se asignan los niveles alto/medio/bajo (se fijaron al preparar el modelo con el histórico; no dependen de K).
  - Casos: fecha futura con datos cargados solo hasta un mes antes (la lista sale incompleta: solo aparecen las membresías ya registradas; los planes mensuales comprados después no aparecen → cargar los datos cada mes; para eso existe el aviso de datos antiguos); socios sin cédula (no aparecen en la lista, pero siguen en la base y en el aprendizaje del modelo); fecha pasada (no se permite).
  - Sin términos como score, top K, horizonte, percentil o modelo v1; ningún dato real de socios.

- [x] **DOC-2** · (doc-agent) · Documentación técnica y seguimiento:
  - `docs/API_CONTRACT.md` (`cedula` sin `correo`, `422` por fecha pasada, horizonte 1..31, fecha por defecto = hoy de negocio), `docs/backend/12-modelo-y-listas.md` (fecha de negocio, exclusión sin cédula, decisiones (a)–(e), script), `docs/frontend/01-arquitectura.md` (parámetros, dos tablas, etiquetas), `03-casos-de-uso.md` §7 (información mostrada, parámetros) y §15 (columnas).
  - `05-cronograma-semana.md`: nota "Ajustes posteriores (R-005)" en el Día 3; añadir D4-FE-03 (botón de ayuda) y D6-BE-06 / D6-FE-04 (alerta de datos del mes) como pendientes.
  - `ACTION_PLAN.md`: decisiones en DECISIONES IMPORTANTES, (B) en PRÓXIMO y mover R-005 a TERMINADOS.

**Dependencias**
- Backend: T1 → T3. T2 → T3. T3 y T4 → T5 (T4 y T5 juntas). T4 → T6. T3, T5 y T6 → T7.
- Frontend: T8 puede empezar ya (con MSW) → T9 → T10. T11 es independiente.
- T12 requiere todo lo anterior. DOC-1 puede ir en paralelo; DOC-2 va al final, con la salida de T12.
- Externas: PostgreSQL con `app_db_test` (T2, T5, T7); los libros reales solo para T2 (script) y T12; Docker Desktop para T12.

**Riesgos**
1. **Zona horaria de "hoy".** Si backend y navegador no calculan el mismo día, por la noche el usuario recibe `422` con la fecha por defecto. Mitigación: fecha de negocio UTC−5 en el backend (T1, T3 con reloj a las 02:00Z) y fecha local en el navegador (T9).
2. **Exposición de la cédula.** Pasa a viajar en la API y en el Excel (dato personal). Mitigación: acceso por IP (CU-00), nunca en logs, en el nombre del archivo ni en la salida de los scripts; se guarda como texto sin fórmulas (T6). Revisión en el día 7.
3. **Regresiones en pruebas y conciliación.** Las pruebas actuales usan 2026-08-31 y horizonte 120, y la exclusión cambia la lista frente al notebook. Mitigación: reloj fijo sobrescrito en las pruebas de API (T7) y el script con su propio reloj y todos "con cédula" (T2, decisión (c)); salida `0` exigida en T12.

### R-004 — Día 3 del cronograma (Modelo v1, migración atómica al arrancar, lista y Excel; CU-03, CU-04, CU-05, CU-12) · **DONE** 2026-09-29

**Cierre:** security **diferida** a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)) · tests `pass` (Backend 1.082 pytest, ruff, format 198, mypy app 92 archivos, lint-imports 7 contratos; Frontend 323 Vitest, lint 0; E2E Playwright 1/1). Docker desde cero: `LISTO` en ~5 s, modelo v1, 1.564 ciclos, 2.748 membresías, 1.410 socios; lista 2026-08-31 → 57 ítems, top 25 igual al notebook (`verificar_lista.py` exit 0 con scikit-learn 1.8.0); Excel 3 hojas. Docs: `docs/backend/12-modelo-y-listas.md` (nuevo), [ADR-005](adr/ADR-005-fidelidad-al-notebook-del-modelo-v1.md) (nuevo), `docs/backend/09-esquema-base-de-datos.md`, `docs/backend/01-arquitectura.md`, `docs/backend/10-docker.md`, `docs/API_CONTRACT.md`, `docs/frontend/01-arquitectura.md`, `Backend/README.md`, `README.md`, `Documentation/README.md` (índice), `05-cronograma-semana.md` (avance y resumen del Día 3).

**Pendientes que pasan a otros días:** `gestion_estado` y `campania_asignada` siempre `null` → día 5 (CU-08) · S23 y revisión de seguridad de R-004 → día 7 · dos `POST /listas` simultáneos sin probar · `mypy` sobre `tests/` (tipado estricto en dobles) · el motivo de un fallo de migración vive solo en memoria.

**Objetivo:** al cerrar, `docker compose up` desde cero con los libros reales en `HISTORICO_DIR` migra el histórico y entrena el modelo v1 en una sola transacción y en segundo plano. Inicio muestra "Sistema listo". Desde http://localhost:8080, sin MSW, se genera la lista al 31-08-2026, que coincide con la lista de septiembre del notebook, y se descarga el Excel.

**Fuente:** [05 §3 Día 3](05-cronograma-semana.md) (D3-BD-01, D3-BE-01..06, D3-FE-01..03) · [03 §6 CU-03, §7 CU-04, §8 CU-05, §15 CU-12](03-casos-de-uso.md) · [ADR-002](adr/ADR-002-ml-en-infraestructura.md), [ADR-003](adr/ADR-003-reentrenamiento-y-versionado.md), [ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md) · `docs/backend/11-historico.md` · `Notebookes/MVP.ipynb` §7.2–7.4 (~l. 4085–4374), §9.5 (~l. 4791–4818), §13.3 (~l. 7918–7960), §13.8 (~l. 12037–12082, 12524–12558; top 25 esperado en ~l. 12462–12516), §14.1 (~l. 12757–12762). Localiza cada sección con `Grep` y un `offset`. No leas el notebook entero: tiene líneas enormes de imágenes.

**Notas de alcance del planner**
- No existe `products/P##-*.md`. Validé el alcance contra `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance y nada cae fuera. **Fuera de R-004:** CU-02 (reentrenamiento programado o manual, comando CLI y `OMITIDO`), el día 6; CU-01 real, el día 4; campañas y gestión (`gestion_estado` y `campania_asignada` salen `null`), el día 5; CU-00, el día 6; la revisión de seguridad, el día 7.
- **Sin login (RT-12):** las pruebas de aislamiento entre usuarios no aplican. Cada archivo nuevo de prueba de API o repositorio lo deja escrito en un comentario.
- **Proceso (05 §1):** TDD solo en **T6** (D3-BE-01): el test se escribe primero, en rojo, y después el código. El resto lleva pruebas de sus criterios. La revisión de seguridad queda diferida al día 7.
- **Réplica fiel del notebook.** Estas reglas se copian del notebook y se prueban:
  - `mes_vencimiento` = `"AAAA-MM"` del vencimiento. `inicio_aproximado` = `"True"`/`"False"` (texto). Las categóricas son `str`.
  - Historial previo = ciclos **no excluidos** del mismo socio con `fecha_actividad` estrictamente menor.
  - `monto_historico` = suma de los montos previos, con `None` como 0.
  - `dias_desde_ultima_membresia` = `None` si no hay previos.
  - `antiguedad_dias` = `max(0, (venc − 30) − primera_actividad)`.
  - `monto_actual` = monto; si falta, la mediana del plan y después la mediana general. Las medianas salen de los ciclos no excluidos y se guardan con el modelo.
  - `duracion_modelo` = duración; si falta, `DURACION_ESTANDAR` (`MENSUAL` 30, `TRIMESTRAL` 90, `SEMESTRAL` 180, `ANUAL` 365, `OTRO` 30).
  - Pipeline: `SimpleImputer(median)` + `StandardScaler` / `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")`, y `RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=20, class_weight="balanced", random_state=42)`, entrenado con **todos** los evaluables.
  - El orden de las filas de entrenamiento es el del notebook: (`identidad`, `fecha_actividad`, `fecha_vencimiento`) y, en caso de empate, el orden de lectura. El bootstrap del bosque depende de ese orden.
  - Cartera: vencimiento en `(fecha, fecha + horizonte]`, sin `DIARIO` y sin duración ≤ 21 o > 400 (con `None` pasa).
  - "Ya renovó" = otra membresía no `DIARIO` del mismo socio con `fecha_actividad` mayor.
  - En CU-04, la clasificación de los ciclos del historial usa **corte = fecha de generación**.
- **Decisiones del planner (reversibles; se avisan al usuario en el informe):**
  - (a) **Referencia de los factores (§13.3):** el notebook usa las medianas y modas de `X_train`. La app usa las de los ciclos **evaluables con vencimiento en 2025** (`PERIODO_REFERENCIA_FACTORES` = [2025-01-01, 2026-01-01), parametrizable en `domain/modelo/variables.py`), como el notebook. *Corregido al cerrar R-004:* el plan inicial decía "todo el conjunto de entrenamiento"; con esa referencia los factores no coincidían con el notebook. Con la actual, T19 da 25/25 factores iguales.
  - (b) **Cambios de contrato:**
    - `ListaPriorizadaDTO.fecha_generacion` pasa a `date` y se añade `creada_en: datetime`.
    - `PrediccionDTO` añade `monto_cobrado: Decimal | None` (lo pide el Excel).
    - Endpoint **nuevo** `GET /listas` (resumen para el historial de D3-FE-03).
    - Factores `[]` → la UI y el Excel muestran "Sin factores de riesgo destacados".
  - (c) Un fallo de la migración deja `PENDIENTE` en la base y un resultado en memoria; se reintenta al reiniciar el backend (ADR-004). `GET /sistema/estado` responde `FALTAN_DATOS_HISTORICOS` cuando faltan los libros o no se pueden leer (sin año, hoja sin encabezado), y también ante cualquier otro fallo; el detalle queda solo en el log técnico, sin datos personales. No se añade un estado nuevo.
  - (d) **Umbrales (CU-05):**
    - Se calculan con el percentil lineal (el método por defecto de numpy), en `Decimal`: `umbral_alto` = P80 y `umbral_medio` = P50 de los scores del v1 sobre los evaluables de los 3 meses de vencimiento más recientes.
    - ALTO si `score ≥ umbral_alto`; MEDIO si `score ≥ umbral_medio`; si no, BAJO. `porcentajes_umbral = {"ALTO":20,"MEDIO":30,"BAJO":50}`.
  - (e) Empates de score en la lista: vencimiento ascendente y después `membresia_id` ascendente. El notebook no fija un orden en los empates, así que se comparan como conjunto.
  - (f) Los datos del socio salen del registro más reciente en orden de lectura; `cargas.filas_duplicadas = 0` en la migración.
- **Cruce de capas:** `Decimal ↔ float` solo dentro del adaptador (T9). El puerto `PredictorModel` pasa a recibir `Decimal | int | str | None` y a devolver `score: Decimal`. El artefacto (joblib) se deserializa **solo** desde `modelos.artefacto` (ADR-003).
- **Excepción al límite de 4 archivos:** `__init__.py` vacíos, y la línea `"0003 (head)"` → `"0004 (head)"` de `test_migrations_robustness.py` en T1.

**Tareas**

- [x] **T1** · `db` · Prerrequisito de D3-BE-05 · `membresias.fecha_actividad` (migración `0004`)
  - Archivos: `Backend/alembic/versions/0004_membresias_fecha_actividad.py` (principal), `Backend/app/infrastructure/persistence/models/historial.py`, `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`, `Backend/tests/integration/persistence/test_migrations.py`.
  - Docs: `.claude/rules/database.md` §Migraciones; `Documentation/docs/backend/09-esquema-base-de-datos.md` §Historial.
  - Aceptación:
    - `revision="0004"`, `down_revision="0003"`. `upgrade`: añade `fecha_actividad DATE NULL`, la rellena con `fecha_inicio` donde exista y después `SET NOT NULL`. Falla si queda alguna fila sin valor; hoy ninguna base tiene filas. Añade el índice `ix_membresias_socio_id_fecha_actividad`. `downgrade` elimina el índice y la columna.
    - ORM: `fecha_actividad: Mapped[date]` con `nullable=False`. `alembic check` no encuentra diferencias. `alembic current` → `0004 (head)`.
    - Insertar una membresía sin `fecha_actividad` → `IntegrityError`. El ciclo `downgrade 0003` → `upgrade head` funciona.
  - Pruebas: unitaria (metadatos) + integración.

- [x] **T2** · `application` · D3-BD-01 (1/3) · Puertos de modelo, estado del sistema y listas
  - Archivos: `Backend/app/application/modelo/ports.py` (principal), `Backend/app/application/listas/ports.py`, `Backend/tests/unit/application/modelo/test_ports.py`, `Backend/tests/unit/application/listas/test_ports.py`.
  - Contenido:
    - `ModeloRepository`: `crear(NuevoModelo) -> int`, que desmarca el vigente anterior en la misma transacción, y `obtener_vigente() -> ModeloGuardado | None`.
    - `IntentoRepository.crear(NuevoIntento)`.
    - `EstadoSistemaRepository`: `obtener() -> EstadoSistema`, `fijar_migracion(EstadoMigracion)` y `fijar_proxima_fecha(date)`.
    - `BloqueoMigracion`: `intentar_adquirir() -> bool` y `liberar()`.
    - `ListaRepository`: `crear(NuevaLista, Sequence[NuevaPrediccion]) -> int`, `obtener(id) -> ListaDetalle | None`, `ultima()` y `listar() -> list[ListaResumen]`.
    - Los DTOs son `@dataclass(frozen=True, slots=True)` con `Decimal`, `date`/`datetime` aware y enums.
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas, §Patrón de un caso de uso; `docs/backend/11-historico.md` §Aplicación (patrón de puertos de R-003).
  - Aceptación:
    - Los puertos son `Protocol` `runtime_checkable` y un doble en memoria satisface `isinstance` y `mypy`.
    - Hay un docstring explícito: ningún repositorio hace `commit`/`rollback`; ninguno expone `delete`, porque son instantáneas inmutables.
    - `NuevoModelo.umbral_alto < umbral_medio` → `ValueError`. Un score fuera de `[0,1]` → `ValueError`. `NuevoIntento.fecha` sin zona horaria → `ValueError`.
    - `lint-imports` en verde: `application` no importa `infrastructure`, `sqlalchemy`, `sklearn` ni `pandas`.
  - Pruebas: unitarias.

- [x] **T3** · `infra` · D3-BD-01 (2/3) · Repositorios de modelo, intentos y `estado_sistema` con bloqueo consultivo
  - Archivos: `Backend/app/infrastructure/persistence/repositories/modelo.py` (principal: `SqlAlchemyModeloRepository`, `SqlAlchemyIntentoRepository`, `SqlAlchemyEstadoSistemaRepository` con `(session, clock)`, y `PgBloqueoMigracion(connection)`), `Backend/tests/integration/persistence/test_modelo_repositories.py`.
  - Docs: `.claude/rules/database.md` §Pruebas; `docs/backend/09-esquema-base-de-datos.md` §Modelo predictivo; ADR-003, ADR-004.
  - Aceptación (integración contra `app_db_test`):
    - `artefacto` se guarda como `BYTEA`: se leen los mismos bytes (1 MB de prueba). `metadata_tecnica` y `porcentajes_umbral` se guardan como JSONB. Umbrales y prevalencia se guardan como `Decimal` sin pérdida.
    - **Un solo vigente:** `crear` v1 y después v2 → v2 queda vigente y v1 `vigente=false` y se conserva. Un `INSERT` directo de un segundo vigente → `IntegrityError`. Sin modelos, `obtener_vigente()` → `None`.
    - **Bloqueo:** usa `pg_try_advisory_lock(<constante>)` a nivel de sesión sobre una conexión propia. Con dos conexiones: la 1.ª obtiene `True` y la 2.ª `False`; tras `liberar()`, la 2.ª obtiene `True`.
    - `fijar_migracion(EN_CURSO)` y `fijar_proxima_fecha(date(2027,2,28))` quedan visibles tras el `commit` del llamante. Ningún método hace `commit`, `rollback`, `begin` ni `close` (se verifica con un `grep` en el test).
  - Pruebas: integración.

- [x] **T4** · `infra` · D3-BD-01 (3/3) · Repositorio de listas y predicciones
  - Archivos: `Backend/app/infrastructure/persistence/repositories/listas.py` (principal: `SqlAlchemyListaRepository(session, clock)`), `Backend/tests/integration/persistence/test_listas_repository.py`.
  - Docs: `docs/backend/09-esquema-base-de-datos.md` §Retención; `.claude/rules/database.md` §Pruebas.
  - Aceptación:
    - `crear` inserta la lista y 60 predicciones en bloque (executemany) dentro de la transacción del llamante. `creada_en` sale del `Clock`.
    - Si una predicción es inválida (`score = 2`), falla y tras el `rollback` no queda ni la lista ni ninguna predicción.
    - `obtener(id)` devuelve la lista con: versión del modelo, `umbral_alto`/`umbral_medio`, y los ítems ordenados por `prioridad` con nombre, celular y correo del socio, plan, vencimiento, `monto_cobrado`, score `Decimal`, nivel, factores `list[str]` y `dentro_top_k`. Un id inexistente → `None`.
    - `ultima()` devuelve la de mayor `creada_en` y después el mayor `id`. `listar()` devuelve un resumen (id, fecha, `creada_en`, versión, horizonte, K, total de ítems) de la más reciente a la más antigua.
    - Generar una segunda lista no modifica la primera (RN-04.5).
  - Pruebas: integración.

- [x] **T5** · `infra` · Soporte de D3-BE-04/05 · Historial: `fecha_actividad` al insertar y lecturas para predecir
  - Archivos: `Backend/app/application/historial/ports.py` (principal: `NuevaMembresia.fecha_actividad: date`, `MembresiaRepository.listar_para_prediccion() -> list[MembresiaParaPrediccion]`, `CargaRepository.ultima_fecha_carga() -> datetime | None` y `hay_migracion_o_membresias() -> bool`), `Backend/app/infrastructure/persistence/repositories/historial.py`, `Backend/tests/integration/persistence/test_historial_repositories.py`, `Backend/tests/unit/application/historial/test_ports.py`.
  - Docs: `docs/backend/11-historico.md` §Aplicación, §Infraestructura.
  - Aceptación:
    - Se inserta con `fecha_actividad` y se lee igual.
    - `listar_para_prediccion` devuelve las membresías con `deleted_at IS NULL`, cada una con `membresia_id`, `socio_id`, plan, forma de pago, inicio, vencimiento, `fecha_actividad`, `monto_cobrado` (`Decimal`) e `inicio_aproximado`, en una sola consulta (sin N+1). Las borradas lógicamente se excluyen.
    - `hay_migracion_o_membresias()`: base vacía → `False`; con una carga `MIGRACION_HISTORICA` o con alguna membresía → `True`.
    - `ultima_fecha_carga`: sin cargas → `None`; con dos cargas → la mayor.
    - Las pruebas de R-003 siguen en verde.
  - Pruebas: integración + unitaria.

- [x] **T6** · `domain` · D3-BE-01 · **TDD** · Variables en T−30 (§7.2–7.4)
  - Archivos: `Backend/app/domain/modelo/variables.py` (principal), `Backend/tests/unit/domain/modelo/test_variables.py`, `Backend/app/domain/historico/ciclos.py` (solo amplía el tipo de entrada de `clasificar` a un `Protocol` con `plan`, `fecha_vencimiento` y `duracion_dias`, sin cambiar el comportamiento), `Backend/tests/unit/domain/historico/test_ciclos.py` (sin cambios de expectativa).
  - Contenido de `variables.py`:
    - `CicloModelo` (frozen): `clave_socio`, `ref`, `plan`, `forma_pago`, `fecha_actividad`, `fecha_vencimiento`, `duracion_dias`, `monto_cobrado: Decimal | None`, `inicio_aproximado`, `excluido: bool`, `no_renovo: bool | None`.
    - `MedianasMonto`, `calcular_medianas(ciclos)`, `construir_variables(ciclo, historial, medianas) -> dict[str, Decimal | int | str | None]`.
    - `VARIABLES_NUMERICAS`, `VARIABLES_CATEGORICAS`, `DURACION_ESTANDAR`.
    - `ordenar_para_entrenamiento(ciclos)`.
  - Docs: notebook §7.2 (~l. 4085–4110), §7.3 (~l. 4224–4234), §7.4 (~l. 4367–4374), §6.1 (~l. 3739, `mes_vencimiento`); `DEVELOPMENT_GUIDELINES.md` §Excepciones.
  - Aceptación (tests primero):
    - Socio con 2 previos no excluidos (actividad 2025-01-10, monto 30; 2025-02-10, monto `None`) y ciclo actual con actividad 2025-03-10 y vencimiento 2025-04-09 → `ciclos_previos=2`, `monto_historico=Decimal("30")`, `dias_desde_ultima_membresia=28`, `antiguedad_dias=(2025-03-10 − 2025-01-10).days = 59`.
    - Socio nuevo → `ciclos_previos=0`, `monto_historico=0`, `dias_desde_ultima_membresia=None`, `antiguedad_dias = max(0, venc−30 − actividad)`.
    - Un previo con la **misma** `fecha_actividad` no cuenta (menor estricto). Un previo **excluido** no cuenta. El propio ciclo nunca cuenta.
    - Medianas: los montos del plan `[10, 20, 30, 40]` → `Decimal("25")`. Monto `None` del plan `MENSUAL` → mediana del plan. Un plan sin montos → mediana general. Todo en `Decimal`.
    - `duracion_modelo`: `None` con `TRIMESTRAL` → 90; con `OTRO` → 30.
    - `mes_vencimiento`: 2026-09-05 → `"2026-09"`. `inicio_aproximado` → `"True"`/`"False"`. `plan` y `forma_pago` → `.value`.
    - `ordenar_para_entrenamiento`: ordena por (`clave_socio`, `fecha_actividad`, `fecha_vencimiento`) y es estable (dos iguales conservan el orden de entrada).
    - Ningún valor devuelto es `float`. Solo librería estándar (`grep -r "pandas\|numpy\|sklearn" app/domain` = 0).
  - Pruebas: unitarias.

- [x] **T7** · `domain` · D3-BE-05 (1/3) · Cartera en el horizonte, renovados, orden y top K (§13.8)
  - Archivos: `Backend/app/domain/modelo/cartera.py` (principal: `seleccionar_cartera(ciclos, fecha, horizonte)`, `ya_renovo(ciclo, actividades_del_socio)`, `priorizar(puntuados, top_k) -> list[FilaPriorizada]` con `prioridad`, `dentro_top_k` y `dias_para_vencer`), `Backend/tests/unit/domain/modelo/test_cartera.py`.
  - Docs: notebook §13.8 (~l. 12037–12056, 12533–12552); `03-casos-de-uso.md` §7 (flujo, RN-04.x).
  - Aceptación, con fecha 2026-08-31 y horizonte 30:
    - Cartera: vence el 2026-08-31 → fuera; el 2026-09-01 → dentro; el 2026-09-30 → dentro; el 2026-10-01 → fuera. `DIARIO` → fuera. Duración 21 → fuera; 401 → fuera; `None` → dentro.
    - `ya_renovo`: otra membresía no `DIARIO` del mismo socio con actividad posterior → `True`. Si es `DIARIO` o de otro socio → `False`. La propia membresía nunca cuenta.
    - `priorizar`: orden por score descendente. En empate, por vencimiento ascendente y después por `membresia_id` ascendente. Queda **una fila por socio** (la de mayor score). `prioridad` va de 1 a n. `dentro_top_k = prioridad ≤ K`. `dias_para_vencer = (vencimiento − fecha).days`.
  - Pruebas: unitarias.

- [x] **T8** · `domain` · D3-BE-03 · Umbrales por percentiles, nivel de riesgo y próxima fecha
  - Archivos: `Backend/app/domain/modelo/umbrales.py` (principal: `meses_recientes_con_resultado(ciclos, n=3)`, `calcular_umbrales(scores, porcentajes=(20,30,50)) -> Umbrales`, `nivel_de(score, umbrales) -> NivelRiesgo`), `Backend/tests/unit/domain/modelo/test_umbrales.py`, `Backend/app/domain/common/fechas.py` (`sumar_meses(fecha, meses)`), `Backend/tests/unit/domain/common/test_fechas.py`.
  - Docs: `03-casos-de-uso.md` §8 CU-05; decisión (d) de estas notas.
  - Aceptación:
    - Scores `0.1 … 1.0` (10 valores, `Decimal`) → `umbral_alto = 0.82` y `umbral_medio = 0.55`. Niveles: 2 ALTO, 3 MEDIO, 5 BAJO. Un score exactamente igual al umbral queda en el nivel superior.
    - Con 1 000 scores distintos → 200 / 300 / 500 (±1).
    - `meses_recientes_con_resultado`: con evaluables de 2026-04 a 2026-08 devuelve los ciclos de 2026-06, 07 y 08. Excluye pendientes y excluidos. Lista vacía → `ValueError`.
    - Porcentajes que no suman 100 → `ValueError`.
    - `sumar_meses(2026-08-31, 6)` → 2027-02-28; `(2026-09-29, 6)` → 2027-03-29; `(2027-08-31, 6)` → 2028-02-29.
  - Pruebas: unitarias.

- [x] **T9** · `infra` · D3-BE-02 · Adaptador scikit-learn de `PredictorModel` (pipeline §9.5, factores §13.3, serialización)
  - Archivos: `Backend/app/infrastructure/ml/random_forest.py` (principal: `RandomForestPredictor`), `Backend/app/domain/common/predictor.py` (puerto: `FeatureRow = Mapping[str, Decimal | int | str | None]`, `Prediction.score: Decimal`, `train(features, labels, numericas, categoricas)` si hace falta), `Backend/tests/unit/domain/common/test_predictor_port.py`, `Backend/tests/unit/infrastructure/ml/test_random_forest.py`.
  - Docs: ADR-002; `DEVELOPMENT_GUIDELINES.md` §Excepciones (`Decimal ↔ float` solo aquí); notebook §9.5 (~l. 4791–4818), §13.3 (~l. 7918–7960).
  - Aceptación (datos sintéticos deterministas, unas 300 filas generadas con semilla):
    - El pipeline y los hiperparámetros son exactamente los del notebook (se comprueba con `get_params()`). `metadata_tecnica` incluye los parámetros y las versiones de Python, scikit-learn, numpy y pandas.
    - **Hecho cuando (05):** entrenar → `artefacto: bytes` → deserializar → `predict` da **los mismos scores** que el modelo en memoria (igualdad exacta de `Decimal`).
    - Dos entrenamientos con los mismos datos y el mismo orden → mismos scores.
    - Una categoría no vista (`mes_vencimiento="2027-01"`) no falla. `None` en los numéricos se imputa.
    - El artefacto incluye la referencia de los factores: medianas y modas de los evaluables con vencimiento en `PERIODO_REFERENCIA_FACTORES` (2025), según la decisión (a).
    - Factores:
      - Son hasta 3, con aporte > 0,005 y de mayor a menor. Sin factores → `()`.
      - Excluyen `mes_vencimiento`.
      - Formato del notebook: `"Plan: TRIMESTRAL (+0,09)"`. Los numéricos van con separador de miles `.` y sin decimales. `None` → `"sin dato"`. `inicio_aproximado` → `"sí"`/`"no"`.
    - `score` es `Decimal` en `[0,1]`, cuantizado a 8 decimales (`NUMERIC(10,8)`).
    - `mypy app` y `lint-imports` en verde; sklearn solo se usa en `infrastructure`.
  - Pruebas: unitarias (el adaptador con sklearn real).

- [x] **T10** · `application` · D3-BE-02/03 · Servicio `EntrenarModeloInicial`: ciclos → variables → entrenamiento → umbrales
  - Archivos: `Backend/app/application/modelo/entrenar_modelo.py` (principal: `EntrenarModeloInicial(predictor).ejecutar(registros, ciclos_etiquetados, fecha_corte) -> ModeloEntrenado` con artefacto, `metadata_tecnica`, `ciclos_entrenamiento`, `periodo_desde`/`hasta`, prevalencia `Decimal`, umbrales, porcentajes y medianas), `Backend/app/application/modelo/mapeo.py` (`RegistroHistorico` + `CicloEtiquetado` → `CicloModelo`), `Backend/tests/unit/application/modelo/test_entrenar_modelo.py`.
  - Docs: `03-casos-de-uso.md` §6 paso 12, §8; ADR-002 (puerto con doble); notebook §8.1 (~l. 4426).
  - Aceptación (con un doble de `PredictorModel` que registra lo que recibe):
    - Solo se entrenan los `EVALUABLE`, con etiqueta `int(no_renovo)`, en el orden de `ordenar_para_entrenamiento`.
    - El historial de variables usa los ciclos no excluidos (evaluables y pendientes).
    - Con 6 evaluables (4 no renovó) → `ciclos_entrenamiento=6`, `prevalencia=Decimal(4)/6`, periodo = vencimiento mínimo / máximo.
    - Los umbrales se calculan con los scores del doble sobre los evaluables de los 3 meses recientes (T8).
    - Las medianas se guardan en `metadata_tecnica["medianas_monto"]` como texto `Decimal`.
    - 0 evaluables, o una sola clase → `DomainError` con un mensaje sin datos personales.
    - Si el doble lanza una excepción, se propaga (la reversión la hace T11).
  - Pruebas: unitarias.

- [x] **T11** · `application` · D3-BE-04 (1/3) · Caso de uso `MigrarHistorico` (CU-03 completo, atómico)
  - Archivos: `Backend/app/application/sistema/migrar_historico.py` (principal), `Backend/app/application/sistema/ports.py` (`UnidadDeTrabajo`: context manager con los repositorios de historial, modelo, intentos y estado, más `commit()`; `FabricaUnidadDeTrabajo`; `LocalizadorLibros.rutas() -> list[Path]`; `ResultadoMigracion` en memoria), `Backend/tests/unit/application/sistema/test_migrar_historico.py`.
  - Docs: `03-casos-de-uso.md` §6 (flujo 1–15, alternativos, RN-03.x); ADR-004; `docs/backend/11-historico.md` §Flujo.
  - Flujo:
    1. Adquirir el bloqueo. Si no se consigue, no hace nada.
    2. Si `hay_migracion_o_membresias()` o el estado es `COMPLETADA`, no hace nada. Un `EN_CURSO` huérfano, con el bloqueo adquirido y la base vacía, se trata como `PENDIENTE`.
    3. Transacción corta que marca `EN_CURSO` y hace `commit`.
    4. `ProcesarHistorico`, después `EntrenarModeloInicial`.
    5. En **una** unidad de trabajo guarda:
       - la carga `MIGRACION_HISTORICA` con sus conteos;
       - los socios (uno por identidad, decisión (f));
       - las membresías, con origen `HISTORICO`, `referencia_origen`, originales y `fecha_actividad`;
       - el modelo v1 vigente;
       - el intento `INICIAL`/`ENTRENADO` con `modelo_id`;
       - `proxima_fecha = sumar_meses(hoy, 6)`;
       - el estado `COMPLETADA`.

       Después hace `commit`.
    6. Si algo falla: no hay `commit`, una transacción corta vuelve a `PENDIENTE`, y queda en memoria `FALLIDA` o `FALTAN_DATOS`.
    7. Libera el bloqueo en `finally`.
  - Aceptación (dobles en memoria):
    - Éxito → 1 carga, socios = identidades distintas, membresías = `con_identidad`, 1 modelo `version=1` vigente, 1 intento `INICIAL`. Con el reloj en 2026-09-29, la próxima fecha es 2027-03-29 y el estado `COMPLETADA`.
    - El doble del predictor falla → no se ejecuta ningún `commit` sobre la unidad grande, el estado final es `PENDIENTE` y el resultado es `FALLIDA`.
    - Sin rutas (carpeta vacía o inexistente) → no entrena, el estado sigue `PENDIENTE` y el resultado es `FALTAN_DATOS`.
    - `LibroSinAnioError`/`HojaSinEncabezadoError` → `FALTAN_DATOS` y el log lleva el libro y la hoja.
    - El bloqueo no se obtiene → no se llama al lector.
    - Base ya migrada → no se llama al lector.
    - Los logs solo llevan conteos, libro y hoja (test con `caplog`: ningún nombre ni cédula del doble).
  - Pruebas: unitarias.

- [x] **T12** · `infra` · D3-BE-04 (2/3) · Unidad de trabajo SQLAlchemy y migración real con libros sintéticos
  - Archivos: `Backend/app/infrastructure/persistence/unit_of_work.py` (principal: `SqlAlchemyUnidadDeTrabajo`; `session.begin()` único y `rollback` automático ante una excepción), `Backend/app/infrastructure/historico/localizador_libros.py` (`*.xlsx` de la carpeta, ignorando `~$*`, en orden alfabético), `Backend/tests/integration/sistema/test_migrar_historico_pg.py`.
  - Docs: `.claude/rules/database.md` §Transacciones, §Pruebas; ADR-004; `docs/backend/11-historico.md` §Datos sintéticos.
  - Aceptación (PostgreSQL `app_db_test` + libros de `tests/fixtures/historico/` + `RandomForestPredictor` real):
    - **Hecho cuando (05):** arranque en limpio con datos sintéticos → `migracion_historica = COMPLETADA`. Las membresías coinciden con `esperado.py` y todas tienen `fecha_actividad`. Hay 1 modelo v1 vigente con artefacto no vacío, 1 intento `INICIAL` y `proxima_fecha_reentrenamiento` fijada.
    - **Fallo forzado del entrenamiento** (predictor que lanza) → `socios`, `membresias`, `cargas`, `modelos` e `intentos_reentrenamiento` quedan con 0 filas, y el estado vuelve a `PENDIENTE`.
    - **Dos migraciones simultáneas** (2 hilos con fábricas de conexión propias) → solo una migra: 1 carga y 1 modelo.
    - Una segunda ejecución con la base migrada no cambia ningún conteo.
    - La prueba deja la base limpia; la fixture solo trunca en una base `*_test`.
  - Pruebas: integración.

- [x] **T13** · `api` · D3-BE-04 (3/3) · Lanzamiento en segundo plano al arrancar
  - Archivos: `Backend/app/main.py` (principal: el `lifespan` lanza un `threading.Thread(daemon=True)` si `settings.MIGRAR_HISTORICO_AL_ARRANCAR`), `Backend/app/core/config.py` (`HISTORICO_PATH: Path = /data/historico` y `MIGRAR_HISTORICO_AL_ARRANCAR: bool = True`), `Backend/app/api/dependencies.py` (composition root: engine, `SystemClock`, `LectorLibrosExcel`, `RandomForestPredictor`, repositorios y el `ResultadoMigracion` compartido), `Backend/tests/integration/api/test_arranque_migracion.py`.
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Configuración, §Capas; `docs/backend/10-docker.md` §Variables; ADR-004.
  - Aceptación:
    - Mientras la migración está bloqueada (un predictor doble espera un `Event`): `GET /api/v1/health` → `200` en menos de 2 s y `GET /api/v1/sistema/estado` → `INICIALIZANDO`. Al liberarla → `LISTO`.
    - Con `MIGRAR_HISTORICO_AL_ARRANCAR=false` no se lanza nada; es la opción por defecto en las demás pruebas de API.
    - Una excepción en el hilo se registra en el log sin datos personales y no tumba el proceso.
    - El backend sigue sin ejecutar Alembic (`grep -r "alembic\|create_all" app` = 0).
  - Pruebas: integración.

- [x] **T14** · `api` · D3-BE-04 · `GET /api/v1/sistema/estado` real
  - Archivos: `Backend/app/application/sistema/consultar_estado.py` (principal), `Backend/app/api/routers/sistema.py`, `Backend/tests/unit/application/sistema/test_consultar_estado.py`, `Backend/tests/integration/api/test_sistema_api.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md` §Operaciones de negocio; `03-casos-de-uso.md` §6 (alternativos); decisión (c).
  - Aceptación:
    - `EN_CURSO`, o un hilo en curso → `200 {"estado":"INICIALIZANDO", "migracion_historica":"EN_CURSO", ...}`.
    - `PENDIENTE` con resultado `FALTAN_DATOS`/`FALLIDA` → `FALTAN_DATOS_HISTORICOS`. `PENDIENTE` sin resultado todavía → `INICIALIZANDO`.
    - `COMPLETADA` → `LISTO`, con `modelo_vigente {"version":"v1","fecha_entrenamiento":…,"ciclos_entrenamiento":n}`, `ultima_carga_en` y `proxima_fecha_reentrenamiento`.
    - Deja de responder `501`. El OpenAPI mantiene ejemplos de los tres estados.
  - Pruebas: unitaria + integración (API).

- [x] **T15** · `application` · D3-BE-05 (2/3) · Casos de uso `GenerarLista` y consultas de listas
  - Archivos: `Backend/app/application/listas/generar_lista.py` (principal), `Backend/app/application/listas/consultar_listas.py` (`obtener`, `ultima`, `listar` y advertencia), `Backend/tests/unit/application/listas/test_generar_lista.py`, `Backend/tests/unit/application/listas/test_consultar_listas.py`.
  - Flujo de `GenerarLista`:
    1. Si el estado ≠ `COMPLETADA` o no hay modelo vigente → `SistemaNoListoError` (→ 409).
    2. La fecha por defecto es `clock.today()`.
    3. Lee las membresías (T5) y las convierte en `CicloModelo`. `excluido` sale de `clasificar` con **corte = fecha de generación**.
    4. Calcula la cartera, quita a los que ya renovaron y construye las variables con las medianas del modelo.
    5. `predict(artefacto)`, `priorizar` y el nivel con los umbrales del modelo.
    6. Guarda la lista y las predicciones en **una** unidad de trabajo.
  - Docs: `03-casos-de-uso.md` §7 (flujo, RN-04.1–04.5, criterios), §8 RN-05.1/05.2; decisiones (a), (b), (e).
  - Aceptación (dobles):
    - Ningún socio que ya renovó ni ningún `DIARIO` aparece en la lista. Hay una fila por socio, ordenada por score de mayor a menor. `dentro_top_k` es verdadero en exactamente `min(K, n)` filas.
    - La lista guarda el `modelo_id` y los umbrales del modelo con que se generó. Si después se crea otro modelo vigente, `obtener(id)` devuelve los niveles y la versión originales (RT-07).
    - Advertencia: la última carga es del 2026-07-01 y la fecha de generación el 2026-08-31 (61 días) → `advertencia_datos_antiguos = true`. Con 30 días exactos → `false`. En la consulta se evalúa con la última carga cuya `fecha_carga` ≤ `creada_en`.
    - Sin modelo vigente → `SistemaNoListoError`. Una cartera vacía → lista con 0 ítems (válida).
  - Pruebas: unitarias.

- [x] **T16** · `api` · D3-BE-05 (3/3) · Endpoints `POST /listas`, `GET /listas`, `GET /listas/ultima`, `GET /listas/{id}`
  - Archivos: `Backend/app/api/routers/listas.py` (principal), `Backend/app/application/listas/dtos.py` (decisión (b): `fecha_generacion: date`, `creada_en`, `monto_cobrado`, `ListaResumenDTO`), `Backend/app/api/dependencies.py`, `Backend/tests/integration/api/test_listas_api.py`.
  - Docs: `Documentation/docs/API_CONTRACT.md` §Operaciones de negocio, §Convenciones de los DTOs; `.claude/rules/backend.md`.
  - Aceptación (API con PostgreSQL de pruebas, migración sintética de T12 como fixture):
    - `POST /api/v1/listas {"fecha_referencia":"2026-08-31","horizonte_dias":30,"top_k":25}` → `201`. Los ítems vienen ordenados por `prioridad`. `score`, `umbral_alto` y `umbral_medio` son **strings** decimales; `modelo_version` = `"v1"`.
    - Con `horizonte_dias=0` o `top_k=0` → `400 validation_error`. Con la migración no completada → `409 conflict` con el mensaje "El sistema se esta inicializando; intente de nuevo en unos minutos."
    - `GET /listas` → `200 [ListaResumenDTO]`, de la más reciente a la más antigua. `GET /listas/ultima` sin listas → `404`. `GET /listas/999999` → `404`. `GET /listas/abc` → `400`.
    - El OpenAPI incluye ejemplos de éxito y de error de cada operación, y `GET /listas` está documentado.
  - Pruebas: integración (API).

- [x] **T17** · `infra` · D3-BE-06 (1/2) · Generador del Excel en memoria (CU-12)
  - Archivos: `Backend/app/infrastructure/exportacion/excel_lista.py` (principal: `ExcelListaOpenpyxl.generar(lista: ListaDetalle) -> bytes`), `Backend/app/application/listas/ports.py` (añade `ExportadorLista`), `Backend/tests/unit/infrastructure/exportacion/test_excel_lista.py`.
  - Docs: `03-casos-de-uso.md` §15 (contenido, columnas, RN-12.1–12.3); notebook §14.1 (~l. 12757–12762).
  - Aceptación (leyendo el archivo de vuelta con openpyxl):
    - El archivo tiene 3 hojas: `top_{K}` (p. ej. `top_25`), `cartera_completa` y `resumen`. `top_{K}` tiene como máximo K filas de datos.
    - Columnas: prioridad, nombre, celular, correo, plan, fecha de vencimiento, días para vencer, monto cobrado, score, nivel de riesgo, factores principales, estado de la gestión, campaña asignada.
    - `resumen`: fecha de generación, horizonte, K, versión del modelo, umbrales y conteos (total, top K, por nivel).
    - **Hecho cuando (05):** un nombre `=HYPERLINK("x")` o textos que empiezan por `+`, `-` o `@` se guardan como texto con el prefijo `'`. El XML de las hojas no contiene ningún elemento `<f>`.
    - Se genera en memoria (`BytesIO`); no se escribe ningún archivo (se comprueba el directorio temporal). Las propiedades del libro (`created`/`modified`) salen de `creada_en`, así que la misma lista produce bytes idénticos.
    - Factores `[]` → "Sin factores de riesgo destacados".
  - Pruebas: unitarias.

- [x] **T18** · `api` · D3-BE-06 (2/2) · `GET /api/v1/listas/{id}/excel`
  - Archivos: `Backend/app/api/routers/listas.py` (principal), `Backend/app/application/listas/consultar_listas.py` (`descargar_excel`), `Backend/tests/integration/api/test_listas_excel_api.py`.
  - Docs: `API_CONTRACT.md`; `03-casos-de-uso.md` §15.
  - Aceptación:
    - `200` con `Content-Type` `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` y `Content-Disposition: attachment; filename="lista_<id>_<AAAA-MM-DD>.xlsx"`, sin datos personales en el nombre del archivo.
    - Id inexistente → `404`. Id no numérico → `400`.
    - Descargar dos veces, con otro modelo vigente creado entre medias → el contenido es el mismo y **no** se ejecuta el modelo (el doble del predictor no se llama; RN-12.3).
  - Pruebas: integración (API).

- [x] **T19** · `infra-deploy` (script local) · Criterio de D3-BE-05 · Verificación de la lista de septiembre con los libros reales
  - Archivos: `Backend/scripts/verificar_lista.py` (principal: `python scripts/verificar_lista.py <carpeta>`. Compone, **en memoria y sin BD**, `LectorLibrosExcel` + `ProcesarHistorico` + `EntrenarModeloInicial` + las funciones de cartera y variables con fecha 2026-08-31, horizonte 30 y K 25. Compara con las referencias codificadas del notebook y sale con 0 o 1), `Backend/tests/unit/scripts/test_verificar_lista.py` (solo con los libros sintéticos y referencias inyectadas).
  - Docs: notebook §13.8 (~l. 12026–12029 y 12462–12516); `docs/backend/11-historico.md` §Conciliación.
  - Aceptación:
    - Las referencias vienen del notebook:
      - cartera 59; ya renovaron 2; a priorizar 57; socios 57; 1.564 ciclos de entrenamiento;
      - el top 25 como códigos `MTB-` + los 8 primeros caracteres hexadecimales en mayúsculas de `sha256(identidad)`, con su probabilidad a 3 decimales (p. ej. 1 `MTB-7C5F302E` 0,702 … 25 `MTB-043DE3C6` 0,605).
    - Compara: los conteos; la probabilidad de cada código a 3 decimales; el orden, con los empates comparados como conjunto; y los factores, como porcentaje de coincidencia, informativo por la decisión (a).
    - La salida solo imprime códigos `MTB-`, conteos y cifras. Nunca imprime nombres, cédulas, celulares ni correos (test con sintéticos).
    - El developer lo ejecuta con la carpeta real y **pega la salida** en el handoff. Si difiere, localiza la causa (orden de las filas, montos negativos, versión de scikit-learn) y la anota. Si la diferencia es de un caso, se documenta (03 §6).
  - Pruebas: unitaria del script + ejecución manual local.

- [x] **T20** · `frontend` · D3-FE-01 (1/3) · Cliente de la API de listas y handlers MSW
  - Archivos: `Frontend/src/features/lista/api/lista-api.ts` (principal: `generarLista`, `obtenerLista`, `obtenerUltima`, `listarListas`, `descargarExcel(id) -> Blob`), `Frontend/src/features/lista/types.ts`, `Frontend/src/features/lista/api/lista-api.handlers.ts`, `Frontend/src/features/lista/api/lista-api.test.ts`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura, §MSW; `API_CONTRACT.md` (decisión (b)).
  - Aceptación:
    - `snake_case` → camelCase solo en `api/`. `score` y los umbrales se mantienen como `string`; nunca se convierten a número para cálculos.
    - `409` → error tipado con el mensaje del servidor.
    - `descargarExcel` hace `GET /api/v1/listas/{id}/excel` y devuelve un `Blob`.
    - Los handlers devuelven dos listas simuladas con datos ficticios (una con `advertenciaDatosAntiguos: true`), más `409` y `404`. Los tests de `api` están en verde.
  - Pruebas: frontend.

- [x] **T21** · `frontend` · D3-FE-01 (2/3) · Página Lista: parámetros, generar, tabla y advertencia
  - Archivos: `Frontend/src/features/lista/pages/ListaPage.tsx` (principal), `Frontend/src/features/lista/hooks/useLista.ts`, `Frontend/src/features/lista/components/TablaLista.tsx`, `Frontend/src/features/lista/pages/ListaPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Estructura, §`shared/ui`; `03-casos-de-uso.md` §7 (parámetros, información mostrada, RN-05.3).
  - Aceptación (Vitest + MSW):
    - Campos con etiqueta accesible: fecha (vacía = hoy en el servidor), horizonte (por defecto 30, entre 1 y 365) y K (por defecto 25, ≥ 1). Un valor inválido muestra un mensaje local y no llama a la API.
    - "Generar lista" → `POST`. El botón se deshabilita mientras envía (sin doble envío).
    - La tabla muestra prioridad, nombre, celular, correo, plan, vencimiento (`es-EC`), días, score (como "indicador de prioridad"), nivel, factores (`[]` → "Sin factores de riesgo destacados") y top K (las filas dentro del top K se marcan con texto, no solo con color).
    - `advertenciaDatosAntiguos` → un aviso visible con `role="alert"`.
    - `409` → "El sistema se esta inicializando…".
    - Al entrar se carga `GET /listas/ultima`; con `404` se muestra un estado vacío.
    - `pages` no importa `api/` ni `core/http`.
  - Pruebas: frontend.

- [x] **T22** · `frontend` · D3-FE-02 · Botón de descarga del Excel
  - Archivos: `Frontend/src/features/lista/components/DescargarExcelButton.tsx` (principal), `Frontend/src/features/lista/hooks/useDescargarExcel.ts`, `Frontend/src/features/lista/components/DescargarExcelButton.test.tsx`, `Frontend/src/features/lista/pages/ListaPage.tsx` (lo monta).
  - Docs: `docs/frontend/01-arquitectura.md`; `03-casos-de-uso.md` §15.
  - Aceptación:
    - **Hecho cuando (05):** el clic llama a `GET /api/v1/listas/{id}/excel` con el id de la lista mostrada (se comprueba con un handler MSW que registra la petición).
    - Crea la descarga con `URL.createObjectURL` y la libera después. Mientras descarga, el botón queda deshabilitado.
    - Un error muestra `ErrorAlert`. Sin lista, el botón no aparece.
  - Pruebas: frontend.

- [x] **T23** · `frontend` · D3-FE-03 · Historial de listas generadas
  - Archivos: `Frontend/src/features/lista/components/HistorialListas.tsx` (principal: un selector), `Frontend/src/features/lista/hooks/useHistorialListas.ts`, `Frontend/src/features/lista/components/HistorialListas.test.tsx`, `Frontend/src/features/lista/pages/ListaPage.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md`; `03-casos-de-uso.md` §7 RN-04.5.
  - Aceptación:
    - **Hecho cuando (05):** con dos listas simuladas, el selector muestra 2 opciones (fecha, versión y K), de la más reciente a la más antigua.
    - Elegir la anterior → `GET /listas/{id}` y la tabla y el botón Excel pasan a esa lista.
    - Tras generar una lista nueva, el historial se refresca y la selecciona.
  - Pruebas: frontend.

- [x] **T24** · `frontend` · Soporte del hito · Inicio consulta de nuevo mientras inicializa
  - Archivos: `Frontend/src/features/inicio/hooks/useEstadoSistema.ts` (principal), `Frontend/src/features/inicio/pages/InicioPage.test.tsx`.
  - Docs: `docs/frontend/01-arquitectura.md` §Feature `inicio`.
  - Aceptación:
    - Con `INICIALIZANDO`, vuelve a pedir el estado cada 5 s (con temporizadores falsos) hasta `LISTO` o `FALTAN_DATOS_HISTORICOS`, y entonces se detiene.
    - Deja de consultar al desmontar (`AbortController` y `clearTimeout`).
    - Las pruebas de R-003 siguen en verde.
  - Pruebas: frontend.

- [x] **T25** · `infra-deploy` · Hito del día · Verificación de punta a punta en Docker con los libros reales
  - Archivos: `compose.yaml` (principal: el `backend` recibe `HISTORICO_PATH=/data/historico`; el montaje de solo lectura ya existe), `.env.example` (comentario sobre `HISTORICO_DIR`, sin valores reales), `Backend/README.md` (sección "Primer arranque").
  - Docs: `docs/backend/10-docker.md` §Servicios, §Uso; `.claude/rules/deploy.md`.
  - Aceptación (manual; el developer pega la salida, solo estados y conteos):
    1. `docker compose down -v && docker compose up -d --build` → `migrate` termina con 0; `curl /api/v1/health` → `200` durante la migración; `curl /api/v1/sistema/estado` pasa de `INICIALIZANDO` a `LISTO` con `"version":"v1"`.
    2. En `psql`: 1 modelo vigente, 1 intento `INICIAL`, 2.748 membresías y 1.410 socios.
    3. En el navegador, en http://localhost:8080 (build de producción, sin MSW): Inicio muestra "Sistema listo" → Lista con fecha 2026-08-31, horizonte 30 y K 25 → 57 filas → la descarga del Excel abre con `top_25`, `cartera_completa` y `resumen`.
    4. `docker compose restart backend` → sin nueva migración (los conteos no cambian).
    5. `docker compose logs backend` no contiene nombres ni cédulas (revisión con `grep` de 3 nombres conocidos, sin pegarlos en el handoff).
  - Pruebas: verificación del stack por comandos y navegador.

- [x] **DOC-1** · (doc-agent) · Documentar R-004:
  - `docs/backend/09-esquema-base-de-datos.md`: `0004` y `fecha_actividad`.
  - Nuevo `docs/backend/12-modelo-y-listas.md`: variables, adaptador, umbrales, migración al arrancar con bloqueo y estados, CU-04, Excel, conciliación de T19 y las decisiones (a)–(f).
  - `docs/API_CONTRACT.md`: `GET /listas`, cambios de DTO y endpoints que ya no responden `501`.
  - `docs/backend/10-docker.md` (`HISTORICO_PATH`), `docs/frontend/01-arquitectura.md` (Lista, historial, Excel, consulta periódica en Inicio), `Backend/README.md` y `README.md` (índice).
  - `05-cronograma-semana.md`: estado de las tareas del Día 3 y "Avance y resumen del Día 3".
  - Mover R-004 a TERMINADOS.

**Dependencias**
- Backend:
  - T1 va primero.
  - T2 → T3, T4. T5 requiere T1.
  - T6 (TDD) → T7, T8. T9 requiere T6.
  - T10 requiere T6, T8 y T9. T11 requiere T2, T5 y T10. T12 requiere T3, T5, T9 y T11. T13 requiere T12. T14 requiere T3 y T13.
  - T15 requiere T4, T5, T7, T8 y T9. T16 requiere T12 (fixture) y T15. T17 requiere T4. T18 requiere T16 y T17. T19 requiere T7 y T10.
- Frontend: T20 puede empezar ya (con MSW y el contrato de la decisión (b)) → T21 → T22, T23. T24 es independiente.
- T25 requiere todo lo anterior. DOC-1 va al final, con las salidas de T19 y T25.
- Externas: PostgreSQL con `app_db_test` (T1, T3–T5, T12–T18); los libros reales en `HISTORICO_DIR` solo para T19 y T25; Docker Desktop para T25.

**Riesgos**
1. **La lista no reproduce la del notebook.** Pueden cambiarla el orden de las filas de entrenamiento (bootstrap con `random_state=42`), la versión de scikit-learn, los montos negativos (en la app pasan a `None`; el notebook los conserva, lo que afecta a las medianas y a `monto_historico`) y la referencia de los factores (decisión (a)). Mitigación: orden explícito y estable (T6/T10), y T19 compara código por código con los empates como conjunto. Si no coincide, se documenta la diferencia de un caso (03 §6) y se sigue (05 §5).
2. **Atomicidad y concurrencia de la migración.** La transacción es larga en un hilo de fondo; el bloqueo consultivo de sesión va en una conexión propia; y un `EN_CURSO` puede quedar huérfano tras una caída. Mitigación: `EN_CURSO` y la vuelta a `PENDIENTE` van en transacciones cortas separadas, la regla del huérfano (T11), y pruebas reales de fallo forzado y de dos hilos simultáneos (T12).
3. **Privacidad y seguridad.** Datos personales en logs, excepciones del hilo o la salida de los scripts; inyección de fórmulas en el Excel; deserialización del artefacto (joblib/pickle). Mitigación: logs solo con conteos, libro y hoja (tests con `caplog`); prefijo `'` y ningún `<f>` (T17); el artefacto solo se carga desde `modelos` (ADR-003). La revisión completa es del día 7.

### R-003 — Día 2 del cronograma (Histórico): lectura de libros, limpieza, identidad, ciclos y etiquetas (CU-03 lógica), repositorios del historial, datos sintéticos y páginas Inicio y Carga · **DONE** 2026-09-29

**Cierre:** security **diferida** a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)) · tests `pass` (Backend 729 pytest, ruff, format, mypy app 67 archivos, lint-imports 7 contratos; Frontend 270 Vitest, lint 0, build). Libros reales: 2.771 / 2.748 / 1.410 / 1.564 evaluables (1.098 / 466), iguales al notebook; 2 diferencias conocidas sin efecto en etiquetas. Docs: `docs/backend/09-esquema-base-de-datos.md`, `docs/backend/11-historico.md` (nuevo), `docs/backend/01-arquitectura.md`, `docs/frontend/01-arquitectura.md`, `Backend/README.md`, `README.md` (índice), `05-cronograma-semana.md` (avance y resumen del Día 2).

**Pendientes que pasan a otros días:** conectar `ProcesarHistorico` con los repositorios en la migración atómica → día 3 (D3-BE-04) · S23 y revisión de seguridad de R-003 → día 7 · `mypy` sobre `tests/` (stubs de `openpyxl`, `generar_fixtures.py:836`, `type: ignore` sin uso en `test_procesar_historico.py:33`) · el resumen de carga no muestra `filasLeidas` ni `fechaCarga`.

**Objetivo:** al cerrar, los libros (sintéticos en la suite, reales en local) se leen, se limpian y se convierten en ciclos etiquetados con las reglas del notebook, y en local da **2.771 / 2.748 / 1.410** y **1.564 evaluables** (1.098 no renovó / 466 renovó); los repositorios del historial insertan en bloque dentro de una transacción externa; Inicio y Carga funcionan con MSW.

**Fuente:** [05 §3 Día 2](05-cronograma-semana.md) (D2-BD-01, D2-BE-01..05, D2-OP-01, D2-FE-01..02) · [03 §6 CU-03](03-casos-de-uso.md), [03 §4 CU-01](03-casos-de-uso.md) (formato de plantilla) · [04 §4.4](04-pendientes-para-iniciar-desarrollo.md) · `Notebookes/MVP.ipynb` secciones 2.4–5.5 (localizar con `Grep`; no leer el notebook entero).

**Notas de alcance del planner**
- No existe `products/P##-*.md`; alcance validado contra `DEVELOPMENT_GUIDELINES.md` §Fuera de alcance: nada cae fuera. **No** se cambia la lógica del notebook (`inicio_aproximado`, estados del registro, asistencias quedan como en el notebook: diferido).
- **Fuera de R-003:** migración atómica al arrancar, bloqueo, entrenamiento, `estado_sistema` y endpoints reales (día 3, D3-BE-04); lector de la plantilla y validaciones de CU-01 (día 4, D4-BE-01); consultas de duplicados/enlace (D4-BD-01). Los endpoints siguen en `501`.
- **Decisión del usuario:** `membresias.socio_id` pasa a `NOT NULL` (migración `0003`). Coherente con el notebook: los 23 registros sin identidad utilizable (nombre normalizado < 5 letras) se descartan antes de guardar y solo cuentan en el informe.
- **Sin login (RT-12):** las pruebas de aislamiento entre usuarios no aplican; cada archivo de prueba nuevo de API/repositorio lo deja en un comentario.
- **Proceso (05 §1):** TDD solo en T2, T3, T4, T5 (test primero, en rojo, luego código); el resto con pruebas de sus criterios. Revisión de seguridad diferida al día 7.
- **Dominio sin pandas:** las conversiones del notebook (§3.3 `convertir_fecha`, `convertir_numero`) se reescriben en Python puro en `domain`; el lector de infraestructura solo entrega valores crudos de celda (`None` en vez de `NaN`). Montos siempre `Decimal` (el notebook usa `float`: `Decimal(str(valor))` en el borde del lector). Fechas `datetime.date`.
- Ubicaciones nuevas: `app/domain/historico/` (conversiones, normalización, registro/identidad, ciclos), `app/application/historial/` (puertos y servicio de procesamiento), `app/infrastructure/historico/` (lector), `app/infrastructure/persistence/repositories/`, `Backend/scripts/` (verificación local), `Backend/tests/fixtures/`.
- Excepción al límite de 4 archivos: `__init__.py` vacíos; los `.xlsx` generados de T8 (salida del generador, no código); la línea `"0002 (head)"` → `"0003 (head)"` de `test_migrations_robustness.py` en T1.

**Tareas**

- [x] **T1** · `db` · Decisión día 2 · `membresias.socio_id NOT NULL` (migración `0003`)
  - Archivos: `Backend/alembic/versions/0003_membresias_socio_id_not_null.py` (principal), `Backend/app/infrastructure/persistence/models/historial.py`, `Backend/tests/unit/infrastructure/persistence/test_models_metadata.py`, `Backend/tests/integration/persistence/test_migrations.py` (+1 línea tolerada en `test_migrations_robustness.py`).
  - Docs: `.claude/rules/database.md` §Migraciones; `Documentation/docs/backend/09-esquema-base-de-datos.md` §Historial, §Pendientes.
  - Aceptación:
    - `revision = "0003"`, `down_revision = "0002"`; `upgrade()` = `ALTER COLUMN socio_id SET NOT NULL`; `downgrade()` lo revierte a `NULL`. No toca `predicciones.socio_id` (sigue `NULL`).
    - ORM: `socio_id: Mapped[int]` con `nullable=False`; el test de metadatos pasa a `nullable is False`.
    - Tras `upgrade head`: insertar una membresía con `socio_id NULL` → `IntegrityError` (not-null); con socio válido → OK; `alembic check` sin diferencias; `alembic current` → `0003 (head)`.
    - `downgrade` a `0002` → la inserción con `socio_id NULL` vuelve a ser aceptada; `upgrade head` otra vez funciona. El helper `membresia()` de las pruebas crea un socio por defecto.
    - Suite completa de migraciones en verde; `mypy app` y `lint-imports` en verde.
  - Pruebas: unitaria (metadatos) + integración (PostgreSQL de `app_db_test`).

- [x] **T2** · `domain` · D2-BE-02 (1/2) · **TDD** · Conversiones de celda: fecha, monto y texto de encabezado
  - Archivos: `Backend/app/domain/historico/conversiones.py` (principal: `convertir_fecha(valor: object) -> date | None`, `convertir_monto(valor: object) -> Decimal | None`, `normalizar_texto_encabezado(valor: object) -> str`), `Backend/tests/unit/domain/historico/test_conversiones.py`.
  - Docs: notebook §3.1 (`normalizar_texto_encabezado`) y §3.3 (`convertir_fecha`, `convertir_numero`); `DEVELOPMENT_GUIDELINES.md` §Excepciones (decimal); `Documentation/docs/backend/01-arquitectura.md` §Capas.
  - Aceptación (tests primero):
    - Fecha: `datetime(2025,1,6,14,30)` → `date(2025,1,6)`; `date` → igual; `45663` (int o float, serial Excel desde 1899-12-30, rango 20000..60000) → `date(2025,1,6)`; `19999` o `60001` → se intenta como texto y da `None`; `"06/01/2025"` → `date(2025,1,6)` (día primero); `"2025-01-06"` → `date(2025,1,6)`; `"13/25/2025"` → `None`; `""`, `"  "`, `None` → `None`; `True` → `None` (bool no es número).
    - Monto: `"39,50 USD"` → `Decimal("39.50")`; `25` → `Decimal("25")`; `39.5` (float de celda) → `Decimal("39.5")` (vía `str`, nunca `Decimal(float)`); `"USD 1.200"` → `Decimal("1.200")` (primer número tras cambiar coma por punto, como el notebook); `"sin valor"`, `None`, `""` → `None`; `"-5"` → `Decimal("-5")` (el dominio no filtra; el `CHECK >= 0` se trata en T10: negativos se guardan como `None` y se cuentan).
    - Encabezado: `" Cédula  "` → `"CEDULA"`; `"Nombres   y apellidos"` → `"NOMBRES Y APELLIDOS"`; `None` → `""`.
    - Ningún valor devuelto es `float`; solo librería estándar (`lint-imports`, `grep -r "pandas\|numpy" app/domain` = 0).
  - Pruebas: unitarias.

- [x] **T3** · `domain` · D2-BE-02 (2/2) · **TDD** · Normalización: filas útiles, nombre, cédula, plan y forma de pago
  - Archivos: `Backend/app/domain/historico/normalizacion.py` (principal: `es_fila_util(nombre_crudo) -> bool`, `normalizar_nombre`, `normalizar_cedula(valor) -> str | None`, `normalizar_plan(texto, duracion_dias: int | None) -> Plan`, `normalizar_forma_pago(texto) -> FormaPago`), `Backend/tests/unit/domain/historico/test_normalizacion.py`.
  - Docs: notebook §3.6 (`es_fila_util`), §4.1, §4.2, §4.5 (`normalizar_plan`, `FORMAS_PAGO_EN_CAMPO_PLAN`), §4.6 (`normalizar_forma_pago`); `Backend/app/domain/common/enums.py`.
  - Aceptación (tests primero; reglas copiadas tal cual del notebook, en el mismo orden):
    - Fila útil: `""`/`None`/`"   "` → `False`; `"TOTAL ENERO"`, `"subtotal"`, `"SUMA"`, `"MONTO"` → `False`; `"STATUS"`, `"NOMBRES Y APELLIDOS"`, `"NOMBRES Y APELLIDOS DEL SOCIO"` → `False`; `"Ana Pérez"` → `True`.
    - Nombre: `"  José  Núñez-2 "` → `"JOSE NUNEZ"` (sin tildes, solo `A-Z` y espacio simple).
    - Cédula: `"171234567-8"` → `"1712345678"`; `"12345678"` (8 dígitos) → `None`; `123456789` (int) → `"123456789"`; `None` → `None`.
    - Plan: `"PROMO 3 MESES"` → `TRIMESTRAL`; `"DATAFAST"` con duración 30 → `MENSUAL` (regla 1: el campo tenía una forma de pago y se usa la duración); `"TRANSFERENCIA ANUAL"` con duración `None` → `OTRO`; `"pase diario"` → `DIARIO`; `"PLAN AÑO"` → `ANUAL`; `"6 meses"` → `SEMESTRAL`; `"1 MES"` → `MENSUAL`; `""` con 100 → `TRIMESTRAL`, con 170 → `SEMESTRAL`, con 350 → `ANUAL`, con 60 → `OTRO`, con 21 y 45 → `MENSUAL` (bordes). Devuelve `Plan`, nunca texto.
    - Forma de pago: `""`/`None` → `SIN_DATO`; `"efectivo"` → `EFECTIVO`; `"TARJ. DATAFAST"` → `TARJETA_DATAFAST`; `"Pichincha"`, `"TRANSF"`, `"Produbanco"`, `"DINERS"`, `"INTERNACIONAL"` → `TRANSFERENCIA`; `"cheque"` → `OTRO`. Orden de reglas del notebook (`"EFECT"` antes que `"TARJ"`).
  - Pruebas: unitarias.

- [x] **T4** · `domain` · D2-BE-03 · **TDD** · Registro histórico e identidad del socio
  - Archivos: `Backend/app/domain/historico/registro.py` (principal: `FilaCruda` (frozen: `anio`, `hoja`, `fila`, `mes_hoja: date`, `nombre`, `cedula`, `celular`, `correo`, `plan`, `fecha_inicio`, `fecha_fin`, `forma_pago`, `monto_cobrado`, todos `object`), `RegistroHistorico` (frozen: `identidad`, `cedula`, `nombre`, `nombre_normalizado`, `plan`, `plan_original`, `forma_pago`, `forma_pago_original`, `fecha_inicio`, `fecha_vencimiento`, `fecha_actividad`, `inicio_aproximado`, `duracion_dias`, `monto_cobrado: Decimal | None`, `referencia: (anio, hoja, fila)`), `limpiar(filas) -> ResultadoLimpieza` con conteos), `Backend/app/domain/historico/identidad.py` (`identidad_de(cedula_norm, nombre_norm) -> str`), `Backend/tests/unit/domain/historico/test_registro.py`, `Backend/tests/unit/domain/historico/test_identidad.py`.
  - Docs: notebook §3.6, §3.7, §4.1–4.4, §5.4 (`fecha_actividad`, `inicio_aproximado`); `03-casos-de-uso.md` §6 pasos 7–10.
  - Aceptación (tests primero):
    - Identidad: cédula normalizada `"1712345678"` → `"C:1712345678"`; sin cédula válida y nombre `"ANA PEREZ"` → `"N:ANA PEREZ"`; misma cédula con nombres distintos → misma identidad.
    - `limpiar`: fila no útil → cuenta en `descartadas_no_utiles`; fila útil con nombre normalizado de < 5 letras (`"A-1"`, `"LUIS"`) → cuenta en `sin_identidad` y no produce registro; resto → `RegistroHistorico`. `ResultadoLimpieza` expone `filas_leidas`, `descartadas_no_utiles`, `utiles` (= leídas − no útiles), `sin_identidad`, `con_identidad`, `socios_distintos`, `por_cedula`, `por_nombre`, `inicio_aproximado`.
    - Sin fecha de inicio: `fecha_inicio = None`, `inicio_aproximado = True`, `fecha_actividad = mes_hoja` (primer día del mes de la hoja); con fecha: `inicio_aproximado = False`, `fecha_actividad = fecha_inicio`.
    - `duracion_dias = (fecha_vencimiento − fecha_inicio).days` solo si ambas existen (si no, `None`); el plan se normaliza con esa duración (T3); `plan_original` y `forma_pago_original` conservan el texto crudo (`str` recortado o `None`).
    - Monto negativo → `monto_cobrado = None` y cuenta en `montos_invalidos` (la BD exige `>= 0`); desviación del notebook documentada en el docstring y en el informe de T11.
    - Los duplicados exactos se **conservan** (dos filas iguales → dos registros), como el notebook.
    - Ningún `repr`/`str` de `ResultadoLimpieza` contiene nombres ni cédulas (solo conteos).
  - Pruebas: unitarias.

- [x] **T5** · `domain` · D2-BE-04 · **TDD** · Ciclos: fecha de corte, estado del ciclo y etiqueta T..T+30
  - Archivos: `Backend/app/domain/historico/ciclos.py` (principal: `fecha_corte(meses_hoja) -> date` = último día del mes máximo; `MotivoCiclo` (`StrEnum`: `SIN_VENCIMIENTO`, `FECHA_FUERA_DE_RANGO`, `VENCIMIENTO_POSTERIOR_AL_CORTE`, `PASE_DIARIO`, `DURACION_IMPLAUSIBLE`, `VENTANA_INCOMPLETA`, `EVALUABLE`); `clasificar(registro, corte) -> (EstadoCiclo, MotivoCiclo)`; `etiquetar(registros, corte) -> list[CicloEtiquetado]` con `no_renovo: bool | None` y `fecha_renovacion: date | None`; constantes `FECHA_MINIMA_RAZONABLE = date(2024,12,1)`, `DIAS_OBSERVACION = 30`, `DIAS_RENOVACION_ANTICIPADA = 0`), `Backend/tests/unit/domain/historico/test_ciclos.py`.
  - Docs: notebook §5.1 (`fecha_corte_datos`), §5.2 (caso del tutor), §5.3 (`motivo_estado_ciclo`, JSON ~l. 3198–3215), §5.5 (`buscar_renovacion`, ~l. 3397–3423), §1.2 (parámetros); `03-casos-de-uso.md` RN-01.5, RT-02, RT-03.
  - Aceptación (tests primero; orden exacto de reglas del notebook):
    - `fecha_corte([date(2026,8,1), date(2025,1,1)])` → `date(2026,8,31)`; `fecha_corte([date(2024,2,1)])` → `date(2024,2,29)`; lista vacía → `ValueError`.
    - Con corte 2026-08-31: sin vencimiento → `EXCLUIDO/SIN_VENCIMIENTO`; vence 2024-11-30 → `EXCLUIDO/FECHA_FUERA_DE_RANGO`; vence 2026-09-05 → `EXCLUIDO/VENCIMIENTO_POSTERIOR_AL_CORTE`; plan `DIARIO` → `EXCLUIDO/PASE_DIARIO`; duración 21 o 401 → `EXCLUIDO/DURACION_IMPLAUSIBLE`, 22 y 400 → no excluido por duración; duración `None` → no excluido por duración; **caso del tutor:** vence 2026-08-20 → `PENDIENTE/VENTANA_INCOMPLETA` (T+30 = 2026-09-19 > corte); vence 2026-08-01 → `EVALUABLE` (T+30 = 2026-08-31 = corte, límite inclusivo); vence 2026-07-15 → `EVALUABLE`.
    - Prioridad de reglas: `DIARIO` sin vencimiento → `SIN_VENCIMIENTO` (primera regla que aplica).
    - Renovación (solo evaluables): otra membresía no `DIARIO` del mismo socio con `fecha_actividad` en `[T, T+30]` (ambos inclusive) → `no_renovo = False` y `fecha_renovacion` = la mínima; en T−1 o T+31 → `no_renovo = True`; otra membresía de **otro** socio en la ventana → `True`; el propio registro nunca cuenta como su renovación; un duplicado exacto del mismo socio con la misma `fecha_actividad` dentro de la ventana **sí** cuenta (igual que el notebook, que solo excluye el mismo índice). Pendientes y excluidos → `no_renovo = None`.
    - Solo librería estándar; `EstadoCiclo` de `domain/common/enums.py`.
  - Pruebas: unitarias.

- [x] **T6** · `application` · D2-BD-01 (1/2) · Puertos del historial y del lector
  - Archivos: `Backend/app/application/historial/ports.py` (principal: `LectorHistorico` (`leer(rutas) -> LibrosLeidos` con `filas: Sequence[FilaCruda]` y hojas incluidas/omitidas por libro); `SocioRepository.insertar_en_bloque(socios: Sequence[NuevoSocio]) -> list[int]` (ids en el mismo orden); `MembresiaRepository.insertar_en_bloque(Sequence[NuevaMembresia]) -> int`; `CargaRepository.crear(NuevaCarga) -> int`; `NuevoSocio`, `NuevaMembresia`, `NuevaCarga` como `@dataclass(frozen=True, slots=True)` con montos `Decimal`, fechas `date`, instantes `datetime` aware, enums del dominio), `Backend/app/application/historial/__init__.py`, `Backend/tests/unit/application/historial/test_ports.py`.
  - Docs: `Documentation/docs/backend/01-arquitectura.md` §Capas, §Patrón de un caso de uso; `.claude/rules/backend.md`.
  - Aceptación:
    - Los puertos son `typing.Protocol` (`runtime_checkable`); dobles en memoria en el test satisfacen `isinstance` y `mypy`.
    - Los puertos **no** reciben ni devuelven sesiones, engines ni ORM; la transacción la gestiona quien llama (unit of work) — docstring explícito: los repositorios nunca hacen `commit` ni `rollback`.
    - `NuevaMembresia.socio_id: int` (no opcional, T1); `NuevaCarga.fecha_carga` sin zona → `ValueError`.
    - `lint-imports` en verde (`application` no importa `infrastructure` ni pandas).
  - Pruebas: unitarias.

- [x] **T7** · `infra` · D2-BD-01 (2/2) · Repositorios SQLAlchemy con inserción masiva en transacción externa
  - Archivos: `Backend/app/infrastructure/persistence/repositories/historial.py` (principal: `SqlAlchemySocioRepository`, `SqlAlchemyMembresiaRepository`, `SqlAlchemyCargaRepository`, todos con `__init__(self, session: Session)`), `Backend/app/infrastructure/persistence/repositories/__init__.py`, `Backend/tests/integration/persistence/test_historial_repositories.py`, `Backend/tests/integration/conftest.py` (fixture `db_session`: `Session` sobre una conexión con transacción externa que termina en `rollback`).
  - Docs: `.claude/rules/database.md` §Pruebas, §Convenciones; `Documentation/docs/backend/09-esquema-base-de-datos.md` §Historial.
  - Aceptación (integración contra `app_db_test`):
    - Inserción masiva con `insert(...)` + lista de parámetros (executemany / *insertmanyvalues*), no fila a fila con `session.add`; socios con `RETURNING id` y `sort_by_parameter_order=True` → ids en el mismo orden de entrada.
    - `created_at`/`updated_at` salen de un `Clock` inyectado en el constructor (nunca `datetime.now()`); `referencia_origen` se guarda como JSONB `{"anio", "hoja", "fila"}`; montos `Decimal` sin pérdida (`Decimal("39.50")` se lee igual).
    - **Hecho cuando (05):** 1 carga + 1.000 socios + 3.000 membresías insertados en la misma transacción → `count` visible dentro; tras `rollback` → `socios`, `membresias` y `cargas` con 0 filas. Tiempo de la inserción de 3.000 < 5 s (aserción holgada).
    - Ningún método llama `commit`, `rollback`, `begin` ni `close` (test que usa un doble de sesión o `grep` en el test: 0 apariciones en el módulo).
    - Una membresía con `socio_id` inexistente → `IntegrityError` y la transacción externa queda revertible.
    - Comentario en el test: aislamiento entre usuarios no aplica (RT-12).
  - Pruebas: integración.

- [x] **T8** · `infra` (datos de prueba) · D2-OP-01 · Datos sintéticos: 2 libros históricos y 5 plantillas
  - Archivos: `Backend/tests/fixtures/generar_fixtures.py` (principal: genera con `openpyxl`, determinista, sin aleatoriedad no sembrada), `Backend/tests/fixtures/esperado.py` (conteos esperados de los libros sintéticos para T9–T11), `Backend/tests/unit/fixtures/test_fixtures_sinteticos.py`; salida (excepción: binarios generados) `Backend/tests/fixtures/historico/Control Gym 2025 sintetico.xlsx`, `.../historico/Control Gym 2026 sintetico.xlsx`, `Backend/tests/fixtures/plantillas/{plantilla_valida,plantilla_cedula_invalida,plantilla_catalogo_invalido,plantilla_fechas_invalidas,plantilla_501_filas}.xlsx`.
  - Docs: `Documentation/05-cronograma-semana.md` §3 Día 2 (D2-OP-01); `Documentation/04-pendientes-para-iniciar-desarrollo.md` §4.4; `Documentation/03-casos-de-uso.md` §4 (tabla de columnas A–P y hojas de la plantilla); notebook §2.3–2.5 (estructura real de las hojas).
  - Aceptación:
    - Libros: hojas mensuales (p. ej. `ENERO`, `FEBRERO `, ` MARZO`) + auxiliares (`DIARIOS`, `NOVEDADES`, `VENTAS`); encabezado en filas distintas (0, 2 y 4); nombres de columna cambiantes entre hojas (alias del notebook §3.2); filas vacías, filas de totales, encabezado repetido, nombres de < 5 letras, socios sin cédula, cédula con guion, fechas como `datetime`, serial Excel y texto `dd/mm/yyyy`, montos `"39,50 USD"`, planes con forma de pago dentro, un duplicado exacto, un vencimiento sin fecha, un pase diario, una renovación dentro de T..T+30 y el caso del tutor (vence el 20 del último mes).
    - Plantillas: hojas `Instrucciones`, `Registros`, `Ejemplo`, `Catalogos`; títulos de `Registros` en la fila 1 según 03 §4 (A–P); `valida` (≥ 5 filas correctas, cédulas con dígito verificador válido); `cedula_invalida` (dígito verificador incorrecto); `catalogo_invalido` (plan `SEMANAL`); `fechas_invalidas` (vencimiento anterior al inicio); `501_filas` (501 filas con datos).
    - **Sin datos reales:** nombres de una lista ficticia fija en el generador; cédulas sintéticas; test que comprueba que el generador reproduce byte a byte los conteos de `esperado.py` y que ningún archivo de `tests/fixtures/` viene de `plantillas/` (nombres distintos, `git check-ignore` no los ignora).
    - `python tests/fixtures/generar_fixtures.py` regenera los 7 archivos sin cambios en los conteos.
  - Pruebas: unitaria de estructura (openpyxl) — permitido en `tests/`, no en `app/domain`.

- [x] **T9** · `infra` · D2-BE-01 · Lector de libros históricos (pandas + openpyxl)
  - Archivos: `Backend/app/infrastructure/historico/lector_libros.py` (principal: `LectorLibrosExcel` implementa `LectorHistorico`), `Backend/app/infrastructure/historico/alias_columnas.py` (`MESES`, `ALIAS_COLUMNAS` copiados del notebook §2.4 y §3.2), `Backend/app/domain/historico/errores.py` (`LibroSinAnioError`, `HojaSinEncabezadoError` como `DomainError`, mensajes con libro/hoja, sin datos personales), `Backend/tests/integration/infrastructure/test_lector_libros.py`.
  - Docs: notebook §2.2 (`buscar_archivo`), §2.4 (`MESES`, `clasificar_hojas`), §3.1 (`encontrar_fila_encabezado`, `max_filas=10`), §3.2 (`ALIAS_COLUMNAS`, `buscar_indice_columna`), §3.4 (`leer_hoja_mensual`); `Documentation/docs/backend/01-arquitectura.md` (ADR-002: pandas solo en infraestructura).
  - Aceptación (con los libros de T8):
    - Año desde el nombre del archivo (`"Control Gym 2025 sintetico.xlsx"` → 2025; `"Control Gym (1).xlsx"` → `LibroSinAnioError`).
    - Solo hojas cuyo nombre recortado y en mayúsculas es un mes; las auxiliares se reportan como omitidas.
    - Encabezado = primera fila (de las 10 primeras) que contiene `CEDULA` y `NOMBRE` tras `normalizar_texto_encabezado` (T2); hoja mensual sin encabezado → `HojaSinEncabezadoError` con libro y hoja.
    - Columna por alias; si falta, el campo sale `None`. `fila` = número de fila visible en Excel (1-based, como `datos.index + 1` del notebook); `mes_hoja` = primer día del mes de la hoja.
    - Valores crudos: `NaN`/`NaT` → `None`; `Timestamp` → `datetime`; números → `int`/`float` tal cual (la conversión a `Decimal`/`date` es del dominio). Lectura con `header=None` y `dtype=object`.
    - Los conteos del libro sintético coinciden con `esperado.py` (filas leídas por hoja y hojas incluidas/omitidas).
    - No escribe nada en disco ni en logs con datos de celdas (RN-03.5, RT-13): solo nombre de libro, hoja y conteos.
  - Pruebas: integración (archivos reales de fixtures, sin BD).

- [x] **T10** · `application` · CU-03 (lógica) · Servicio `ProcesarHistorico`: lector → limpieza → identidad → ciclos, con informe sin datos personales
  - Archivos: `Backend/app/application/historial/procesar_historico.py` (principal: `ProcesarHistorico(lector: LectorHistorico).ejecutar(rutas) -> ResultadoProcesamiento` con `registros`, `ciclos`, `fecha_corte` e `InformeHistorico` (conteos de T4, ciclos por estado y por motivo, evaluables, no renovó, renovó, prevalencia como `Decimal`, rango de vencimientos)), `Backend/tests/unit/application/historial/test_procesar_historico.py`, `Backend/tests/integration/infrastructure/test_procesar_historico_fixtures.py`.
  - Docs: `Documentation/03-casos-de-uso.md` §6 pasos 4–11 y 15; `Documentation/docs/backend/01-arquitectura.md` §Patrón de un caso de uso.
  - Aceptación:
    - Unitaria con lector doble: 6 filas conocidas → conteos exactos (leídas, no útiles, sin identidad, socios, evaluables, pendientes, excluidos por motivo); sin persistencia (no usa repositorios: el guardado atómico es D3-BE-04).
    - Integración con `LectorLibrosExcel` y los libros de T8 → `InformeHistorico` igual a `esperado.py`, incluida la etiqueta del caso del tutor (`PENDIENTE`).
    - Suma de ciclos por estado = `con_identidad`; prevalencia = no_renovó / evaluables (`Decimal`, sin `float`).
    - `InformeHistorico` es serializable a `dict` solo con números, fechas y claves fijas (test: ningún valor es un nombre o cédula de las filas).
  - Pruebas: unitaria + integración.

- [x] **T11** · `infra-deploy` (script local) · D2-BE-05 · Verificación con los libros reales, fuera de la suite
  - Archivos: `Backend/scripts/verificar_historico.py` (principal: `python scripts/verificar_historico.py <carpeta>`; compone `LectorLibrosExcel` + `ProcesarHistorico`; imprime una tabla "obtenido vs notebook" y sale con 0 si todo coincide, 1 si hay diferencias), `Backend/tests/unit/scripts/test_verificar_historico.py` (solo con los libros sintéticos y valores esperados inyectados).
  - Docs: `Documentation/03-casos-de-uso.md` §6 Criterios de aceptación; notebook §3.6, §4.1, §4.3, §5.3, §5.5 (cifras de referencia).
  - Aceptación:
    - Valores de referencia del notebook codificados en el script: útiles **2.771**, con identidad **2.748**, socios **1.410**, corte **2026-08-31**, `EVALUABLE` **1.564**, `SIN_VENCIMIENTO` 855, `VENCIMIENTO_POSTERIOR_AL_CORTE` 160, `VENTANA_INCOMPLETA` 96, `DURACION_IMPLAUSIBLE` 49, `PASE_DIARIO` 16, `FECHA_FUERA_DE_RANGO` 8, no renovó **1.098**, renovó **466**.
    - Con la carpeta real (`HISTORICO_DIR` local) el developer lo ejecuta y **pega la salida** (solo conteos) en el handoff; si difiere, identifica la causa por hoja/regla (p. ej. inferencia de tipos de `read_excel` en pandas 3.x, parseo de fechas en texto) y la anota. **Si la causa es pandas 3.x**, se prueba con pandas 2.x fijado en `pyproject.toml` (cambio condicionado, se reporta antes de aplicarlo).
    - La salida nunca imprime nombres, cédulas, celulares ni correos (test con sintéticos: ningún nombre de la lista ficticia aparece en `stdout`).
    - El script no está bajo `tests/` ni lo recoge `pytest` por defecto; no escribe archivos.
  - Pruebas: unitaria del script con sintéticos + ejecución manual local.

- [x] **T12** · `frontend` · D2-FE-01 · Página Inicio con estado del sistema
  - Archivos: `Frontend/src/features/inicio/pages/InicioPage.tsx` (principal), `Frontend/src/features/inicio/hooks/useEstadoSistema.ts`, `Frontend/src/features/inicio/components/EstadoSistemaPanel.tsx`, `Frontend/src/features/inicio/pages/InicioPage.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura, §Feature `health` (patrón), §MSW; `Documentation/03-casos-de-uso.md` §6 (flujos alternativos).
  - Aceptación (Vitest + MSW, `server.use` por estado):
    - `INICIALIZANDO` → texto "Inicializando datos históricos" en `role="status"`.
    - `FALTAN_DATOS_HISTORICOS` → aviso "Faltan los datos históricos" con indicación de revisar la carpeta configurada (sin rutas ni datos).
    - `LISTO` → "Sistema listo", versión del modelo (`"v1"`), fecha de entrenamiento y última carga formateadas en `es-EC`; `modeloVigente = null` → "Sin modelo vigente".
    - Cargando → `LoadingIndicator`; `501`/`500` → `ErrorAlert` con "Reintentar" que vuelve a pedir. `AbortController` al desmontar.
    - `pages` no importa `api/` ni `core/http`; sin `fetch` directo (test de arquitectura existente en verde).
  - Pruebas: frontend.

- [x] **T13** · `frontend` · D2-FE-02 · Página Carga: selección, vista previa, errores y confirmación
  - Archivos: `Frontend/src/features/carga/pages/CargaPage.tsx` (principal), `Frontend/src/features/carga/hooks/useCarga.ts` (vista previa y confirmación con estados), `Frontend/src/features/carga/components/VistaPreviaCarga.tsx` (conteos + `DataTable` de errores `fila`/`columna`/`motivo`), `Frontend/src/features/carga/pages/CargaPage.test.tsx`.
  - Docs: `Documentation/docs/frontend/01-arquitectura.md` §Estructura, §`shared/ui`; `Documentation/03-casos-de-uso.md` §4 (flujo y excepciones).
  - Aceptación (Vitest + MSW con los handlers de T27 de R-002):
    - Input `type="file"` con `accept=".xlsx"` y etiqueta accesible; archivo no `.xlsx` → mensaje local sin llamar a la API.
    - `valida.xlsx` → conteos (leídas, válidas, con error, duplicadas, rango de vencimientos) y botón "Confirmar" **habilitado**; `con-errores.xlsx` → tabla con una fila por error y botón **deshabilitado**; `puedeConfirmar: false` sin errores (todo duplicado) → deshabilitado.
    - Clic en "Confirmar" → `POST /api/v1/cargas` y resumen (`filasGuardadas`, `filasDuplicadas`, `avisosEnlace`); `422`/`409`/`400` simulados → `ErrorAlert` con el mensaje del servidor; mientras envía, botón deshabilitado (sin doble envío).
    - Cambiar de archivo limpia la vista previa anterior.
  - Pruebas: frontend.

- [x] **DOC-1** · (doc-agent) · Documentar R-003: `docs/backend/09-esquema-base-de-datos.md` (`socio_id NOT NULL`, `0003`, quitar el pendiente), nuevo `docs/backend/11-historico.md` (lector, dominio `historico`, puertos y repositorios con transacción externa, informe, script de verificación y **diferencias con el notebook** reportadas por T11, incluida la decisión sobre pandas), `docs/backend/01-arquitectura.md` (nuevos paquetes), `docs/frontend/01-arquitectura.md` (Inicio y Carga), `Backend/README.md` (fixtures y script); actualizar `05-cronograma-semana.md` con estado de las tareas del Día 2 y el "Avance y resumen del Día 2"; mover R-003 a TERMINADOS.

**Dependencias**
- Backend: T1 primero (esquema). T2 → T3 → T4 → T5 (TDD, dominio). T6 tras T4 (usa `FilaCruda`) → T7 (requiere T1 y T6). T8 independiente (puede ir en paralelo desde el inicio). T9 requiere T2, T6 y T8. T10 requiere T5, T6 y T9. T11 requiere T10.
- Frontend: T12 y T13 independientes del backend (MSW, contrato de R-002); pueden ir en paralelo.
- DOC-1 al final, con T11 ejecutado (sus cifras alimentan la documentación y el cronograma).
- Externas: PostgreSQL del compose con `app_db_test` (T1, T7); los libros reales en `HISTORICO_DIR` local solo para la ejecución manual de T11.

**Riesgos**
1. **Las cifras no cuadran (2.771 / 2.748 / 1.410 / 1.564):** `read_excel` de pandas 3.x puede inferir tipos distintos (fechas como texto, enteros como float) y el parseo de fechas en texto se reescribe sin `pd.to_datetime`. Mitigación: T9 entrega valores crudos con `dtype=object`, T2 cubre los formatos del notebook, T11 compara por motivo para aislar la regla; fallback: pandas 2.x fijado. Según 05 §5: se documenta y se sigue (máx. medio día del día 3).
2. **Datos personales filtrados** en logs, mensajes de error, `repr` o salida del script (RN-03.5, RT-13): solo conteos, libro y hoja; tests explícitos en T4, T10 y T11. Los fixtures de T8 nunca derivan de `plantillas/`.
3. **Transacción del unit of work:** un repositorio que haga `commit` rompería la atomicidad que exige D3-BE-04 (RN-03.2). Mitigación: la sesión se recibe desde fuera, test de rollback con 3.000 filas y verificación de que el módulo no llama `commit`/`rollback`. La `0003` falla si alguna base tuviera membresías con `socio_id NULL` (hoy todas vacías).

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

- 2026-09-29 · R-003 · `membresias.socio_id` pasa a `NOT NULL` (migración `0003`, decisión del usuario); los registros sin identidad se descartan y solo se cuentan; `predicciones.socio_id` sigue `NULL` → [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-29 · R-003 · Conversión de fechas y montos del notebook reescrita en el dominio sin pandas; pandas solo en el lector. Se mantiene pandas 3.0.6 (el notebook corrió con pandas 3) → [11-historico](docs/backend/11-historico.md).
- 2026-09-29 · R-003 · No se replica la conversión de pandas de 2 celdas basura de fecha (diferencias conocidas 857/855 y 6/8, sin efecto en evaluables ni etiquetas); montos negativos → `None` y contados → [11-historico](docs/backend/11-historico.md).
- 2026-09-29 · R-003 · Los repositorios del historial nunca hacen `commit`/`rollback`: la transacción es del llamante (unit of work de D3-BE-04).
- 2026-09-29 · R-003 · La revisión de seguridad de R-003 se difiere a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)).

- 2026-09-29 · R-004 · Referencia de los factores = evaluables con vencimiento en 2025 (`PERIODO_REFERENCIA_FACTORES`, parametrizable), como el notebook; corrige la decisión (a) inicial ("todo el entrenamiento") → [ADR-005](adr/ADR-005-fidelidad-al-notebook-del-modelo-v1.md), [12](docs/backend/12-modelo-y-listas.md).
- 2026-09-29 · R-004 · Contrato de listas: `GET /listas` nuevo; `fecha_generacion` pasa a `date`, se añaden `creada_en` y `monto_cobrado` → [API_CONTRACT](docs/API_CONTRACT.md).
- 2026-09-29 · R-004 · Fallo de migración → `PENDIENTE` y `FALTAN_DATOS_HISTORICOS`; se reintenta al reiniciar el backend (ADR-004).
- 2026-09-29 · R-004 · scikit-learn fijado a 1.8.0, la versión del notebook: con 1.9.1 cambia el bosque; con 1.8.0 la lista de septiembre es idéntica → [ADR-005](adr/ADR-005-fidelidad-al-notebook-del-modelo-v1.md), [Backend/README](../Backend/README.md). Corrige la línea de R-002 sobre versiones "no las del notebook" para esta librería.
- 2026-09-29 · R-004 · Niveles de riesgo por percentiles 20/30/50 (CU-05), no los umbrales fijos 0,70/0,50 del notebook: difieren por diseño.
- 2026-09-29 · R-004 · Los ítems de una lista guardada no filtran `deleted_at` (lista inmutable, RN-04.5); la versión del modelo la calcula el llamante; bloqueo consultivo de sesión en conexión propia `AUTOCOMMIT`, liberado en `finally`; el localizador solo lee `*Control*Gym*.xlsx`.
- 2026-09-29 · R-004 · La revisión de seguridad de R-004 se difiere a la revisión única del día 7 (decisión del usuario, [05 §1](05-cronograma-semana.md)).

- 2026-09-29 · R-005 · "Hoy" = fecha de negocio de Ecuador (UTC−5 fijo) en el backend; en el navegador, la fecha local. Fecha pasada → `422`; horizonte fuera de 1..31 → `400` → [ADR-006](adr/ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md).
- 2026-09-29 · R-005 · Cédula en lugar de correo en la API, el Excel y el repositorio de listas; socios sin cédula fuera de las listas nuevas (siguen en la base y el entrenamiento); listas antiguas inmutables → [ADR-006](adr/ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md), [API_CONTRACT](docs/API_CONTRACT.md). Ajusta CU-04 §7 y CU-12 §15 de [03](03-casos-de-uso.md) a petición del usuario.
- 2026-09-29 · R-005 · El Excel conserva score y aportes; la pantalla no (dos tablas: prioritarios y resto) → [frontend/01](docs/frontend/01-arquitectura.md). **Revertida en R-008** (ADR-007).
- 2026-09-29 · R-005 · `verificar_lista.py` conserva su ventana y trata a todos como "con cédula": la conciliación al 31-08-2026 ya solo se hace con el script → [12](docs/backend/12-modelo-y-listas.md).
- 2026-09-29 · R-005 · La revisión de seguridad de R-005 (incluida la exposición de la cédula) se difiere a la revisión única del día 7 ([05 §1](05-cronograma-semana.md)).

- 2026-09-30 · R-006 · Borrado físico puntual de las listas de prueba (`predicciones` 117, `listas_priorizadas` 3) en la base de Docker, por decisión explícita del usuario; excepción única que no cambia la regla → [DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md), [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-29 · R-006 · Fechas cortas con tabla fija de meses sin punto ("sep"), aritmética en UTC; un rango en el mismo mes no se compacta ("1 oct – 15 oct 2026") → [frontend/01](docs/frontend/01-arquitectura.md).
- 2026-09-29 · R-006 · En "Listas anteriores", N prioritarios = `min(topK, totalItems)`, sin cambiar la API → [frontend/01](docs/frontend/01-arquitectura.md).
- 2026-09-29 · R-006 · El celular sale de la pantalla y se mantiene en la API y el Excel → [06 §5](06-como-funciona-la-lista.md). **En el Excel, revertida en R-008** (ADR-007); sigue en la API.
- 2026-09-29 · R-006 · La revisión de seguridad de R-006 se difiere a la revisión única del día 7 ([05 §1](05-cronograma-semana.md)).

- 2026-09-29 · R-007 · (l) Confirmaciones de carga de prueba y E2E solo en el stack aislado `mtabolic-e2e` (8081/8001/5433, base y libros sintéticos); en el principal solo vista previa y lista; puertos e `IMAGE_TAG` configurables → [10-docker](docs/backend/10-docker.md).
- 2026-09-29 · R-007 · (a) Las duplicadas cuentan como válidas; confirmar exige sin errores y al menos una fila nueva → [API_CONTRACT §Cargas](docs/API_CONTRACT.md#cargas-cu-01-r-007).
- 2026-09-29 · R-007 · (d)(e) Cédula de 10 dígitos módulo 10 sin reglas de provincia; búsqueda con y sin cero inicial (sin reescribir la histórica); celda numérica de 9 dígitos → antepone `0`. Precisa CU-01 sin contradecirlo → [13-cargas](docs/backend/13-cargas.md).
- 2026-09-29 · R-007 · (f) Títulos A..N exactos; (g) plantilla ≤ 5 MB → `413`; (h) montos con máximo 2 decimales → [13-cargas](docs/backend/13-cargas.md).
- 2026-09-29 · R-007 · (j) Bloqueo consultivo de transacción en la confirmación; sin índice único de duplicados (D-04 conserva duplicados históricos); migración `0005` solo añade el índice parcial de socios sin cédula → [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-29 · R-007 · Un socio enlazado por nombre recibe la cédula aunque sus filas sean duplicadas; `ClaveMembresia` única en el dominio.
- 2026-09-29 · R-007 · La revisión de seguridad de R-007 (incluidos 2 avisos moderados de `npm audit` por `uuid` vía `exceljs`, solo desarrollo) se difiere a la revisión única del día 7 ([05 §1](05-cronograma-semana.md)).

- 2026-09-29 · R-008 · Excel igual a la tabla de la pantalla (hojas "Socios prioritarios a contactar", "Otros socios por vencer", "Resumen"; sin celular, score ni monto; motivos sin aporte). **Revierte** R-005 (e) (score y aportes en el Excel) y R-006 (celular en el Excel), por decisión del usuario; la API conserva esos campos. Ajusta CU-12 §15 de [03](03-casos-de-uso.md) → [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md).
- 2026-09-29 · R-008 · Nombre editable de la lista: `nombre` 1..80 (migración `0006`, `CHECK`), opcional en `POST /listas`, por defecto "Lista del d mmm aaaa"; es el título, aparece en "Listas anteriores" y en el Excel; sustituye el título fijo de R-006 (d) → [ADR-007](adr/ADR-007-excel-igual-a-la-pantalla-y-nombre-de-lista.md), [API_CONTRACT](docs/API_CONTRACT.md).
- 2026-09-29 · R-008 · Carga en tres pasos (elegir → "Revisar archivo" → "Confirmar carga"); elegir no llama a la API → [frontend/01](docs/frontend/01-arquitectura.md).
- 2026-09-29 · R-008 · Reinicio de la base principal solo con scripts versionados (`-p proyectofinal` fijo, confirmación `BORRAR`); excepción de borrado físico explícito del usuario, no función de la app. No se ejecutó en R-008 para no borrar las 2 listas del usuario → [comandos](comandos/reiniciar-base-historica.md), [DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md).
- 2026-09-29 · R-008 · La revisión de seguridad de R-008 se difiere a la revisión única del día 7 ([05 §1](05-cronograma-semana.md)).

- 2026-09-30 · R-009 · (a) `GET /alertas` y `GET /gestiones?filtro=` siguen en `501` hasta el día 6 (CU-09) → [API_CONTRACT](docs/API_CONTRACT.md).
- 2026-09-30 · R-009 · (b) `PrediccionDTO` añade `gestion_id`; `prioridad` de campaña 1..999; `GestionDTO.fecha_asignacion` = instante de creación → [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md).
- 2026-09-30 · R-009 · (c) Migración `0008`: `gestiones_retencion.campania_nombre` congela el nombre de la campaña al asignarla (RN-08.2) → [ADR-008](adr/ADR-008-gestion-por-ciclo-y-nombre-de-campania-congelado.md), [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-30 · R-009 · (d) 3 campañas de ejemplo "Ejemplo: …" por migración de datos `0007` (el cronograma decía `0003`), sin duplicar → [09](docs/backend/09-esquema-base-de-datos.md).
- 2026-09-30 · R-009 · (e) Nombres de campaña repetidos permitidos; no se reactivan; inactivar es idempotente; editar no cambia `es_ejemplo`.
- 2026-09-30 · R-009 · (g) Fecha de seguimiento sugerida = `max(vencimiento + 25, hoy)`; la gestión es por ciclo y se ve en todas las listas de esa membresía; (h) reglas de coherencia del resultado en el dominio → [API_CONTRACT §Campañas y gestiones](docs/API_CONTRACT.md).
- 2026-09-30 · R-009 · (j) El Excel incluye "Gestión" y "Campaña" para seguir igual a la tabla; **revierte** el criterio de R-008 que las excluía → [12 §Excel](docs/backend/12-modelo-y-listas.md). [03 §15](03-casos-de-uso.md) sin modificar: pendiente de confirmación del usuario.
- 2026-09-30 · R-009 · Reinicio de la base principal **ejecutado** con `scripts/reiniciar-base-historica.sh --si`, autorizado por el usuario (socios 1.410, membresías 2.748, cargas 1, listas 0, predicciones 0; `LISTO`) → [DEVELOPMENT_GUIDELINES §Excepciones](DEVELOPMENT_GUIDELINES.md).
- 2026-09-30 · R-009 · La revisión de seguridad de R-009 se difiere a la revisión única del día 7 ([05 §1](05-cronograma-semana.md)).

## PRÓXIMO

Día 6 del [cronograma](05-cronograma-semana.md): alertas (CU-09, incluye `GET /alertas` y `GET /gestiones?filtro=`, hoy en `501`), dashboard (CU-11), reentrenamiento (CU-02) y acceso por IP (CU-00).

Registrado por R-005, sin implementar: **D6-BE-06 / D6-FE-04** (alerta en Inicio si no hay carga en el mes actual). D4-FE-03 quedó hecho en R-007.

Registrado por R-006, sin implementar: **D7-FE-01** (mejora del diseño visual de la aplicación con los tokens de `shared/ui`, sin cambiar comportamiento; a pedido del usuario) → [05 Día 7](05-cronograma-semana.md).
