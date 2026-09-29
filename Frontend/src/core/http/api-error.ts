/** Error estructurado devuelto por el cliente HTTP ante respuestas no-2xx o fallos de red. */
export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, message: string, body: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}
