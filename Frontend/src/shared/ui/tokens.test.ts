// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import appLayoutSource from '../../core/layout/AppLayout.tsx?raw'
import ayudaSource from './Ayuda.tsx?raw'
import dataTableSource from './DataTable.tsx?raw'
import errorAlertSource from './ErrorAlert.tsx?raw'
import loadingIndicatorSource from './LoadingIndicator.tsx?raw'
import modalSource from './Modal.tsx?raw'
import riskBadgeSource from './RiskBadge.tsx?raw'

// Vitest procesa los .css (un import ?raw de index.css llega vacio): se lee del disco.
const indexCss = readFileSync(new URL('../../index.css', import.meta.url), 'utf8')

// Colores literales o paleta por defecto de Tailwind (bg-red-500, text-gray-700...): prohibidos fuera de index.css.
const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(/
const PALETA_TAILWIND =
  /\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|shadow|divide|accent|caret|decoration)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(?:-\d{2,3})?\b/
const ESTILO_INLINE = /\bstyle=\{/

function themeBlock(css: string): string {
  const match = /@theme\s*\{([\s\S]*?)\}/.exec(css)
  return match?.[1] ?? ''
}

describe('tokens de diseno (index.css)', () => {
  it.each(['--color-risk-high', '--color-risk-medium', '--color-risk-low'])(
    '@theme declara el token %s',
    (token) => {
      expect(themeBlock(indexCss)).toMatch(new RegExp(`${token}\\s*:\\s*[^;]+;`))
    },
  )

  it('los tres tokens de riesgo tienen valores distintos entre alto y bajo', () => {
    const theme = themeBlock(indexCss)
    const valor = (t: string) => new RegExp(`${t}\\s*:\\s*([^;]+);`).exec(theme)?.[1]?.trim()
    expect(valor('--color-risk-high')).toBeDefined()
    expect(valor('--color-risk-high')).not.toBe(valor('--color-risk-low'))
    expect(valor('--color-risk-high')).not.toBe(valor('--color-risk-medium'))
  })
})

describe('componentes solo con tokens de index.css', () => {
  it.each([
    ['core/layout/AppLayout.tsx', appLayoutSource],
    ['shared/ui/Ayuda.tsx', ayudaSource],
    ['shared/ui/DataTable.tsx', dataTableSource],
    ['shared/ui/ErrorAlert.tsx', errorAlertSource],
    ['shared/ui/LoadingIndicator.tsx', loadingIndicatorSource],
    ['shared/ui/Modal.tsx', modalSource],
    ['shared/ui/RiskBadge.tsx', riskBadgeSource],
  ])('%s → sin colores literales, sin paleta por defecto y sin style inline', (_archivo, source) => {
    expect(source).not.toMatch(COLOR_LITERAL)
    expect(source).not.toMatch(PALETA_TAILWIND)
    expect(source).not.toMatch(ESTILO_INLINE)
  })

  it.each([
    ['shared/ui/Ayuda.tsx', ayudaSource],
    ['shared/ui/DataTable.tsx', dataTableSource],
    ['shared/ui/ErrorAlert.tsx', errorAlertSource],
    ['shared/ui/LoadingIndicator.tsx', loadingIndicatorSource],
    ['shared/ui/Modal.tsx', modalSource],
    ['shared/ui/RiskBadge.tsx', riskBadgeSource],
  ])('%s → no importa nada de features/', (_archivo, source) => {
    expect(source).not.toMatch(/from\s+['"][^'"]*features\//)
  })

  it('DataTable → sin any', () => {
    expect(dataTableSource).not.toMatch(/:\s*any\b|<any>|\bas\s+any\b|any\[\]/)
  })
})
