import ExcelJS from 'exceljs'

/**
 * Plantilla oficial de carga SINTETICA para el E2E (decision (l) de R-007).
 *
 * Solo datos ficticios: nombres "SOCIO PRUEBA E2E ..." y cedulas inventadas con verificador
 * modulo 10, unicas por ejecucion. Fechas relativas a hoy (inicio = hoy - 20, vencimiento =
 * hoy + 10) para que los socios entren en la lista con los valores por defecto.
 */

/** Titulos oficiales de la hoja Registros, columnas A..N (mayusculas y tildes exactas). */
export const TITULOS_REGISTROS = [
  'ESTADO DEL REGISTRO',
  'NOMBRES Y APELLIDOS',
  'CÉDULA',
  'CELULAR',
  'CORREO',
  'TIPO DE PLAN',
  'FECHA DE INICIO',
  'FECHA DE VENCIMIENTO',
  'FORMA DE PAGO',
  'N.º DE TRANSACCIÓN',
  'MONTO A FACTURAR (USD)',
  'MONTO COBRADO (USD)',
  'ASISTENCIAS EN EL PERÍODO',
  'OBSERVACIONES',
] as const

const NOMBRES = ['SOCIO PRUEBA E2E UNO', 'SOCIO PRUEBA E2E DOS', 'SOCIO PRUEBA E2E TRES'] as const
const DIAS_DESDE_INICIO = 20
const DIAS_HASTA_VENCIMIENTO = 10
const MS_POR_DIA = 86_400_000

export interface SocioSintetico {
  nombre: string
  cedula: string
}

export interface PlantillaSintetica {
  ruta: string
  socios: SocioSintetico[]
}

/** Digito verificador modulo 10 (coeficientes 2, 1, 2, ... sobre los 9 primeros digitos). */
export function verificadorModulo10(nueveDigitos: string): number {
  let total = 0
  for (let i = 0; i < 9; i++) {
    const producto = Number(nueveDigitos[i]) * (i % 2 === 0 ? 2 : 1)
    total += producto > 9 ? producto - 9 : producto
  }
  return (10 - (total % 10)) % 10
}

/**
 * Cedulas validas, distintas entre si y (en la practica) entre ejecuciones: 8 digitos que
 * salen del reloj y un aleatorio, mas el indice de fila, mas el verificador.
 */
export function cedulasUnicas(cantidad: number, ahora: number = Date.now()): string[] {
  const semilla = (ahora + Math.floor(Math.random() * 1_000_000)) % 100_000_000
  const base = String(semilla).padStart(8, '0')
  return Array.from({ length: cantidad }, (_, i) => {
    const nueve = `${base}${i % 10}`
    return `${nueve}${verificadorModulo10(nueve)}`
  })
}

/** Fecha de hoy (calendario local) desplazada `dias`, como Date a medianoche UTC. */
function hoyMas(dias: number): Date {
  const ahora = new Date()
  const hoyUtc = Date.UTC(ahora.getFullYear(), ahora.getMonth(), ahora.getDate())
  return new Date(hoyUtc + dias * MS_POR_DIA)
}

/** Escribe la plantilla en `ruta` (hoja Registros, 3 filas MENSUAL validas). */
export async function crearPlantillaSintetica(ruta: string): Promise<PlantillaSintetica> {
  const cedulas = cedulasUnicas(NOMBRES.length)
  const socios = NOMBRES.map((nombre, i) => ({ nombre, cedula: cedulas[i] ?? '' }))
  const inicio = hoyMas(-DIAS_DESDE_INICIO)
  const vencimiento = hoyMas(DIAS_HASTA_VENCIMIENTO)

  const libro = new ExcelJS.Workbook()
  const hoja = libro.addWorksheet('Registros')
  hoja.addRow([...TITULOS_REGISTROS])
  socios.forEach((socio, i) => {
    hoja.addRow([
      'NUEVO',
      socio.nombre,
      socio.cedula,
      '',
      `socio.prueba.e2e.${i + 1}@example.com`,
      'MENSUAL',
      inicio,
      vencimiento,
      'EFECTIVO',
      '',
      35,
      35,
      8,
      'Dato ficticio de prueba E2E',
    ])
  })
  hoja.getColumn(7).numFmt = 'yyyy-mm-dd'
  hoja.getColumn(8).numFmt = 'yyyy-mm-dd'

  await libro.xlsx.writeFile(ruta)
  return { ruta, socios }
}
