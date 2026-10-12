# Backend · 10 · Docker y entorno local

Stack local definido en `compose.yaml` (raíz). Creado en R-001.

## Servicios

| Servicio | Imagen | Puerto publicado | Health check | Depende de |
|---|---|---|---|---|
| `db` | `postgres:16.15-alpine`, volumen nombrado `pgdata` | `127.0.0.1:${DB_PORT:-5432}` | `pg_isready` | — |
| `db-roles` | `postgres:16.15-alpine` (un solo uso, `restart: "no"`) | — | — | `db` healthy |
| `migrate` | `backend:${IMAGE_TAG:-dev}` (`pull_policy: never`, no construye) | — | desactivado | `db` healthy, `db-roles` `service_completed_successfully` |
| `backend` | `Backend/Dockerfile` → `backend:${IMAGE_TAG:-dev}` | `127.0.0.1:${BACKEND_PORT:-8000}` | `GET /api/v1/health` (falla si responde 503) | `db` healthy, `migrate` `service_completed_successfully` |
| `frontend` | `Frontend/Dockerfile` → `frontend:${IMAGE_TAG:-dev}` | `127.0.0.1:${FRONTEND_PORT:-8080}` | `GET /healthz` (nginx) | `backend` healthy |

Los puertos se publican solo en loopback. Puertos y etiqueta de imagen son configurables desde R-007; sin definirlos, el stack principal sigue en 5432/8000/8080 con imágenes `:dev`. Todas las variables obligatorias usan `${VAR:?}`: compose falla si falta alguna.

**`migrate`** (R-002): ejecuta `alembic upgrade head` con la misma imagen del backend y termina (`restart: "no"`). Solo `backend` construye la imagen; `migrate` la reutiliza. El backend arranca únicamente si `migrate` salió con código 0, y nunca migra por sí mismo ([ADR-004](../../adr/ADR-004-migracion-datos-al-arrancar.md)). Con la base ya migrada, un nuevo `up` vuelve a terminar en 0 sin cambios. Esquema: [09-esquema-base-de-datos.md](09-esquema-base-de-datos.md). Desde R-013 se conecta con el rol **propietario** (`MIGRATE_DATABASE_URL`; sin ella, `DATABASE_URL`, solo en la transición).

**`db-roles`** (R-013, S23): ejecuta `Backend/db/roles/aplicar-roles.sh` (montado `:ro`) en cada `up`, antes de `migrate`, y termina. Crea o actualiza el rol de la aplicación `APP_DB_USER` (por defecto `mtabolic_app`: sin superusuario, sin `CREATE` en `public`, sin `DELETE`/`TRUNCATE`, `alembic_version` solo lectura) y fija los privilegios por defecto para las tablas que creen migraciones futuras (`Backend/db/roles/permisos.sql`). Idempotente; sirve para volúmenes nuevos y existentes. La contraseña llega a `psql` como variable y no se registra (`log_statement` desactivado en esa sesión). Valida el nombre del rol (`^[a-z_][a-z0-9_]{0,62}$`, distinto de `POSTGRES_USER`). **Transición:** sin `APP_DB_PASSWORD` solo avisa y termina en 0; todo sigue con el propietario. Detalle: [ADR-012](../../adr/ADR-012-rol-de-aplicacion-sin-superusuario.md), [09 §Roles](09-esquema-base-de-datos.md).

**Libros históricos:** `backend` monta `${HISTORICO_DIR}` en `/data/historico` en **solo lectura** (`:ro`) y recibe `HISTORICO_PATH=/data/historico` (R-004). Solo se leen los `*Control*Gym*.xlsx` de esa carpeta (sin subcarpetas); la plantilla de carga u otros `.xlsx` se ignoran. Con la base vacía, el backend migra el histórico y entrena el modelo v1 en segundo plano al arrancar (CU-03, ADR-004); `/health` responde mientras tanto. Detalle: [12-modelo-y-listas.md](12-modelo-y-listas.md).

## Variables (`.env`, no versionado; plantilla en `.env.example`)

