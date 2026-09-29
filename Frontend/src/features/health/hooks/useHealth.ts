import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { getHealth } from '../api/health-api'
import type { Health } from '../types'

const GENERIC_ERROR_MESSAGE = 'No se pudo consultar el estado del servicio.'

/** Error apto para la UI: solo el mensaje, nunca el cuerpo crudo de la respuesta. */
export interface HealthError {
  message: string
}

export interface UseHealthResult {
  data: Health | null
  error: HealthError | null
  isLoading: boolean
  refetch: () => void
}

function toHealthError(error: unknown): HealthError {
  if (error instanceof ApiError) return { message: error.message }
  return { message: GENERIC_ERROR_MESSAGE }
}

export function useHealth(): UseHealthResult {
  const [data, setData] = useState<Health | null>(null)
  const [error, setError] = useState<HealthError | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [requestId, setRequestId] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    getHealth(controller.signal).then(
      (health) => {
        if (controller.signal.aborted) return
        setData(health)
        setError(null)
        setIsLoading(false)
      },
      (reason: unknown) => {
        // Una peticion cancelada (desmontaje o refetch) no es un error de UI.
        if (controller.signal.aborted) return
        setData(null)
        setError(toHealthError(reason))
        setIsLoading(false)
      },
    )

    return () => {
      controller.abort()
    }
  }, [requestId])

  const refetch = () => {
    setIsLoading(true)
    setRequestId((id) => id + 1)
  }

  return { data, error, isLoading, refetch }
}
