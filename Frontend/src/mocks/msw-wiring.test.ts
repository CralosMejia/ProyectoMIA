import { describe, expect, it } from 'vitest'
import mainSource from '../main.tsx?raw'
import { collectHandlers, handlers } from './handlers'

const FEATURES_CON_MOCKS = ['campanias', 'carga', 'dashboard', 'inicio', 'lista']

describe('mocks/handlers (autodescubrimiento)', () => {
  it('sin archivos *.handlers.ts → lista vacia', () => {
    expect(collectHandlers({})).toEqual([])
  })

  it('descubre los handlers de cada feature de la API', () => {
    const modules = import.meta.glob<{ handlers?: unknown[] }>(
      '../features/*/api/*.handlers.ts',
      { eager: true },
    )
    const features = Object.keys(modules)
      .map((path) => path.split('/')[2])
      .sort()

    expect(features).toEqual(FEATURES_CON_MOCKS)
    for (const module of Object.values(modules)) {
      expect(module.handlers?.length ?? 0).toBeGreaterThan(0)
    }
    const total = Object.values(modules).reduce((n, m) => n + (m.handlers?.length ?? 0), 0)
    expect(handlers).toHaveLength(total)
  })
})

describe('main.tsx (MSW en el navegador)', () => {
  it('no importa el worker de forma estatica → queda fuera del bundle de produccion', () => {
    expect(mainSource).not.toMatch(/^\s*import\s[^\n]*['"]\.\/mocks\/browser['"]/m)
    expect(mainSource).not.toMatch(/from\s+['"]msw/)
  })

  it('arranca el worker solo con DEV y apiMocks, antes de montar', () => {
    const guard = mainSource.indexOf('import.meta.env.DEV && config.apiMocks')
    const dynamicImport = mainSource.indexOf("await import('./mocks/browser')")
    const start = mainSource.indexOf('worker.start(')
    const render = mainSource.indexOf('enableMocking().then(')

    expect(guard).toBeGreaterThan(-1)
    expect(dynamicImport).toBeGreaterThan(guard)
    expect(start).toBeGreaterThan(dynamicImport)
    expect(render).toBeGreaterThan(start)
  })
})
