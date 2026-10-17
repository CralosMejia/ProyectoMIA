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

const FECHA_VALIDA = /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/

/** "2026-09-01" → "1 de septiembre de 2026", sin pasar por fechas. Invalida → tal cual. */
export function fechaEnPalabras(iso: string): string {
  const partes = FECHA_VALIDA.exec(iso)
  if (!partes) return iso
  const [, anio = '', numero = '', dia = ''] = partes
  return `${Number.parseInt(dia, 10)} de ${MESES[Number.parseInt(numero, 10) - 1]} de ${anio}`
}

const DECIMAL = /^(-?)(\d+)(?:\.(\d*))?$/

interface DecimalRedondeado {
  negativo: boolean
  entero: string
  fraccion: string
}

/**
 * Redondea un decimal en texto a `decimales` cifras (a la mitad, alejandose del cero) operando
 * con sus digitos, nunca con coma flotante. `desplazar` multiplica por 10^desplazar antes
 * (2 → porcentaje). Texto no decimal → null.
 */
function redondear(texto: string, decimales: number, desplazar = 0): DecimalRedondeado | null {
  const partes = DECIMAL.exec(texto.trim())
  if (!partes) return null
  const [, signo = '', ent = '0', frac = ''] = partes
  const fraccion = frac.padEnd(desplazar + decimales + 1, '0')
  const cifras = `${ent}${fraccion.slice(0, desplazar + decimales)}`
    .split('')
    .map((c) => Number.parseInt(c, 10))
  if ((fraccion[desplazar + decimales] ?? '0') >= '5') {
    let i = cifras.length - 1
    while (i >= 0 && cifras[i] === 9) {
      cifras[i] = 0
      i -= 1
    }
    if (i >= 0) cifras[i] = (cifras[i] ?? 0) + 1
    else cifras.unshift(1)
  }
  const todas = cifras.join('')
  const entero = todas.slice(0, todas.length - decimales).replace(/^0+(?=\d)/, '') || '0'
  const decimalesTexto = decimales > 0 ? todas.slice(todas.length - decimales) : ''
  const esCero = /^0*$/.test(todas)
  return { negativo: signo === '-' && !esCero, entero, fraccion: decimalesTexto }
}

/** Decimal exacto 0..1 como texto → porcentaje con un decimal y coma: "0.41176471" → "41,2 %". */
export function porcentajeDecimal(texto: string): string {
  const r = redondear(texto, 1, 2)
  if (!r) return texto
  return `${r.negativo ? '-' : ''}${r.entero},${r.fraccion} %`
}

/** Decimal como texto → un decimal con coma: "4.5" → "4,5"; "-1.5" → "-1,5". */
export function decimalConComa(texto: string): string {
  const r = redondear(texto, 1)
  if (!r) return texto
  return `${r.negativo ? '-' : ''}${r.entero},${r.fraccion}`
}

/** Monto en USD como texto → formato es-EC: "1234567.89" → "$1.234.567,89". */
export function montoUsd(texto: string): string {
  const r = redondear(texto, 2)
  if (!r) return texto
  const miles = r.entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${r.negativo ? '-' : ''}$${miles},${r.fraccion}`
}
