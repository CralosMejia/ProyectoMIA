import { lazy, Suspense, type ComponentType } from 'react'
import type { RouteObject } from 'react-router-dom'

// El componente lazy se crea dentro de una funcion (no a nivel de modulo como constante
// PascalCase) para que este archivo solo exporte rutas y no dispare react-refresh/only-export-components.
function lazyElement(load: () => Promise<{ default: ComponentType }>) {
  const Page = lazy(load)
  return (
    <Suspense
      fallback={
        <p role="status" className="p-8 font-sans text-ink">
          Cargando...
        </p>
      }
    >
      <Page />
    </Suspense>
  )
}

export const healthRoutes: RouteObject[] = [
  {
    path: '/',
    element: lazyElement(() => import('./pages/HealthPage')),
  },
]
