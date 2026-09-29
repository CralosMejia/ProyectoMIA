import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api-error'
import { httpGet } from './http-client'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('httpGet', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('resolves the parsed body on 200 with JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { status: 'ok' }))

    await expect(httpGet<{ status: string }>('/api/health')).resolves.toEqual({ status: 'ok' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(String(url)).toBe('/api/health')
    expect(init?.method).toBe('GET')
  })

  it('throws ApiError with the structured message on 404', async () => {
    const body = { error: { code: 'not_found', message: 'X' } }
    fetchMock.mockResolvedValue(jsonResponse(404, body))

    const error = await httpGet('/api/missing').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 404, message: 'X', body })
  })

  it('throws ApiError with status 503 and accessible body', async () => {
    const body = { error: { code: 'unavailable', message: 'down' }, checks: { db: 'fail' } }
    fetchMock.mockResolvedValue(jsonResponse(503, body))

    const error = await httpGet('/api/health').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
    expect((error as ApiError).body).toEqual(body)
  })

  it('uses a generic message when the error body is not structured', async () => {
    fetchMock.mockResolvedValue(new Response('boom', { status: 500 }))

    const error = await httpGet('/api/x').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(500)
    expect((error as ApiError).message).not.toBe('')
    expect((error as ApiError).body).toBe('boom')
  })

  it('throws ApiError with status 0 and a generic message on network error', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await httpGet('/api/health').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
    expect((error as ApiError).message).not.toContain('Failed to fetch')
    expect((error as ApiError).message.length).toBeGreaterThan(0)
  })

  it('rejects with AbortError (not ApiError) when the signal is aborted', async () => {
    fetchMock.mockImplementation((_input, init) => {
      return new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal
        const abort = () => reject(new DOMException('The operation was aborted.', 'AbortError'))
        if (signal?.aborted) abort()
        signal?.addEventListener('abort', abort)
      })
    })
    const controller = new AbortController()

    const promise = httpGet('/api/health', { signal: controller.signal })
    controller.abort()

    const error = await promise.catch((e: unknown) => e)
    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal)
  })

  it('throws ApiError with the raw body when a 2xx JSON response is malformed', async () => {
    fetchMock.mockResolvedValue(
      new Response('{not json', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    )

    const error = await httpGet('/api/health').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(200)
    expect((error as ApiError).message).not.toBe('')
    expect((error as ApiError).message).not.toContain('{not json')
    expect((error as ApiError).body).toBe('{not json')
  })

  it('does not touch web storage nor log responses', async () => {
    const logSpy = vi.spyOn(console, 'log')
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem')
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
    fetchMock.mockResolvedValue(jsonResponse(200, { secret: 'value' }))

    await httpGet('/api/health')

    expect(logSpy).not.toHaveBeenCalled()
    expect(getItemSpy).not.toHaveBeenCalled()
    expect(setItemSpy).not.toHaveBeenCalled()
    logSpy.mockRestore()
    getItemSpy.mockRestore()
    setItemSpy.mockRestore()
  })
})
