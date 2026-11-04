import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import type { IndicadoresPiloto as DatosPiloto, IndicadorProporcion } from '../types'
import { IndicadoresPiloto } from './IndicadoresPiloto'
import source from './IndicadoresPiloto.tsx?raw'

const TITULO = '¿Cómo le fue a la lista del mes?'
const H3 = [
  '¿Cuántos contactamos y cuántos renovaron?',
  '¿Con cuánta anticipación?',
]
const AVISO_SESGO =
  'Llamar a un socio puede hacer que se quede; por eso algunos que estaban por irse terminan renovando y la cuenta de aciertos puede quedar corta.'
const AVISO_CAUSAL =
  'Estas cifras cuentan lo que pasó; no prueban que la llamada haya causado la renovación.'
const POCOS_CASOS = 'Son pocos socios todavía: tómalo con cuidado'
const PENDIENTE = 'Todavía es pronto: el resultado se conoce 30 días después del vencimiento'

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

/** Caso parcial de 2026-09 (mismo que el handler de MSW). */
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
  diasAnticipacion: { valor: '4.5', n: 19, estado: 'COMPLETO', minimo: null, maximo: null, tramos: null },
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
  diasAnticipacion: { valor: null, n: 0, estado: 'SIN_DATOS', minimo: null, maximo: null, tramos: null },
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

function region() {
  return screen.getByRole('region', { name: TITULO })
}

function grafico(titulo: string) {
  return within(screen.getByRole('region', { name: titulo }))
}

