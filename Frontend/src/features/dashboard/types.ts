export interface Embudo {
  asignadas: number
  contactadas: number
  ofrecidas: number
  aceptadas: number
  renovaron: number
}

/** Cifras descriptivas por campaña; `campaniaId` null = gestiones sin campaña. */
export interface ResultadoCampania {
  campaniaId: number | null
  nombre: string
  gestiones: number
  contactados: number
  renovaciones: number
  gestionesCerradas: number
  /** Decimal exacto (0..1) como `string`; null si hay casos insuficientes. */
  tasaRenovacion: string | null
  casosInsuficientes: boolean
}

export interface EstadoModelo {
  version: string
  fechaEntrenamiento: Date
  ciclosEntrenamiento: number
  /** Fecha `YYYY-MM-DD`. */
  proximaFechaReentrenamiento: string | null
  ciclosNuevosEvaluables: number
}

export interface Dashboard {
  /** Mes `YYYY-MM`. */
  mes: string
  embudo: Embudo
  porCampania: ResultadoCampania[]
  estadoModelo: EstadoModelo | null
}
