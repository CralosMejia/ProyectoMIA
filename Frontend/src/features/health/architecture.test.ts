import { describe, expect, it } from 'vitest'
import healthPageSource from './pages/HealthPage.tsx?raw'
import healthStatusCardSource from './components/HealthStatusCard.tsx?raw'

/** Extrae los especificadores de import estaticos, dinamicos y re-exports de un fuente. */
function importSpecifiers(source: string): string[] {
  const patterns = [
    /\bimport\s+[^'"]*?\s+from\s+['"]([^'"]+)['"]/g,
    /\bimport\s+['"]([^'"]+)['"]/g,
    /\bexport\s+[^'"]*?\s+from\s+['"]([^'"]+)['"]/g,
    /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
  ]
  return patterns.flatMap((re) => [...source.matchAll(re)].map((m) => m[1] ?? ''))
}

/** Nombres importados con llaves desde 'react' (para detectar hooks de React). */
function reactNamedImports(source: string): string[] {
  const names: string[] = []
  for (const m of source.matchAll(/\bimport\s+(?:type\s+)?([^'"]*?)\s+from\s+['"]react['"]/g)) {
    const braces = (m[1] ?? '').match(/\{([^}]*)\}/)
    if (braces?.[1]) {
      names.push(
        ...braces[1]
          .split(',')
          .map((n) => n.trim().replace(/^type\s+/, '').split(/\s+as\s+/)[0] ?? '')
          .filter(Boolean),
      )
    }
  }
  return names
}

const API_DIR = /(^|\/)api(\/|$)/
const HOOKS_DIR = /(^|\/)hooks(\/|$)/
const CORE_HTTP = /(^|\/)core\/http(\/|$)/

describe('health feature (fronteras de importacion)', () => {
  it('extractor sobre imports conocidos → los detecta (sanity check del parser)', () => {
    const specs = importSpecifiers(
      "import { a } from '../api/x'\nimport type { B } from \"../hooks/y\"\nconst c = import('../../core/http/z')",
    )
    expect(specs).toEqual(expect.arrayContaining(['../api/x', '../hooks/y', '../../core/http/z']))
    expect(reactNamedImports("import { useState, type FC } from 'react'")).toEqual(['useState', 'FC'])
  })

  it('HealthStatusCard → no importa hooks del feature, api/ ni core/http', () => {
    const specs = importSpecifiers(healthStatusCardSource)

    expect(specs.length).toBeGreaterThan(0)
    expect(specs.filter((s) => HOOKS_DIR.test(s))).toEqual([])
    expect(specs.filter((s) => API_DIR.test(s))).toEqual([])
    expect(specs.filter((s) => CORE_HTTP.test(s))).toEqual([])
  })

  it('HealthStatusCard → no usa hooks de React (componente presentacional)', () => {
    expect(reactNamedImports(healthStatusCardSource).filter((n) => /^use[A-Z]/.test(n))).toEqual([])
    expect(healthStatusCardSource).not.toMatch(/\bReact\.use[A-Z]/)
  })

  it('HealthPage → no importa api/ ni core/http', () => {
    const specs = importSpecifiers(healthPageSource)

    expect(specs.length).toBeGreaterThan(0)
    expect(specs.filter((s) => API_DIR.test(s))).toEqual([])
    expect(specs.filter((s) => CORE_HTTP.test(s))).toEqual([])
  })

  it('HealthPage → no llama a fetch directamente', () => {
    expect(healthPageSource).not.toMatch(/\bfetch\s*\(/)
  })
})
