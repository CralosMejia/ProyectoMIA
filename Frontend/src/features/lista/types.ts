import type { NivelRiesgo } from '../../shared/ui/RiskBadge'

export type { NivelRiesgo }
export type Plan = 'MENSUAL' | 'TRIMESTRAL' | 'SEMESTRAL' | 'ANUAL' | 'DIARIO' | 'OTRO'
export type EstadoGestion = 'PENDIENTE' | 'CERRADA'
/** Grupo de alertas de seguimiento (CU-09): vencidos, para hoy o proximos 7 dias. */
export type FiltroAlerta = 'vencidas' | 'hoy' | 'proximas'
/** Nombre anterior de `FiltroAlerta`. */
export type FiltroGestiones = FiltroAlerta

export type RespuestaOfrecimiento = 'SI' | 'NO' | 'NO_APLICA'
export type RespuestaAceptacion = 'SI' | 'NO' | 'PENDIENTE' | 'NO_APLICA'
export type RespuestaRenovacion = 'SI' | 'NO' | 'PENDIENTE'

/**
 * Parametros de CU-04. `fechaReferencia` (`YYYY-MM-DD`) debe ser hoy o posterior; ausente o null =
 * hoy segun el servidor. `horizonteDias` entre 1 y 31.
 */
export interface GenerarListaParams {
  fechaReferencia?: string | null
  horizonteDias: number
  topK: number
  /**
   * Nombre de la lista (1..80 caracteres tras recortar). Ausente o null = el servidor usa
   * "Lista del <d mmm aaaa>" con la fecha de la lista.
   */
  nombre?: string | null
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
  /** Cedula como texto (conserva el cero inicial); `null` en listas antiguas de socios sin cedula. */
  cedula: string | null
  plan: Plan
  fechaVencimiento: string
  diasParaVencer: number
  /** Monto cobrado del ciclo, decimal exacto como `string`; `null` si no se registro. */
  montoCobrado: string | null
  score: string
  nivelRiesgo: NivelRiesgo
  factoresPrincipales: string[]
  dentroTopK: boolean
  /** Gestion del ciclo (la misma aunque la membresia este en varias listas); `null` si no hay. */
  gestionId: number | null
  gestionEstado: EstadoGestion | null
  /** Nombre de la campaña al asignarla; `null` sin gestion o gestion sin campaña. */
  campaniaAsignada: string | null
}

/**
 * Lista priorizada (instantanea inmutable). Umbrales decimales como `string`.
 * `fechaGeneracion` es la fecha de referencia (`YYYY-MM-DD`); `creadaEn`, el momento en que se genero.
 */
export interface ListaPriorizada {
  id: number
  /** Nombre de la lista; es su titulo en pantalla. */
  nombre: string
  modeloVersion: string
  fechaGeneracion: string
  creadaEn: Date
  horizonteDias: number
  topK: number
  umbralAlto: string
  umbralMedio: string
  advertenciaDatosAntiguos: boolean
  items: Prediccion[]
}

/** Resumen de una lista generada, para el historial (D3-FE-03). */
export interface ListaResumen {
  id: number
  nombre: string
  /** Fecha de referencia `YYYY-MM-DD`. */
  fechaGeneracion: string
  creadaEn: Date
  modeloVersion: string
  horizonteDias: number
  topK: number
  totalItems: number
}

/** Campaña sugerida para un socio (CU-07), ordenada por prioridad. */
export interface CampaniaSugerida {
  id: number
  nombre: string
  descripcion: string | null
  prioridad: number
}

/**
 * CU-08. `campaniaId` ausente o null = sin campaña: la gestion nace cerrada y no lleva fecha de
 * seguimiento (`null`) ni responsable. Con campaña, la fecha de seguimiento es obligatoria.
 */
export interface CrearGestionParams {
  prediccionId: number
  campaniaId?: number | null
  fechaSeguimiento: string | null
  responsable?: string | null
}

/** Datos del formulario de CU-08 (la prediccion la aporta la ventana abierta). */
export type DatosNuevaGestion = Omit<CrearGestionParams, 'prediccionId'>

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
  /** Prediccion de la lista a la que pertenece la gestion (para abrir su ventana). */
  prediccionId: number
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
