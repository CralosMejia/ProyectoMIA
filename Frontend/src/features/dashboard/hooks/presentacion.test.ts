// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type {
  IndicadorDias,
  IndicadoresPiloto,
  IndicadorProporcion,
  ResultadoCampania,
  TramosAnticipacion,
} from '../types'
import {
  anticipacionPiloto,
  decimalConComa,
  detalleAnticipacion,
  embudoPiloto,
  fechaEnPalabras,
  montoUsd,
  nombreDelMes,
  porcentaje,
  porcentajeDecimal,
  resumenResultados,
  textoEstadoPiloto,
} from './presentacion'
import presentacionSource from './presentacion.ts?raw'

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

/** Caso parcial de 2026-09 del handler de MSW, ya mapeado. */
const PILOTO_PARCIAL: IndicadoresPiloto = {
  estado: 'PARCIAL',
  lista: {
    id: 12,
    nombre: 'Ejemplo: Lista septiembre',
    fechaGeneracion: '2026-09-01',
  },
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

const PILOTO_SIN_DATOS: IndicadoresPiloto = {
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

function fila(
  nombre: string,
  gestiones: number,
  gestionesCerradas: number,
  renovaciones: number,
): ResultadoCampania {
  return {
    campaniaId: nombre === 'Sin campaña' ? null : nombre.length,
    nombre,
    gestiones,
    contactados: 0,
    renovaciones,
    gestionesCerradas,
    tasaRenovacion: null,
    casosInsuficientes: true,
  }
}

describe('resumenResultados', () => {
  it('suma renovaron, no renovaron y sin resultado sobre todas las filas (incluida "Sin campaña")', () => {
    expect(
      resumenResultados([fila('A', 12, 10, 4), fila('B', 9, 9, 3), fila('Sin campaña', 3, 0, 0)]),
    ).toEqual({ renovaron: 7, noRenovaron: 12, sinResultado: 5, total: 24 })
  })

  it('lista vacia → todo 0', () => {
    expect(resumenResultados([])).toEqual({
      renovaron: 0,
      noRenovaron: 0,
      sinResultado: 0,
      total: 0,
    })
  })
})

describe('porcentaje', () => {
  it.each([
    [7, 24, '29,2 %'],
    [12, 24, '50,0 %'],
    [5, 24, '20,8 %'],
    [4, 10, '40,0 %'],
    [10, 10, '100,0 %'],
    [1, 3, '33,3 %'],
    [2, 3, '66,7 %'],
    [1, 8, '12,5 %'],
    [0, 0, '0,0 %'],
    [5, 0, '0,0 %'],
  ])('porcentaje(%i, %i) → %s', (parte, total, esperado) => {
    expect(porcentaje(parte, total)).toBe(esperado)
  })
})

describe('nombreDelMes', () => {
  it.each([
    ['2026-01', 'enero de 2026'],
    ['2026-09', 'septiembre de 2026'],
    ['2026-12', 'diciembre de 2026'],
  ])('%s → %s', (mes, esperado) => {
    expect(nombreDelMes(mes)).toBe(esperado)
  })

  it.each(['', '2026-13', '2026-00', '2026-9', 'septiembre', '26-09'])(
    'formato invalido %j → devuelve la entrada tal cual',
    (mes) => {
      expect(nombreDelMes(mes)).toBe(mes)
    },
  )

  it('no usa Date (no depende de la zona horaria del navegador)', () => {
    expect(presentacionSource).not.toMatch(/\bDate\b/)
  })
})

describe('porcentajeDecimal (R-018, decimal 0..1 como texto)', () => {
  it.each([
    ['0.60000000', '60,0 %'],
    ['0.41176471', '41,2 %'],
    ['0.72000000', '72,0 %'],
    ['0.33333333', '33,3 %'],
    ['0.66666667', '66,7 %'],
    ['0.00050000', '0,1 %'],
    ['0.00049999', '0,0 %'],
    ['0.99950000', '100,0 %'],
    ['1', '100,0 %'],
    ['1.00000000', '100,0 %'],
    ['0', '0,0 %'],
  ])('%s → %s', (texto, esperado) => {
    expect(porcentajeDecimal(texto)).toBe(esperado)
  })
})

describe('decimalConComa (R-018, dias de anticipacion)', () => {
  it.each([
    ['4.5', '4,5'],
    ['3', '3,0'],
    ['3.0', '3,0'],
    ['4.45', '4,5'],
    ['4.44', '4,4'],
    ['9.96', '10,0'],
    ['-1.5', '-1,5'],
    ['-0.04', '0,0'],
    ['0', '0,0'],
  ])('%s → %s', (texto, esperado) => {
    expect(decimalConComa(texto)).toBe(esperado)
  })
})

describe('montoUsd (R-018, USD con coma decimal y punto de miles)', () => {
  it.each([
    ['312.50', '$312,50'],
    ['1450.00', '$1.450,00'],
    ['1234567.89', '$1.234.567,89'],
    ['0', '$0,00'],
    ['12.345', '$12,35'],
    ['999.995', '$1.000,00'],
    ['7.5', '$7,50'],
  ])('%s → %s', (texto, esperado) => {
    expect(montoUsd(texto)).toBe(esperado)
  })
})

describe('fechaEnPalabras (R-018)', () => {
  it.each([
    ['2026-09-01', '1 de septiembre de 2026'],
    ['2026-10-28', '28 de octubre de 2026'],
    ['2027-01-15', '15 de enero de 2027'],
  ])('%s → %s', (iso, esperado) => {
    expect(fechaEnPalabras(iso)).toBe(esperado)
  })

  it.each(['', '2026-13-01', '2026-09', '01/09/2026'])('invalida %j → tal cual', (iso) => {
    expect(fechaEnPalabras(iso)).toBe(iso)
  })

  it('no convierte decimales a coma flotante', () => {
    expect(presentacionSource).not.toMatch(/parseFloat|Number\(|toFixed/)
  })
})

describe('embudoPiloto (R-021)', () => {
  it('contactados 12, antes 9, renovaron 4, por confirmar 3 → esos numeros y anchos sobre nTop', () => {
    const piloto: IndicadoresPiloto = {
      ...PILOTO_PARCIAL,
      contactadosAntesVencimiento: proporcion({
        numerador: 9,
        denominador: 25,
        n: 25,
      }),
      tasaRenovacionContactados: proporcion({
        valor: '0.44444444',
        numerador: 4,
        denominador: 9,
        n: 12,
        pendientes: 3,
        estado: 'PARCIAL',
      }),
    }
    expect(embudoPiloto(piloto)).toEqual([
      { etapa: 'Lista del mes', numero: 25, ancho: 100 },
      { etapa: 'Los contactamos', numero: 12, ancho: 48, antesVencimiento: 9 },
      {
        etapa: 'Renovaron',
        numero: 4,
        ancho: 16,
        porConfirmar: 3,
        anchoPorConfirmar: 12,
        porcentaje: '44,4 %',
      },
    ])
  })

  it('caso parcial del handler: contactados = n de la tasa, renovaron = numerador, % del valor', () => {
    const [lista, contactados, renovaron] = embudoPiloto(PILOTO_PARCIAL)
    expect(lista).toEqual({ etapa: 'Lista del mes', numero: 25, ancho: 100 })
    expect(contactados).toEqual({
      etapa: 'Los contactamos',
      numero: 21,
      ancho: 84,
      antesVencimiento: 18,
    })
    expect(renovaron).toEqual({
      etapa: 'Renovaron',
      numero: 7,
      ancho: 28,
      porConfirmar: 4,
      anchoPorConfirmar: 16,
      porcentaje: '41,2 %',
    })
  })

  it('anchos enteros redondeados (1 de 3 → 33; 2 de 3 → 67)', () => {
    const piloto: IndicadoresPiloto = {
      ...PILOTO_SIN_DATOS,
      nTop: 3,
      tasaRenovacionContactados: proporcion({
        numerador: 1,
        n: 2,
        pendientes: 1,
      }),
    }
    const [, contactados, renovaron] = embudoPiloto(piloto)
    expect(contactados.ancho).toBe(67)
    expect(renovaron.ancho).toBe(33)
    expect(renovaron.anchoPorConfirmar).toBe(33)
    expect(renovaron.porcentaje).toBeNull()
  })

  it('nTop = 0 → numeros y anchos en 0, sin porcentaje', () => {
    expect(embudoPiloto(PILOTO_SIN_DATOS)).toEqual([
      { etapa: 'Lista del mes', numero: 0, ancho: 0 },
      { etapa: 'Los contactamos', numero: 0, ancho: 0, antesVencimiento: 0 },
      {
        etapa: 'Renovaron',
        numero: 0,
        ancho: 0,
        porConfirmar: 0,
        anchoPorConfirmar: 0,
        porcentaje: null,
      },
    ])
  })
})

describe('textoEstadoPiloto (R-021)', () => {
  it.each([
    ['COMPLETO', 0, 'Resultado final'],
    ['PARCIAL', 5, 'Faltan 5 socios por confirmar: lo sabremos 30 días después de su vencimiento'],
    ['PENDIENTE', 24, 'Todavía es pronto: el resultado se conoce 30 días después del vencimiento'],
    ['SIN_DATOS', 0, 'Sin datos este mes'],
  ] as const)('%s (%i) → %s', (estado, pendientes, esperado) => {
    expect(textoEstadoPiloto(estado, pendientes)).toBe(esperado)
  })

  it('PARCIAL con 1 pendiente → singular; con 2 → plural', () => {
    expect(textoEstadoPiloto('PARCIAL', 1)).toBe(
      'Falta 1 socio por confirmar: lo sabremos 30 días después de su vencimiento',
    )
    expect(textoEstadoPiloto('PARCIAL', 2)).toBe(
      'Faltan 2 socios por confirmar: lo sabremos 30 días después de su vencimiento',
    )
  })

  it('nunca devuelve el nombre interno del estado', () => {
    for (const estado of ['COMPLETO', 'PARCIAL', 'PENDIENTE', 'SIN_DATOS'] as const) {
      expect(textoEstadoPiloto(estado, 3)).not.toMatch(/COMPLETO|PARCIAL|PENDIENTE|SIN_DATOS/)
    }
  })
})

describe('anticipacionPiloto (R-021)', () => {
  it('"9.5" → antes del vencimiento, llamada a la izquierda del vencimiento', () => {
    expect(anticipacionPiloto('9.5')).toEqual({
      texto: '9,5 días antes del vencimiento',
      frase: 'En promedio, llamamos 9,5 días antes del vencimiento',
      momento: 'antes',
      posicionLlamada: 68,
      posicionVencimiento: 100,
    })
  })

  it('"-2.0" → despues del vencimiento, llamada a la derecha del vencimiento', () => {
    expect(anticipacionPiloto('-2.0')).toEqual({
      texto: '2,0 días después del vencimiento',
      frase: 'En promedio, llamamos 2,0 días después del vencimiento',
      momento: 'despues',
      posicionLlamada: 7,
      posicionVencimiento: 0,
    })
  })

  it.each(['0.0', '0', '-0.04', '0.04'])(
    '%j → el mismo dia, llamada sobre el vencimiento',
    (dias) => {
      expect(anticipacionPiloto(dias)).toEqual({
        texto: 'el mismo día del vencimiento',
        frase: 'En promedio, llamamos el mismo día del vencimiento',
        momento: 'mismoDia',
        posicionLlamada: 100,
        posicionVencimiento: 100,
      })
    },
  )

  it('null → todavia no hay llamadas; sin marca de llamada', () => {
    expect(anticipacionPiloto(null)).toEqual({
      texto: 'Todavía no hay llamadas registradas',
      frase: 'Todavía no hay llamadas registradas',
      momento: null,
      posicionLlamada: null,
      posicionVencimiento: 100,
    })
  })

  it('escala 0..max(30, |valor|): 30 dias → 0; 45 dias → 0; 4.5 → 85', () => {
    expect(anticipacionPiloto('30.0').posicionLlamada).toBe(0)
    expect(anticipacionPiloto('45.0').posicionLlamada).toBe(0)
    expect(anticipacionPiloto('45.0').texto).toBe('45,0 días antes del vencimiento')
    expect(anticipacionPiloto('4.5').posicionLlamada).toBe(85)
    expect(anticipacionPiloto('-45.0').posicionLlamada).toBe(100)
  })

  it('texto no decimal → sin llamadas registradas (no rompe)', () => {
    expect(anticipacionPiloto('abc').posicionLlamada).toBeNull()
  })
})

describe('detalleAnticipacion (R-022)', () => {
  function tramos(q: number, o: number, u: number, m: number): TramosAnticipacion {
    return { quinceOMas: q, deOchoACatorce: o, deUnoASiete: u, mismoDiaODespues: m }
  }

  function conDias(dias: Partial<IndicadorDias>, antes: number): IndicadoresPiloto {
    return {
      ...PILOTO_PARCIAL,
      contactadosAntesVencimiento: proporcion({ numerador: antes, denominador: 25, n: 25 }),
      diasAnticipacion: {
        valor: '4.5',
        n: 19,
        estado: 'COMPLETO',
        minimo: null,
        maximo: null,
        tramos: null,
        ...dias,
      },
    }
  }

  const COMPLETO = conDias(
    { valor: '4.5', n: 19, minimo: -2, maximo: 21, tramos: tramos(2, 5, 8, 4) },
    15,
  )

  it('conteo: antes = llamados antes del vencimiento; el resto, el mismo dia o despues', () => {
    const d = detalleAnticipacion(COMPLETO)

    expect(d.antes).toBe(15)
    expect(d.mismoDiaODespues).toBe(4)
    expect(d.fraseConteo).toBe(
      '15 socios se llamaron antes del vencimiento y 4 el mismo día o después',
    )
  })

  it('conteo en singular con 1 socio', () => {
    const d = detalleAnticipacion(conDias({ n: 2, minimo: 0, maximo: 3 }, 1))

    expect(d.fraseConteo).toBe('1 socio se llamó antes del vencimiento y 1 el mismo día o después')
  })

  it('mismoDiaODespues nunca es negativo', () => {
    expect(detalleAnticipacion(conDias({ n: 2 }, 5)).mismoDiaODespues).toBe(0)
  })

  it('etiqueta del promedio con coma: antes, despues y el mismo dia', () => {
    expect(detalleAnticipacion(COMPLETO).etiquetaPromedio).toBe('Promedio: 4,5 días antes')
    expect(detalleAnticipacion(conDias({ valor: '-2.0' }, 0)).etiquetaPromedio).toBe(
      'Promedio: 2,0 días después',
    )
    expect(detalleAnticipacion(conDias({ valor: '0.0' }, 0)).etiquetaPromedio).toBe(
      'Promedio: el mismo día',
    )
    expect(detalleAnticipacion(conDias({ valor: null, n: 0 }, 0)).etiquetaPromedio).toBeNull()
  })

  it('rango: la mas temprana antes y la mas tardia despues', () => {
    expect(detalleAnticipacion(COMPLETO).fraseRango).toBe(
      'La llamada más temprana fue 21 días antes del vencimiento y la más tardía, 2 días después',
    )
  })

  it('rango: minimo 0 → el mismo dia; 1 dia en singular', () => {
    expect(detalleAnticipacion(conDias({ minimo: 0, maximo: 1 }, 1)).fraseRango).toBe(
      'La llamada más temprana fue 1 día antes del vencimiento y la más tardía, el mismo día',
    )
  })

  it('rango: todas el mismo dia del vencimiento; una sola llamada', () => {
    expect(detalleAnticipacion(conDias({ n: 3, minimo: 0, maximo: 0 }, 0)).fraseRango).toBe(
      'Todas las llamadas fueron el mismo día del vencimiento',
    )
    expect(detalleAnticipacion(conDias({ n: 1, minimo: 5, maximo: 5 }, 1)).fraseRango).toBe(
      'La única llamada fue 5 días antes del vencimiento',
    )
  })

  it('rango: minimo o maximo null → sin frase de rango', () => {
    expect(detalleAnticipacion(conDias({ minimo: null, maximo: null }, 15)).fraseRango).toBeNull()
    expect(detalleAnticipacion(conDias({ minimo: 3, maximo: null }, 15)).fraseRango).toBeNull()
  })

  it('escala de 30 dias: marcas 30, 15, 7 y Vence en posiciones enteras', () => {
    const d = detalleAnticipacion(conDias({ minimo: 1, maximo: 20, tramos: tramos(1, 1, 1, 0) }, 3))

    expect(d.marcas).toEqual([
      { etiqueta: '30 días', posicion: 0, vence: false },
      { etiqueta: '15 días', posicion: 50, vence: false },
      { etiqueta: '7 días', posicion: 77, vence: false },
      { etiqueta: 'Vence', posicion: 100, vence: true },
    ])
    expect(d.posicionPromedio).toBe(85)
  })

  it('escala max(30, maximo) y del otro lado hasta |minimo|; 7 dias queda cerca de Vence', () => {
    const d = detalleAnticipacion(conDias({ valor: '10.0', minimo: -10, maximo: 40 }, 3))

    expect(d.marcas.map((m) => [m.etiqueta, m.posicion])).toEqual([
      ['30 días', 20],
      ['15 días', 50],
      ['Vence', 80],
    ])
    expect(d.posicionPromedio).toBe(60)
    for (const m of d.marcas) expect(Number.isInteger(m.posicion)).toBe(true)
  })

  it('una marca demasiado cerca de la anterior o de Vence se omite (sin solaparse)', () => {
    const d = detalleAnticipacion(conDias({ valor: '50.0', minimo: 1, maximo: 100 }, 3))

    expect(d.marcas.map((m) => m.etiqueta)).toEqual(['30 días', 'Vence'])
  })

  it('sin rango (backend anterior) la escala sale del promedio', () => {
    expect(detalleAnticipacion(conDias({ valor: '45.0' }, 3)).posicionPromedio).toBe(0)
    const despues = detalleAnticipacion(conDias({ valor: '-3.0' }, 0))
    expect(despues.marcas.at(-1)).toEqual({ etiqueta: 'Vence', posicion: 91, vence: true })
    expect(despues.posicionPromedio).toBe(100)
  })

  it('tramos con etiqueta, numero y ancho sobre n', () => {
    expect(detalleAnticipacion(COMPLETO).tramos).toEqual([
      { etiqueta: '15 días o más antes', numero: 2, ancho: 11 },
      { etiqueta: 'Entre 8 y 14 días antes', numero: 5, ancho: 26 },
      { etiqueta: 'Entre 1 y 7 días antes', numero: 8, ancho: 42 },
      { etiqueta: 'El mismo día o después', numero: 4, ancho: 21 },
    ])
  })

  it('n = 0 → anchos en 0 y sin conteo; tramos null → null', () => {
    const vacio = detalleAnticipacion(
      conDias({ valor: null, n: 0, estado: 'SIN_DATOS', tramos: tramos(0, 0, 0, 0) }, 0),
    )
    expect(vacio.tramos?.map((t) => t.ancho)).toEqual([0, 0, 0, 0])
    expect(vacio.fraseConteo).toBeNull()
    expect(vacio.posicionPromedio).toBeNull()
    expect(detalleAnticipacion(conDias({}, 15)).tramos).toBeNull()
  })

  it('lectura literal y resumen en palabras', () => {
    const d = detalleAnticipacion(COMPLETO)

    expect(d.lectura).toBe(
      'Solo cuentan como «antes del vencimiento» las llamadas hechas antes del día en que vence la membresía.',
    )
    expect(d.resumen).toBe(
      'En promedio, llamamos 4,5 días antes del vencimiento. 15 socios se llamaron antes del vencimiento y 4 el mismo día o después. La llamada más temprana fue 21 días antes del vencimiento y la más tardía, 2 días después.',
    )
  })

  it('ningun texto devuelto habla de n =, dinero ni "al menos una semana"', () => {
    for (const piloto of [COMPLETO, conDias({ valor: null, n: 0 }, 0), conDias({}, 15)]) {
      const textos = JSON.stringify(detalleAnticipacion(piloto))
      expect(textos).not.toMatch(/n =|promedio aritmético|\$|USD|monto|al menos una semana/i)
    }
  })
})

describe('token --color-brand (index.css)', () => {
  // Vitest procesa los .css (un import ?raw de index.css llega vacio): se lee del disco.
  const indexCss = readFileSync(new URL('../../../index.css', import.meta.url), 'utf8')
  const theme = /@theme\s*\{([\s\S]*?)\}/.exec(indexCss)?.[1] ?? ''
  const valor = (t: string) => new RegExp(`${t}\\s*:\\s*([^;]+);`).exec(theme)?.[1]?.trim()

  it('@theme declara --color-brand distinto de --color-ink', () => {
    expect(valor('--color-brand')).toBeDefined()
    expect(valor('--color-brand')).not.toBe(valor('--color-ink'))
  })
})
