import type { NivelRiesgo } from '../../shared/ui/RiskBadge'

export type { NivelRiesgo }
export type Plan = 'MENSUAL' | 'TRIMESTRAL' | 'SEMESTRAL' | 'ANUAL' | 'DIARIO' | 'OTRO'
export type EstadoGestion = 'PENDIENTE' | 'CERRADA'
export type FiltroGestiones = 'vencidas' | 'hoy' | 'proximas'

export type RespuestaOfrecimiento = 'SI' | 'NO' | 'NO_APLICA'
export type RespuestaAceptacion = 'SI' | 'NO' | 'PENDIENTE' | 'NO_APLICA'
export type RespuestaRenovacion = 'SI' | 'NO' | 'PENDIENTE'

/** Parametros de CU-04. `fechaReferencia` (`YYYY-MM-DD`) ausente o null = hoy. */
export interface GenerarListaParams {
  fechaReferencia?: string | null
  horizonteDias: number
  topK: number
}

/**
 * Un socio de la lista priorizada. `score` es decimal exacto como `string`
 * (nunca se convierte a `number`). Las fechas sin hora son `YYYY-MM-DD`.
 */
export interface Prediccion {
  prediccionId: number
  prioridad: number
  socioNombre: string
  celular: string | null
  correo: string | null
  plan: Plan
  fechaVencimiento: string
  diasParaVencer: number
  score: string
  nivelRiesgo: NivelRiesgo
  factoresPrincipales: string[]
  dentroTopK: boolean
  gestionEstado: EstadoGestion | null
  campaniaAsignada: string | null
}

/** Lista priorizada (instantanea inmutable). Umbrales decimales como `string`. */
export interface ListaPriorizada {
  id: number
  modeloVersion: string
  fechaGeneracion: Date
  horizonteDias: number
  topK: number
  umbralAlto: string
  umbralMedio: string
  advertenciaDatosAntiguos: boolean
  items: Prediccion[]
}

/** Campaña sugerida para un socio (CU-07), ordenada por prioridad. */
export interface CampaniaSugerida {
  id: number
  nombre: string
  descripcion: string | null
  prioridad: number
}

/** CU-08. `campaniaId` ausente o null = sin campaña. */
export interface CrearGestionParams {
  prediccionId: number
  campaniaId?: number | null
  fechaSeguimiento: string
  responsable?: string | null
}

/** CU-10. `renovoDeclarado` SI/NO cierra la gestion. */
export interface ResultadoGestionParams {
  contactado: boolean
  campaniaOfrecida: RespuestaOfrecimiento
  campaniaAceptada: RespuestaAceptacion
  renovoDeclarado: RespuestaRenovacion
  fechaContacto?: string | null
  observaciones?: string | null
  responsable?: string | null
  fechaSeguimiento?: string | null
}

/** Gestion de retencion completa, con el score y el nivel originales de la lista. */
export interface Gestion {
  id: number
  prediccionId: number
  socioNombre: string
  plan: Plan
  fechaVencimiento: string
  modeloVersion: string
  score: string
  nivelRiesgo: NivelRiesgo
  campaniaId: number | null
  campaniaNombre: string | null
  estado: EstadoGestion
  fechaAsignacion: Date
  fechaSeguimiento: string
  responsable: string | null
  contactado: boolean | null
  campaniaOfrecida: RespuestaOfrecimiento | null
  campaniaAceptada: RespuestaAceptacion | null
  renovoDeclarado: RespuestaRenovacion | null
  fechaContacto: string | null
  observaciones: string | null
  fechaCierre: Date | null
}

/** Fila de la lista de gestiones pendientes de un grupo de alertas. */
export interface GestionResumen {
  id: number
  socioNombre: string
  celular: string | null
  plan: Plan
  fechaVencimiento: string
  fechaSeguimiento: string
  nivelRiesgo: NivelRiesgo
  campaniaNombre: string | null
  responsable: string | null
  estado: EstadoGestion
}
