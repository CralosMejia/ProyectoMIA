import type { EstadoIndicador, IndicadoresPiloto, ResultadoCampania } from '../types'

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

/** Porcentaje entero 0..100 de `parte` sobre `total` (redondeo a la mitad hacia arriba); total 0 → 0. */
function anchoSobre(parte: number, total: number): number {
  if (total <= 0 || parte <= 0) return 0
  return Math.min(100, Math.floor((parte * 200 + total) / (2 * total)))
}

export interface EtapaListaDelMes {
  etapa: 'Lista del mes'
  numero: number
  /** Ancho de la barra, entero 0..100 sobre `nTop`. */
  ancho: number
}

export interface EtapaContactamos {
  etapa: 'Los contactamos'
  numero: number
  ancho: number
  /** Cuantos de los contactados se llamaron antes del vencimiento. */
  antesVencimiento: number
}

export interface EtapaRenovaron {
  etapa: 'Renovaron'
  numero: number
  ancho: number
  /** Contactados cuyo resultado aun no se conoce (tramo rayado). */
  porConfirmar: number
  anchoPorConfirmar: number
  /** Porcentaje sobre los contactados ya confirmados ("41,2 %"); null sin cifra. */
  porcentaje: string | null
}

export type EmbudoPiloto = [EtapaListaDelMes, EtapaContactamos, EtapaRenovaron]

/**
 * Embudo del piloto (R-021, definicion (a)): Lista del mes = nTop; Los contactamos = n de la
 * renovacion de los contactados; Renovaron = su numerador, con los pendientes "por confirmar".
 */
export function embudoPiloto(piloto: IndicadoresPiloto): EmbudoPiloto {
  const { nTop, tasaRenovacionContactados: tasa } = piloto
  return [
    { etapa: 'Lista del mes', numero: nTop, ancho: anchoSobre(nTop, nTop) },
    {
      etapa: 'Los contactamos',
      numero: tasa.n,
      ancho: anchoSobre(tasa.n, nTop),
      antesVencimiento: piloto.contactadosAntesVencimiento.numerador,
    },
    {
      etapa: 'Renovaron',
      numero: tasa.numerador,
      ancho: anchoSobre(tasa.numerador, nTop),
      porConfirmar: tasa.pendientes,
      anchoPorConfirmar: anchoSobre(tasa.pendientes, nTop),
      porcentaje: tasa.valor === null ? null : porcentajeDecimal(tasa.valor),
    },
  ]
}

/** Estado en lenguaje simple (R-021, definicion (b)); nunca el nombre interno. */
export function textoEstadoPiloto(estado: EstadoIndicador, pendientes: number): string {
  switch (estado) {
    case 'COMPLETO':
      return 'Resultado final'
    case 'PARCIAL':
      return pendientes === 1
        ? 'Falta 1 socio por confirmar: lo sabremos 30 días después de su vencimiento'
        : `Faltan ${pendientes} socios por confirmar: lo sabremos 30 días después de su vencimiento`
    case 'PENDIENTE':
      return 'Todavía es pronto: el resultado se conoce 30 días después del vencimiento'
    case 'SIN_DATOS':
      return 'Sin datos este mes'
  }
}

export interface AnticipacionPiloto {
  /** "9,5 días antes del vencimiento" / "… después …" / "el mismo día …" / sin llamadas. */
  texto: string
  /** Frase completa para pantalla: "En promedio, llamamos …". */
  frase: string
  momento: 'antes' | 'despues' | 'mismoDia' | null
  /** Posicion 0..100 de la marca "Llamada"; null sin llamadas. */
  posicionLlamada: number | null
  /** Posicion 0..100 de la marca "Vencimiento" (100 si la llamada va antes; 0 si va despues). */
  posicionVencimiento: number
}

const SIN_LLAMADAS = 'Todavía no hay llamadas registradas'
/** Escala minima de la linea de tiempo, en decimas de dia (30 dias). */
const ESCALA_MINIMA_DECIMAS = 300

/**
 * Linea de tiempo de "¿Con cuánta anticipación?" (R-021, definicion (a)). Todo con decimas de
 * dia enteras sacadas de los digitos del decimal (sin coma flotante); el texto, con coma.
 */
