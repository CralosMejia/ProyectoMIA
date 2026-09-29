import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { RiskBadge } from './RiskBadge'
import riskBadgeSource from './RiskBadge.tsx?raw'

describe('RiskBadge', () => {
  afterEach(() => {
    cleanup()
  })

  it.each([
    { nivel: 'ALTO', texto: 'Alto', token: 'risk-high' },
    { nivel: 'MEDIO', texto: 'Medio', token: 'risk-medium' },
    { nivel: 'BAJO', texto: 'Bajo', token: 'risk-low' },
  ] as const)('$nivel → muestra "$texto" con clase basada en el token $token', ({ nivel, texto, token }) => {
    render(<RiskBadge nivel={nivel} />)

    expect(screen.getByText(texto).className).toContain(token)
  })

  it('cada nivel usa una clase distinta', () => {
    const clases = (['ALTO', 'MEDIO', 'BAJO'] as const).map((nivel) => {
      const { unmount } = render(<RiskBadge nivel={nivel} />)
      const className = screen.getByText(/^(Alto|Medio|Bajo)$/).className
      unmount()
      return className
    })

    expect(new Set(clases).size).toBe(3)
  })

  it('no importa nada de features/ ni escribe colores literales', () => {
    expect(riskBadgeSource).not.toMatch(/from\s+['"][^'"]*features\//)
    expect(riskBadgeSource).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(/)
  })
})
