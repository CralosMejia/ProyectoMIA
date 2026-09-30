/**
 * Formato corto de fechas `YYYY-MM-DD` para la pantalla Lista.
 *
 * Meses abreviados con una tabla fija (sin punto final): no depende del ICU del navegador,
 * que en es-EC da "sept.". Toda la aritmetica es en UTC para no desplazar el dia por zona
 * horaria. Funciones puras: no leen el reloj.
 */

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const MS_POR_DIA = 86_400_000

interface Partes {
  dia: number
  mes: string
  anio: number
}

function aFecha(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`)
}

function partes(fecha: Date): Partes {
  return {
    dia: fecha.getUTCDate(),
    mes: MESES[fecha.getUTCMonth()] ?? '',
    anio: fecha.getUTCFullYear(),
  }
}

/** "2026-09-29" → "29 sep 2026". */
export function fechaCorta(iso: string): string {
  const { dia, mes, anio } = partes(aFecha(iso))
  return `${dia} ${mes} ${anio}`
}

/**
 * Rango desde `isoDesde` hasta `isoDesde + dias`: "29 sep – 29 oct 2026"; si cruza de año,
 * ambos años: "20 dic 2026 – 10 ene 2027".
 */
export function rangoFechas(isoDesde: string, dias: number): string {
  const desde = aFecha(isoDesde)
  const inicio = partes(desde)
  const fin = partes(new Date(desde.getTime() + dias * MS_POR_DIA))
  const textoInicio =
    inicio.anio === fin.anio
      ? `${inicio.dia} ${inicio.mes}`
      : `${inicio.dia} ${inicio.mes} ${inicio.anio}`
  return `${textoInicio} – ${fin.dia} ${fin.mes} ${fin.anio}`
}
