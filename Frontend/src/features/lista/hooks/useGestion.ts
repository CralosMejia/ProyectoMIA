import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import {
  crearGestion,
  getCampaniasSugeridas,
  getGestion,
  registrarResultado,
} from '../api/lista-api'
import type {
  CampaniaSugerida,
  DatosNuevaGestion,
  Gestion,
  Prediccion,
  ResultadoGestionParams,
} from '../types'
import { fechaLocalIso } from './reglasGestion'

const MENSAJE_GENERICO = 'No se pudo completar la operación. Intente de nuevo.'

/**
 * `inactivo`: ventana cerrada · `cargando`: pide sugeridas o la gestion · `listo`: formulario
 * disponible · `enviando`: crear o registrar en curso · `error`: fallo la carga (se puede reintentar).
 */
export type EstadoVentanaGestion = 'inactivo' | 'cargando' | 'listo' | 'enviando' | 'error'

export interface UseGestionOptions {
  /** Se llama tras crear la gestion o registrar su resultado (p. ej. para recargar la lista). */
  onGuardada?: (gestion: Gestion) => void
}

export interface UseGestionResult {
  /** Socio de la lista cuya gestion esta abierta; `null` = ventana cerrada. */
  prediccion: Prediccion | null
  estado: EstadoVentanaGestion
  /** Campañas sugeridas (solo si el socio aun no tiene gestion). */
  sugeridas: CampaniaSugerida[]
  /** Gestion existente o recien creada; `null` mientras no exista. */
  gestion: Gestion | null
  /** Error de la carga o del ultimo envio, con el mensaje del servidor. */
  error: string | null
  /** Fecha local `YYYY-MM-DD` al abrir (la del formulario). */
  hoy: string
  abrir: (prediccion: Prediccion) => void
  reintentar: () => void
  cerrar: () => void
  /** Crea la gestion; devuelve la creada o `null` si fallo o ya habia un envio en curso. */
  crear: (datos: DatosNuevaGestion) => Promise<Gestion | null>
  /** Registra el resultado; devuelve la gestion o `null` si fallo o ya habia un envio en curso. */
  registrar: (datos: ResultadoGestionParams) => Promise<Gestion | null>
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

/**
 * Estado de la ventana de gestion de un socio de la lista (CU-07, CU-08, CU-10): al abrir carga
 * las campañas sugeridas (sin gestion) o la gestion existente; crea y registra sin doble envio.
 * Cerrar, abrir otro socio o desmontar cancela lo pendiente.
 */
export function useGestion({ onGuardada }: UseGestionOptions = {}): UseGestionResult {
  const [prediccion, setPrediccion] = useState<Prediccion | null>(null)
  const [estado, setEstado] = useState<EstadoVentanaGestion>('inactivo')
  const [sugeridas, setSugeridas] = useState<CampaniaSugerida[]>([])
  const [gestion, setGestion] = useState<Gestion | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hoy, setHoy] = useState(() => fechaLocalIso(new Date()))
  const peticionRef = useRef<AbortController | null>(null)
  // Guarda sincrona contra doble envio (dos clics antes de que React vuelva a pintar).
  const enviandoRef = useRef(false)

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

  const cargar = (p: Prediccion) => {
    const { signal } = nuevaPeticion()
    enviandoRef.current = false
    setEstado('cargando')
    setError(null)
    setGestion(null)
    setSugeridas([])
    const carga =
      p.gestionId === null
        ? getCampaniasSugeridas(p.prediccionId, signal).then((s) => {
            if (!signal.aborted) setSugeridas(s)
          })
        : getGestion(p.gestionId, signal).then((g) => {
            if (!signal.aborted) setGestion(g)
          })
    carga.then(
      () => {
        if (!signal.aborted) setEstado('listo')
      },
      (reason: unknown) => {
        if (signal.aborted) return
        setError(toMessage(reason))
        setEstado('error')
      },
    )
  }

  const abrir = (p: Prediccion) => {
    setPrediccion(p)
    setHoy(fechaLocalIso(new Date()))
    cargar(p)
  }

  const reintentar = () => {
    if (prediccion !== null) cargar(prediccion)
  }

  // Estable a proposito: el `Modal` vuelve a enfocar el dialogo cada vez que cambia su `onClose`,
  // y un `cerrar` nuevo en cada render le quitaria el foco al campo que se esta usando.
  const cerrar = useCallback(() => {
    peticionRef.current?.abort()
    enviandoRef.current = false
    setPrediccion(null)
    setEstado('inactivo')
    setSugeridas([])
    setGestion(null)
    setError(null)
  }, [])

  const enviar = async (
    peticion: (signal: AbortSignal) => Promise<Gestion>,
  ): Promise<Gestion | null> => {
    if (enviandoRef.current) return null
    enviandoRef.current = true
    const { signal } = nuevaPeticion()
    setEstado('enviando')
    setError(null)
    try {
      const guardada = await peticion(signal)
      if (signal.aborted) return null
      setGestion(guardada)
      setEstado('listo')
      onGuardada?.(guardada)
      return guardada
    } catch (reason: unknown) {
      if (signal.aborted) return null
      setError(toMessage(reason))
      setEstado('listo')
      return null
    } finally {
      if (!signal.aborted) enviandoRef.current = false
    }
  }

  const crear = (datos: DatosNuevaGestion): Promise<Gestion | null> => {
    if (prediccion === null) return Promise.resolve(null)
    const prediccionId = prediccion.prediccionId
    return enviar((signal) => crearGestion({ ...datos, prediccionId }, signal))
  }

  const registrar = (datos: ResultadoGestionParams): Promise<Gestion | null> => {
    if (gestion === null) return Promise.resolve(null)
    const gestionId = gestion.id
    return enviar((signal) => registrarResultado(gestionId, datos, signal))
  }

  return {
    prediccion,
    estado,
    sugeridas,
    gestion,
    error,
    hoy,
    abrir,
    reintentar,
    cerrar,
    crear,
    registrar,
  }
}