| Variable | Uso |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | inicialización del servicio `db` |
| `DATABASE_URL` | backend; host `db` dentro de la red de compose; driver `postgresql+psycopg://`. Con S23 activo, con el **rol de la aplicación** |
| `MIGRATE_DATABASE_URL` | R-013; `migrate`, con el rol **propietario** (`POSTGRES_USER`). Sin ella, `migrate` usa `DATABASE_URL` (transición) |
| `APP_DB_USER`, `APP_DB_PASSWORD` | R-013; rol de la aplicación que crea `db-roles` (por defecto `mtabolic_app`). Contraseña URL-safe distinta de `POSTGRES_PASSWORD`; vacía → S23 sin activar |
| `CORS_ORIGINS` | orígenes explícitos separados por coma; también los únicos orígenes aceptados en escrituras (R-013, S1). En operación, **solo** el del frontend |
| `HOSTS_PERMITIDOS` | opcional (R-013, S1); nombres aceptados en la cabecera `Host`, por defecto `localhost,127.0.0.1`. Otro `Host` → `400` ([ADR-013](../../adr/ADR-013-proteccion-host-y-origin.md)) |
| `APP_ENV` | `development` · `test` · `production` |
| `TEST_DATABASE_URL` | pytest desde el host (`127.0.0.1:5432`), base **`app_db_test`**: las pruebas de migración abortan si el nombre no termina en `_test` |
| `HISTORICO_DIR` | carpeta del host con los libros `Control Gym *.xlsx`; obligatoria para `backend` (montada `:ro` en `/data/historico`) |
| `HISTORICO_PATH` | ruta de los libros **dentro** del contenedor; la fija `compose.yaml` a `/data/historico` (valor por defecto) |
| `MIGRAR_HISTORICO_AL_ARRANCAR` | `true` por defecto; `false` desactiva la migración de CU-03 al arrancar (pruebas) |
| `DB_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` | opcionales (R-007); puertos publicados en `127.0.0.1`, por defecto `5432`/`8000`/`8080` |
| `IMAGE_TAG` | opcional (R-007); etiqueta de `backend:`/`frontend:`, por defecto `dev`; el stack E2E usa `e2e` para no pisar las imágenes del principal |
| `IPS_PERMITIDAS` | opcional (R-011, CU-00); IPs o rangos CIDR separados por coma. Por defecto `127.0.0.1,::1,<FRONTEND_IP>`. Vacío, `*` o un valor inválido → el backend no arranca (el error no muestra el valor) |
| `RED_INTERNA_SUBNET`, `FRONTEND_IP` | opcionales (R-011); subred fija de la red `interna` e IP fija del contenedor `frontend` dentro de ella. Se definen **juntas** |
| `REENTRENAMIENTO_AUTOMATICO` | `true` por defecto (R-011); `false` no arranca el planificador de CU-02 (pruebas) |
| `REENTRENAR_MIN_CICLOS_NUEVOS`, `REENTRENAR_MIN_COBERTURA_VENCIMIENTO`, `REENTRENAR_MIN_CASOS_POR_CLASE`, `REENTRENAR_MESES_COMPARACION` | opcionales (R-011); criterios de CU-02, por defecto `150` / `0.60` / `20` / `3`. `compose.yaml` los pasa al backend |

La contraseña debe ser **URL-safe** (p. ej. hex): se inserta sin codificar en `DATABASE_URL` y `TEST_DATABASE_URL`.

## Imagen del Backend

- Multi-stage sobre `python:3.12.13-slim-bookworm`: dependencias instaladas en `build`, copiadas a `runtime`.
- Runtime sin herramientas de desarrollo ni `pip`; usuario `app` (UID 10001).
- `APP_ENV=production` por defecto en la imagen.
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-server-header`, sin `--reload`.
- `.dockerignore` excluye `.venv`, `__pycache__`, `tests`, `.git`, `.env`.
- Copia `alembic.ini` y `alembic/` a `/srv` (los usa el servicio `migrate`).
- Sin `DATABASE_URL` el contenedor sale con código ≠ 0 y el log nombra la variable sin valores.

## Imagen del Frontend

- Build con `node:22.23.2-alpine` (`npm run build`; después borra `dist/mockServiceWorker.js`: MSW nunca llega a la imagen), runtime `nginxinc/nginx-unprivileged:1.29.1-alpine`, usuario `nginx`, puerto 8080. La imagen final no lleva `node_modules` ni `src/`.
- `Frontend/nginx.conf`: fallback SPA a `index.html`; `/assets/` inexistente → 404; proxy `/api/` → `http://backend:8000` (resolución DNS de Docker en tiempo de petición); `X-Forwarded-For` = `$remote_addr` (descarta el del cliente); `server_tokens off`; cabeceras `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`.
- Desde R-013 (revisión de seguridad única): un `server` `default_server` responde `444` (cierra sin respuesta) a cualquier `Host` que no sea `localhost` o `127.0.0.1` (DNS rebinding, [ADR-013](../../adr/ADR-013-proteccion-host-y-origin.md)); `Content-Security-Policy` solo `'self'` (sin `unsafe-inline`, `frame-ancestors 'none'`, `object-src 'none'`), `Permissions-Policy` restrictiva, `Cross-Origin-Opener-Policy` y `Cross-Origin-Resource-Policy` `same-origin`, `Cache-Control: no-store` en `/api/`. Las cabeceras se declaran a nivel `server` (ningún `location` añade las suyas, para heredarlas todas). `client_max_body_size` 1m en general y 6m en `/api/v1/cargas`.

