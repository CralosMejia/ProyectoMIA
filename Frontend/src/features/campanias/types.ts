import type { NivelRiesgo } from '../../shared/ui/RiskBadge'

export type { NivelRiesgo }

/** Planes que admite una campaña: todos salvo `DIARIO`. */
export type PlanCampania = 'MENSUAL' | 'TRIMESTRAL' | 'SEMESTRAL' | 'ANUAL' | 'OTRO'

export interface Campania {
  id: number
  nombre: string
  descripcion: string | null
  activa: boolean
  nivelesRiesgo: NivelRiesgo[]
  planes: PlanCampania[]
  /** 1 es la mas prioritaria. */
  prioridad: number
  esEjemplo: boolean
}

/** Datos para crear o editar una campaña. */
export interface CampaniaEntrada {
  nombre: string
  descripcion?: string | null
  nivelesRiesgo: NivelRiesgo[]
  planes: PlanCampania[]
  prioridad: number
}
