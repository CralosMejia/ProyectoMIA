import { createElement, lazy } from 'react'
import type { RouteObject } from 'react-router-dom'

// Pagina lazy; el Suspense lo aporta AppLayout (core/layout). createElement evita declarar un
// componente local en un archivo que solo exporta rutas (react-refresh/only-export-components).
export const campaniasRoutes: RouteObject[] = [
  { path: 'campanias', element: createElement(lazy(() => import('./pages/CampaniasPage'))) },
]
