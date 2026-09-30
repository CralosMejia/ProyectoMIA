# Contrato de la API

Base: `/api/v1`. JSON. El OpenAPI generado (`/openapi.json`, `/docs`) es el spec detallado con ejemplos; este documento resume el contrato.

## Formato único de error

Toda respuesta de error tiene la forma:

```json
{ "error": { "code": "not_found", "message": "El recurso solicitado no existe." } }
```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `validation_error` | Entrada inválida (sustituye al 422 por defecto de FastAPI). No expone los campos al cliente. |
| 401 | `unauthorized` | Reservado. No habrá login (RT-12). |
| 403 | `forbidden` | Petición desde una IP no autorizada (CU-00, día 6). Mensaje: "El acceso no esta permitido desde este equipo." (R-002 quitó la referencia a sesión). |
| 404 | `not_found` | Ruta o recurso inexistente. |
| 405 | `method_not_allowed` | Método no permitido. |
| 409 | `conflict` | Conflicto con el estado del sistema (migración no completada, sin modelo vigente, gestión ya existente o cerrada). |
| 413 | `payload_too_large` | El archivo supera el tamaño máximo permitido. |
| 422 | `domain_rule_violated` | Excepción de dominio (`DomainError`); `message` es el de la excepción, que debe ser apto para el usuario. |
| 500 | `internal_error` | Error no controlado. Mensaje genérico; el detalle solo en el log del servidor. |
| 501 | `not_implemented` | Contrato publicado, lógica pendiente. Mensaje: "Esta funcion aun no esta disponible." |

Los routers declaran sus errores con `error_responses(...)` de `app/api/openapi.py`, que añade el modelo de error y un ejemplo por código al OpenAPI; `raise_not_implemented()` produce el `501`.

Nunca se devuelven tracebacks, SQL ni rutas del sistema.

## CORS

Solo los orígenes listados en `CORS_ORIGINS`. Métodos `GET, POST, PUT, PATCH, DELETE, OPTIONS`; cabeceras `Authorization, Content-Type`; credenciales permitidas (el comodín está prohibido).

## Endpoints

### `GET /api/v1/health`

Público. Informa si el servicio y la base de datos responden (`SELECT 1`, timeout ~2 s).

| HTTP | Cuerpo |
|---|---|
| 200 | `{"status":"ok","database":"up","checked_at":"2026-01-01T00:00:00Z"}` |
| 503 | `{"status":"degraded","database":"down","checked_at":"2026-01-01T00:00:00Z"}` |

- `status`: `"ok"` \| `"degraded"`. `database`: `"up"` \| `"down"`.
- `checked_at`: ISO-8601 en UTC, tomado del reloj inyectable.
- El 503 **no** usa el formato de error: es un cuerpo de health válido. El frontend lo trata como estado `degraded`.
- Sin datos de usuario: no aplica aislamiento por propietario. Sin rate limit por ahora (S13).

### Operaciones de negocio (contrato del día 1, R-002)

Las operaciones están publicadas en `/openapi.json` con DTOs Pydantic (`app/application/{modulo}/dtos.py`) y un ejemplo en la respuesta de éxito y en cada error. Las marcadas **(real)** tienen su caso de uso implementado (R-004, día 3; cargas en R-007, día 4); **el resto responde `501 not_implemented`** hasta que se implemente; la validación de entrada ya está activa (`400 validation_error`). Sin login (RT-12): no hay filtro por propietario; todas documentan `403` (CU-00).

