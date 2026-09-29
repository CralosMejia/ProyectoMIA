---
paths:
  - "Frontend/src/**/*.ts"
  - "Frontend/src/**/*.tsx"
  - "Frontend/src/**/*.css"
  - "Frontend/*.json"
  - "Frontend/vite.config.ts"
  - "Frontend/eslint.config.js"
---

# Reglas — Frontend (React SPA feature-first)

Stack: React 18+ · TypeScript estricto · Vite · React Router · Tailwind · Vitest + Testing Library · Playwright (E2E).

Referencia larga: `Documentation/docs/frontend/01-arquitectura.md`, `06-estilos-y-design-system.md`.

## Estructura

```
src/
  features/{feature}/
    routes.tsx      ← rutas del feature (lazy)
    api/            ← llamadas a la API (servicios)
    hooks/          ← hooks del feature que consumen los servicios
    components/     ← presentacionales
    pages/          ← componentes de ruta (smart)
    types.ts        ← tipos del feature
  core/             ← auth, http, layout, config: transversal, una sola instancia
  shared/ui/        ← componentes visuales reutilizables entre features
```

### Capas y responsabilidades

Dentro de cada feature el flujo es de una sola dirección: `pages` → `hooks` → `api` → `core/http`. Cada capa solo conoce a la siguiente.

| Capa | Responsabilidad única | Nunca hace |
|---|---|---|
| `components/` | Pintar a partir de props y emitir eventos | Llamar hooks de datos, HTTP, leer el contexto de auth |
| `pages/` | Componer componentes y conectar con los hooks del feature | Llamar a `api/` o `fetch` directamente, lógica de transformación |
| `hooks/` | Estado de pantalla y de servidor: carga, error, caché, cancelación | JSX, acceso directo a `fetch` |
| `api/` | Contrato con el backend: URLs, mapeo request/response ↔ `types.ts` | Estado de React, lógica de UI |
| `core/http` | Cliente HTTP único: base URL, token, refresh, errores estructurados | Conocer features concretos |

- Un feature no importa internals de otro feature; lo compartido sube a `shared/` o `core/`.
- Los tipos que devuelve el backend se mapean en `api/`; los componentes no dependen del formato crudo de la API.

- Solo componentes funcionales y hooks. Sin componentes de clase.
- Rutas de feature **lazy-loaded** con `React.lazy` + `Suspense`.
- `useMemo`/`useCallback`/`React.memo` solo donde haya un problema de rendimiento medido, no por defecto.

## Estado y asincronía

- Estado local con `useState`/`useReducer`; estado compartido de interfaz con Context acotado al subárbol que lo necesita.
- Estado de servidor (HTTP, caché, reintentos, cancelación) a través de los hooks del feature; cancelación con `AbortController`.
- Sin librería de estado global hasta que exista una necesidad real, documentada en un ADR.
- Ningún componente llama al cliente HTTP ni a `fetch` directamente: siempre a través del servicio/hook del feature.

## Seguridad

- El access token vive **solo en memoria** (contexto de auth en `core/auth`). `localStorage` y `sessionStorage` están prohibidos para tokens.
- El refresh token viaja en cookie `HttpOnly`; el cliente nunca lo lee (`credentials: 'include'`).
- El cliente HTTP de `core/http` añade la cabecera de autorización y maneja el refresh ante `401` en un único punto.
- Rutas privadas protegidas con un componente guard (`<RequireAuth>`).
- `dangerouslySetInnerHTML` prohibido salvo con contenido saneado (DOMPurify) y justificación escrita en el mismo archivo.
- Nunca registrar tokens ni datos personales en la consola.
- Variables `VITE_*` son públicas: jamás contienen secretos.

## Formularios

- Formularios controlados (o React Hook Form + esquema de validación) para autenticación y todo lo transaccional.
- La validación de cliente nunca sustituye la del servidor.
- Los errores del servidor se muestran junto al campo o en un banner, con el mensaje del error estructurado.
- Valores numéricos exactos: parseo validado y transporte como `string` decimal, nunca `parseFloat` sobre texto libre para dinero o cantidades.

## Estilos

- Los tokens de diseño (color, tipografía, espaciado, radios) se declaran en un único punto (config de Tailwind / variables CSS) y se consumen por nombre.
- No se escribe CSS custom fuera del archivo de estilos global.
- Una clase o composición repetida entre features se convierte en componente de `shared/ui/`. Nunca se duplica.
- Si existe una maqueta de referencia, es de **solo lectura**: se copian clases, tokens y medidas; nunca su lógica, su estado ni sus datos de ejemplo.

## Pruebas

- Vitest + Testing Library; se prueba el comportamiento visible (roles, textos), no detalles de implementación.
- Cada servicio que llama a la API tiene pruebas con la red mockeada (MSW o `fetch` mockeado).
- Cada formulario tiene pruebas de validación y de flujo.
- Cada guard tiene prueba de redirección.
- Los componentes con lógica de negocio visible tienen pruebas de estado.
- E2E con Playwright para los flujos críticos del producto.

## Comandos (desde `Frontend/`)

- Build (incluye `tsc`): `npm run build` · Lint: `npm run lint` · Pruebas: `npm test` · E2E: `npx playwright test`

## Finalización

Build correcto (sin errores de TypeScript), lint sin errores, suite en verde, y el componente reutiliza `shared/ui/` en vez de duplicar estilos.

## Prohibido

- Modificar la maqueta de referencia si existe.
- Guardar tokens en almacenamiento del navegador.
- Duplicar estilos entre features.
- `any` o `@ts-ignore` sin justificación escrita en el mismo archivo.
- Llamar a la API desde un componente.
