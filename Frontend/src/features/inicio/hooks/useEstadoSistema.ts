import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { getEstadoSistema } from '../api/inicio-api'
import type { EstadoSistema } from '../types'

const GENERIC_ERROR_MESSAGE = 'No se pudo consultar el estado del sistema.'
/** Intervalo de la consulta periodica mientras el sistema se inicializa. */
export const INTERVALO_CONSULTA_MS = 5000

export interface UseEstadoSistemaResult {
  data: EstadoSistema | null
  /** Solo el mensaje apto para la UI, nunca el cuerpo crudo de la respuesta. */
  error: string | null
  isLoading: boolean
  refetch: () => void
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : GENERIC_ERROR_MESSAGE
}

/**
 * Estado general del sistema (CU-03) con cancelacion al desmontar y reintento.
 * Mientras el estado es `INICIALIZANDO` vuelve a consultar cada 5 s; se detiene con
 * `LISTO`, `FALTAN_DATOS_HISTORICOS`, un error o al desmontar.
 */
export function useEstadoSistema(): UseEstadoSistemaResult {
  const [data, setData] = useState<EstadoSistema | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [requestId, setRequestId] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let temporizador: ReturnType<typeof setTimeout> | undefined

    const consultar = () => {
      temporizador = undefined
      getEstadoSistema(controller.signal).then(
        (estado) => {
          if (controller.signal.aborted) return
          setData(estado)
          setError(null)
          setIsLoading(false)
          if (estado.estado === 'INICIALIZANDO') {
            temporizador = setTimeout(consultar, INTERVALO_CONSULTA_MS)
          }
        },
        (reason: unknown) => {
          if (controller.signal.aborted) return
          setData(null)
          setError(toMessage(reason))
          setIsLoading(false)
        },
      )
    }

    consultar()

    return () => {
      controller.abort()
      if (temporizador !== undefined) clearTimeout(temporizador)
    }
  }, [requestId])

  const refetch = () => {
    setIsLoading(true)
    setRequestId((id) => id + 1)
  }

  return { data, error, isLoading, refetch }
}
