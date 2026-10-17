import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import type { IndicadoresPiloto as DatosPiloto, IndicadorProporcion } from '../types'
import { IndicadoresPiloto } from './IndicadoresPiloto'
import source from './IndicadoresPiloto.tsx?raw'

const NOMBRES = [
  'Precisión del top 25',
  'Contactados antes del vencimiento',
  'Días de anticipación',
  'Renovación de los contactados',
  'Monto retenido',
]

const AVISO_SESGO =
  'Los socios del top 25 se contactan; por eso la precisión observada puede quedar por debajo de la real.'
const AVISO_CAUSAL = 'Cifras observadas, no causales.'
const POCOS_CASOS = 'Pocos casos: léase con cuidado'
const TEXTO_PENDIENTE =
  'Pendiente: aún no se puede verificar (se verifica 30 días después del vencimiento)'

function proporcion(parcial: Partial<IndicadorProporcion>): IndicadorProporcion {
  return {
    valor: null,
    numerador: 0,
    denominador: 0,
    n: 0,
    pendientes: 0,
    estado: 'SIN_DATOS',
    ...parcial,
  }
}

/** Ejemplo del contrato (mes parcial). */
const PARCIAL: DatosPiloto = {
  estado: 'PARCIAL',
  lista: { id: 12, nombre: 'Lista septiembre', fechaGeneracion: '2026-09-01' },
  corteVerificacion: '2026-10-28',
  nTop: 25,
  sinDato: 0,
  precisionTop25: proporcion({
    valor: '0.60000000',
    numerador: 12,
    denominador: 20,
    n: 25,
    pendientes: 5,
    estado: 'PARCIAL',
  }),
  contactadosAntesVencimiento: proporcion({
    valor: '0.72000000',
    numerador: 18,
    denominador: 25,
    n: 25,
    estado: 'COMPLETO',
  }),
  diasAnticipacion: { valor: '4.5', n: 19, estado: 'COMPLETO' },
  tasaRenovacionContactados: proporcion({
    valor: '0.41176471',
    numerador: 7,
    denominador: 17,
    n: 21,
    pendientes: 4,
    estado: 'PARCIAL',
  }),
  montoRetenido: {
    total: '312.50',
    renovaciones: 7,
    renovacionesSinMonto: 1,
    n: 17,
    pendientes: 4,
    estado: 'PARCIAL',
  },
}

const SIN_DATOS: DatosPiloto = {
  estado: 'SIN_DATOS',
  lista: null,
  corteVerificacion: null,
  nTop: 0,
  sinDato: 0,
  precisionTop25: proporcion({}),
  contactadosAntesVencimiento: proporcion({}),
  diasAnticipacion: { valor: null, n: 0, estado: 'SIN_DATOS' },
  tasaRenovacionContactados: proporcion({}),
  montoRetenido: {
    total: null,
    renovaciones: 0,
    renovacionesSinMonto: 0,
    n: 0,
    pendientes: 0,
    estado: 'SIN_DATOS',
  },
}

/** El bloque (`div` del `dl`) del indicador con ese nombre. */
function indicador(nombre: string): HTMLElement {
  const termino = screen.getByText(nombre, { selector: 'dt' })
  const bloque = termino.parentElement
  if (!bloque) throw new Error(`sin bloque para ${nombre}`)
  return bloque
}

