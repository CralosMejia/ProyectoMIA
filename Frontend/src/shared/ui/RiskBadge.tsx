export type NivelRiesgo = 'ALTO' | 'MEDIO' | 'BAJO'

export interface RiskBadgeProps {
  nivel: NivelRiesgo
}

const LABEL: Record<NivelRiesgo, string> = {
  ALTO: 'Alto',
  MEDIO: 'Medio',
  BAJO: 'Bajo',
}

// Solo nombres de token (--color-risk-* en index.css); ningun color literal.
const TOKEN_CLASSES: Record<NivelRiesgo, string> = {
  ALTO: 'border-risk-high bg-risk-high/10 text-risk-high',
  MEDIO: 'border-risk-medium bg-risk-medium/10 text-risk-medium',
  BAJO: 'border-risk-low bg-risk-low/10 text-risk-low',
}

/** Insignia presentacional del nivel de riesgo de un socio. */
export function RiskBadge({ nivel }: RiskBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-pill border px-3 py-0.5 font-sans text-sm font-medium ${TOKEN_CLASSES[nivel]}`}
    >
      {LABEL[nivel]}
    </span>
  )
}
