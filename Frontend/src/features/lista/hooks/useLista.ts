import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { generarLista, obtenerLista, obtenerUltima } from '../api/lista-api'
import type { GenerarListaParams, ListaPriorizada } from '../types'

const MENSAJE_GENERICO = 'No se pudo completar la operación. Intente de nuevo.'
const HORIZONTE_MAXIMO = 31
const FECHA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/
const ENTERO = /^\d+$/

export const HORIZONTE_POR_DEFECTO = '30'
export const TOP_K_POR_DEFECTO = '25'

export const MENSAJE_FECHA_VACIA = 'Indique la fecha de la lista.'
export const MENSAJE_FECHA_INVALIDA = 'Ingrese una fecha válida (AAAA-MM-DD).'
export const MENSAJE_FECHA_PASADA = 'La fecha debe ser hoy o posterior.'
export const MENSAJE_DIAS = `Entre 1 y ${HORIZONTE_MAXIMO} días.`
export const MENSAJE_PRIORITARIOS = 'Debe ser un número entero mayor o igual a 1.'

/** Fecha local del navegador `YYYY-MM-DD` (en la instalacion, la misma que la fecha de negocio). */
export function hoyLocal(ahora: Date = new Date()): string {
  const dosCifras = (n: number) => String(n).padStart(2, '0')
  return `${ahora.getFullYear()}-${dosCifras(ahora.getMonth() + 1)}-${dosCifras(ahora.getDate())}`
}

/** Valores del formulario tal como los escribe el usuario (texto). */
export interface ParametrosLista {
  /** `YYYY-MM-DD`; por defecto hoy; no puede ser anterior a hoy. */
  fechaReferencia: string
  horizonteDias: string
  topK: string
}

export type CampoParametro = keyof ParametrosLista
export type ErroresParametros = Partial<Record<CampoParametro, string>>

export interface UseListaOptions {
  /** Se llama tras generar una lista nueva (p. ej. para refrescar el historial). */
  onGenerada?: (lista: ListaPriorizada) => void
}

