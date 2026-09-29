export interface ErrorFila {
  fila: number
  columna: string | null
  motivo: string
}

/** Resultado de validar la plantilla sin guardar nada (CU-01). */
export interface VistaPreviaCarga {
  filasLeidas: number
  filasValidas: number
  filasConError: number
  filasDuplicadas: number
  /** Fechas `YYYY-MM-DD`. */
  vencimientoDesde: string | null
  vencimientoHasta: string | null
  errores: ErrorFila[]
  puedeConfirmar: boolean
}

/** Carga confirmada y guardada. */
export interface CargaResumen {
  id: number
  fechaCarga: Date
  nombreArchivo: string
  filasLeidas: number
  filasGuardadas: number
  filasDuplicadas: number
  sociosEnlazados: number
  avisosEnlace: string[]
}