| Operación | Éxito | Errores además de `403`/`501` | CU |
|---|---|---|---|
| `GET /sistema/estado` **(real)** | 200 `EstadoSistemaDTO` | — | CU-03 |
| `POST /cargas/vista-previa` **(real; R-007)** (multipart `archivo`; no guarda nada) | 200 `VistaPreviaCargaDTO` | 400, 409, 413 (detalle en [Cargas](#cargas-cu-01-r-007)) | CU-01 |
| `POST /cargas` **(real; R-007)** (multipart `archivo`; revalida, sin estado entre vista previa y confirmación; todo o nada) | 201 `CargaDTO` | 400, 409, 413, 422 | CU-01 |
| `POST /listas` **(real)** | 201 `ListaPriorizadaDTO` | 400 (horizonte fuera de 1..31, K menor que 1, fecha inválida o `nombre` inválido —R-008—), 409 (sistema no `LISTO`: migración en curso o sin modelo; tiene precedencia sobre el 422), 422 `domain_rule_violated` "La fecha de la lista debe ser hoy o posterior." (R-005) | CU-04 |
| `GET /listas` **(real; nuevo en R-004)** | 200 `[ListaResumenDTO]`, de la más reciente a la más antigua | — | CU-05 |
| `GET /listas/ultima` **(real)** | 200 `ListaPriorizadaDTO` | 404 (no hay listas) | CU-05 |
| `GET /listas/{lista_id}` **(real)** | 200 `ListaPriorizadaDTO` | 400, 404 | CU-05 |
| `GET /listas/{lista_id}/excel` **(real)** | 200 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `Content-Disposition: attachment; filename="lista_<id>_<fecha>.xlsx"` (sin datos personales) | 400, 404 | CU-12 |
| `GET /campanias` | 200 `[CampaniaDTO]` | — | CU-06 |
| `POST /campanias` | 201 `CampaniaDTO` | 400 | CU-06 |
| `PUT /campanias/{campania_id}` | 200 `CampaniaDTO` | 400, 404 | CU-06 |
| `POST /campanias/{campania_id}/inactivar` (no hay `DELETE`) | 200 `CampaniaDTO` | 400, 404 | CU-06 |
| `GET /predicciones/{prediccion_id}/campanias-sugeridas` | 200 `[CampaniaDTO]` por prioridad | 400, 404 | CU-07 |
| `POST /gestiones` | 201 `GestionDTO` | 400, 404, 409, 422 | CU-08 |
| `GET /gestiones?filtro=vencidas\|hoy\|proximas` | 200 `[GestionResumenDTO]` | 400 (filtro fuera de la lista blanca) | CU-09 |
| `GET /gestiones/{gestion_id}` | 200 `GestionDTO` | 400, 404 | CU-10 |
| `PUT /gestiones/{gestion_id}/resultado` | 200 `GestionDTO` | 400, 404, 409 (cerrada), 422 | CU-10 |
| `GET /alertas` | 200 `AlertasDTO` {`vencidas`, `hoy`, `proximos_7_dias`} | — | CU-09 |
| `GET /dashboard?mes=YYYY-MM` (opcional; por defecto mes actual del reloj) | 200 `DashboardDTO` | 400 | CU-11 |

Convenciones de los DTOs:

- JSON en `snake_case`; el frontend convierte a camelCase solo en `features/*/api/`.
- Decimales (`score`, `umbral_*`, `tasa_renovacion`) viajan como **string** decimal; nunca como número de coma flotante.
- `version` del modelo (`modelo_vigente.version`, `modelo_version`, `estado_modelo.version`) es **string** `"v<n>"` (p. ej. `"v1"`); en BD es `INTEGER` ([09](backend/09-esquema-base-de-datos.md)). Corrige el texto previo de T26 de R-002, que la describía como número.
- Catálogos (`plan`, `nivel_riesgo`, respuestas SI/NO/…) con los valores de los enums del dominio; `planes` de campaña excluye `DIARIO`; `campania_ofrecida` admite SI/NO/NO_APLICA.
- Listas (cambio de contrato de R-004, decisión (b)):
  - `ListaPriorizadaDTO`: `id`, `modelo_version`, `fecha_generacion` (**`date`**: fecha de referencia de la cartera; antes `datetime`), `creada_en` (**nuevo**, `datetime` con zona: instante en que se guardó), `horizonte_dias`, `top_k`, `umbral_alto`, `umbral_medio` (string decimal), `advertencia_datos_antiguos`, `items` ordenados por `prioridad`.
  - `PrediccionDTO` añade `monto_cobrado` (string decimal o `null`; desde R-008 el Excel ya no lo incluye). `score` es string decimal de 8 decimales. `factores_principales` = hasta 3 textos; `[]` → la UI y el Excel muestran "Sin factores de riesgo destacados". `gestion_estado` y `campania_asignada` salen `null` hasta CU-08 (día 5).
  - `ListaResumenDTO` (nuevo): `id`, `fecha_generacion`, `creada_en`, `modelo_version`, `horizonte_dias`, `top_k`, `total_items`.
  - Una lista guardada es inmutable (RN-04.5): sus ítems se devuelven aunque el socio tenga después `deleted_at`.
  - **R-008 (cambio de contrato):** `GenerarListaDTO` (cuerpo de `POST /listas`) acepta `nombre` opcional (`maxLength` 80): se recorta y debe quedar en 1..80 caracteres sin caracteres de control; vacío tras recortar, > 80, con caracteres de control o no string → `400 validation_error` sin guardar nada. Ausente o `null` → `"Lista del <d> <mmm> <aaaa>"` con la fecha de la lista (p. ej. `"Lista del 29 sep 2026"`). Se permiten nombres repetidos. `nombre` (string, requerido) se añade a `ListaPriorizadaDTO` y `ListaResumenDTO`; las listas anteriores a la migración `0006` reciben el nombre por defecto de su fecha.
  - **R-008 (Excel):** `GET /listas/{id}/excel` mantiene ruta, tipo y nombre de archivo; cambia el contenido: hojas `Socios prioritarios a contactar`, `Otros socios por vencer` y `Resumen`, con las columnas de la tabla de la pantalla (sin celular, score ni monto) → [12 §Excel](backend/12-modelo-y-listas.md#excel-cu-12). `PrediccionDTO` **conserva** `celular`, `score` y `monto_cobrado` (ya no los usa el Excel).
  - **R-005 (cambio de contrato):** `PrediccionDTO` ya no tiene `correo`; tiene `cedula` (string con el cero inicial, o `null` en listas antiguas con socios sin cédula). Ninguna respuesta de la API devuelve el correo (sigue en la base). Los socios sin cédula no entran en las listas nuevas. Los DTO de **respuesta** aceptan `horizonte_dias` 1..365 para leer listas antiguas; la entrada solo 1..31.
- `GET /sistema/estado`: `INICIALIZANDO` mientras migra CU-03; `LISTO` con `modelo_vigente`; `FALTAN_DATOS_HISTORICOS` si faltan los libros o la migración falló (el motivo solo va al log; se reintenta al reiniciar el backend, ADR-004).
- Límites propios (cargas): plantilla ≤ 5 MB y ≤ 500 filas con datos (R-007). Resto: `nombre` de campaña 1..120, `descripcion` ≤ 500 (decisión propia, 03 no la fija), `observaciones` ≤ 500, `responsable` ≤ 120; `horizonte_dias` 1..31 en `POST /listas` (defecto 30; antes 1..365, R-005), `top_k` ≥ 1 (defecto 25), `fecha_referencia` null = hoy de negocio (Ecuador, UTC−5: `hoy_en_negocio(clock.now())`); una fecha anterior a ese día → `422`.

### Cargas (CU-01, R-007)

Detalle del proceso en [backend/13-cargas](backend/13-cargas.md). Los DTOs son los publicados el día 1 (sin cambios de forma); se retiró el `501`.

- **`VistaPreviaCargaDTO`**: `filas_leidas` (filas con algún valor en A..N; O y P se ignoran), `filas_validas` (sin error; **incluye** las duplicadas), `filas_con_error`, `filas_duplicadas` (⊆ válidas), `vencimiento_desde`/`vencimiento_hasta` (mín./máx. de H entre las válidas, `null` si no hay), `errores` [`ErrorFilaDTO` {`fila` = número real de la fila en Excel, `columna` = letra A..M, `motivo`}], `puede_confirmar` = `filas_con_error == 0` y al menos una fila nueva (válida no duplicada).
- **`CargaDTO`**: `id`, `fecha_carga` (del reloj), `nombre_archivo` (solo el nombre base, ≤ 255), `filas_leidas`, `filas_guardadas` (= válidas − duplicadas), `filas_duplicadas`, `socios_enlazados` (socios existentes distintos que recibieron al menos una fila nueva), `avisos_enlace` (p. ej. `"Fila 22: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."`).
- Ningún `motivo` ni mensaje contiene valores de celdas (nombres, cédulas, celulares, correos).

Orden de comprobación y mensajes exactos (`error.message`):

| Orden | HTTP · `code` | Cuándo | Mensaje |
|---|---|---|---|
| 1 | 413 `payload_too_large` | Archivo > 5 MB (se leen como máximo 5 MB + 1 byte) | "El archivo supera el tamaño máximo permitido." |
| 0 | 400 `validation_error` | Sin campo `archivo` (validación de entrada, antes de leer) | Mensaje genérico de validación |
| 2 | 400 `validation_error` | Bytes que no son `.xlsx` o libro dañado | "El archivo está dañado o no es un .xlsx válido." |
| 2 | 400 `validation_error` | Sin hoja `Registros` (y sin hojas de meses) | "El archivo no tiene la hoja Registros." |
| 2 | 400 `validation_error` | Sin `Registros` y con hojas con nombre de mes | "El archivo tiene el formato antiguo de hojas mensuales; use la plantilla oficial de carga." |
| 2 | 400 `validation_error` | Títulos A..N de la fila 1 distintos de la plantilla oficial | "Los títulos de la hoja Registros no coinciden con la plantilla oficial." |
| 2 | 400 `validation_error` | Más de 500 filas con datos | "El archivo tiene más de 500 filas con datos; divídalo en varios archivos." |
| 3 | 409 `conflict` | Migración histórica (CU-03) no `COMPLETADA` | "La migracion del historico aun no se ha completado." |
| 4 | 422 `domain_rule_violated` | `POST /cargas` con alguna fila con error | "Hay filas con error; corrija el archivo y vuelva a subirlo." |
| 4 | 422 `domain_rule_violated` | `POST /cargas` sin filas nuevas (vacío o todo duplicado, incluida una segunda confirmación concurrente) | "El archivo no tiene filas nuevas para guardar." |

Un archivo ilegible da `400` aunque la migración esté pendiente (el archivo se lee antes de consultar el estado). La vista previa nunca devuelve `422`: los errores por fila van en `errores` con `200`.
