export interface LoadingIndicatorProps {
  /** Texto accesible (y visible) del indicador. */
  label?: string
}

/** Indicador de carga accesible: region viva role="status" con un punto animado decorativo. */
export function LoadingIndicator({ label = 'Cargando...' }: LoadingIndicatorProps) {
  return (
    <p role="status" className="flex items-center gap-2 font-sans text-sm text-muted">
      <span aria-hidden="true" className="size-2 animate-pulse rounded-pill bg-brand" />
      {label}
    </p>
  )
}
