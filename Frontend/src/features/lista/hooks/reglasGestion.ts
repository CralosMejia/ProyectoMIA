/**
 * Reglas del formulario de gestion (CU-08, CU-10; decisiones (g), (h) y (k) de R-009).
 *
 * Son las mismas reglas que valida el servidor, probadas con los mismos casos: aqui solo guian
 * al usuario (la validacion del servidor sigue mandando). Funciones puras: "hoy" llega como
 * parametro (`YYYY-MM-DD`, fecha local del navegador) y la aritmetica de fechas es en UTC.
 */
import type {
  RespuestaAceptacion,
  RespuestaOfrecimiento,
  RespuestaRenovacion,
  ResultadoGestionParams,
} from '../types'

/** Dias tras el vencimiento hasta los que se puede programar el seguimiento. */
const DIAS_PLAZO = 30
/** Dias tras el vencimiento de la fecha de seguimiento sugerida. */
const DIAS_SUGERIDA = 25
const MS_POR_DIA = 86_400_000
const FECHA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/

export const MENSAJE_PLAZO_TERMINADO = 'El plazo de seguimiento de este ciclo ya terminó.'
export const MENSAJE_FECHA_SEGUIMIENTO_VACIA = 'Indique la fecha de seguimiento.'
export const MENSAJE_FECHA_INVALIDA = 'Ingrese una fecha válida (AAAA-MM-DD).'
export const MENSAJE_CONTACTADO = 'Indique si se contactó al socio.'
export const MENSAJE_SIN_CAMPANIA =
  'Sin campaña asignada, la oferta y la aceptación deben ser «No aplica».'
export const MENSAJE_NO_CONTACTADO =
  'Si no se contactó al socio, la oferta y la aceptación deben ser «No aplica».'
export const MENSAJE_OFRECIDA = 'Indique si se ofreció la campaña (Sí o No).'
export const MENSAJE_NO_OFRECIDA = 'Si no se ofreció la campaña, la aceptación debe ser «No aplica».'
export const MENSAJE_ACEPTADA = 'Indique si el socio aceptó la campaña (Sí, No o Pendiente).'
export const MENSAJE_FECHA_CONTACTO = 'Indique la fecha del contacto.'
export const MENSAJE_FECHA_CONTACTO_SOBRANTE =
  'Si no se contactó al socio, no indique la fecha del contacto.'
export const MENSAJE_RENOVO = 'Indique si el socio renovó.'

export interface RangoFechas {
  desde: string
  hasta: string
}

/** Fecha local `YYYY-MM-DD` de un instante (en la instalacion, la fecha de negocio de Ecuador). */
export function fechaLocalIso(instante: Date): string {
  const dosCifras = (n: number) => String(n).padStart(2, '0')
  return `${instante.getFullYear()}-${dosCifras(instante.getMonth() + 1)}-${dosCifras(instante.getDate())}`
}

function sumarDias(iso: string, dias: number): string {
  return new Date(Date.parse(`${iso}T00:00:00Z`) + dias * MS_POR_DIA).toISOString().slice(0, 10)
}

function esFechaValida(texto: string): boolean {
  const partes = FECHA_ISO.exec(texto)
  if (!partes) return false
  const fecha = new Date(`${texto}T00:00:00Z`)
  return !Number.isNaN(fecha.getTime()) && fecha.toISOString().slice(0, 10) === texto
}

/** "2026-11-04" → "04/11/2026". */
export function fechaDdMmAaaa(iso: string): string {
  const [anio, mes, dia] = iso.split('-')
  return `${dia}/${mes}/${anio}`
}

/**
 * Rango permitido para la fecha de seguimiento: `[hoy, vencimiento + 30]`.
 * `null` si el plazo ya termino (`vencimiento + 30 < hoy`).
 */
export function rangoSeguimiento(hoy: string, vencimiento: string): RangoFechas | null {
  const hasta = sumarDias(vencimiento, DIAS_PLAZO)
  // Comparacion lexicografica valida para `YYYY-MM-DD`.
  return hasta < hoy ? null : { desde: hoy, hasta }
}

/** Fecha sugerida = `max(vencimiento + 25, hoy)`; `null` si el plazo ya termino. */
export function fechaSugerida(hoy: string, vencimiento: string): string | null {
  if (rangoSeguimiento(hoy, vencimiento) === null) return null
  const sugerida = sumarDias(vencimiento, DIAS_SUGERIDA)
  return sugerida < hoy ? hoy : sugerida
}

