import type { ResultadoCampania } from '../types'

/** Cifras del grafico "Resultado de las gestiones del mes" (decision (b) de R-012). */
export interface ResumenResultados {
  /** Gestiones cerradas en las que el socio renovo. */
  renovaron: number
  /** Gestiones cerradas en las que el socio no renovo. */
  noRenovaron: number
  /** Gestiones abiertas o sin campaña (sin resultado anotado). */
  sinResultado: number
  /** Todas las gestiones del mes. */
  total: number
}

/**
 * Suma sobre todas las filas por campaña (incluida "Sin campaña"):
 * renovaron = Σ renovaciones · no renovaron = Σ (cerradas − renovaciones) · sin resultado = Σ (gestiones − cerradas).
 */
export function resumenResultados(porCampania: readonly ResultadoCampania[]): ResumenResultados {
  let renovaron = 0
  let noRenovaron = 0
  let sinResultado = 0
  let total = 0
  for (const fila of porCampania) {
    renovaron += fila.renovaciones
    noRenovaron += Math.max(0, fila.gestionesCerradas - fila.renovaciones)
    sinResultado += Math.max(0, fila.gestiones - fila.gestionesCerradas)
    total += fila.gestiones
  }
  return { renovaron, noRenovaron, sinResultado, total }
}

/**
 * Parte sobre total como porcentaje con un decimal y coma: (7, 24) → "29,2 %".
 * Aritmetica entera (decimas de punto porcentual, redondeo a la mitad hacia arriba); total 0 → "0,0 %".
 */
export function porcentaje(parte: number, total: number): string {
  if (total <= 0 || parte <= 0) return '0,0 %'
  const decimas = Math.floor((parte * 2000 + total) / (2 * total))
  return `${Math.floor(decimas / 10)},${decimas % 10} %`
}

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
]

const MES_VALIDO = /^(\d{4})-(0[1-9]|1[0-2])$/

/** "2026-09" → "septiembre de 2026", sin pasar por fechas (no depende de la zona). Invalido → tal cual. */
export function nombreDelMes(mes: string): string {
  const partes = MES_VALIDO.exec(mes)
  if (!partes) return mes
  const [, anio = '', numero = ''] = partes
  return `${MESES[Number.parseInt(numero, 10) - 1]} de ${anio}`
}
