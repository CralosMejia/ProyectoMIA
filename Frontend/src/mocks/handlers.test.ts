import { http, HttpResponse, type RequestHandler } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { httpGet } from '../core/http/http-client'
import { collectHandlers, handlers } from './handlers'
import { server } from './server'

describe('mocks/handlers', () => {
  it('is empty while no feature declares *.handlers.ts', () => {
    const discovered = Object.keys(
      import.meta.glob('../features/*/api/*.handlers.ts', { eager: false }),
    )
    if (discovered.length === 0) {
      expect(handlers).toEqual([])
    } else {
      expect(handlers.length).toBeGreaterThan(0)
    }
  })

  it('flattens the handlers exported by every discovered module', () => {
    const a = http.get('/api/a', () => HttpResponse.json({}))
    const b = http.get('/api/b', () => HttpResponse.json({}))
    const c = http.post('/api/c', () => HttpResponse.json({}))

    const result = collectHandlers({
      '../features/zeta/api/zeta.handlers.ts': { handlers: [c] },
      '../features/alfa/api/alfa.handlers.ts': { handlers: [a, b] },
      '../features/vacio/api/vacio.handlers.ts': {},
    })

    expect(result).toEqual<RequestHandler[]>([a, b, c])
  })
})

describe('mocks/server', () => {
  it('answers with a handler registered through server.use', async () => {
    server.use(http.get('/api/probe', () => HttpResponse.json({ probe: 'ok' })))

    await expect(httpGet<{ probe: string }>('/api/probe')).resolves.toEqual({ probe: 'ok' })
  })

  it('rejects a request without handler (onUnhandledRequest: "error")', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await expect(fetch('/api/sin-handler')).rejects.toThrow()
    expect(errorSpy).toHaveBeenCalled()
    errorSpy.mockRestore()
  })
})
