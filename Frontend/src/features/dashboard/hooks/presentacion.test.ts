// @vitest-environment node
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import type { ResultadoCampania } from '../types'
import { nombreDelMes, porcentaje, resumenResultados } from './presentacion'
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
