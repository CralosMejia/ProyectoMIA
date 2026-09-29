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
| 401 | `unauthorized` | Reservado (no hay autenticación todavía). |
| 403 | `forbidden` | Reservado. |
| 404 | `not_found` | Ruta o recurso inexistente. |
| 405 | `method_not_allowed` | Método no permitido. |
| 409 | `conflict` | Reservado. |
| 422 | `domain_rule_violated` | Excepción de dominio (`DomainError`); `message` es el de la excepción, que debe ser apto para el usuario. |
| 500 | `internal_error` | Error no controlado. Mensaje genérico; el detalle solo en el log del servidor. |

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
