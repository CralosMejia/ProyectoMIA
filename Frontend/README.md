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

## Variables

`VITE_API_BASE_URL` (opcional, por defecto vacío = mismo origen). `VITE_API_MOCKS` (opcional; solo el valor exacto `true` activa MSW en el navegador, y solo en desarrollo). Las variables `VITE_*` son públicas: nunca contienen secretos.

## Docker

Imagen nginx sin privilegios en el puerto 8080 con proxy `/api/` → `backend:8000`. Se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.
