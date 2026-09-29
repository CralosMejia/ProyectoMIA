import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadConfig() {
  vi.resetModules()
  return (await import('./config')).config
}

describe('config.apiMocks', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('VITE_API_MOCKS="true" → apiMocks true', async () => {
    vi.stubEnv('VITE_API_MOCKS', 'true')

    expect((await loadConfig()).apiMocks).toBe(true)
  })

  it('sin VITE_API_MOCKS → apiMocks false (no se registra el worker)', async () => {
    vi.stubEnv('VITE_API_MOCKS', undefined)

    expect((await loadConfig()).apiMocks).toBe(false)
  })

  it.each(['false', 'TRUE', '1', ''])('VITE_API_MOCKS="%s" → apiMocks false', async (value) => {
    vi.stubEnv('VITE_API_MOCKS', value)

    expect((await loadConfig()).apiMocks).toBe(false)
  })
})