export function anticipacionPiloto(dias: string | null): AnticipacionPiloto {
  const r = dias === null ? null : redondear(dias, 1)
  if (r === null) {
    return {
      texto: SIN_LLAMADAS,
      frase: SIN_LLAMADAS,
      momento: null,
      posicionLlamada: null,
      posicionVencimiento: 100,
    }
  }
  const decimas = Number.parseInt(`${r.entero}${r.fraccion}`, 10)
  // Texto visible: decimalConComa sobre el valor absoluto (el sentido lo dice "antes"/"después").
  const cifra = decimalConComa((dias ?? '').trim().replace(/^-/, ''))
  const escala = Math.max(ESCALA_MINIMA_DECIMAS, decimas)
  const distancia = anchoSobre(decimas, escala)
  let texto: string
  let momento: AnticipacionPiloto['momento']
  let posicionLlamada: number
  let posicionVencimiento: number
  if (decimas === 0) {
    texto = 'el mismo día del vencimiento'
    momento = 'mismoDia'
    posicionLlamada = 100
    posicionVencimiento = 100
  } else if (r.negativo) {
    texto = `${cifra} días después del vencimiento`
    momento = 'despues'
    posicionLlamada = distancia
    posicionVencimiento = 0
  } else {
    texto = `${cifra} días antes del vencimiento`
    momento = 'antes'
    posicionLlamada = 100 - distancia
    posicionVencimiento = 100
  }
  return {
    texto,
    frase: `En promedio, llamamos ${texto}`,
    momento,
    posicionLlamada,
    posicionVencimiento,
  }
}

/** Marca de la escala en dias de "¿Con cuánta anticipación?"; `posicion` entera 0..100. */
export interface MarcaEscala {
  etiqueta: string
  posicion: number
  /** La marca del dia del vencimiento ("Vence"). */
  vence: boolean
}

export interface TramoAnticipacionTexto {
  etiqueta: string
  numero: number
  /** Ancho de la barra, entero 0..100 sobre los llamados con fecha. */
  ancho: number
}

export interface DetalleAnticipacion {
  /** "30 días", "15 días", "7 días" (las que no se solapan) y "Vence". */
  marcas: MarcaEscala[]
  /** "Promedio: 4,5 días antes"; null sin llamadas. */
  etiquetaPromedio: string | null
  /** Posicion 0..100 del promedio en la misma escala; null sin llamadas. */
  posicionPromedio: number | null
  antes: number
  mismoDiaODespues: number
  /** "15 socios se llamaron antes del vencimiento y 4 el mismo día o después"; null sin llamadas. */
  fraseConteo: string | null
  /** La mas temprana y la mas tardia; null sin rango (sin llamadas o backend anterior). */
  fraseRango: string | null
  /** Los cuatro tramos; null si el backend no los envia. */
  tramos: TramoAnticipacionTexto[] | null
  lectura: string
  /** Promedio, conteo y rango en una sola frase (para lectores de pantalla). */
  resumen: string
}

export const LECTURA_ANTICIPACION =
  'Solo cuentan como «antes del vencimiento» las llamadas hechas antes del día en que vence la membresía.'

const MARCAS_DIAS = [30, 15, 7] as const
/** Separacion minima (puntos de 0..100) entre marcas para que sus etiquetas no se solapen. */
const SEPARACION_MINIMA = 16

function dias(cantidad: number): string {
  return `${cantidad} ${cantidad === 1 ? 'día' : 'días'}`
}

/** Dias antes del vencimiento (puede ser <= 0) en palabras; `completo` añade "del vencimiento". */
function momentoEnDias(d: number, completo: boolean): string {
  if (d === 0) return completo ? 'el mismo día del vencimiento' : 'el mismo día'
  const sentido = d > 0 ? 'antes' : 'después'
  return `${dias(Math.abs(d))} ${sentido}${completo ? ' del vencimiento' : ''}`
}

function fraseRango(minimo: number | null, maximo: number | null, n: number): string | null {
  if (minimo === null || maximo === null) return null
  if (minimo === maximo) {
    const sujeto = n === 1 ? 'La única llamada fue' : 'Todas las llamadas fueron'
    return `${sujeto} ${momentoEnDias(maximo, true)}`
  }
  return `La llamada más temprana fue ${momentoEnDias(maximo, true)} y la más tardía, ${momentoEnDias(minimo, false)}`
}

