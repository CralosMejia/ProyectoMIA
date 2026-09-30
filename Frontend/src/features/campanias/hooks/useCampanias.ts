import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import {
  activarCampania,
  crearCampania,
  editarCampania,
  inactivarCampania,
  listarCampanias,
} from '../api/campanias-api'
import type { Campania, CampaniaEntrada } from '../types'

const MENSAJE_CARGA = 'No se pudieron consultar las campañas.'
const MENSAJE_OPERACION = 'No se pudo guardar el cambio. Intente de nuevo.'

export interface UseCampaniasResult {
  /** En el orden del servidor: activas primero, luego por prioridad. */
  campanias: Campania[]
  cargando: boolean
  /** Error al consultar la lista. */
  errorCarga: string | null
  /** Error de la última operación (crear, editar, inactivar o activar), con el mensaje del servidor. */
  error: string | null
  guardando: boolean
  recargar: () => void
  /** Devuelven `true` si la operación terminó bien. */
  crear: (entrada: CampaniaEntrada) => Promise<boolean>
  editar: (id: number, entrada: CampaniaEntrada) => Promise<boolean>
  inactivar: (id: number) => Promise<boolean>
  activar: (id: number) => Promise<boolean>
  limpiarError: () => void
}

function toMessage(error: unknown, generico: string): string {
  return error instanceof ApiError ? error.message : generico
}

/** Campañas de retención (CU-06): carga, alta, edición e inactivación con cancelación al desmontar. */
export function useCampanias(): UseCampaniasResult {
  const [campanias, setCampanias] = useState<Campania[]>([])
  const [cargando, setCargando] = useState(true)
  const [errorCarga, setErrorCarga] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [consulta, setConsulta] = useState(0)
  const operacionesRef = useRef(new Set<AbortController>())
  const guardandoRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    listarCampanias(controller.signal).then(
      (lista) => {
        if (controller.signal.aborted) return
        setCampanias(lista)
        setErrorCarga(null)
        setCargando(false)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setErrorCarga(toMessage(reason, MENSAJE_CARGA))
        setCargando(false)
      },
    )
    return () => {
      controller.abort()
    }
  }, [consulta])

  useEffect(() => {
    const operaciones = operacionesRef.current
    return () => {
      operaciones.forEach((controller) => controller.abort())
    }
  }, [])

  /** Vuelve a consultar mostrando el indicador de carga (p. ej. "Reintentar"). */
  const recargar = () => {
    setCargando(true)
    setConsulta((n) => n + 1)
  }

  /** Tras guardar: vuelve a consultar sin ocultar la tabla actual. */
  const refrescar = () => {
    setConsulta((n) => n + 1)
  }

  /** Ejecuta una operación sin doble envío; ante error guarda el mensaje y no toca la lista. */
  async function ejecutar(
    operacion: (signal: AbortSignal) => Promise<Campania>,
    alTerminar: (campania: Campania) => void,
  ): Promise<boolean> {
    if (guardandoRef.current) return false
    guardandoRef.current = true
    const controller = new AbortController()
    operacionesRef.current.add(controller)
    setError(null)
    setGuardando(true)
    try {
      const campania = await operacion(controller.signal)
      if (controller.signal.aborted) return false
      alTerminar(campania)
      return true
    } catch (reason: unknown) {
      if (!controller.signal.aborted) setError(toMessage(reason, MENSAJE_OPERACION))
      return false
    } finally {
      guardandoRef.current = false
      operacionesRef.current.delete(controller)
      if (!controller.signal.aborted) setGuardando(false)
    }
  }

  const crear = (entrada: CampaniaEntrada) =>
    ejecutar((signal) => crearCampania(entrada, signal), refrescar)

  const editar = (id: number, entrada: CampaniaEntrada) =>
    ejecutar((signal) => editarCampania(id, entrada, signal), refrescar)

  const inactivar = (id: number) =>
    ejecutar(
      (signal) => inactivarCampania(id, signal),
      (inactiva) => {
        setCampanias((actuales) => actuales.map((c) => (c.id === inactiva.id ? inactiva : c)))
      },
    )

  /** Vuelve a activar una inactiva; la fila se actualiza en su sitio, igual que al inactivar. */
  const activar = (id: number) =>
    ejecutar(
      (signal) => activarCampania(id, signal),
      (activa) => {
        setCampanias((actuales) => actuales.map((c) => (c.id === activa.id ? activa : c)))
      },
    )

  const limpiarError = () => {
    setError(null)
  }

  return {
    campanias,
    cargando,
    errorCarga,
    error,
    guardando,
    recargar,
    crear,
    editar,
    inactivar,
    activar,
    limpiarError,
  }
}
