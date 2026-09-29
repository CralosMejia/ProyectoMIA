import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { getHealth } from './health-api'
import healthApiSource from './health-api.ts?raw'
import healthTypesSource from '../types.ts?raw'

// Todo el codigo fuente bajo src/features. El patron es relativo a la raiz del proyecto,
// asi que las claves tienen siempre la forma '/src/features/...' (no './x.ts').
const HEALTH_API_KEY = '/src/features/health/api/health-api.ts'
const featureSources = import.meta.glob<string>('/src/features/**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
})

const VALID_BODY = { status: 'ok', database: 'up', checked_at: '2026-01-01T00:00:00Z' }

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function rawResponse(status: number, text: string, contentType = 'application/json'): Response {
  return new Response(text, { status, headers: { 'Content-Type': contentType } })
}

describe('getHealth (limites y errores)', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // --- Criterio 1: mapeo snake_case -> camelCase ---

  it('200 valido → el resultado no expone claves snake_case ni campos extra del backend', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, { ...VALID_BODY, extra: 'leak' }))

    const health = await getHealth()

    expect(Object.keys(health).sort()).toEqual(['checkedAt', 'database', 'status'])
    expect(health).not.toHaveProperty('checked_at')
    expect(health).not.toHaveProperty('extra')
  })

  it('200 con checked_at con offset → checkedAt representa el mismo instante UTC', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(200, { ...VALID_BODY, checked_at: '2026-01-01T02:00:00+02:00' }),
    )

    const health = await getHealth()

    expect(health.checkedAt.toISOString()).toBe('2026-01-01T00:00:00.000Z')
  })

  it('200 degraded/down → se mapea igual que ok/up', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(200, { status: 'degraded', database: 'down', checked_at: '2026-01-01T00:00:00Z' }),
    )

    await expect(getHealth()).resolves.toEqual({
      status: 'degraded',
      database: 'down',
      checkedAt: new Date('2026-01-01T00:00:00Z'),
    })
  })

  it('types.ts → el tipo de dominio no conoce la forma snake_case', () => {
    expect(healthTypesSource).not.toMatch(/checked_at/)
    expect(healthTypesSource).toMatch(/checkedAt/)
  })

  it('codigo de produccion de features → checked_at solo aparece en health-api.ts', () => {
    // La exclusion no puede ser vacia: el archivo permitido debe estar en el mapa y contener checked_at.
    expect(featureSources[HEALTH_API_KEY]).toMatch(/checked_at/)

    const offenders = Object.entries(featureSources)
      .filter(([path]) => !/\.test\.tsx?$/.test(path))
      .filter(([path]) => path !== HEALTH_API_KEY)
      .filter(([, source]) => /checked_at/.test(source))
      .map(([path]) => path)

    expect(offenders).toEqual([])
  })

  // --- Criterio 1 (error): 200 que no cumple el contrato ---

  it.each([
    ['sin checked_at', { status: 'ok', database: 'up' }],
    ['checked_at no es fecha', { ...VALID_BODY, checked_at: 'ayer' }],
    ['checked_at numerico', { ...VALID_BODY, checked_at: 1767225600000 }],
    ['status desconocido', { ...VALID_BODY, status: 'OK' }],
    ['database desconocido', { ...VALID_BODY, database: 'unknown' }],
    ['clave ya en camelCase', { status: 'ok', database: 'up', checkedAt: '2026-01-01T00:00:00Z' }],
    ['cuerpo null (JSON literal)', null],
    ['cuerpo array', [VALID_BODY]],
  ])('200 con cuerpo invalido (%s) → lanza ApiError', async (_label, body) => {
    fetchMock.mockResolvedValue(jsonResponse(200, body))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
  })

  it('200 con cuerpo vacio → lanza ApiError', async () => {
    fetchMock.mockResolvedValue(new Response('', { status: 200 }))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
  })

  it('200 con JSON malformado → lanza ApiError (no entrega texto crudo)', async () => {
    fetchMock.mockResolvedValue(rawResponse(200, '{"status":"ok",'))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
  })

  it('200 con texto plano → lanza ApiError', async () => {
    fetchMock.mockResolvedValue(rawResponse(200, 'OK', 'text/plain'))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
  })

  // --- Criterio 2: 503 con cuerpo valido ---

  it('503 con cuerpo valido → no lanza y no expone checked_at', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(503, { status: 'degraded', database: 'down', checked_at: '2026-01-01T00:00:00Z' }),
    )

    const health = await getHealth()

    expect(health.status).toBe('degraded')
    expect(health.database).toBe('down')
    expect(health.checkedAt).toBeInstanceOf(Date)
    expect(health.checkedAt.toISOString()).toBe('2026-01-01T00:00:00.000Z')
    expect(health).not.toHaveProperty('checked_at')
  })

  it('503 con checked_at invalido → propaga ApiError 503', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(503, { status: 'degraded', database: 'down', checked_at: 'nope' }),
    )

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
  })

  it('503 con texto plano → propaga ApiError 503', async () => {
    fetchMock.mockResolvedValue(rawResponse(503, 'Service Unavailable', 'text/plain'))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
  })

  it('503 con JSON malformado → propaga ApiError 503', async () => {
    fetchMock.mockResolvedValue(rawResponse(503, '{"status":'))

    const error = await getHealth().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(503)
  })

  // --- Criterio 3: otros errores ---

  it.each([400, 401, 403, 404, 429, 500, 502, 504])(
    '%i con cuerpo de health valido → propaga ApiError con ese status (solo 503 se tolera)',
    async (status) => {
      fetchMock.mockResolvedValue(
        jsonResponse(status, { status: 'degraded', database: 'down', checked_at: '2026-01-01T00:00:00Z' }),
      )

      const error = await getHealth().catch((e: unknown) => e)

      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).status).toBe(status)
    },
  )

  it('500 con error estructurado → ApiError conserva mensaje y body', async () => {
    const body = { error: { code: 'internal', message: 'Fallo interno' } }
    fetchMock.mockResolvedValue(jsonResponse(500, body))

    const error = (await getHealth().catch((e: unknown) => e)) as ApiError

    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe('Fallo interno')
    expect(error.body).toEqual(body)
  })

  it('signal abortado → rechaza con AbortError, no ApiError', async () => {
    const controller = new AbortController()
    fetchMock.mockImplementation((_input, init) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('The operation was aborted.', 'AbortError'))
        })
      })
    })

    const pending = getHealth(controller.signal).catch((e: unknown) => e)
    controller.abort()
    const error = await pending

    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as { name: string }).name).toBe('AbortError')
  })

  // --- Concurrencia ---

  it('dos llamadas simultaneas → cada una resuelve su propia respuesta', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, VALID_BODY))
      .mockResolvedValueOnce(
        jsonResponse(503, { status: 'degraded', database: 'down', checked_at: '2026-02-02T00:00:00Z' }),
      )

    const [first, second] = await Promise.all([getHealth(), getHealth()])

    expect(first).toEqual({ status: 'ok', database: 'up', checkedAt: new Date('2026-01-01T00:00:00Z') })
    expect(second).toEqual({
      status: 'degraded',
      database: 'down',
      checkedAt: new Date('2026-02-02T00:00:00Z'),
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  // --- Criterio 4: uso exclusivo de core/http ---

  it('health-api.ts → importa httpGet de core/http y no referencia fetch', () => {
    expect(healthApiSource).toMatch(/from '\.\.\/\.\.\/\.\.\/core\/http\/http-client'/)
    expect(healthApiSource).not.toMatch(/\bfetch\b/)
  })

  it('codigo de produccion de features → 0 referencias a fetch', () => {
    const productionFiles = Object.entries(featureSources).filter(
      ([path]) => !/\.test\.tsx?$/.test(path),
    )
    const offenders = productionFiles
      .filter(([, source]) => /\bfetch\b/.test(source))
      .map(([path]) => path)

    expect(productionFiles.length).toBeGreaterThan(0)
    expect(offenders).toEqual([])
  })

  it('getHealth → hace exactamente una peticion GET a /api/v1/health', async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, VALID_BODY))

    await getHealth()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(/\/api\/v1\/health$/)
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe('GET')
  })
})
