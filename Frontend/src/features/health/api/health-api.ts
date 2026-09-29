import { ApiError } from '../../../core/http/api-error'
import { httpGet } from '../../../core/http/http-client'
import type { Health } from '../types'

const HEALTH_PATH = '/api/v1/health'
const INVALID_CONTRACT_MESSAGE = 'Respuesta de salud con formato inesperado.'

/** Forma cruda (snake_case) que devuelve el backend. Solo se conoce en este archivo. */
interface HealthResponse {
  status: 'ok' | 'degraded'
  database: 'up' | 'down'
  checked_at: string
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    (v.status === 'ok' || v.status === 'degraded') &&
    (v.database === 'up' || v.database === 'down') &&
    typeof v.checked_at === 'string' &&
    !Number.isNaN(Date.parse(v.checked_at))
  )
}

function toHealth(response: HealthResponse): Health {
  return {
    status: response.status,
    database: response.database,
    checkedAt: new Date(response.checked_at),
  }
}

/**
 * Consulta el estado del backend. Un 503 con cuerpo de salud valido se considera
 * respuesta legitima (estado degradado); cualquier otro error se propaga como ApiError.
 */
export async function getHealth(signal?: AbortSignal): Promise<Health> {
  let raw: unknown
  try {
    raw = await httpGet<unknown>(HEALTH_PATH, { signal })
  } catch (error) {
    if (error instanceof ApiError && error.status === 503 && isHealthResponse(error.body)) {
      return toHealth(error.body)
    }
    throw error
  }

  if (!isHealthResponse(raw)) {
    throw new ApiError(200, INVALID_CONTRACT_MESSAGE, raw)
  }
  return toHealth(raw)
}
