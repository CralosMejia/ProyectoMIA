import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { fechaCorta, rangoFechas } from './formatoFechas'
import fuente from './formatoFechas.ts?raw'

const TZ_ORIGINAL = process.env.TZ

describe.each(['America/Guayaquil', 'UTC'])('formatoFechas con TZ=%s', (zona) => {
  beforeEach(() => {
    process.env.TZ = zona
  })

  afterEach(() => {
    if (TZ_ORIGINAL === undefined) delete process.env.TZ
    else process.env.TZ = TZ_ORIGINAL
  })

  it('la zona del proceso esta aplicada', () => {
    const desfase = new Date('2026-09-29T12:00:00Z').getTimezoneOffset()
    expect(desfase).toBe(zona === 'UTC' ? 0 : 300)
  })

  it.each([
    ['2026-09-29', '29 sep 2026'],
    ['2026-01-05', '5 ene 2026'],
    ['2026-12-31', '31 dic 2026'],
    ['2027-01-01', '1 ene 2027'],
  ])('fechaCorta(%j) → %j', (iso, esperado) => {
    expect(fechaCorta(iso)).toBe(esperado)
  })

  it('los doce meses usan la abreviatura fija, sin punto', () => {
    const meses = Array.from({ length: 12 }, (_, i) =>
      fechaCorta(`2026-${String(i + 1).padStart(2, '0')}-15`),
    )
    expect(meses).toEqual([
      '15 ene 2026',
      '15 feb 2026',
      '15 mar 2026',
      '15 abr 2026',
      '15 may 2026',
      '15 jun 2026',
      '15 jul 2026',
      '15 ago 2026',
      '15 sep 2026',
      '15 oct 2026',
      '15 nov 2026',
      '15 dic 2026',
    ])
  })

  it.each([
    ['2026-09-29', 30, '29 sep – 29 oct 2026'],
    ['2026-12-20', 21, '20 dic 2026 – 10 ene 2027'],
    ['2026-10-01', 14, '1 oct – 15 oct 2026'],
    ['2026-02-28', 1, '28 feb – 1 mar 2026'],
  ])('rangoFechas(%j, %i) → %j', (iso, dias, esperado) => {
    expect(rangoFechas(iso, dias)).toBe(esperado)
  })
})

it('funciones puras: no leen el reloj', () => {
  expect(fuente).not.toMatch(/Date\.now|new Date\(\s*\)/)
})
