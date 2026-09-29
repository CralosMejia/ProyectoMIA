import { cleanup, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { healthRoutes } from './routes'

describe('healthRoutes', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('ruta "/salud" → renderiza HealthPage (lazy) y muestra el estado del API', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const router = createMemoryRouter(healthRoutes, { initialEntries: ['/salud'] })

    render(<RouterProvider router={router} />)

    expect(await screen.findByRole('heading', { name: 'Estado del sistema' })).toBeInTheDocument()
    expect(await screen.findByText('Sistema operativo')).toBeInTheDocument()
  })

  it('ruta "/salud" antes de resolver chunk o API → hay un indicador role="status"', () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}))
    const router = createMemoryRouter(healthRoutes, { initialEntries: ['/salud'] })

    render(<RouterProvider router={router} />)

    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