describe('IndicadoresPiloto', () => {
  afterEach(cleanup)

  it('region con nombre "Indicadores del piloto" y los cinco indicadores con los nombres de la ayuda', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const region = screen.getByRole('region', { name: 'Indicadores del piloto' })
    expect(region.tagName).toBe('SECTION')
    expect(region).toHaveAttribute('aria-labelledby')
    const terminos = within(region)
      .getAllByRole('term')
      .map((dt) => dt.textContent)
    expect(terminos).toEqual(NOMBRES)
  })

  it('PARCIAL: valores con coma, n de cada indicador, estados traducidos, lista y corte', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    expect(
      screen.getByText('Lista del mes: Lista septiembre, generada el 1 de septiembre de 2026.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Verificado con datos hasta el 28 de octubre de 2026.')).toBeInTheDocument()

    const precision = within(indicador('Precisión del top 25'))
    expect(precision.getByText('60,0 %')).toBeInTheDocument()
    expect(precision.getByText('12 de 20')).toBeInTheDocument()
    expect(precision.getByText('n = 25')).toBeInTheDocument()
    expect(
      precision.getByText('Parcial: faltan 5 por verificar (20 de 25 verificados)'),
    ).toBeInTheDocument()

    const contactados = within(indicador('Contactados antes del vencimiento'))
    expect(contactados.getByText('72,0 %')).toBeInTheDocument()
    expect(contactados.getByText('18 de 25')).toBeInTheDocument()
    expect(contactados.getByText('n = 25')).toBeInTheDocument()
    expect(contactados.getByText('Completo')).toBeInTheDocument()

    const dias = within(indicador('Días de anticipación'))
    expect(dias.getByText('4,5 días')).toBeInTheDocument()
    expect(dias.getByText('n = 19')).toBeInTheDocument()
    expect(dias.getByText('Completo')).toBeInTheDocument()

    const tasa = within(indicador('Renovación de los contactados'))
    expect(tasa.getByText('41,2 %')).toBeInTheDocument()
    expect(tasa.getByText('7 de 17')).toBeInTheDocument()
    expect(tasa.getByText('n = 21')).toBeInTheDocument()
    expect(tasa.getByText('Parcial: faltan 4 por verificar (17 de 21 verificados)')).toBeInTheDocument()

    const monto = within(indicador('Monto retenido'))
    expect(monto.getByText('$312,50')).toBeInTheDocument()
    expect(monto.getByText('7 renovaciones; 1 sin monto registrado')).toBeInTheDocument()
    // El n del monto cuenta solo a los verificados (17), no a todos los contactados (21).
    expect(monto.getByText('n = 17 contactados ya verificados')).toBeInTheDocument()
    expect(monto.queryByText('n = 17')).not.toBeInTheDocument()
    expect(tasa.queryByText(/contactados ya verificados/)).not.toBeInTheDocument()

    expect(screen.queryByText(POCOS_CASOS)).not.toBeInTheDocument()
    expect(screen.queryByText(/COMPLETO|PARCIAL|PENDIENTE|SIN_DATOS/)).not.toBeInTheDocument()
  })

  it('avisos de sesgo y de cifras no causales siempre visibles', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)
    expect(screen.getByText(AVISO_SESGO)).toBeInTheDocument()
    expect(screen.getByText(AVISO_CAUSAL)).toBeInTheDocument()

    cleanup()
    render(<IndicadoresPiloto piloto={SIN_DATOS} />)
    expect(screen.getByText(AVISO_SESGO)).toBeInTheDocument()
    expect(screen.getByText(AVISO_CAUSAL)).toBeInTheDocument()
  })

  it('COMPLETO: estado "Completo" en todos y monto con punto de miles', () => {
    const completo: DatosPiloto = {
      ...PARCIAL,
      estado: 'COMPLETO',
      precisionTop25: { ...PARCIAL.precisionTop25, pendientes: 0, estado: 'COMPLETO' },
      tasaRenovacionContactados: {
        ...PARCIAL.tasaRenovacionContactados,
        pendientes: 0,
        estado: 'COMPLETO',
      },
      montoRetenido: {
        ...PARCIAL.montoRetenido,
        total: '1450.00',
        renovacionesSinMonto: 0,
        pendientes: 0,
        estado: 'COMPLETO',
      },
    }
    render(<IndicadoresPiloto piloto={completo} />)

    for (const nombre of NOMBRES) {
      expect(within(indicador(nombre)).getByText('Completo')).toBeInTheDocument()
    }
    const monto = within(indicador('Monto retenido'))
    expect(monto.getByText('$1.450,00')).toBeInTheDocument()
    expect(monto.getByText('7 renovaciones')).toBeInTheDocument()
    expect(screen.queryByText(/Parcial|Pendiente/)).not.toBeInTheDocument()
  })

  it('PENDIENTE: sin cifra, texto de pendiente y "Pocos casos" con n < 10', () => {
    const pendiente: DatosPiloto = {
      ...PARCIAL,
      estado: 'PENDIENTE',
      sinDato: 1,
      precisionTop25: proporcion({ n: 24, pendientes: 24, estado: 'PENDIENTE' }),
      diasAnticipacion: { valor: '3.0', n: 8, estado: 'COMPLETO' },
      tasaRenovacionContactados: proporcion({ n: 8, pendientes: 8, estado: 'PENDIENTE' }),
      montoRetenido: { ...SIN_DATOS.montoRetenido, pendientes: 8, estado: 'PENDIENTE' },
    }
    render(<IndicadoresPiloto piloto={pendiente} />)

    const precision = within(indicador('Precisión del top 25'))
    expect(precision.getByText('Sin cifra')).toBeInTheDocument()
    expect(precision.getByText(TEXTO_PENDIENTE)).toBeInTheDocument()
    expect(precision.getByText('n = 24')).toBeInTheDocument()
    expect(precision.queryByText(POCOS_CASOS)).not.toBeInTheDocument()

    const tasa = within(indicador('Renovación de los contactados'))
    expect(tasa.getByText(TEXTO_PENDIENTE)).toBeInTheDocument()
    expect(tasa.getByText(POCOS_CASOS)).toBeInTheDocument()

    const dias = within(indicador('Días de anticipación'))
    expect(dias.getByText('3,0 días')).toBeInTheDocument()
    expect(dias.getByText(POCOS_CASOS)).toBeInTheDocument()

    expect(within(indicador('Monto retenido')).getByText(TEXTO_PENDIENTE)).toBeInTheDocument()
    expect(
      screen.getByText('1 socio del top 25 sin datos de membresía: no cuenta en los casos.'),
    ).toBeInTheDocument()
  })

  it('SIN_DATOS: sin lista, "Sin datos" y n = 0 en los cinco, sin "Pocos casos"', () => {
    render(<IndicadoresPiloto piloto={SIN_DATOS} />)

    expect(screen.getByText('No hay una lista generada en este mes.')).toBeInTheDocument()
    for (const nombre of NOMBRES) {
      const bloque = within(indicador(nombre))
      expect(bloque.getByText('Sin datos')).toBeInTheDocument()
      expect(
        bloque.getByText(nombre === 'Monto retenido' ? 'n = 0 contactados ya verificados' : 'n = 0'),
      ).toBeInTheDocument()
      expect(bloque.getByText('Sin cifra')).toBeInTheDocument()
    }
    expect(screen.queryByText(POCOS_CASOS)).not.toBeInTheDocument()
    expect(screen.queryByText(/Verificado con datos/)).not.toBeInTheDocument()
  })

  it('lista sin fecha de corte → aviso de que todo queda pendiente', () => {
    render(<IndicadoresPiloto piloto={{ ...PARCIAL, corteVerificacion: null }} />)
    expect(
      screen.getByText('Aún no hay fecha de corte para verificar: todo queda pendiente.'),
    ).toBeInTheDocument()
  })

  it('impresion: sin print:hidden y sin cortes dentro de la seccion ni de cada indicador', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const region = screen.getByRole('region', { name: 'Indicadores del piloto' })
    expect(region.closest('.print\\:hidden')).toBeNull()
    expect(region.querySelector('.print\\:hidden')).toBeNull()
    expect(region.className).toMatch(/\bbreak-inside-avoid\b/)
    for (const nombre of NOMBRES) {
      expect(indicador(nombre).className).toMatch(/\bbreak-inside-avoid\b/)
    }
    expect(source).not.toMatch(/print:hidden/)
  })

  it('presentacional: sin api/, hooks de datos, core/http, style ni coma flotante', () => {
    expect(source).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(source).not.toMatch(/from\s+['"][^'"]*\/hooks\/(?!presentacion['"])/)
    expect(source).not.toMatch(/core\/http/)
    expect(source).not.toMatch(/parseFloat|Number\(|toFixed/)
    expect(source).not.toMatch(/\bstyle=\{/)
    expect(source).toMatch(/\bTarjeta\b/)
  })
})
