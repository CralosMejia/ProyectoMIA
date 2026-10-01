import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { EstadoModelo, ResultadoCampania } from '../types'
import { EmbudoGestion } from './EmbudoGestion'
import { EstadoModeloCard } from './EstadoModeloCard'
import { TablaResultadosCampania } from './TablaResultadosCampania'
import embudoSource from './EmbudoGestion.tsx?raw'
import tablaSource from './TablaResultadosCampania.tsx?raw'
import tarjetaSource from './EstadoModeloCard.tsx?raw'
import graficoSource from './GraficoResultados.tsx?raw'

function fila(cambios: Partial<ResultadoCampania>): ResultadoCampania {
  return {
    campaniaId: 2,
    nombre: 'Ejemplo: Renovación anticipada',
    gestiones: 12,
    contactados: 10,
    renovaciones: 4,
    gestionesCerradas: 10,
    tasaRenovacion: '0.40000000',
    casosInsuficientes: false,
    ...cambios,
  }
}

const MODELO: EstadoModelo = {
  version: 'v1',
  fechaEntrenamiento: new Date('2026-09-28T14:30:00Z'),
  ciclosEntrenamiento: 1843,
  proximaFechaReentrenamiento: '2027-03-28',
  ciclosNuevosEvaluables: 57,
}

describe('EmbudoGestion', () => {
  afterEach(() => {
    cleanup()
  })

  it('5 barras en orden con numero y % sobre asignadas, colores de token y texto accesible', () => {
    const { container } = render(
      <EmbudoGestion
        embudo={{ asignadas: 10, contactadas: 8, ofrecidas: 6, aceptadas: 5, renovaron: 4 }}
      />,
    )

    expect(
      screen.getByRole('heading', { name: 'Avance de las gestiones con campaña' }),
    ).toBeInTheDocument()
    const grafico = screen.getByRole('img')
    expect(grafico).toHaveAttribute(
      'aria-label',
      'Embudo del mes: asignadas 10, contactadas 8, ofrecidas 6, aceptadas 5, renovaron 4',
    )

    const etapas = [...grafico.querySelectorAll('[data-etapa]')]
    expect(etapas.map((e) => e.textContent)).toEqual([
      'Gestiones asignadas10 · 100,0 %',
      'Socios contactados8 · 80,0 %',
      'Campaña ofrecida6 · 60,0 %',
      'Campaña aceptada5 · 50,0 %',
      'Renovaron4 · 40,0 %',
    ])

    const barras = [...container.querySelectorAll('[data-barra]')]
    expect(barras).toHaveLength(5)
    expect(barras[0]).toHaveStyle({ width: '100%' })
    expect(barras[4]).toHaveStyle({ width: '40%' })
    for (const barra of barras.slice(0, 4)) expect(barra).toHaveClass('bg-brand')
    expect(barras[4]).toHaveClass('bg-ok')
    expect(barras[0]?.parentElement).toHaveClass('bg-ink/10')
  })

  it('tabla equivalente "Datos del embudo" con etapa, numero y % de asignadas', () => {
    render(
      <EmbudoGestion
        embudo={{ asignadas: 21, contactadas: 17, ofrecidas: 14, aceptadas: 8, renovaron: 6 }}
      />,
    )

    const tabla = screen.getByRole('table', { name: 'Datos del embudo' })
    const encabezados = within(tabla).getAllByRole('columnheader').map((c) => c.textContent)
    expect(encabezados).toEqual(['Etapa', 'Número', '% de asignadas'])
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas.map((f) => within(f).getAllByRole('cell').map((c) => c.textContent))).toEqual([
      ['Gestiones asignadas', '21', '100,0 %'],
      ['Socios contactados', '17', '81,0 %'],
      ['Campaña ofrecida', '14', '66,7 %'],
      ['Campaña aceptada', '8', '38,1 %'],
      ['Renovaron', '6', '28,6 %'],
    ])
  })

  it('embudo en ceros → barras vacias y "0 · 0,0 %" sin dividir por cero', () => {
    const { container } = render(
      <EmbudoGestion
        embudo={{ asignadas: 0, contactadas: 0, ofrecidas: 0, aceptadas: 0, renovaron: 0 }}
      />,
    )

    for (const barra of container.querySelectorAll('[data-barra]')) {
      expect(barra).toHaveStyle({ width: '0%' })
    }
    for (const etapa of container.querySelectorAll('[data-etapa]')) {
      expect(etapa).toHaveTextContent('0 · 0,0 %')
    }
  })

  it('fuente sin colores literales ni paleta por defecto de Tailwind', () => {
    expect(embudoSource).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(|oklch\(/)
    expect(embudoSource).not.toMatch(
      /\b(?:bg|text|border|ring|fill|stroke|from|to|via|shadow)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(?:-\d{2,3})?\b/,
    )
  })
})

