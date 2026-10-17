// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { ResultadoCampania } from '../types'
import {
  decimalConComa,
  fechaEnPalabras,
  montoUsd,
  nombreDelMes,
  porcentaje,
  porcentajeDecimal,
  resumenResultados,
} from './presentacion'
import presentacionSource from './presentacion.ts?raw'

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
