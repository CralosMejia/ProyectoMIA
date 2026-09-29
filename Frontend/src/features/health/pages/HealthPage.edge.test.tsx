import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HealthPage from './HealthPage'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const OK_BODY = { status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }
const SERVER_ERROR_BODY = { error: { code: 'internal_error', message: 'Error interno del servidor.' } }

describe('HealthPage (edge cases)', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('cargando → no muestra tarjeta de estado ni alerta', () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}))

    render(<HealthPage />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByText('Sistema operativo')).not.toBeInTheDocument()
    expect(screen.queryByText('Servicio degradado')).not.toBeInTheDocument()
  })

  it('fallo de red (fetch rechaza) → alerta con mensaje no vacio, sin el error crudo, y boton Reintentar', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    render(<HealthPage />)

    const alert = await screen.findByRole('alert')
    expect(alert).not.toHaveTextContent('Failed to fetch')
    expect(alert.querySelector('p')?.textContent?.trim()).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('click en Reintentar con peticion pendiente → vuelve a mostrar role="status" y oculta la alerta', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(500, SERVER_ERROR_BODY))
      .mockReturnValueOnce(new Promise<Response>(() => {}))
    const user = userEvent.setup()

    render(<HealthPage />)
    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('Reintentar que vuelve a fallar → la alerta sigue visible con el mensaje', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse(500, SERVER_ERROR_BODY)))
    const user = userEvent.setup()

    render(<HealthPage />)
    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
    expect(screen.queryByText('Sistema operativo')).not.toBeInTheDocument()
  })

  it('doble click rapido en Reintentar → solo se pinta el resultado final, sin estado mezclado', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(500, SERVER_ERROR_BODY))
      .mockImplementation(() => Promise.resolve(jsonResponse(200, OK_BODY)))
    const user = userEvent.setup()

    render(<HealthPage />)
    await user.dblClick(await screen.findByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Sistema operativo')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('desmontar con peticion pendiente → no registra errores en consola', () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}))
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { unmount } = render(<HealthPage />)
    unmount()

    expect(errorSpy).not.toHaveBeenCalled()
  })
})
