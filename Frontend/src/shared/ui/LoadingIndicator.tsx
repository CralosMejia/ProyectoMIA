export interface LoadingIndicatorProps {
  /** Texto accesible (y visible) del indicador. */
  label?: string
}

/** Indicador de carga accesible: region viva role="status". */
export function LoadingIndicator({ label = 'Cargando...' }: LoadingIndicatorProps) {
  return (
    <p role="status" className="font-sans text-ink/70">
      {label}
    </p>
  )
}
