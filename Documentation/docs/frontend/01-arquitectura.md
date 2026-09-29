# Frontend · 01 · Arquitectura

React 19 · TypeScript estricto · Vite 8 · Tailwind CSS 4 · React Router 7 · Vitest + Testing Library + MSW · Playwright. Creado en R-001 (ver [ADR-001](../../adr/ADR-001-fastapi-react-postgresql.md)).

## Estructura

```
Frontend/src/
  main.tsx               arranque
  index.css              Tailwind + tokens de diseño (@theme): único archivo de estilos
  app/router.tsx         createBrowserRouter; monta las rutas de cada feature
  core/config.ts         VITE_API_BASE_URL (fallback "": mismo origen)
  core/http/             cliente HTTP único: http-client.ts (httpGet), api-error.ts (ApiError)
  features/{feature}/
    routes.tsx           rutas lazy (React.lazy + Suspense)
    pages/               componen y conectan con hooks
    hooks/               estado de servidor: carga, error, cancelación
    api/                 contrato con el backend y mapeo snake_case → camelCase
    components/          presentacionales, solo props
    types.ts
Frontend/e2e/            Playwright
```

Flujo en una sola dirección: `pages → hooks → api → core/http`. `components/` no importa hooks ni `api/`; `pages/` no importa `api/` ni `core/http`; ningún feature llama a `fetch` directamente (lo verifica `features/health/architecture.test.ts`).

## `core/http`

- `httpGet<T>(path, { signal })` antepone la base URL y parsea JSON.
- Respuesta no 2xx → `ApiError { status, message, body }`; `message` sale de `error.message` del formato único del backend.
- Error de red → `ApiError` con `status: 0` y mensaje genérico.
- Petición abortada → se propaga el `AbortError` original (no se envuelve).
- 2xx con JSON malformado → `ApiError`.
- Sin `localStorage`/`sessionStorage`, sin `console.log` de respuestas.

## Feature `health` (patrón de referencia)

| Capa | Archivo | Rol |
|---|---|---|
| types | `types.ts` | `Health = { status: "ok" \| "degraded"; database: "up" \| "down"; checkedAt: Date }` |
| api | `api/health-api.ts` | `getHealth(signal)`; mapea `checked_at` → `checkedAt`; un `503` con cuerpo de health válido se devuelve como `degraded` (no lanza); otros errores propagan `ApiError` |
| hooks | `hooks/useHealth.ts` | `{ data, error, isLoading, refetch }`; `AbortController` al desmontar; expone solo `error.message` |
| pages | `pages/HealthPage.tsx` | estados: cargando (`role="status"`), ok, degradado, error (`role="alert"` + "Reintentar") |
| components | `components/HealthStatusCard.tsx` | tarjeta presentacional |
| routes | `routes.tsx` | ruta `/`, lazy |

## Estilos

Tokens (colores `ok`/`degraded`, tipografía, radios) declarados una sola vez en `src/index.css` dentro de `@theme` y consumidos por nombre en clases Tailwind. No hay CSS fuera de `index.css`. Aún no existe `shared/ui/` ni `06-estilos-y-design-system.md`.

## Desarrollo local

`npm run dev` sirve en `http://localhost:5173` con proxy de Vite `/api` → `http://localhost:8000`. En Docker, nginx hace el mismo proxy (ver [10-docker.md](../backend/10-docker.md)).

## Pruebas

96 pruebas Vitest (unitarias de `core/http`, `api`, hooks, páginas y componentes, con red mockeada) y 1 E2E Playwright (`e2e/health.spec.ts`, `E2E_BASE_URL`, por defecto `http://localhost:8080`, requiere el stack levantado). Comandos en `Frontend/README.md`.
