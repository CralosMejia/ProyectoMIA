import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './api-error'
import { httpGet } from './http-client'
import httpClientSource from './http-client.ts?raw'
import apiErrorSource from './api-error.ts?raw'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** Simula la semantica real de fetch ante AbortSignal (ya abortado o abortado en vuelo). */
function abortAwareFetch(response?: () => Response): typeof fetch {
  return (_input, init) =>
    new Promise<Response>((resolve, reject) => {
      const signal = init?.signal
      const abort = () => reject(new DOMException('The operation was aborted.', 'AbortError'))
      if (signal?.aborted) {
        abort()
        return
      }
      signal?.addEventListener('abort', abort)
      if (response) setTimeout(() => resolve(response()), 0)
    })
}

describe('httpGet (casos limite)', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('200 con cuerpo vacio → resuelve null', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 200 }))

    await expect(httpGet('/api/empty')).resolves.toBeNull()
  })

  it('envia cabecera Accept: application/json → peticion GET con Accept JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, {}))

    await httpGet('/api/health')

    const init = fetchMock.mock.calls[0]?.[1]
    expect(init?.method).toBe('GET')
    expect(new Headers(init?.headers).get('Accept')).toBe('application/json')
  })

  it('404 con message vacio en el error estructurado → ApiError con mensaje generico no vacio y body accesible', async () => {
    const body = { error: { code: 'not_found', message: '' } }
    fetchMock.mockResolvedValue(jsonResponse(404, body))

    const error = await httpGet('/api/missing').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).message.length).toBeGreaterThan(0)
    expect((error as ApiError).body).toEqual(body)
  })

  it('503 con JSON sin forma de error estructurado → ApiError 503 con mensaje generico y body intacto', async () => {
    const body = { status: 'degraded', checks: { db: 'fail' } }
    fetchMock.mockResolvedValue(jsonResponse(503, body))

    const error = await httpGet('/api/health').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
    expect((error as ApiError).message.length).toBeGreaterThan(0)
    expect((error as ApiError).body).toEqual(body)
  })

  it('500 con Content-Type JSON pero cuerpo malformado → ApiError 500 sin lanzar SyntaxError', async () => {
    fetchMock.mockResolvedValue(
      new Response('{not json', { status: 500, headers: { 'Content-Type': 'application/json' } }),
    )

    const error = await httpGet('/api/x').catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(500)
  })

  it('error de red → ApiError con status 0 y mismo mensaje generico sea cual sea la causa', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    fetchMock.mockRejectedValueOnce(new TypeError('NetworkError: secret-host.internal:5432'))

    const first = (await httpGet('/a').catch((e: unknown) => e)) as ApiError
    const second = (await httpGet('/b').catch((e: unknown) => e)) as ApiError

    expect(first).toBeInstanceOf(ApiError)
    expect(second).toBeInstanceOf(ApiError)
    expect(first.status).toBe(0)
    expect(second.status).toBe(0)
    expect(second.message).toBe(first.message)
    expect(second.message).not.toContain('secret-host')
  })

  it('signal ya abortado antes de llamar → rechaza con AbortError (no ApiError)', async () => {
    fetchMock.mockImplementation(abortAwareFetch())
    const controller = new AbortController()
    controller.abort()

    const error = await httpGet('/api/health', { signal: controller.signal }).catch((e: unknown) => e)

    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
  })

  it('abortado durante la lectura del cuerpo → rechaza con AbortError (no ApiError)', async () => {
    const controller = new AbortController()
    const response = jsonResponse(200, { ok: true })
    vi.spyOn(response, 'text').mockImplementation(() => {
      controller.abort()
      return Promise.reject(new DOMException('The operation was aborted.', 'AbortError'))
    })
    fetchMock.mockResolvedValue(response)

    const error = await httpGet('/api/health', { signal: controller.signal }).catch((e: unknown) => e)

    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
  })

  it('dos peticiones simultaneas y se aborta una → la otra resuelve su propio cuerpo', async () => {
    fetchMock.mockImplementationOnce(abortAwareFetch(() => jsonResponse(200, { id: 'a' })))
    fetchMock.mockImplementationOnce(abortAwareFetch(() => jsonResponse(200, { id: 'b' })))
    const controllerA = new AbortController()
    const controllerB = new AbortController()

    const a = httpGet('/a', { signal: controllerA.signal })
    const b = httpGet('/b', { signal: controllerB.signal })
    controllerA.abort()

    const [resA, resB] = await Promise.allSettled([a, b])
    expect(resA.status).toBe('rejected')
    expect((resA as PromiseRejectedResult).reason).not.toBeInstanceOf(ApiError)
    expect(((resA as PromiseRejectedResult).reason as Error).name).toBe('AbortError')
    expect(resB).toEqual({ status: 'fulfilled', value: { id: 'b' } })
  })

  it('VITE_API_BASE_URL definida → la URL se construye con ese prefijo', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test')
    vi.resetModules()
    const { httpGet: freshHttpGet } = await import('./http-client')
    fetchMock.mockResolvedValue(jsonResponse(200, {}))

    await freshHttpGet('/api/health')

    expect(String(fetchMock.mock.calls[0]?.[0])).toBe('https://api.example.test/api/health')
  })

  it('exito y error → no toca localStorage/sessionStorage ni escribe en consola', async () => {
    const consoleSpies = (['log', 'info', 'debug', 'warn', 'error'] as const).map((m) =>
      vi.spyOn(console, m).mockImplementation(() => undefined),
    )
    const storageSpies = (['getItem', 'setItem', 'removeItem', 'clear'] as const).map((m) =>
      vi.spyOn(Storage.prototype, m),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { secret: 'value' }))
    fetchMock.mockResolvedValueOnce(jsonResponse(404, { error: { code: 'not_found', message: 'X' } }))
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await httpGet('/ok')
    await httpGet('/missing').catch(() => undefined)
    await httpGet('/down').catch(() => undefined)

    for (const spy of [...consoleSpies, ...storageSpies]) expect(spy).not.toHaveBeenCalled()
  })

  it('codigo fuente de core/http → no referencia localStorage, sessionStorage ni console', () => {
    for (const source of [httpClientSource, apiErrorSource]) {
      expect(source).not.toMatch(/localStorage|sessionStorage/)
      expect(source).not.toMatch(/console\./)
    }
  })
})