## Uso

```bash
cp .env.example .env          # sustituir los valores marcador
docker compose up -d --build
curl http://localhost:8000/api/v1/health   # backend directo (única ruta exenta del filtro de IP)
curl http://localhost:8080/api/v1/health   # vía nginx
curl http://localhost:8080/api/v1/sistema/estado   # el resto de la API, siempre por 8080
```

`docker compose stop db` → el backend sigue vivo y `/api/v1/health` responde `503`.

### Red interna y acceso por IP (R-011, CU-00)

- El backend filtra por la IP **de la conexión** (no lee `X-Forwarded-For` ni `Forwarded`); solo `GET /api/v1/health` está exento. IP no autorizada → `403 forbidden` con el formato único de error, también en `/docs` y `/openapi.json` ([ADR-010](../../adr/ADR-010-acceso-por-ip-detras-de-nginx.md)).
- Dentro de Docker el backend ve la IP del contenedor nginx, no la del navegador. Por eso la red `interna` tiene subred fija y `frontend` una IP fija (`ipv4_address`), autorizada por defecto. Valores por defecto: stack principal `172.30.0.0/24` con frontend `172.30.0.10`; un `.env` que define `IMAGE_TAG` y/o `DB_PORT` (como el del stack E2E) cambia el tercer octeto (`10`, `20` o `120`; el E2E queda en `172.30.120.0/24` y `.10`) para que las dos subredes no choquen.
- **Consecuencia:** desde el host, el backend por 8000 (u 8001 en E2E) responde `403` salvo `/health`; la aplicación y la API se usan por 8080 (u 8081).
- Verificación: `docker run --rm --network mtabolic-e2e_interna curlimages/curl` contra `http://backend:8000/api/v1/sistema/estado` → `403` y contra `/api/v1/health` → `200`.
- **No implementado:** abrir la aplicación a otro PC de la red. Todos los navegadores llegan al backend con la IP de nginx, así que exigiría filtrar también en nginx y publicar el puerto fuera de `127.0.0.1`.