export interface UseListaResult {
  parametros: ParametrosLista
  /** Fecha minima permitida (`YYYY-MM-DD`): hoy. */
  fechaMinima: string
  errores: ErroresParametros
  cambiarParametro: (campo: CampoParametro, valor: string) => void
  /** Lista mostrada (la ultima al entrar, la generada o la elegida en el historial). */
  lista: ListaPriorizada | null
  /** Carga inicial de `GET /listas/ultima`. */
  cargandoInicial: boolean
  /** Error de la carga inicial (se ofrece reintentar). */
  errorInicial: string | null
  reintentar: () => void
  /** No hay ninguna lista generada todavia (404 en `/ultima`). */
  sinListas: boolean
  generando: boolean
  cargandoLista: boolean
  /** Error de generar o de abrir una lista del historial. */
  error: string | null
  generar: () => void
  seleccionar: (id: number) => void
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

function enteroValido(texto: string, minimo: number, maximo?: number): number | null {
  const valor = texto.trim()
  if (!ENTERO.test(valor)) return null
  const numero = Number.parseInt(valor, 10)
  if (!Number.isSafeInteger(numero) || numero < minimo) return null
  if (maximo !== undefined && numero > maximo) return null
  return numero
}

function fechaValida(texto: string): boolean {
  const partes = FECHA_ISO.exec(texto)
  if (!partes) return false
  const [, anio, mes, dia] = partes
  const fecha = new Date(`${texto}T00:00:00Z`)
  return (
    !Number.isNaN(fecha.getTime()) &&
    fecha.getUTCFullYear() === Number.parseInt(anio ?? '', 10) &&
    fecha.getUTCMonth() + 1 === Number.parseInt(mes ?? '', 10) &&
    fecha.getUTCDate() === Number.parseInt(dia ?? '', 10)
  )
}

function errorFecha(fecha: string, hoy: string): string | null {
  if (fecha === '') return MENSAJE_FECHA_VACIA
  if (!fechaValida(fecha)) return MENSAJE_FECHA_INVALIDA
  // Comparacion lexicografica valida para `YYYY-MM-DD`.
  if (fecha < hoy) return MENSAJE_FECHA_PASADA
  return null
}

/**
 * Validacion local (no sustituye la del servidor). `hoy` es `YYYY-MM-DD`.
 * Devuelve los parametros o los errores.
 */
export function validarParametros(
  parametros: ParametrosLista,
  hoy: string,
): { params: GenerarListaParams; errores: null } | { params: null; errores: ErroresParametros } {
  const errores: ErroresParametros = {}
  const fecha = parametros.fechaReferencia.trim()
  const fechaError = errorFecha(fecha, hoy)
  if (fechaError !== null) errores.fechaReferencia = fechaError
  const horizonteDias = enteroValido(parametros.horizonteDias, 1, HORIZONTE_MAXIMO)
  if (horizonteDias === null) errores.horizonteDias = MENSAJE_DIAS
  const topK = enteroValido(parametros.topK, 1)
  if (topK === null) errores.topK = MENSAJE_PRIORITARIOS
  if (horizonteDias === null || topK === null || fechaError !== null) {
    return { params: null, errores }
  }
  return { params: { fechaReferencia: fecha, horizonteDias, topK }, errores: null }
}

/**
 * Estado de la pagina Lista (CU-04/CU-05): parametros, generar sin doble envio, carga inicial
 * de la ultima lista y cambio a una lista del historial. Cancela lo pendiente al desmontar.
 */
export function useLista({ onGenerada }: UseListaOptions = {}): UseListaResult {
  const [parametros, setParametros] = useState<ParametrosLista>(() => ({
    fechaReferencia: hoyLocal(),
    horizonteDias: HORIZONTE_POR_DEFECTO,
    topK: TOP_K_POR_DEFECTO,
  }))
  const [errores, setErrores] = useState<ErroresParametros>({})
  const [lista, setLista] = useState<ListaPriorizada | null>(null)
  const [cargandoInicial, setCargandoInicial] = useState(true)
  const [errorInicial, setErrorInicial] = useState<string | null>(null)
  const [intentoInicial, setIntentoInicial] = useState(0)
  const [generando, setGenerando] = useState(false)
  const [cargandoLista, setCargandoLista] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Peticion que decide la lista mostrada: una nueva cancela a la anterior.
  const peticionRef = useRef<AbortController | null>(null)
  // Guarda sincrona contra doble envio (dos clics antes de que React vuelva a pintar).
  const generandoRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    peticionRef.current = controller
    obtenerUltima(controller.signal).then(
      (ultima) => {
        if (controller.signal.aborted) return
        setLista(ultima)
        setErrorInicial(null)
        setCargandoInicial(false)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setErrorInicial(toMessage(reason))
        setCargandoInicial(false)
      },
    )
    return () => {
      controller.abort()
    }
  }, [intentoInicial])

  useEffect(
    () => () => {
      peticionRef.current?.abort()
    },
    [],
  )

  const nuevaPeticion = (): AbortController => {
    peticionRef.current?.abort()
    const controller = new AbortController()
    peticionRef.current = controller
    return controller
  }

  const cambiarParametro = (campo: CampoParametro, valor: string) => {
    setParametros((actual) => ({ ...actual, [campo]: valor }))
    setErrores((actual) => {
      if (!(campo in actual)) return actual
      const siguiente = { ...actual }
      delete siguiente[campo]
      return siguiente
    })
  }

  const reintentar = () => {
    setCargandoInicial(true)
    setErrorInicial(null)
    setIntentoInicial((n) => n + 1)
  }

  const generar = () => {
    if (generandoRef.current) return
    const validacion = validarParametros(parametros, hoyLocal())
    if (validacion.params === null) {
      setErrores(validacion.errores)
      return
    }
    setErrores({})
    generandoRef.current = true
    const controller = nuevaPeticion()
    setError(null)
    setGenerando(true)
    // Una generacion reemplaza a la carga inicial o al cambio de lista pendientes.
    setCargandoInicial(false)
    setCargandoLista(false)
    generarLista(validacion.params, controller.signal).then(
      (nueva) => {
        generandoRef.current = false
        setGenerando(false)
        if (controller.signal.aborted) return
        setLista(nueva)
        setErrorInicial(null)
        onGenerada?.(nueva)
      },
      (reason: unknown) => {
        generandoRef.current = false
        setGenerando(false)
        if (controller.signal.aborted) return
        setError(toMessage(reason))
      },
    )
  }

  const seleccionar = (id: number) => {
    if (generandoRef.current || lista?.id === id) return
    const controller = nuevaPeticion()
    setError(null)
    setCargandoLista(true)
    obtenerLista(id, controller.signal).then(
      (elegida) => {
        if (controller.signal.aborted) return
        setLista(elegida)
        setCargandoLista(false)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setError(toMessage(reason))
        setCargandoLista(false)
      },
    )
  }

  return {
    parametros,
    fechaMinima: hoyLocal(),
    errores,
    cambiarParametro,
    lista,
    cargandoInicial,
    errorInicial,
    reintentar,
    sinListas: !cargandoInicial && errorInicial === null && lista === null,
    generando,
    cargandoLista,
    error,
    generar,
    seleccionar,
  }
}
