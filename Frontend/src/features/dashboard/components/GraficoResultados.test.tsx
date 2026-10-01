import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { GraficoResultados } from './GraficoResultados'
import graficoSource from './GraficoResultados.tsx?raw'

const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(/
const PALETA_TAILWIND =
  /\b(?:bg|text|border|ring|outline|fill|stroke|from|to|via|shadow|divide|accent|caret|decoration)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(?:-\d{2,3})?\b/

describe('GraficoResultados', () => {
  afterEach(() => {
    cleanup()
  })

  it('con {7, 12, 5, 24}: leyenda con numero y %, total en el centro y texto accesible', () => {
    const { container } = render(
      <GraficoResultados resumen={{ renovaron: 7, noRenovaron: 12, sinResultado: 5, total: 24 }} />,
    )

    expect(
      screen.getByRole('heading', { name: 'Resultado de las gestiones del mes' }),
    ).toBeInTheDocument()

    const leyenda = within(screen.getByRole('list', { name: 'Leyenda' })).getAllByRole('listitem')
    expect(leyenda.map((li) => li.textContent)).toEqual([
      'Renovaron 7 (29,2 %)',
      'No renovaron 12 (50,0 %)',
      'Sin resultado 5 (20,8 %)',
    ])
    expect(leyenda[0]?.querySelector('.bg-ok')).not.toBeNull()
    expect(leyenda[1]?.querySelector('.bg-risk-high')).not.toBeNull()
    expect(leyenda[2]?.querySelector('.bg-ink\\/30')).not.toBeNull()

    const grafico = screen.getByRole('img')
    const etiqueta = grafico.getAttribute('aria-label') ?? ''
    expect(etiqueta).toContain('renovaron 7')
    expect(etiqueta).toContain('no renovaron 12')
    expect(etiqueta).toContain('sin resultado 5')
    expect(grafico).toHaveTextContent('24 gestiones')

    const sectores = container.querySelectorAll('circle[data-sector]')
    expect([...sectores].map((c) => c.getAttribute('data-sector'))).toEqual([
      'renovaron',
      'noRenovaron',
      'sinResultado',
    ])
    expect(sectores[0]).toHaveClass('stroke-ok')
    expect(sectores[1]).toHaveClass('stroke-risk-high')
    expect(sectores[2]).toHaveClass('stroke-ink/30')

    expect(screen.getByText('Sin resultado: gestiones abiertas o sin campaña.')).toBeInTheDocument()
  })

  it('tabla equivalente con caption "Datos del gráfico de resultados"', () => {
    render(
      <GraficoResultados resumen={{ renovaron: 7, noRenovaron: 12, sinResultado: 5, total: 24 }} />,
    )

    const tabla = screen.getByRole('table', { name: 'Datos del gráfico de resultados' })
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas.map((f) => within(f).getAllByRole('cell').map((c) => c.textContent))).toEqual([
      ['Renovaron', '7', '29,2 %'],
      ['No renovaron', '12', '50,0 %'],
      ['Sin resultado', '5', '20,8 %'],
    ])
  })

  it('total 0 → sin SVG y "Sin gestiones en este mes"', () => {
    const { container } = render(
      <GraficoResultados resumen={{ renovaron: 0, noRenovaron: 0, sinResultado: 0, total: 0 }} />,
    )

    expect(screen.getByText('Sin gestiones en este mes')).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeNull()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('un solo sector al 100 % se dibuja como circulo completo', () => {
    const { container } = render(
      <GraficoResultados resumen={{ renovaron: 0, noRenovaron: 0, sinResultado: 3, total: 3 }} />,
    )

    const sectores = container.querySelectorAll('circle[data-sector]')
    expect(sectores).toHaveLength(1)
    expect(sectores[0]).toHaveAttribute('data-sector', 'sinResultado')
    expect(sectores[0]).toHaveAttribute('stroke-dasharray', '100 0')
    expect(screen.getByRole('img')).toHaveTextContent('3 gestiones')
    expect(screen.getAllByRole('listitem')[2]).toHaveTextContent('Sin resultado 3 (100,0 %)')
  })

  it('un total de 1 → "1 gestión"', () => {
    render(
      <GraficoResultados resumen={{ renovaron: 1, noRenovaron: 0, sinResultado: 0, total: 1 }} />,
    )

    expect(screen.getByRole('img')).toHaveTextContent('1 gestión')
  })

  it('fuente sin colores literales, sin paleta por defecto de Tailwind ni style inline', () => {
    expect(graficoSource).not.toMatch(COLOR_LITERAL)
    expect(graficoSource).not.toMatch(PALETA_TAILWIND)
    expect(graficoSource).not.toMatch(/\bstyle=\{/)
  })
})
