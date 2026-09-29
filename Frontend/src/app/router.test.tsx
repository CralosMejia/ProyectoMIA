import { cleanup, render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { routes } from './router'
import inicioRoutesSource from '../features/inicio/routes.tsx?raw'
import cargaRoutesSource from '../features/carga/routes.tsx?raw'
import listaRoutesSource from '../features/lista/routes.tsx?raw'
import campaniasRoutesSource from '../features/campanias/routes.tsx?raw'
import dashboardRoutesSource from '../features/dashboard/routes.tsx?raw'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(<RouterProvider router={router} />)
  return router
}

describe('router de la aplicacion', () => {
  afterEach(() => {
    cleanup()
  })

  it.each([
    { path: '/', titulo: 'Inicio' },
    { path: '/carga', titulo: 'Carga de datos' },
    { path: '/lista', titulo: 'Lista priorizada' },
    { path: '/campanias', titulo: 'Campañas' },
    { path: '/dashboard', titulo: 'Dashboard' },
  ])('$path → muestra el h1 "$titulo" dentro del layout', async ({ path, titulo }) => {
    renderAt(path)

    const main = await screen.findByRole('main')
    expect(await within(main).findByRole('heading', { level: 1, name: titulo })).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('ruta inexistente → muestra "Página no encontrada" dentro del layout', async () => {
    renderAt('/no-existe')

    expect(await screen.findByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it.each([
    ['inicio', inicioRoutesSource],
    ['carga', cargaRoutesSource],
    ['lista', listaRoutesSource],
    ['campanias', campaniasRoutesSource],
    ['dashboard', dashboardRoutesSource],
  ])('features/%s/routes.tsx carga su pagina con React.lazy', (_feature, source) => {
    expect(source).toMatch(/\blazy\s*\(\s*\(\)\s*=>\s*import\(\s*['"]\.\/pages\//)
  })
})
