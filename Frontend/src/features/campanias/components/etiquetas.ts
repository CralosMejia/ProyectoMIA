import type { NivelRiesgo, PlanCampania } from '../types'

/** Niveles en orden canónico (ALTO, MEDIO, BAJO) con su texto para el personal. */
export const NIVELES: { valor: NivelRiesgo; etiqueta: string }[] = [
  { valor: 'ALTO', etiqueta: 'Alto' },
  { valor: 'MEDIO', etiqueta: 'Medio' },
  { valor: 'BAJO', etiqueta: 'Bajo' },
]

/** Planes de campaña en orden canónico; `DIARIO` no admite campañas. */
export const PLANES: { valor: PlanCampania; etiqueta: string }[] = [
  { valor: 'MENSUAL', etiqueta: 'Mensual' },
  { valor: 'TRIMESTRAL', etiqueta: 'Trimestral' },
  { valor: 'SEMESTRAL', etiqueta: 'Semestral' },
  { valor: 'ANUAL', etiqueta: 'Anual' },
  { valor: 'OTRO', etiqueta: 'Otro' },
]

/** Textos amigables en orden canónico, unidos con ", ". */
export function etiquetasDe<T extends string>(
  opciones: { valor: T; etiqueta: string }[],
  valores: T[],
): string {
  return opciones
    .filter((o) => valores.includes(o.valor))
    .map((o) => o.etiqueta)
    .join(', ')
}