/** Decimas de dia (enteras) de un decimal en texto; null si no es decimal. */
function decimasDe(texto: string | null): number | null {
  const r = texto === null ? null : redondear(texto, 1)
  if (r === null) return null
  const decimas = Number.parseInt(`${r.entero}${r.fraccion}`, 10)
  return r.negativo ? -decimas : decimas
}

/** Dias enteros que cubren `decimas` hacia arriba (sin coma flotante). */
function diasHaciaArriba(decimas: number): number {
  return decimas <= 0 ? 0 : Math.trunc((decimas + 9) / 10)
}

/**
 * Detalle de "¿Con cuánta anticipación?" (R-022, definiciones (b) y (c)). Escala en dias: a la
 * izquierda `max(30, maximo)` dias antes, a la derecha del vencimiento `|minimo|` dias despues si
 * hubo llamadas tarde; posiciones enteras con `anchoSobre`. Antes = llamados antes del
 * vencimiento; el resto de los llamados con fecha, el mismo dia o despues.
 */
export function detalleAnticipacion(piloto: IndicadoresPiloto): DetalleAnticipacion {
  const { diasAnticipacion: d } = piloto
  const decimas = decimasDe(d.valor)
  const antes = piloto.contactadosAntesVencimiento.numerador
  const mismoDiaODespues = Math.max(0, d.n - antes)

  const izquierda = Math.max(30, d.maximo ?? 0, diasHaciaArriba(decimas ?? 0))
  const derecha = Math.max(0, -(d.minimo ?? 0), diasHaciaArriba(-(decimas ?? 0)))
  const total = izquierda + derecha
  const posicion = (diasAntes: number) => anchoSobre(izquierda - diasAntes, total)
  const posicionVence = posicion(0)

  const marcas: MarcaEscala[] = []
  for (const dia of MARCAS_DIAS) {
    const lugar = posicion(dia)
    const anterior = marcas.at(-1)
    const libre =
      (anterior === undefined || lugar - anterior.posicion >= SEPARACION_MINIMA) &&
      posicionVence - lugar >= SEPARACION_MINIMA
    if (libre) marcas.push({ etiqueta: dias(dia), posicion: lugar, vence: false })
  }
  marcas.push({ etiqueta: 'Vence', posicion: posicionVence, vence: true })

  let etiquetaPromedio: string | null = null
  let posicionPromedio: number | null = null
  if (decimas !== null) {
    const cifra = decimalConComa((d.valor ?? '').trim().replace(/^-/, ''))
    etiquetaPromedio =
      decimas === 0
        ? 'Promedio: el mismo día'
        : `Promedio: ${cifra} días ${decimas > 0 ? 'antes' : 'después'}`
    posicionPromedio = anchoSobre(izquierda * 10 - decimas, total * 10)
  }

  const conteo =
    d.n > 0
      ? `${antes} ${antes === 1 ? 'socio se llamó' : 'socios se llamaron'} antes del vencimiento y ${mismoDiaODespues} el mismo día o después`
      : null
  const rango = d.n > 0 ? fraseRango(d.minimo, d.maximo, d.n) : null

  const t = d.tramos
  const tramos =
    t === null
      ? null
      : [
          { etiqueta: '15 días o más antes', numero: t.quinceOMas },
          { etiqueta: 'Entre 8 y 14 días antes', numero: t.deOchoACatorce },
          { etiqueta: 'Entre 1 y 7 días antes', numero: t.deUnoASiete },
          { etiqueta: 'El mismo día o después', numero: t.mismoDiaODespues },
        ].map((tramo) => ({ ...tramo, ancho: anchoSobre(tramo.numero, d.n) }))

  const resumen = [anticipacionPiloto(d.valor).frase, conteo, rango]
    .filter((parte): parte is string => parte !== null)
    .map((parte) => `${parte}.`)
    .join(' ')

  return {
    marcas,
    etiquetaPromedio,
    posicionPromedio,
    antes,
    mismoDiaODespues,
    fraseConteo: conteo,
    fraseRango: rango,
    tramos,
    lectura: LECTURA_ANTICIPACION,
    resumen,
  }
}
