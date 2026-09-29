import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from './router'
import healthSpecSource from '../../e2e/health.spec.ts?raw'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(<RouterProvider router={router} />)
  return router
}

describe('router de la aplicacion (bordes)', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('/salud → renderiza HealthPage dentro del layout de la app', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    renderAt('/salud')

    const main = await screen.findByRole('main')
    expect(await within(main).findByRole('heading', { name: 'Estado del sistema' })).toBeInTheDocument()
    expect(await within(main).findByText('Sistema operativo')).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
  })

  it('/ ya no es la pagina de salud → muestra "Inicio" y no pide /health', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Estado del sistema' })).not.toBeInTheDocument()
    // Desde R-003/T12 Inicio consulta el estado del sistema; lo que no debe ocurrir es pedir /health.
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const urls = fetchMock.mock.calls.map(([url]) => String(url))
    expect(urls.some((url) => url.includes('/api/v1/sistema/estado'))).toBe(true)
    expect(urls.some((url) => url.includes('/health'))).toBe(false)
  })

  it('ruta anidada inexistente → "Página no encontrada" y ningun enlace marcado salvo que coincida', async () => {
    renderAt('/campanias/x/y')

    expect(await screen.findByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation')
    expect(within(nav).getByRole('link', { name: 'Inicio' })).not.toHaveAttribute('aria-current')
  })

  it('navegar desde 404 con el menu → muestra la pagina destino', async () => {
    const user = userEvent.setup()
    const router = renderAt('/no-existe')
    await screen.findByRole('heading', { name: 'Página no encontrada' })

    await user.click(screen.getByRole('link', { name: 'Dashboard' }))

    expect(router.state.location.pathname).toBe('/dashboard')
    expect(await screen.findByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Página no encontrada' })).not.toBeInTheDocument()
  })

  it('e2e/health.spec.ts → navega a /salud', () => {
    expect(healthSpecSource).toMatch(/page\.goto\(\s*['"]\/salud['"]\s*\)/)
  })
})
