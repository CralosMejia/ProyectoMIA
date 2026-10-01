import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { obtenerAlertas } from '../api/inicio-api'
import type { Alertas } from '../types'

const GENERIC_ERROR_MESSAGE = 'No se pudieron consultar los seguimientos pendientes.'

export interface UseAlertasResult {
  data: Alertas | null
  /** Solo el mensaje apto para la UI. */
  error: string | null
  isLoading: boolean
  refetch: () => void
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : GENERIC_ERROR_MESSAGE
}

/**
 * Contadores de seguimientos pendientes (CU-09). Solo consulta con `habilitado` (el sistema esta
 * listo); cancela la peticion al desmontar o al deshabilitarse.
 */
export function useAlertas(habilitado: boolean): UseAlertasResult {
  const [data, setData] = useState<Alertas | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [requestId, setRequestId] = useState(0)

  useEffect(() => {
    if (!habilitado) return undefined
    const controller = new AbortController()
    obtenerAlertas(controller.signal).then(
      (alertas) => {
        if (controller.signal.aborted) return
        setData(alertas)
        setError(null)
        setIsLoading(false)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setData(null)
        setError(toMessage(reason))
        setIsLoading(false)
      },
    )
    return () => {
      controller.abort()
    }
  }, [habilitado, requestId])

  const refetch = () => {
    setIsLoading(true)
    setRequestId((id) => id + 1)
  }

  return { data, error, isLoading, refetch }
}
