# Backend · 10 · Docker y entorno local

Stack local definido en `compose.yaml` (raíz). Creado en R-001.

## Servicios

| Servicio | Imagen | Puerto publicado | Health check | Depende de |
|---|---|---|---|---|
| `db` | `postgres:16.15-alpine`, volumen nombrado `pgdata` | `127.0.0.1:5432` | `pg_isready` | — |
| `backend` | `Backend/Dockerfile` → `backend:dev` | `127.0.0.1:8000` | `GET /api/v1/health` (falla si responde 503) | `db` healthy |
| `frontend` | `Frontend/Dockerfile` → `frontend:dev` | `127.0.0.1:8080` | `GET /healthz` (nginx) | `backend` healthy |

Los puertos se publican solo en loopback. Todas las variables obligatorias usan `${VAR:?}`: compose falla si falta alguna.

## Variables (`.env`, no versionado; plantilla en `.env.example`)

| Variable | Uso |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | inicialización del servicio `db` |
| `DATABASE_URL` | backend; host `db` dentro de la red de compose; driver `postgresql+psycopg://` |
| `CORS_ORIGINS` | orígenes explícitos separados por coma |
| `APP_ENV` | `development` · `test` · `production` |
| `TEST_DATABASE_URL` | pytest desde el host (`127.0.0.1:5432`) |

La contraseña debe ser **URL-safe** (p. ej. hex): se inserta sin codificar en `DATABASE_URL` y `TEST_DATABASE_URL`.

## Imagen del Backend

- Multi-stage sobre `python:3.12.13-slim-bookworm`: dependencias instaladas en `build`, copiadas a `runtime`.
- Runtime sin herramientas de desarrollo ni `pip`; usuario `app` (UID 10001).
- `APP_ENV=production` por defecto en la imagen.
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-server-header`, sin `--reload`.
- `.dockerignore` excluye `.venv`, `__pycache__`, `tests`, `.git`, `.env`.
- Sin `DATABASE_URL` el contenedor sale con código ≠ 0 y el log nombra la variable sin valores.

## Imagen del Frontend

- Build con `node:22.23.2-alpine` (`npm run build`), runtime `nginxinc/nginx-unprivileged:1.29.1-alpine`, usuario `nginx`, puerto 8080. La imagen final no lleva `node_modules` ni `src/`.
- `Frontend/nginx.conf`: fallback SPA a `index.html`; `/assets/` inexistente → 404; proxy `/api/` → `http://backend:8000` (resolución DNS de Docker en tiempo de petición); `X-Forwarded-For` = `$remote_addr` (descarta el del cliente); `server_tokens off`; cabeceras `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`.

## Uso

```bash
cp .env.example .env          # sustituir los valores marcador
docker compose up -d --build
curl http://localhost:8000/api/v1/health   # backend directo
curl http://localhost:8080/api/v1/health   # vía nginx
```

`docker compose stop db` → el backend sigue vivo y `/api/v1/health` responde `503`.

## Limitaciones conocidas y pendientes

- **S24:** `frontend` espera a `backend` healthy y el health check del backend falla si la BD no responde; si la BD no está disponible al arrancar, el frontend no arranca.
- **S21:** imágenes base fijadas por versión, aún no por digest.
- **S18:** al poner TLS delante, propagar `X-Forwarded-Proto` real y configurar hosts de confianza.
- **S19:** añadir CSP y HSTS; verificar que el build no publica sourcemaps.
- **S23:** con la primera migración Alembic, rol de BD sin superusuario para la app y rol separado para migraciones.
- CI/CD aún no existe (`11-ci-cd.md` pendiente).