/** Mensaje de error de la fecha de seguimiento o `null` si es valida. */
export function validarFechaSeguimiento(
  fecha: string,
  hoy: string,
  vencimiento: string,
): string | null {
  const rango = rangoSeguimiento(hoy, vencimiento)
  if (rango === null) return MENSAJE_PLAZO_TERMINADO
  const valor = fecha.trim()
  if (valor === '') return MENSAJE_FECHA_SEGUIMIENTO_VACIA
  if (!esFechaValida(valor)) return MENSAJE_FECHA_INVALIDA
  if (valor < rango.desde || valor > rango.hasta) {
    return `La fecha de seguimiento debe estar entre el ${fechaDdMmAaaa(rango.desde)} y el ${fechaDdMmAaaa(rango.hasta)}.`
  }
  return null
}

/** Respuestas de "¿Se contactó?", "¿Se ofreció?" y "¿Aceptó?" (null = sin responder). */
export interface RespuestasContacto {
  contactado: boolean | null
  ofrecida: RespuestaOfrecimiento | null
  aceptada: RespuestaAceptacion | null
}

export interface OpcionesPermitidas {
  ofrecida: RespuestaOfrecimiento[]
  aceptada: RespuestaAceptacion[]
}

/**
 * Opciones coherentes de "¿Se ofreció?" y "¿Aceptó?": sin campaña o sin contacto, solo
 * "No aplica"; con campaña y contacto, ofrecida Sí/No, y aceptada segun lo ofrecido.
 */
export function opcionesPermitidas({
  conCampania,
  contactado,
  ofrecida,
}: {
  conCampania: boolean
  contactado: boolean | null
  ofrecida: RespuestaOfrecimiento | null
}): OpcionesPermitidas {
  if (!conCampania || contactado === false) return { ofrecida: ['NO_APLICA'], aceptada: ['NO_APLICA'] }
  if (contactado === null) return { ofrecida: [], aceptada: [] }
  if (ofrecida === 'SI') return { ofrecida: ['SI', 'NO'], aceptada: ['SI', 'NO', 'PENDIENTE'] }
  if (ofrecida === 'NO') return { ofrecida: ['SI', 'NO'], aceptada: ['NO_APLICA'] }
  return { ofrecida: ['SI', 'NO'], aceptada: [] }
}

function ajustar<T>(valor: T | null, permitidas: T[]): T | null {
  if (permitidas.length === 1) return permitidas[0] ?? null
  return valor !== null && permitidas.includes(valor) ? valor : null
}

/**
 * Tras cambiar una respuesta, deja las demas coherentes: una respuesta que ya no se permite se
 * borra y, si solo queda una opcion, se elige sola.
 */
export function ajustarRespuestas(
  conCampania: boolean,
  respuestas: RespuestasContacto,
): RespuestasContacto {
  const { contactado } = respuestas
  const ofrecida = ajustar(
    respuestas.ofrecida,
    opcionesPermitidas({ conCampania, contactado, ofrecida: null }).ofrecida,
  )
  const aceptada = ajustar(
    respuestas.aceptada,
    opcionesPermitidas({ conCampania, contactado, ofrecida }).aceptada,
  )
  return { contactado, ofrecida, aceptada }
}

/** Valores del formulario de resultado tal como estan en pantalla (texto; '' = vacio). */
export interface BorradorResultado {
  contactado: boolean | null
  campaniaOfrecida: RespuestaOfrecimiento | null
  campaniaAceptada: RespuestaAceptacion | null
  renovoDeclarado: RespuestaRenovacion | null
  fechaContacto: string
  observaciones: string
  responsable: string
  fechaSeguimiento: string
}

export interface ContextoResultado {
  conCampania: boolean
  /** Fecha (`YYYY-MM-DD`) en que se asigno la gestion. */
  fechaAsignacion: string
  hoy: string
  vencimiento: string
  /** Fecha de seguimiento guardada; si no cambia, no se envia (el servidor la conserva). */
  fechaSeguimientoActual: string
}

export type CampoResultado =
  | 'contactado'
  | 'campaniaOfrecida'
  | 'campaniaAceptada'
  | 'renovoDeclarado'
  | 'fechaContacto'
  | 'fechaSeguimiento'

