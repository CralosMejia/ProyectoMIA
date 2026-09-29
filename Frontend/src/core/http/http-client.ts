import { config } from '../config'
import { ApiError } from './api-error'

export interface RequestOptions {
  signal?: AbortSignal
}

const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor.'
const GENERIC_ERROR_MESSAGE = 'Ocurrio un error inesperado.'

function buildUrl(path: string): string {
  return `${config.apiBaseUrl}${path}`
}

function isAbortError(error: unknown, signal?: AbortSignal): boolean {
  if (signal?.aborted) return true
  // DOMException no siempre hereda de Error (p. ej. en jsdom): se compara por nombre.
  return (
    typeof error === 'object' &&
    error !== null &&
    'name' in error &&
    (error as { name: unknown }).name === 'AbortError'
  )
}

interface ReadBody {
  body: unknown
  malformedJson: boolean
}

async function readBody(response: Response): Promise<ReadBody> {
  const text = await response.text()
  if (text === '') return { body: null, malformedJson: false }
  const contentType = response.headers.get('Content-Type') ?? ''
  if (contentType.includes('application/json')) {
    try {
      return { body: JSON.parse(text) as unknown, malformedJson: false }
    } catch {
      return { body: text, malformedJson: true }
    }
  }
  return { body: text, malformedJson: false }
}

function extractMessage(body: unknown): string {
  if (typeof body === 'object' && body !== null && 'error' in body) {
    const error = (body as { error: unknown }).error
    if (typeof error === 'object' && error !== null && 'message' in error) {
      const message = (error as { message: unknown }).message
      if (typeof message === 'string' && message !== '') return message
    }
  }
  return GENERIC_ERROR_MESSAGE
}

export async function httpGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path), {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: options.signal,
    })
  } catch (error) {
    if (isAbortError(error, options.signal)) throw error
    throw new ApiError(0, NETWORK_ERROR_MESSAGE)
  }

  let result: ReadBody
  try {
    result = await readBody(response)
  } catch (error) {
    if (isAbortError(error, options.signal)) throw error
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE)
  }

  const { body, malformedJson } = result
  if (!response.ok) {
    throw new ApiError(response.status, extractMessage(body), body)
  }
  if (malformedJson) {
    // Un 2xx que anuncia JSON y no parsea no se entrega como si fuera T.
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE, body)
  }
  return body as T
}