Operación en el PC del gimnasio (instalación, libros, variables, reentrenamiento manual con `docker compose exec backend python -m app.cli reentrenar`, respaldo y restauración): [Backend/README §Operación en el PC del gimnasio](../../../Backend/README.md#operación-en-el-pc-del-gimnasio-d6-op-01).

Primer arranque desde cero (R-004): `docker compose down -v && docker compose up -d --build` → `migrate` termina con 0 → `GET /api/v1/sistema/estado` pasa de `INICIALIZANDO` a `LISTO` (unos 5 s con los libros reales). `docker compose restart backend` no vuelve a migrar. Si el estado queda en `FALTAN_DATOS_HISTORICOS`, se corrige `HISTORICO_DIR` y se reinicia el backend. Pasos: `Backend/README.md` §Primer arranque.

Reinicio de la base principal a solo histórico (R-008): scripts `scripts/reiniciar-base-historica.ps1` / `.sh`, con `-p proyectofinal` fijo y confirmación `BORRAR`; desde R-013 esperan `LISTO` por `FRONTEND_PORT` → [comandos/reiniciar-base-historica.md](../../comandos/reiniciar-base-historica.md).

Respaldo y restauración (R-013, D7-BD-01): `scripts/respaldar-base.{sh,ps1}` y `scripts/restaurar-base.{sh,ps1}`, lista blanca `proyectofinal`/`mtabolic-e2e`/`mtabolic-limpia`, restauración solo a base nueva → [comandos/respaldo-y-restauracion.md](../../comandos/respaldo-y-restauracion.md).

### Instalación limpia (R-013, D7-OP-01)

Tercer stack efímero `mtabolic-limpia` para comprobar una instalación desde cero con los libros **reales** y S23 activo, sin tocar el principal ni el e2e:

```bash
cp .env.limpia.example .env.limpia   # no versionado; contraseñas URL-safe propias y HISTORICO_DIR real
docker compose -p mtabolic-limpia --env-file .env.limpia up -d --build
curl http://localhost:8082/api/v1/sistema/estado   # LISTO
docker compose -p mtabolic-limpia --env-file .env.limpia down -v   # al terminar
```

`.env.limpia.example`: `DB_PORT=5434`, `BACKEND_PORT=8002`, `FRONTEND_PORT=8082`, `IMAGE_TAG=limpia`, `RED_INTERNA_SUBNET=172.31.0.0/24`, `FRONTEND_IP=172.31.0.10`, `CORS_ORIGINS=http://localhost:8082`, `POSTGRES_DB=app_db_limpia`. Resultado en R-013: `db-roles` y `migrate` en 0, 1.410 socios y 2.748 membresías, v1 con las mismas métricas que el del principal, lista de hoy `201` y Excel `200`, backend conectado como `mtabolic_app`.

### Stack E2E aislado (R-007)

Segundo stack con base, volumen, red e imágenes propios y libros históricos **sintéticos**, para confirmar cargas de prueba y correr el E2E sin tocar la base con datos reales (en ella no se pueden borrar físicamente socios ficticios). En el stack principal solo se usa la vista previa de la carga (no guarda) y la lista/Excel; confirmar allí queda a decisión del usuario.

```bash
cp .env.e2e.example .env.e2e   # no versionado; contraseña de prueba URL-safe, distinta de la del principal
docker compose -p mtabolic-e2e --env-file .env.e2e up -d --build
curl http://localhost:8081/api/v1/sistema/estado   # espera LISTO (migración sintética y modelo v1); por 8001 da 403 desde R-011
# App en http://localhost:8081 · PostgreSQL en 127.0.0.1:5433 · base app_db_e2e
docker compose -p mtabolic-e2e --env-file .env.e2e down -v   # -v borra solo el volumen mtabolic-e2e_pgdata
```

- `.env.e2e.example` (versionado, solo marcadores): `DB_PORT=5433`, `BACKEND_PORT=8001`, `FRONTEND_PORT=8081`, `IMAGE_TAG=e2e`, `CORS_ORIGINS=http://localhost:8081`, `HISTORICO_DIR=./Backend/tests/fixtures/historico`. `.env.e2e` está en `.gitignore`.
- Siempre con `-p mtabolic-e2e`: sin él, `down -v` actuaría sobre el stack principal.
- Operar desde una shell **sin** el `.env` principal cargado: las variables exportadas en la shell ganan a `--env-file`.
- Los E2E (carga → lista → Excel y los posteriores; desde R-011 también alertas → Seguimiento → Dashboard; desde R-013 el escenario principal carga → lista → gestión → resultado → dashboard, 5 en total) se ejecutan contra este stack: [Frontend/README](../../../Frontend/README.md).
- Ensayo de la demostración (R-013): `scripts/ensayo-demo-e2e.{sh,ps1}` desplaza fechas solo en este stack → [comandos/ensayo-demo-e2e.md](../../comandos/ensayo-demo-e2e.md).
- `.env.e2e.example` incluye desde R-013 las variables de S23 con marcadores.
- El `OMITIDO` del reentrenamiento y el comando manual se prueban solo aquí (`docker compose -p mtabolic-e2e --env-file .env.e2e exec backend python -m app.cli reentrenar`); en el stack principal no se ejecuta `reentrenar` sin decisión del usuario.

## Limitaciones conocidas y pendientes

- **S24:** `frontend` espera a `backend` healthy y el health check del backend falla si la BD no responde; si la BD no está disponible al arrancar, el frontend no arranca.
- **S21:** imágenes base fijadas por versión, aún no por digest.
- **S18 / TLS futuro:** al poner TLS delante, propagar `X-Forwarded-Proto` real y configurar hosts de confianza; el filtro de `Origin` compara con `scope["scheme"]`, que pasaría a `https` ([ADR-013](../../adr/ADR-013-proteccion-host-y-origin.md)).
- **S19:** CSP añadida en R-013; HSTS queda para cuando haya TLS. Verificar que el build no publica sourcemaps.
- **S23 (cerrado en R-013):** la app usa `mtabolic_app` sin superusuario y `migrate` el propietario ([ADR-012](../../adr/ADR-012-rol-de-aplicacion-sin-superusuario.md)). **Residual:** el propietario `POSTGRES_USER` sigue siendo superusuario del clúster (imagen oficial).
- **S5:** el filtro por IP solo es efectivo mientras los puertos se publiquen en `127.0.0.1`; abrirlos a la red anula CU-00 ([ADR-010](../../adr/ADR-010-acceso-por-ip-detras-de-nginx.md)).
- **S10:** dependencias fijadas por versión pero sin lockfile de Python; `pip-audit`/`npm audit` no se ejecutaron en R-013 (sin red).
- **S26:** en producción `CORS_ORIGINS` debe listar solo el origen del frontend.
- CI/CD aún no existe (`11-ci-cd.md` pendiente).