describe('IndicadoresPiloto (R-021)', () => {
  afterEach(cleanup)

  it('region con el h2 nuevo y los dos graficos con sus h3', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const r = region()
    expect(r.tagName).toBe('SECTION')
    expect(r).toHaveAttribute('aria-labelledby', 'piloto-title')
    expect(within(r).getByRole('heading', { level: 2, name: TITULO })).toBeInTheDocument()
    expect(
      within(r)
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(H3)
  })

  it('PARCIAL: embudo con aria-label en palabras, numeros, porcentaje y estado', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const embudo = grafico(H3[0] ?? '')
    expect(
      embudo.getByRole('img', {
        name: '25 socios en la lista del mes, 21 contactados, 18 antes del vencimiento, 7 renovaron y 4 por confirmar',
      }),
    ).toBeInTheDocument()
    expect(embudo.getByText('Lista del mes')).toBeInTheDocument()
    expect(embudo.getByText('Los contactamos')).toBeInTheDocument()
    expect(embudo.getByText('18 antes del vencimiento')).toBeInTheDocument()
    expect(embudo.getByText('41,2 % de los contactados ya confirmados')).toBeInTheDocument()
    const leyenda = within(embudo.getByRole('list', { name: 'Leyenda del embudo' }))
    expect(leyenda.getByText('Por confirmar').parentElement).toHaveTextContent('Por confirmar 4')
    expect(
      embudo.getByText(
        'Faltan 4 socios por confirmar: lo sabremos 30 días después de su vencimiento',
      ),
    ).toBeInTheDocument()

    const barras = region().querySelectorAll<HTMLElement>('[data-barra]')
    const anchos = Object.fromEntries(
      [...barras].map((b) => [b.dataset.barra, b.style.width] as const),
    )
    expect(anchos).toEqual({
      lista: '100%',
      contactados: '84%',
      renovaron: '28%',
      'por-confirmar': '16%',
    })
    // "Por confirmar" se pinta rayado, no con el color de fallo.
    const porConfirmar = region().querySelector('[data-barra="por-confirmar"]')
    expect(porConfirmar?.className).toMatch(/\brayado\b/)
    expect(porConfirmar?.className).not.toMatch(/risk-high|danger/)
  })

  it('cambio del usuario: sin el grafico «¿La lista acertó?» ni sus puntitos (precision no se pinta)', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    expect(screen.queryByRole('region', { name: '¿La lista acertó?' })).toBeNull()
    expect(region().querySelectorAll('[data-punto]')).toHaveLength(0)
    expect(screen.queryByText(/Estaba por irse|Se habría quedado igual|socios ya confirmados/)).toBeNull()
    expect(screen.queryByText(AVISO_SESGO)).toBeNull()
    expect(source).not.toMatch(/puntosPiloto|PuntosAcierto/)
  })

  it('PARCIAL: linea de tiempo con Llamada y Vencimiento y frase con coma', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const anticipacion = grafico('¿Con cuánta anticipación?')
    const img = anticipacion.getByRole('img', {
      name: 'En promedio, llamamos 4,5 días antes del vencimiento. 18 socios se llamaron antes del vencimiento y 1 el mismo día o después.',
    })
    expect(img.querySelector<HTMLElement>('[data-marca="Llamada"]')?.style.left).toBe('85%')
    expect(img.querySelector<HTMLElement>('[data-marca="Vencimiento"]')?.style.left).toBe('100%')
    expect(
      anticipacion.getByText('En promedio, llamamos 4,5 días antes del vencimiento', {
        selector: 'p',
      }),
    ).toBeInTheDocument()
  })

  it('textos prohibidos: sin n =, precision, dinero ni nombres internos de estado', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const texto = region().textContent ?? ''
    const etiquetas = [...region().querySelectorAll('[aria-label]')]
      .map((e) => e.getAttribute('aria-label') ?? '')
      .join(' ')
    for (const t of [texto, etiquetas]) {
      expect(t).not.toMatch(/n = /)
      expect(t).not.toMatch(/precisi[oó]n/i)
      expect(t).not.toMatch(/\$|USD|monto/i)
      expect(t).not.toMatch(/COMPLETO|PARCIAL|PENDIENTE|SIN_DATOS/)
    }
    expect(source).not.toMatch(/montoUsd/)
  })

  it('avisos en lenguaje simple siempre visibles', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)
    expect(screen.getByText(AVISO_CAUSAL)).toBeInTheDocument()

    cleanup()
    render(<IndicadoresPiloto piloto={SIN_DATOS} />)
    expect(screen.getByText(AVISO_CAUSAL)).toBeInTheDocument()
  })

  it('COMPLETO: "Resultado final" en el embudo', () => {
    const completo: DatosPiloto = {
      ...PARCIAL,
      estado: 'COMPLETO',
      precisionTop25: {
        ...PARCIAL.precisionTop25,
        pendientes: 0,
        denominador: 25,
        estado: 'COMPLETO',
      },
      tasaRenovacionContactados: {
        ...PARCIAL.tasaRenovacionContactados,
        pendientes: 0,
        estado: 'COMPLETO',
      },
    }
    render(<IndicadoresPiloto piloto={completo} />)

    expect(grafico(H3[0] ?? '').getByText('Resultado final')).toBeInTheDocument()
    expect(screen.queryByText(/Faltan/)).not.toBeInTheDocument()
  })

  it('PENDIENTE: texto de pendiente y aviso de pocos socios', () => {
    const pendiente: DatosPiloto = {
      ...PARCIAL,
      estado: 'PENDIENTE',
      sinDato: 1,
      precisionTop25: proporcion({ n: 24, pendientes: 24, estado: 'PENDIENTE' }),
      contactadosAntesVencimiento: proporcion({ numerador: 8, denominador: 24, n: 24 }),
      diasAnticipacion: { valor: '3.0', n: 8, estado: 'COMPLETO', minimo: null, maximo: null, tramos: null },
      tasaRenovacionContactados: proporcion({ n: 8, pendientes: 8, estado: 'PENDIENTE' }),
    }
    render(<IndicadoresPiloto piloto={pendiente} />)

    const embudo = grafico(H3[0] ?? '')
    expect(embudo.getByText(PENDIENTE)).toBeInTheDocument()
    expect(embudo.getByText(POCOS_CASOS)).toBeInTheDocument()

    const anticipacion = grafico('¿Con cuánta anticipación?')
    expect(
      anticipacion.getByRole('img', {
        name: 'En promedio, llamamos 3,0 días antes del vencimiento. 8 socios se llamaron antes del vencimiento y 0 el mismo día o después.',
      }),
    ).toBeInTheDocument()
    expect(anticipacion.getByText(POCOS_CASOS)).toBeInTheDocument()
  })

  it('conteos de 1 en singular: estado, aria-label del embudo y promedio', () => {
    const uno: DatosPiloto = {
      ...PARCIAL,
      nTop: 1,
      sinDato: 0,
      precisionTop25: proporcion({
        valor: '1.00000000',
        numerador: 1,
        denominador: 1,
        n: 1,
        pendientes: 1,
        estado: 'PARCIAL',
      }),
      contactadosAntesVencimiento: proporcion({ numerador: 1, denominador: 1, n: 1 }),
      diasAnticipacion: { valor: '2.0', n: 1, estado: 'COMPLETO', minimo: null, maximo: null, tramos: null },
      tasaRenovacionContactados: proporcion({
        valor: '1.00000000',
        numerador: 1,
        denominador: 1,
        n: 1,
        pendientes: 1,
        estado: 'PARCIAL',
      }),
    }
    render(<IndicadoresPiloto piloto={uno} />)

    expect(
      screen.getAllByText(
        'Falta 1 socio por confirmar: lo sabremos 30 días después de su vencimiento',
      ),
    ).toHaveLength(1)
    expect(
      screen.getByRole('img', {
        name: '1 socio en la lista del mes, 1 contactado, 1 antes del vencimiento, 1 renovó y 1 por confirmar',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('Promedio de 1 socio llamado.')).toBeInTheDocument()
    expect(
      screen.queryByText(/Faltan 1 |1 contactados|1 renovaron/),
    ).toBeNull()
  })

  it('conteos de 2 en plural', () => {
    const dos: DatosPiloto = {
      ...PARCIAL,
      precisionTop25: proporcion({
        valor: '0.50000000',
        numerador: 1,
        denominador: 2,
        n: 25,
        pendientes: 2,
        estado: 'PARCIAL',
      }),
      diasAnticipacion: { valor: '2.0', n: 2, estado: 'COMPLETO', minimo: null, maximo: null, tramos: null },
    }
    render(<IndicadoresPiloto piloto={dos} />)

    expect(screen.getByText('Promedio de 2 socios llamados.')).toBeInTheDocument()
  })

  it('anticipacion negativa → despues del vencimiento; null → sin llamadas registradas', () => {
    render(
      <IndicadoresPiloto
        piloto={{ ...PARCIAL, diasAnticipacion: { valor: '-2.0', n: 12, estado: 'COMPLETO', minimo: null, maximo: null, tramos: null } }}
      />,
    )
    expect(
      screen.getByRole('img', {
        name: 'En promedio, llamamos 2,0 días después del vencimiento. 18 socios se llamaron antes del vencimiento y 0 el mismo día o después.',
      }),
    ).toBeInTheDocument()

    cleanup()
    render(
      <IndicadoresPiloto
        piloto={{ ...PARCIAL, diasAnticipacion: { valor: null, n: 0, estado: 'PENDIENTE', minimo: null, maximo: null, tramos: null } }}
      />,
    )
    const img = screen.getByRole('img', { name: 'Todavía no hay llamadas registradas.' })
    expect(img.querySelector('[data-marca="Llamada"]')).toBeNull()
  })

  it('SIN_DATOS: sin lista y los dos graficos en "Sin datos este mes" sin romperse', () => {
    render(<IndicadoresPiloto piloto={SIN_DATOS} />)

    expect(screen.getByText('No hay una lista generada en este mes.')).toBeInTheDocument()
    for (const titulo of H3) {
      expect(grafico(titulo).getByText('Sin datos este mes')).toBeInTheDocument()
    }
    expect(region().querySelectorAll('[data-punto]')).toHaveLength(0)
    for (const barra of region().querySelectorAll<HTMLElement>('[data-barra]')) {
      expect(barra.style.width).toBe('0%')
    }
    expect(screen.queryByText(POCOS_CASOS)).not.toBeInTheDocument()
  })

  it('impresion y telefono: sin cortes, una columna por defecto y dos en lg', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const r = region()
    expect(r.closest('.print\\:hidden')).toBeNull()
    expect(r.className).toMatch(/\bbreak-inside-avoid\b/)
    for (const titulo of H3) {
      expect(screen.getByRole('region', { name: titulo }).className).toMatch(
        /\bbreak-inside-avoid\b/,
      )
    }
    const rejilla = screen.getByRole('region', { name: H3[0] }).parentElement
    expect(rejilla?.className).toMatch(/\bgrid-cols-1\b/)
    expect(rejilla?.className).toMatch(/\blg:grid-cols-2\b/)
    // Lo unico que no se imprime es el boton "¿Cómo se calcula?".
    const ocultos = [...r.querySelectorAll('.print\\:hidden')]
    expect(ocultos).toHaveLength(1)
    expect(ocultos[0]).toContainElement(screen.getByRole('button', { name: '¿Cómo se calcula?' }))
    expect(ocultos[0]?.textContent).toBe('¿Cómo se calcula?')
  })

  it('"¿Cómo se calcula?" abre las definiciones exactas y devuelve el foco al cerrar', async () => {
    const user = userEvent.setup()
    render(<IndicadoresPiloto piloto={PARCIAL} />)
    const boton = screen.getByRole('button', { name: '¿Cómo se calcula?' })

    await user.click(boton)
    const dialogo = screen.getByRole('dialog', { name: '¿Cómo se calcula?' })
    const texto = (dialogo.textContent ?? '').replace(/\s+/g, ' ')
    expect(texto).toMatch(
      /Contactados antes del vencimiento: socios contactados antes de su fecha de vencimiento ÷ socios con datos de membresía/,
    )
    expect(texto).toMatch(
      /Días de anticipación: promedio de \(fecha de vencimiento − fecha del contacto\), con un decimal\. Puede ser cero o negativo/,
    )
    expect(texto).toMatch(
      /Renovación de los contactados: contactados que renovaron ÷ contactados ya verificados/,
    )
    expect(texto).toMatch(/«n» es el número de socios con el que se calcula cada cifra/)
    expect(texto).toMatch(/30 días después del vencimiento/)
    expect(texto).not.toMatch(/precisi[oó]n|¿La lista acertó\?/)
    expect(texto).toMatch(/no prueban que la llamada cause la renovación/)
    expect(texto).not.toMatch(/\$|USD|monto|cobr|factur/i)

    await user.click(within(dialogo).getByRole('button', { name: 'Cerrar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton).toHaveFocus()

    await user.click(boton)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton).toHaveFocus()
  })

  it('presentacional: sin api/, hooks de datos, core/http ni coma flotante; style solo width/left', () => {
    expect(source).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(source).not.toMatch(/from\s+['"][^'"]*\/hooks\/(?!presentacion['"])/)
    expect(source).not.toMatch(/core\/http/)
    expect(source).not.toMatch(/parseFloat|Number\(|toFixed/)
    expect(source).not.toMatch(/dangerouslySetInnerHTML/)
    // Todo `style=` es exactamente un ancho o una posicion calculada en %.
    const todos = source.match(/\bstyle=/g) ?? []
    const permitidos = source.match(/\bstyle=\{\{ (?:width|left): `\$\{[\w.]+\}%` \}\}/g) ?? []
    expect(todos.length).toBeGreaterThan(0)
    expect(permitidos).toHaveLength(todos.length)
    expect(source).toMatch(/\bTarjeta\b/)
  })
})

/** R-022: rango y tramos del caso 2026-09 del handler (19 llamados, 18 antes del vencimiento). */
const CON_TRAMOS: DatosPiloto = {
  ...PARCIAL,
  diasAnticipacion: {
    valor: '4.5',
    n: 19,
    estado: 'COMPLETO',
    minimo: -1,
    maximo: 16,
    tramos: { quinceOMas: 1, deOchoACatorce: 4, deUnoASiete: 13, mismoDiaODespues: 1 },
  },
}
const RESUMEN_CON_TRAMOS =
  'En promedio, llamamos 4,5 días antes del vencimiento. 18 socios se llamaron antes del vencimiento y 1 el mismo día o después. La llamada más temprana fue 16 días antes del vencimiento y la más tardía, 1 día después.'
const LECTURA =
  'Solo cuentan como «antes del vencimiento» las llamadas hechas antes del día en que vence la membresía.'

describe('IndicadoresPiloto: ¿Con cuánta anticipación? (R-022)', () => {
  afterEach(cleanup)

  it('escala en dias con 30, 15, 7 y Vence, y la etiqueta del promedio', () => {
    render(<IndicadoresPiloto piloto={CON_TRAMOS} />)

    const img = grafico('¿Con cuánta anticipación?').getByRole('img', { name: RESUMEN_CON_TRAMOS })
    const dibujo = within(img)
    for (const etiqueta of ['30 días', '15 días', '7 días', 'Vence']) {
      expect(dibujo.getByText(etiqueta)).toBeInTheDocument()
    }
    expect(dibujo.getByText('Promedio: 4,5 días antes')).toBeInTheDocument()
    expect(img.querySelector<HTMLElement>('[data-marca="30 días"]')?.style.left).toBe('0%')
    expect(img.querySelector<HTMLElement>('[data-marca="Vencimiento"]')?.style.left).toBe('97%')
    expect(img.querySelector<HTMLElement>('[data-marca="Llamada"]')?.style.left).toBe('82%')
  })

  it('frases de conteo, rango y lectura en lenguaje simple', () => {
    render(<IndicadoresPiloto piloto={CON_TRAMOS} />)

    const anticipacion = grafico('¿Con cuánta anticipación?')
    expect(
      anticipacion.getByText(
        '18 socios se llamaron antes del vencimiento y 1 el mismo día o después.',
      ),
    ).toBeInTheDocument()
    expect(
      anticipacion.getByText(
        'La llamada más temprana fue 16 días antes del vencimiento y la más tardía, 1 día después.',
      ),
    ).toBeInTheDocument()
    expect(anticipacion.getByText(LECTURA)).toBeInTheDocument()
  })

  it('los cuatro tramos como lista legible, con leyenda y numero', () => {
    render(<IndicadoresPiloto piloto={CON_TRAMOS} />)

    const lista = grafico('¿Con cuánta anticipación?').getByRole('list', {
      name: 'Llamadas según los días antes del vencimiento',
    })
    expect(lista.tagName).toBe('UL')
    expect(lista.className).toMatch(/\bflex-col\b/)
    const items = within(lista).getAllByRole('listitem')
    expect(items.map((li) => [...li.querySelectorAll('span')].map((e) => e.textContent))).toEqual([
      ['15 días o más antes', '1'],
      ['Entre 8 y 14 días antes', '4'],
      ['Entre 1 y 7 días antes', '13'],
      ['El mismo día o después', '1'],
    ])
    const barras = [...lista.querySelectorAll<HTMLElement>('[data-tramo]')]
    expect(barras.map((b) => b.style.width)).toEqual(['5%', '21%', '68%', '5%'])
    // "El mismo dia o despues" se distingue por la forma (rayado), no solo por el color.
    expect(barras[3]?.className).toMatch(/\brayado\b/)
    expect(barras[0]?.className).not.toMatch(/\brayado\b/)
  })

  it('contraste: linea base solida sin opacidad y "Vence" con forma propia y negrita', () => {
    render(<IndicadoresPiloto piloto={CON_TRAMOS} />)

    const img = grafico('¿Con cuánta anticipación?').getByRole('img')
    const linea = img.querySelector<HTMLElement>('[data-linea-anticipacion]')
    // Trazo con currentColor: el oscuro automatico invierte el texto y la linea lo sigue.
    expect(linea?.className).toMatch(/\bborder-t-2\b/)
    expect(linea?.className).toMatch(/\bborder-current\b/)
    expect(linea?.className).not.toMatch(/\/\d+\b/)
    expect(source).not.toMatch(/bg-ink\/20/)
    const vence = img.querySelector<HTMLElement>('[data-marca="Vencimiento"]')
    const formaVence = vence?.querySelector<HTMLElement>('[data-forma-anticipacion]')
    const formaDia = img
      .querySelector<HTMLElement>('[data-marca="15 días"]')
      ?.querySelector<HTMLElement>('[data-forma-anticipacion]')
    expect(formaVence?.className).not.toBe(formaDia?.className)
    expect(formaVence?.className).toMatch(/\bborder-l-4\b/)
    expect(within(img).getByText('Vence').className).toMatch(/\bfont-semibold\b/)
  })

  it('una sola llamada antes del vencimiento → "1 socio se llamó"; el mismo dia en el rango', () => {
    const uno: DatosPiloto = {
      ...PARCIAL,
      contactadosAntesVencimiento: proporcion({ numerador: 1, denominador: 2, n: 2 }),
      diasAnticipacion: {
        valor: '2.5',
        n: 2,
        estado: 'COMPLETO',
        minimo: 0,
        maximo: 5,
        tramos: { quinceOMas: 0, deOchoACatorce: 0, deUnoASiete: 1, mismoDiaODespues: 1 },
      },
    }
    render(<IndicadoresPiloto piloto={uno} />)

    const anticipacion = grafico('¿Con cuánta anticipación?')
    expect(
      anticipacion.getByText('1 socio se llamó antes del vencimiento y 1 el mismo día o después.'),
    ).toBeInTheDocument()
    expect(
      anticipacion.getByText(
        'La llamada más temprana fue 5 días antes del vencimiento y la más tardía, el mismo día.',
      ),
    ).toBeInTheDocument()
  })

  it('backend anterior (tramos null) → sin tramos ni rango, sin romperse', () => {
    render(<IndicadoresPiloto piloto={PARCIAL} />)

    const anticipacion = grafico('¿Con cuánta anticipación?')
    expect(
      anticipacion.queryByRole('list', { name: 'Llamadas según los días antes del vencimiento' }),
    ).toBeNull()
    expect(anticipacion.queryByText(/más temprana/)).toBeNull()
    expect(anticipacion.getByText('Vence')).toBeInTheDocument()
  })

  it('n = 0 → sin tramos, rango ni conteo; SIN_DATOS → "Sin datos este mes"', () => {
    const vacio: DatosPiloto = {
      ...SIN_DATOS,
      diasAnticipacion: {
        valor: null,
        n: 0,
        estado: 'SIN_DATOS',
        minimo: null,
        maximo: null,
        tramos: { quinceOMas: 0, deOchoACatorce: 0, deUnoASiete: 0, mismoDiaODespues: 0 },
      },
    }
    render(<IndicadoresPiloto piloto={vacio} />)

    const anticipacion = grafico('¿Con cuánta anticipación?')
    expect(anticipacion.queryByRole('list')).toBeNull()
    expect(anticipacion.queryByText(/se llamaron|se llamó|más temprana/)).toBeNull()
    expect(anticipacion.getByText('Sin datos este mes')).toBeInTheDocument()
  })

  it('textos prohibidos en la region con rango y tramos', () => {
    render(<IndicadoresPiloto piloto={CON_TRAMOS} />)

    const texto = region().textContent ?? ''
    const etiquetas = [...region().querySelectorAll('[aria-label]')]
      .map((e) => e.getAttribute('aria-label') ?? '')
      .join(' ')
    for (const t of [texto, etiquetas]) {
      expect(t).not.toMatch(/n = /)
      expect(t).not.toMatch(/\$|USD|monto/i)
      expect(t).not.toMatch(/COMPLETO|PARCIAL|PENDIENTE|SIN_DATOS/)
      expect(t).not.toMatch(/al menos una semana/i)
    }
  })
})
