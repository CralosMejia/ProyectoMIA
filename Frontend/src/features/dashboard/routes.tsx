import { createElement, lazy } from 'react'
import type { RouteObject } from 'react-router-dom'

// Pagina lazy; el Suspense lo aporta AppLayout (core/layout). createElement evita declarar un
// componente local en un archivo que solo exporta rutas (react-refresh/only-export-components).
export const dashboardRoutes: RouteObject[] = [
  { path: 'dashboard', element: createElement(lazy(() => import('./pages/DashboardPage'))) },
]
