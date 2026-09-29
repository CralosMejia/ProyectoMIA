import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { getHealth } from './health-api'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('getHealth', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('maps a 200 snake_case body to the camelCase Health type', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(200, { status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }),
    )

    const health = await getHealth()

    expect(health).toEqual({
      status: 'ok',
      database: 'up',
      checkedAt: new Date('2026-01-01T00:00:00Z'),
    })
    expect(health.checkedAt).toBeInstanceOf(Date)
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe('/api/v1/health')
  })

  it('returns a degraded Health on 503 with a valid health body (does not throw)', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(503, { status: 'degraded', database: 'down', checked_at: '2026-01-01T00:00:00Z' }),
    )

    await expect(getHealth()).resolves.toEqual({
      status: 'degraded',
      database: 'down',
      checkedAt: new Date('2026-01-01T00:00:00Z'),
    })
  })

  it('propagates ApiError on 503 without a valid health body', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(503, { error: { code: 'unavailable', message: 'down' } }),
    )

    const error = await getHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
  })

  it('propagates ApiError on 500', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { error: { code: 'internal', message: 'X' } }))

    const error = await getHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(500)
  })

  it('propagates ApiError on network failure', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await getHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
  })

  it('throws ApiError when a 200 body does not match the health contract', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(200, { status: 'weird', database: 'up', checked_at: 'not-a-date' }),
    )

    const error = await getHealth().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
  })

  it('forwards the abort signal to the HTTP client', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(200, { status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }),
    )
    const controller = new AbortController()

    await getHealth(controller.signal)

    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal)
  })
})
