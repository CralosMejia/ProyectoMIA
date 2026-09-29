import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { AppLayout } from '../core/layout/AppLayout'
import { campaniasRoutes } from '../features/campanias/routes'
import { cargaRoutes } from '../features/carga/routes'
import { dashboardRoutes } from '../features/dashboard/routes'
import { healthRoutes } from '../features/health/routes'
import { inicioRoutes } from '../features/inicio/routes'
import { listaRoutes } from '../features/lista/routes'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      ...inicioRoutes,
      ...cargaRoutes,
      ...listaRoutes,
      ...campaniasRoutes,
      ...dashboardRoutes,
      ...healthRoutes,
      {
        path: '*',
        element: <h1 className="text-2xl font-semibold">Página no encontrada</h1>,
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
