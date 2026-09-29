# Frontend · 01 · Arquitectura

React 19 · TypeScript estricto · Vite 8 · Tailwind CSS 4 · React Router 7 · Vitest + Testing Library + MSW · Playwright. Creado en R-001 (ver [ADR-001](../../adr/ADR-001-fastapi-react-postgresql.md)).

## Estructura

```
Frontend/src/
  main.tsx               arranque (MSW en navegador solo con DEV y VITE_API_MOCKS=true)
  index.css              Tailwind + tokens de diseño (@theme): único archivo de estilos
  app/router.tsx         createBrowserRouter; ruta raíz con AppLayout y rutas hijas de cada feature
  core/config.ts         VITE_API_BASE_URL (fallback "": mismo origen), apiMocks
  core/http/             cliente HTTP único: http-client.ts, api-error.ts (ApiError)
  core/layout/AppLayout  header + nav (5 enlaces) + <main> con Suspense y <Outlet/>
  shared/ui/             componentes base sin lógica de negocio (no importan features/)
  mocks/                 MSW: handlers.ts (autodescubrimiento), server.ts (pruebas), browser.ts (dev)
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
- `httpPost<T>` y `httpPut<T>` envían JSON (`Content-Type: application/json`); `httpPostForm<T>(path, FormData)` envía multipart sin fijar `Content-Type`; `httpGetBlob(path)` devuelve un `Blob` (descarga del Excel).
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
| routes | `routes.tsx` | ruta `/salud`, lazy (antes `/`; movida en R-002) |

## Navegación (R-002)

| Ruta | Feature | Página |
|---|---|---|
| `/` (index) | `inicio` | "Inicio" |
| `/carga` | `carga` | "Carga de datos" |
| `/lista` | `lista` | "Lista priorizada" |
| `/campanias` | `campanias` | "Campañas" |
| `/dashboard` | `dashboard` | "Dashboard" |
| `/salud` | `health` | `HealthPage` (fuera del menú) |
| `*` | — | "Página no encontrada" |

Las páginas de negocio son placeholders con `<h1>` hasta sus días del cronograma, salvo Inicio y Carga (R-003, abajo). Cada feature expone ya su capa `api/` (`types.ts`, `api/<feature>-api.ts`, `api/<feature>-api.handlers.ts`) según el [contrato](../API_CONTRACT.md): `inicio` (estado del sistema, alertas), `carga` (vista previa y confirmación con `FormData` campo `archivo`), `lista` (generar, última, por id, Excel, sugerencias, gestiones), `campanias` (listar, crear, editar, inactivar; el tipo de `planes` excluye `"DIARIO"`) y `dashboard` (`?mes=YYYY-MM` opcional). Los decimales (`score`, `tasaRenovacion`) se mantienen como `string`; `modeloVigente.version` es `string` (`"v1"`).

### Inicio y Carga (R-003, con MSW)

| Feature | Archivos | Comportamiento |
|---|---|---|
| `inicio` | `hooks/useEstadoSistema.ts`, `components/EstadoSistemaPanel.tsx`, `pages/InicioPage.tsx` | Pide `GET /sistema/estado` (con `AbortController`). `INICIALIZANDO` → "Inicializando datos históricos" (`role="status"`); `FALTAN_DATOS_HISTORICOS` → aviso de revisar la carpeta configurada (sin rutas); `LISTO` → "Sistema listo", versión del modelo y fechas en `es-EC`, o "Sin modelo vigente". Error `501`/`500` → `ErrorAlert` con "Reintentar". |
| `carga` | `hooks/useCarga.ts`, `components/{VistaPreviaCarga,ResumenCarga}.tsx`, `pages/CargaPage.tsx` | Estados `inicial` → `validando` → `vista-previa` → `enviando` → `confirmada`. Input `.xlsx` con etiqueta; otro tipo → mensaje local sin llamar a la API. Vista previa con conteos y `DataTable` de errores (`fila`/`columna`/`motivo`); "Confirmar" deshabilitado si hay errores, si `puedeConfirmar` es `false` (todo duplicado) o mientras envía (sin doble envío). Resumen tras confirmar: `filasGuardadas`, `filasDuplicadas`, `avisosEnlace`; `400`/`409`/`422` → `ErrorAlert` con el mensaje del servidor. Cambiar de archivo limpia la vista previa. |

El resumen de carga no muestra aún `filasLeidas` ni `fechaCarga` (el criterio no lo exige). `router.edge.test.tsx`: la ruta `/` ahora pide `sistema/estado` en vez de `/health`.

## `shared/ui`

| Componente | Contrato |
|---|---|
| `DataTable<T>` | `columns: {key, header, render?}[]`, `rows`, `getRowKey`, `emptyMessage`, `caption` |
| `RiskBadge` | `nivel: "ALTO" \| "MEDIO" \| "BAJO"` → "Alto"/"Medio"/"Bajo" con los tokens `risk-high`/`risk-medium`/`risk-low` |
| `LoadingIndicator` | `role="status"`, texto accesible configurable |
| `ErrorAlert` | `role="alert"`, `message`, `onRetry?` → botón "Reintentar" |
| `Modal` | `open`, `title`, `onClose`; `role="dialog"`, `aria-modal`, `aria-labelledby`; cierra con `Escape` y "Cerrar"; foco al abrir |

## Estilos

Tokens (colores `ok`/`degraded`, `risk-high`/`risk-medium`/`risk-low`, tipografía, radios) declarados una sola vez en `src/index.css` dentro de `@theme` y consumidos por nombre en clases Tailwind. No hay CSS fuera de `index.css`. Aún no existe `06-estilos-y-design-system.md`.

## MSW (datos simulados)

- `mocks/handlers.ts` reúne con `import.meta.glob("../features/*/api/*.handlers.ts", { eager: true })` los `handlers` exportados por cada feature: un feature nuevo solo añade su archivo.
- Pruebas: `mocks/server.ts` (`setupServer`), iniciado en `src/test/setup.ts` con `onUnhandledRequest: "error"` (una petición sin handler hace fallar el test).
- Navegador: `mocks/browser.ts` (`setupWorker`), importado dinámicamente en `main.tsx` solo si `import.meta.env.DEV && config.apiMocks` (`VITE_API_MOCKS=true`), antes de montar. El build de producción no incluye el worker y la imagen Docker borra `dist/mockServiceWorker.js`.
- Los datos simulados son ficticios (sin cédulas reales). Limitación conocida: el handler de `GET /gestiones` devuelve `[]` sin filtro, mientras el backend responde `400`; solo afecta a los datos simulados.

## Desarrollo local

`npm run dev` sirve en `http://localhost:5173` con proxy de Vite `/api` → `http://localhost:8000`. Con `VITE_API_MOCKS=true npm run dev` la API se simula con MSW (sin backend). En Docker, nginx hace el mismo proxy (ver [10-docker.md](../backend/10-docker.md)).

## Pruebas

270 pruebas Vitest al cierre de R-003 (unitarias de `core/http`, `api` de cada feature contra MSW, hooks, layout, router, `shared/ui`, páginas y componentes) y 1 E2E Playwright (`e2e/health.spec.ts` sobre `/salud`, `E2E_BASE_URL`, por defecto `http://localhost:8080`, requiere el stack levantado). Comandos en `Frontend/README.md`.
