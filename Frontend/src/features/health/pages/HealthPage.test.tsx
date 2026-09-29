import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HealthPage from './HealthPage'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const OK_BODY = { status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }
const DEGRADED_BODY = { status: 'degraded', database: 'down', checked_at: '2026-01-01T00:00:00Z' }
const SERVER_ERROR_BODY = {
  error: { code: 'internal_error', message: 'Error interno del servidor.' },
  detail: 'stacktrace-secreto',
}

describe('HealthPage', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows a status indicator while loading', () => {
    fetchMock.mockReturnValue(new Promise<Response>(() => {}))

    render(<HealthPage />)

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows operational state and connected database on 200 ok', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, OK_BODY))

    render(<HealthPage />)

    expect(await screen.findByText('Sistema operativo')).toBeInTheDocument()
    expect(screen.getByText('Base de datos: conectada')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows degraded state and disconnected database on 503', async () => {
    fetchMock.mockResolvedValue(jsonResponse(503, DEGRADED_BODY))

    render(<HealthPage />)

    expect(await screen.findByText('Servicio degradado')).toBeInTheDocument()
    expect(screen.getByText('Base de datos: sin conexión')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows an error banner with only the error message on 500', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, SERVER_ERROR_BODY))

    render(<HealthPage />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Error interno del servidor.')
    expect(alert).not.toHaveTextContent('stacktrace-secreto')
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('refetches when clicking Reintentar and shows the recovered state', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(500, SERVER_ERROR_BODY))
      .mockResolvedValueOnce(jsonResponse(200, OK_BODY))
    const user = userEvent.setup()

    render(<HealthPage />)

    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Sistema operativo')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })
})
