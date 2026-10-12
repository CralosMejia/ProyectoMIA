import { Boton } from './Diseno'

export interface ErrorAlertProps {
  message: string
  /** Si se recibe, se muestra el boton "Reintentar". */
  onRetry?: () => void
}

/** Banner de error accesible (role="alert") con reintento opcional. */
export function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-degraded/40 border-l-4 border-l-degraded bg-degraded/10 p-4 font-sans text-sm text-ink"
    >
      <p>{message}</p>
      {onRetry && <Boton onClick={onRetry}>Reintentar</Boton>}
    </div>
  )
}