describe('TablaResultadosCampania', () => {
  afterEach(() => {
    cleanup()
  })

  it('tasa "40,0 %" junto a "(10 casos)" (RN-11.1)', () => {
    render(<TablaResultadosCampania filas={[fila({})]} />)

    const tabla = within(screen.getByRole('table', { name: 'Resultados por campaña' }))
    const celdas = tabla.getAllByRole('row')[1]
    expect(celdas).toHaveTextContent('40,0 % (10 casos)')
    expect(tabla.getByText('Ejemplo: Renovación anticipada')).toBeInTheDocument()
  })

  it('casos insuficientes → "Casos insuficientes" sin tasa', () => {
    render(
      <TablaResultadosCampania
        filas={[
          fila({ gestionesCerradas: 9, tasaRenovacion: null, casosInsuficientes: true }),
          fila({
            campaniaId: null,
            nombre: 'Sin campaña',
            gestiones: 3,
            contactados: 0,
            renovaciones: 0,
            gestionesCerradas: 0,
            tasaRenovacion: null,
            casosInsuficientes: true,
          }),
        ]}
      />,
    )

    const filas = screen.getAllByRole('row').slice(1)
    expect(filas).toHaveLength(2)
    for (const f of filas) {
      expect(within(f).getByText('Casos insuficientes')).toBeInTheDocument()
      expect(f).not.toHaveTextContent('%')
    }
    expect(filas[1]).toHaveTextContent('Sin campaña')
  })

  it.each([
    ['1', '100,0 %'],
    ['0.08333333333333333333', '8,3 %'],
    ['0.12345000', '12,3 %'],
    ['0.12350000', '12,4 %'],
    ['0.99999999', '100,0 %'],
    ['0', '0,0 %'],
  ])('tasa %s → %s (sin coma flotante)', (tasa, esperado) => {
    render(<TablaResultadosCampania filas={[fila({ tasaRenovacion: tasa })]} />)

    expect(screen.getAllByRole('row')[1]).toHaveTextContent(`${esperado} (10 casos)`)
  })

  it('aviso fijo de resultados observados y mensaje de tabla vacia', () => {
    render(<TablaResultadosCampania filas={[]} />)

    expect(
      screen.getByText(
        'Las cifras son resultados observados; no demuestran que la campaña causó la renovación.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText('No hay gestiones en este mes')).toBeInTheDocument()
  })
})

describe('EstadoModeloCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('muestra version, fecha de entrenamiento, ciclos, proxima revision y ciclos nuevos', () => {
    render(<EstadoModeloCard estadoModelo={MODELO} />)

    expect(screen.getByText('Versión v1')).toBeInTheDocument()
    const fecha = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long' }).format(
      MODELO.fechaEntrenamiento,
    )
    expect(screen.getByText('Fecha de entrenamiento').nextElementSibling).toHaveTextContent(fecha)
    expect(screen.getByText('Ciclos usados para entrenar').nextElementSibling).toHaveTextContent(
      '1843',
    )
    const proxima = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeZone: 'UTC' }).format(
      new Date('2027-03-28T00:00:00Z'),
    )
    expect(screen.getByText('Próxima revisión').nextElementSibling).toHaveTextContent(proxima)
    expect(screen.getByText('Ciclos nuevos evaluables').nextElementSibling).toHaveTextContent('57')
  })

  it('sin proxima fecha → "Sin fecha programada"', () => {
    render(<EstadoModeloCard estadoModelo={{ ...MODELO, proximaFechaReentrenamiento: null }} />)

    expect(screen.getByText('Próxima revisión').nextElementSibling).toHaveTextContent(
      'Sin fecha programada',
    )
  })

  it('estadoModelo null → "Aún no hay un modelo vigente"', () => {
    render(<EstadoModeloCard estadoModelo={null} />)

    expect(screen.getByText('Aún no hay un modelo vigente')).toBeInTheDocument()
    expect(screen.queryByText(/Versión/)).not.toBeInTheDocument()
  })
})

describe('componentes del dashboard (presentacionales)', () => {
  it.each([
    ['EmbudoGestion', embudoSource],
    ['TablaResultadosCampania', tablaSource],
    ['EstadoModeloCard', tarjetaSource],
    ['GraficoResultados', graficoSource],
  ])('%s no importa api/, hooks de datos ni core/http y no usa parseFloat', (_nombre, source) => {
    expect(source).not.toMatch(/from\s+['"][^'"]*\/api\//)
    // Solo se permiten las funciones puras de presentacion (como lista/hooks/reglasGestion).
    expect(source).not.toMatch(/from\s+['"][^'"]*\/hooks\/(?!presentacion['"])/)
    expect(source).not.toMatch(/core\/http/)
    expect(source).not.toMatch(/parseFloat|Number\(/)
  })
})
