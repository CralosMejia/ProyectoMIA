export type EstadoGeneral = 'INICIALIZANDO' | 'FALTAN_DATOS_HISTORICOS' | 'LISTO'
export type EstadoMigracion = 'PENDIENTE' | 'EN_CURSO' | 'COMPLETADA'

export interface ModeloVigente {
  version: string
  fechaEntrenamiento: Date
  ciclosEntrenamiento: number
}

export interface EstadoSistema {
  estado: EstadoGeneral
  migracionHistorica: EstadoMigracion
  modeloVigente: ModeloVigente | null
  ultimaCargaEn: Date | null
  /** Fecha `YYYY-MM-DD` (sin hora). */
  proximaFechaReentrenamiento: string | null
}

/** Contadores de gestiones pendientes por fecha de seguimiento (CU-09). */
export interface Alertas {
  vencidas: number
  hoy: number
  proximos7Dias: number
}
