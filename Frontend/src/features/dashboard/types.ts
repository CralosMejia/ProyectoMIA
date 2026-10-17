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
  /** Indicadores del piloto (R-018); siempre presentes. */
  piloto: IndicadoresPiloto
}

/** Estado de verificacion de un indicador del piloto (o del bloque completo). */
export type EstadoIndicador = 'COMPLETO' | 'PARCIAL' | 'PENDIENTE' | 'SIN_DATOS'

/** Proporcion `numerador / denominador`; `valor` decimal exacto (0..1) como `string` o null. */
export interface IndicadorProporcion {
  valor: string | null
  numerador: number
  denominador: number
  n: number
  pendientes: number
  estado: EstadoIndicador
}

/** Promedio de dias de anticipacion: decimal como `string` (puede ser <= 0) o null. */
export interface IndicadorDias {
  valor: string | null
  n: number
  estado: EstadoIndicador
}

/** Monto retenido en USD: decimal con 2 cifras como `string` o null. */
export interface IndicadorMonto {
  total: string | null
  renovaciones: number
  renovacionesSinMonto: number
  n: number
  pendientes: number
  estado: EstadoIndicador
}

export interface ListaPiloto {
  id: number
  nombre: string
  /** Fecha `YYYY-MM-DD`. */
  fechaGeneracion: string
}

/** Indicadores del top 25 de la ultima lista del mes (R-018 / M04). */
export interface IndicadoresPiloto {
  estado: EstadoIndicador
  lista: ListaPiloto | null
  /** Fecha `YYYY-MM-DD` hasta la que hay datos para verificar; null → todo pendiente. */
  corteVerificacion: string | null
  nTop: number
  /** Filas del top sin membresia o sin vencimiento (fuera de los `n`). */
  sinDato: number
  precisionTop25: IndicadorProporcion
  contactadosAntesVencimiento: IndicadorProporcion
  diasAnticipacion: IndicadorDias
  tasaRenovacionContactados: IndicadorProporcion
  montoRetenido: IndicadorMonto
}
