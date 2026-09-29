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

async function send(path: string, init: RequestInit, signal?: AbortSignal): Promise<Response> {
  try {
    return await fetch(buildUrl(path), { ...init, signal })
  } catch (error) {
    if (isAbortError(error, signal)) throw error
    throw new ApiError(0, NETWORK_ERROR_MESSAGE)
  }
}

async function throwIfNotOk(response: Response, signal?: AbortSignal): Promise<void> {
  if (response.ok) return
  let result: ReadBody
  try {
    result = await readBody(response)
  } catch (error) {
    if (isAbortError(error, signal)) throw error
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE)
  }
  throw new ApiError(response.status, extractMessage(result.body), result.body)
}

async function requestJson<T>(path: string, init: RequestInit, options: RequestOptions): Promise<T> {
  const response = await send(path, init, options.signal)
  await throwIfNotOk(response, options.signal)

  let result: ReadBody
  try {
    result = await readBody(response)
  } catch (error) {
    if (isAbortError(error, options.signal)) throw error
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE)
  }

  if (result.malformedJson) {
    // Un 2xx que anuncia JSON y no parsea no se entrega como si fuera T.
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE, result.body)
  }
  return result.body as T
}

const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json' }

export function httpGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return requestJson<T>(path, { method: 'GET', headers: { Accept: 'application/json' } }, options)
}

export function httpPost<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
  return requestJson<T>(
    path,
    { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body) },
    options,
  )
}

export function httpPut<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
  return requestJson<T>(
    path,
    { method: 'PUT', headers: JSON_HEADERS, body: JSON.stringify(body) },
    options,
  )
}

/**
 * Envia un FormData (multipart). No fija Content-Type: el navegador lo pone
 * con el boundary correcto.
 */
export function httpPostForm<T>(
  path: string,
  form: FormData,
  options: RequestOptions = {},
): Promise<T> {
  return requestJson<T>(
    path,
    { method: 'POST', headers: { Accept: 'application/json' }, body: form },
    options,
  )
}

/** Descarga un archivo: devuelve el Blob con el tipo de la respuesta. */
export async function httpGetBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const response = await send(path, { method: 'GET' }, options.signal)
  await throwIfNotOk(response, options.signal)
  try {
    return await response.blob()
  } catch (error) {
    if (isAbortError(error, options.signal)) throw error
    throw new ApiError(response.status, GENERIC_ERROR_MESSAGE)
  }
}
