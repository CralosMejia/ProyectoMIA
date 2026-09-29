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
      className="flex items-center justify-between gap-4 rounded-card border border-degraded bg-degraded/10 p-4 font-sans text-ink"
    >
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
