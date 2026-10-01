import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { estaDenegado, reiniciarAccesoDenegado, suscribir } from './acceso-denegado'
import { ApiError } from './api-error'
import { httpGet, httpGetBlob, httpPost, httpPostForm, httpPut } from './http-client'

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

function abortableFetch(fetchMock: ReturnType<typeof vi.fn<typeof fetch>>) {
  fetchMock.mockImplementation((_input, init) => {
    return new Promise<Response>((_resolve, reject) => {
      const signal = init?.signal
      const abort = () => reject(new DOMException('The operation was aborted.', 'AbortError'))
      if (signal?.aborted) abort()
      signal?.addEventListener('abort', abort)
    })
  })
}

describe('httpPost / httpPut / httpPostForm / httpGetBlob', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('httpPost sends JSON with Content-Type application/json and resolves the body on 201', async () => {
    fetchMock.mockResolvedValue(jsonResponse(201, { id: 7 }))

    await expect(httpPost<{ id: number }>('/api/items', { name: 'a' })).resolves.toEqual({ id: 7 })
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(String(url)).toBe('/api/items')
    expect(init?.method).toBe('POST')
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    expect(init?.body).toBe(JSON.stringify({ name: 'a' }))
  })

  it('httpPost maps a structured 501 to ApiError with the backend message', async () => {
    const body = {
      error: { code: 'not_implemented', message: 'Esta funcion aun no esta disponible.' },
    }
    fetchMock.mockResolvedValue(jsonResponse(501, body))

    const error = await httpPost('/api/items', {}).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 501, message: 'Esta funcion aun no esta disponible.' })
  })

  it('httpPut sends JSON with method PUT and resolves the body', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { ok: true }))

    await expect(httpPut<{ ok: boolean }>('/api/items/1', { name: 'b' })).resolves.toEqual({
      ok: true,
    })
    const [, init] = fetchMock.mock.calls[0] ?? []
    expect(init?.method).toBe('PUT')
    expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    expect(init?.body).toBe(JSON.stringify({ name: 'b' }))
  })

  it('httpPostForm sends the FormData with the file and does not set Content-Type', async () => {
    fetchMock.mockResolvedValue(jsonResponse(201, { uploaded: true }))
    const form = new FormData()
    const file = new File(['a,b;1,2'], 'datos.csv', { type: 'text/csv' })
    form.append('file', file)

    await expect(httpPostForm<{ uploaded: boolean }>('/api/upload', form)).resolves.toEqual({
      uploaded: true,
    })
    const [, init] = fetchMock.mock.calls[0] ?? []
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe(form)
    expect((init?.body as FormData).get('file')).toBeInstanceOf(File)
    expect(new Headers(init?.headers).has('Content-Type')).toBe(false)
  })

  it('httpGetBlob resolves a Blob with the response type', async () => {
    fetchMock.mockResolvedValue(
      new Response('col;1', { status: 200, headers: { 'Content-Type': 'text/csv' } }),
    )

    const blob = await httpGetBlob('/api/export')
    // Blob de la realm de fetch (Node), no la de jsdom: se compara por etiqueta.
    expect(Object.prototype.toString.call(blob)).toBe('[object Blob]')
    expect(blob.type).toBe('text/csv')
    expect(await blob.text()).toBe('col;1')
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe('GET')
  })

  it('httpGetBlob throws ApiError with the structured message on error', async () => {
    const body = { error: { code: 'not_found', message: 'No existe' } }
    fetchMock.mockResolvedValue(jsonResponse(404, body))

    const error = await httpGetBlob('/api/export').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 404, message: 'No existe', body })
  })

  it.each([
    ['httpPost', (signal: AbortSignal) => httpPost('/api/x', {}, { signal })],
    ['httpPut', (signal: AbortSignal) => httpPut('/api/x', {}, { signal })],
    ['httpPostForm', (signal: AbortSignal) => httpPostForm('/api/x', new FormData(), { signal })],
    ['httpGetBlob', (signal: AbortSignal) => httpGetBlob('/api/x', { signal })],
  ])('%s rejects with AbortError (not ApiError) when aborted', async (_name, call) => {
    abortableFetch(fetchMock)
    const controller = new AbortController()

    const promise = call(controller.signal)
    controller.abort()

    const error = await promise.catch((e: unknown) => e)
    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
  })

  it('httpPost maps a network error to ApiError with status 0', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await httpPost('/api/x', {}).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
  })
})

describe('acceso denegado (CU-00)', () => {
  const fetchMock = vi.fn<typeof fetch>()
  const FORBIDDEN = {
    error: { code: 'forbidden', message: 'El acceso no esta permitido desde este equipo.' },
  }

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    reiniciarAccesoDenegado()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    reiniciarAccesoDenegado()
  })

  it('403 forbidden → ApiError 403 y los suscriptores se notifican una sola vez', async () => {
    const oyente = vi.fn()
    const baja = suscribir(oyente)
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse(403, FORBIDDEN)))

    const error = await httpGet('/api/v1/sistema/estado').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 403, message: FORBIDDEN.error.message })
    expect(estaDenegado()).toBe(true)
    expect(oyente).toHaveBeenCalledTimes(1)

    await httpPost('/api/v1/listas', {}).catch(() => undefined)
    expect(oyente).toHaveBeenCalledTimes(1)
    baja()
  })

  it.each([
    [404, { error: { code: 'not_found', message: 'No existe.' } }],
    [409, { error: { code: 'conflict', message: 'Conflicto.' } }],
    [403, { error: { code: 'otro', message: 'Otro motivo.' } }],
  ])('%i sin code forbidden → no marca el acceso denegado', async (status, body) => {
    const oyente = vi.fn()
    const baja = suscribir(oyente)
    fetchMock.mockResolvedValue(jsonResponse(status, body))

    const error = await httpGet('/api/x').catch((e: unknown) => e)
    expect(error).toMatchObject({ status })
    expect(estaDenegado()).toBe(false)
    expect(oyente).not.toHaveBeenCalled()
    baja()
  })

  it('tras darse de baja, el oyente ya no se notifica', async () => {
    const oyente = vi.fn()
    suscribir(oyente)()
    fetchMock.mockResolvedValue(jsonResponse(403, FORBIDDEN))

    await httpGet('/api/x').catch(() => undefined)
    expect(estaDenegado()).toBe(true)
    expect(oyente).not.toHaveBeenCalled()
  })

  it('core/http no importa ningun feature', () => {
    const fuentes = import.meta.glob(['./*.ts', '!./*.test.ts'], {
      query: '?raw',
      import: 'default',
      eager: true,
    }) as Record<string, string>
    expect(Object.keys(fuentes).length).toBeGreaterThanOrEqual(3)
    for (const codigo of Object.values(fuentes)) {
      expect(codigo).not.toMatch(/features\//)
    }
  })
})
