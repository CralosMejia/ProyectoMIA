// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/*
 * Guardia global de estilos (R-013, T21): recorre todos los .tsx de src/ (salvo pruebas y mocks)
 * y comprueba que solo consumen tokens de index.css, que el unico `style` es el que depende del
 * dato y que no se cargan recursos externos (la CSP de nginx es `default-src 'self'`).
 */

const FUENTES = import.meta.glob<string>(
  ['../../**/*.tsx', '!../../**/*.test.tsx', '!../../mocks/**'],
  { query: '?raw', import: 'default', eager: true },
)

// Vitest procesa los .css (un import ?raw de index.css llega vacio): se lee del disco.
const indexCss = readFileSync(new URL('../../index.css', import.meta.url), 'utf8')
const indexHtml = readFileSync(new URL('../../../index.html', import.meta.url), 'utf8')

const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(/
const PALETA_TAILWIND =
  /\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|shadow|divide|accent|caret|decoration)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(?:-\d{2,3})?\b/
const ESTILO_INLINE = /\bstyle=\{/
const RECURSO_EXTERNO = /(?:https?:)?\/\/[a-z0-9.-]+\.[a-z]{2,}/i

/** Unicos archivos con `style`: anchos de barra que dependen del dato. */
const CON_STYLE_PERMITIDO = [
  'features/dashboard/components/EmbudoGestion.tsx',
  'features/dashboard/components/GraficoResultados.tsx',
]

const archivos = Object.entries(FUENTES).map(
  // Vite abrevia las rutas de esta misma carpeta (`./Diseno.tsx`): se normalizan desde src/.
  ([ruta, fuente]) =>
    [ruta.replace(/^\.\.\/\.\.\//, '').replace(/^\.\//, 'shared/ui/'), fuente] as const,
)

describe('guardia global de estilos (src/**/*.tsx)', () => {
  it('encuentra los componentes de src/ y excluye pruebas y mocks', () => {
    const rutas = archivos.map(([ruta]) => ruta)
    expect(rutas.length).toBeGreaterThan(30)
    expect(rutas).toContain('shared/ui/Diseno.tsx')
    expect(rutas).toContain('features/lista/pages/ListaPage.tsx')
    expect(rutas.some((r) => r.endsWith('.test.tsx') || r.startsWith('mocks/'))).toBe(false)
  })

  it.each(archivos)('%s → sin colores literales ni paleta por defecto de Tailwind', (_ruta, fuente) => {
    expect(fuente).not.toMatch(COLOR_LITERAL)
    expect(fuente).not.toMatch(PALETA_TAILWIND)
  })

  it('style={ solo en los anchos dependientes de datos', () => {
    const conStyle = archivos.filter(([, f]) => ESTILO_INLINE.test(f)).map(([r]) => r)
    for (const ruta of conStyle) expect(CON_STYLE_PERMITIDO).toContain(ruta)
  })

  it.each(archivos)('%s → sin recursos externos (URLs, <link>, <img> remotas)', (_ruta, fuente) => {
    expect(fuente).not.toMatch(RECURSO_EXTERNO)
    expect(fuente).not.toMatch(/<link\b/)
  })

  it('el campo de texto y los enlaces-boton vienen de shared/ui (sin duplicar clases)', () => {
    for (const [ruta, fuente] of archivos) {
      if (ruta.startsWith('shared/ui/')) continue
      expect(fuente, ruta).not.toMatch(/\bconst CLASE_CAMPO\b/)
      expect(fuente, ruta).not.toMatch(/rounded-pill border border-(?:brand|line) bg-(?:brand|surface) px-4 py-2/)
    }
  })

  it('el boton de ayuda usa los tokens de Boton (sin border-ink/20)', () => {
    const ayuda = archivos.find(([r]) => r === 'shared/ui/Ayuda.tsx')?.[1] ?? ''
    expect(ayuda).not.toMatch(/border-ink\/20/)
    expect(ayuda).toMatch(/\bBoton\b/)
  })
})

describe('sin recursos externos (CSP default-src self)', () => {
  it('index.css no importa hojas, fuentes ni imagenes remotas', () => {
    expect(indexCss).not.toMatch(/@import\s+(?:url\()?['"]?(?:https?:)?\/\//)
    expect(indexCss).not.toMatch(/url\(\s*['"]?(?:https?:)?\/\//)
    expect(indexCss).not.toMatch(/@font-face/)
  })

  it('index.html no carga hojas, fuentes ni scripts externos', () => {
    expect(indexHtml).not.toMatch(/(?:src|href)=["'](?:https?:)?\/\//)
    expect(indexHtml).not.toMatch(/<link\b[^>]*stylesheet/)
  })
})