export type ErroresResultado = Partial<Record<CampoResultado, string>>

function erroresDeCampania(b: BorradorResultado, conCampania: boolean): ErroresResultado {
  const noAplica = b.campaniaOfrecida === 'NO_APLICA' && b.campaniaAceptada === 'NO_APLICA'
  if (!conCampania) return noAplica ? {} : { campaniaOfrecida: MENSAJE_SIN_CAMPANIA }
  if (b.contactado === false) return noAplica ? {} : { campaniaOfrecida: MENSAJE_NO_CONTACTADO }
  if (b.contactado === null) return {}
  if (b.campaniaOfrecida !== 'SI' && b.campaniaOfrecida !== 'NO') {
    return { campaniaOfrecida: MENSAJE_OFRECIDA }
  }
  if (b.campaniaOfrecida === 'NO') {
    return b.campaniaAceptada === 'NO_APLICA' ? {} : { campaniaAceptada: MENSAJE_NO_OFRECIDA }
  }
  const aceptadaValida =
    b.campaniaAceptada === 'SI' || b.campaniaAceptada === 'NO' || b.campaniaAceptada === 'PENDIENTE'
  return aceptadaValida ? {} : { campaniaAceptada: MENSAJE_ACEPTADA }
}

function errorFechaContacto(b: BorradorResultado, ctx: ContextoResultado): string | null {
  const fecha = b.fechaContacto.trim()
  if (b.contactado === false) return fecha === '' ? null : MENSAJE_FECHA_CONTACTO_SOBRANTE
  if (b.contactado !== true) return null
  if (fecha === '') return MENSAJE_FECHA_CONTACTO
  if (!esFechaValida(fecha)) return MENSAJE_FECHA_INVALIDA
  if (fecha < ctx.fechaAsignacion || fecha > ctx.hoy) {
    return `La fecha del contacto debe estar entre el ${fechaDdMmAaaa(ctx.fechaAsignacion)} y el ${fechaDdMmAaaa(ctx.hoy)}.`
  }
  return null
}

function textoOpcional(texto: string): string | null {
  const recortado = texto.trim()
  return recortado === '' ? null : recortado
}

/**
 * Valida el resultado con las reglas de coherencia de la decision (h). Devuelve los parametros
 * para `PUT /gestiones/{id}/resultado` o los errores por campo. La fecha de seguimiento solo se
 * envia si Renovó = Pendiente y el usuario la cambio (null = el servidor conserva la actual).
 */
export function validarResultado(
  b: BorradorResultado,
  ctx: ContextoResultado,
): { params: ResultadoGestionParams; errores: null } | { params: null; errores: ErroresResultado } {
  const errores: ErroresResultado = { ...erroresDeCampania(b, ctx.conCampania) }
  if (b.contactado === null) errores.contactado = MENSAJE_CONTACTADO
  const fechaContactoError = errorFechaContacto(b, ctx)
  if (fechaContactoError !== null) errores.fechaContacto = fechaContactoError
  if (b.renovoDeclarado === null) errores.renovoDeclarado = MENSAJE_RENOVO
  const fechaSeguimiento = b.fechaSeguimiento.trim()
  const enviaSeguimiento =
    b.renovoDeclarado === 'PENDIENTE' && fechaSeguimiento !== ctx.fechaSeguimientoActual
  if (enviaSeguimiento) {
    const error = validarFechaSeguimiento(fechaSeguimiento, ctx.hoy, ctx.vencimiento)
    if (error !== null) errores.fechaSeguimiento = error
  }

  if (
    Object.keys(errores).length > 0 ||
    b.contactado === null ||
    b.campaniaOfrecida === null ||
    b.campaniaAceptada === null ||
    b.renovoDeclarado === null
  ) {
    return { params: null, errores }
  }
  return {
    params: {
      contactado: b.contactado,
      campaniaOfrecida: b.campaniaOfrecida,
      campaniaAceptada: b.campaniaAceptada,
      renovoDeclarado: b.renovoDeclarado,
      fechaContacto: b.contactado ? b.fechaContacto.trim() : null,
      observaciones: textoOpcional(b.observaciones),
      responsable: textoOpcional(b.responsable),
      fechaSeguimiento: enviaSeguimiento ? fechaSeguimiento : null,
    },
    errores: null,
  }
}
