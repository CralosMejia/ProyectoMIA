# Frontend

SPA React + TypeScript + Vite + Tailwind, organizada por features (`pages → hooks → api → core/http`). Arquitectura: `../Documentation/docs/frontend/01-arquitectura.md`.

## Requisitos

Node 22 LTS. Para ver datos reales, el Backend en `http://localhost:8000` (el servidor de desarrollo hace proxy de `/api`).

## Comandos (desde `Frontend/`)

| Qué | Comando |
|---|---|
| Instalar | `npm install` |
| Desarrollo | `npm run dev` (http://localhost:5173) |
| Desarrollo con API simulada (MSW, sin backend) | `VITE_API_MOCKS=true npm run dev` |
| Build (incluye `tsc`) | `npm run build` |
| Lint | `npm run lint` |
| Pruebas | `npm test` |
| E2E | `npx playwright test` (requiere el stack levantado; `E2E_BASE_URL`, por defecto `http://localhost:8080`) |

La primera vez que se ejecute Playwright: `npx playwright install chromium`.

### E2E carga → lista → Excel (`e2e/carga-lista-excel.spec.ts`)

Confirma una carga de socios ficticios, así que **solo** se ejecuta contra el stack aislado `mtabolic-e2e` (base propia con libros sintéticos). Contra el stack principal (`8080`) se salta solo, para no dejar datos de prueba en la base con datos reales.

```bash
# desde la raíz, en una shell sin el .env principal cargado
cp .env.e2e.example .env.e2e     # la primera vez; poner una contraseña de prueba
docker compose -p mtabolic-e2e --env-file .env.e2e up -d --build
curl http://localhost:8001/api/v1/sistema/estado   # esperar LISTO

# desde Frontend/
E2E_BASE_URL=http://localhost:8081 npx playwright test
# PowerShell: $env:E2E_BASE_URL="http://localhost:8081"; npx playwright test

# al terminar (desde la raíz; siempre con -p mtabolic-e2e)
docker compose -p mtabolic-e2e --env-file .env.e2e down -v
```

La plantilla se genera en cada ejecución con `exceljs` (`devDependency`) y cédulas únicas, así que la prueba se puede repetir sin `down -v`. Tarda unos 10 s. Detalle del stack: `Documentation/docs/backend/10-docker.md` §Stack E2E aislado.

### E2E campañas → gestión (`e2e/campanias-gestion.spec.ts`)

Crea una campaña y una gestión, así que sigue la misma regla: **solo** contra el stack aislado (`E2E_BASE_URL=http://localhost:8081`, mismos comandos de arriba); contra `8080` se salta solo. Recorre: Campañas (3 de ejemplo, crea una) → Lista (genera, "Gestionar", crea la gestión, registra el resultado hasta "Cerrada") → Excel con la columna "Gestión". Con el stack aislado, `npx playwright test` ejecuta los 3 E2E (`health`, `carga-lista-excel`, `campanias-gestion`); contra `8080` solo `health`.

## Variables

`VITE_API_BASE_URL` (opcional, por defecto vacío = mismo origen). `VITE_API_MOCKS` (opcional; solo el valor exacto `true` activa MSW en el navegador, y solo en desarrollo). Las variables `VITE_*` son públicas: nunca contienen secretos.

## Docker

Imagen nginx sin privilegios en el puerto 8080 con proxy `/api/` → `backend:8000`. Se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.
