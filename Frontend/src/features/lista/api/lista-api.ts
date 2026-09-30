import { ApiError } from '../../../core/http/api-error'
import { httpGet, httpGetBlob, httpPost, httpPut } from '../../../core/http/http-client'
import type {
  CampaniaSugerida,
  CrearGestionParams,
  EstadoGestion,
  FiltroGestiones,
  GenerarListaParams,
  Gestion,
  GestionResumen,
  ListaPriorizada,
  ListaResumen,
  NivelRiesgo,
  Plan,
  Prediccion,
  RespuestaAceptacion,
  RespuestaOfrecimiento,
  RespuestaRenovacion,
  ResultadoGestionParams,
} from '../types'

const LISTAS_PATH = '/api/v1/listas'
const GESTIONES_PATH = '/api/v1/gestiones'

/** Mensaje por defecto si un 409 llega sin mensaje util del servidor. */
export const MENSAJE_SISTEMA_NO_LISTO =
  'El sistema se esta inicializando; intente de nuevo en unos minutos.'

/**
 * `POST /listas` → 409: la migracion historica no ha terminado o no hay modelo vigente.
 * Conserva el status y el mensaje del servidor (es un `ApiError`).
 */
export class SistemaNoListoError extends ApiError {
  constructor(message: string, body: unknown = null) {
    super(409, message, body)
    this.name = 'SistemaNoListoError'
  }
}

/** Mensaje por defecto si un 422 de `POST /listas` llega sin mensaje util del servidor. */
export const MENSAJE_FECHA_PASADA = 'La fecha de la lista debe ser hoy o posterior.'

/**
 * `POST /listas` → 422: la fecha de la lista es anterior a hoy (regla de negocio).
 * Conserva el status y el mensaje del servidor (es un `ApiError`).
 */
export class FechaListaPasadaError extends ApiError {
  constructor(message: string, body: unknown = null) {
    super(422, message, body)
    this.name = 'FechaListaPasadaError'
  }
}

/*
 * Formas crudas (snake_case) del backend. Solo se conocen en este archivo.
 * Los decimales (score, umbrales) llegan como string y se conservan como string:
 * nunca se convierten a number para no perder precision.
 */
interface PrediccionResponse {
  prediccion_id: number
  prioridad: number
  socio_nombre: string
  celular: string | null
  cedula: string | null
  plan: Plan
  fecha_vencimiento: string
  dias_para_vencer: number
  monto_cobrado: string | null
  score: string
  nivel_riesgo: NivelRiesgo
  factores_principales: string[]
  dentro_top_k: boolean
  gestion_id: number | null
  gestion_estado: EstadoGestion | null
  campania_asignada: string | null
}

interface ListaPriorizadaResponse {
  id: number
  nombre: string
  modelo_version: string
  /** Fecha de referencia `YYYY-MM-DD`. */
  fecha_generacion: string
  /** ISO 8601 con zona. */
  creada_en: string
  horizonte_dias: number
  top_k: number
  umbral_alto: string
  umbral_medio: string
  advertencia_datos_antiguos: boolean
  items: PrediccionResponse[]
}

interface ListaResumenResponse {
  id: number
  nombre: string
  fecha_generacion: string
  creada_en: string
  modelo_version: string
  horizonte_dias: number
  top_k: number
  total_items: number
}

interface CampaniaResponse {
  id: number
  nombre: string
  descripcion: string | null
  prioridad: number
}

interface GestionResponse {
  id: number
  prediccion_id: number
  socio_nombre: string
  plan: Plan
  fecha_vencimiento: string
  modelo_version: string
  score: string
  nivel_riesgo: NivelRiesgo
  campania_id: number | null
  campania_nombre: string | null
  estado: EstadoGestion
  fecha_asignacion: string
  fecha_seguimiento: string
  responsable: string | null
  contactado: boolean | null
  campania_ofrecida: RespuestaOfrecimiento | null
  campania_aceptada: RespuestaAceptacion | null
  renovo_declarado: RespuestaRenovacion | null
  fecha_contacto: string | null
  observaciones: string | null
  fecha_cierre: string | null
}

interface GestionResumenResponse {
  id: number
  socio_nombre: string
  celular: string | null
  plan: Plan
  fecha_vencimiento: string
  fecha_seguimiento: string
  nivel_riesgo: NivelRiesgo
  campania_nombre: string | null
  responsable: string | null
  estado: EstadoGestion
}

function toPrediccion(raw: PrediccionResponse): Prediccion {
  return {
    prediccionId: raw.prediccion_id,
    prioridad: raw.prioridad,
    socioNombre: raw.socio_nombre,
    celular: raw.celular ?? null,
    cedula: raw.cedula ?? null,
    plan: raw.plan,
    fechaVencimiento: raw.fecha_vencimiento,
    diasParaVencer: raw.dias_para_vencer,
    montoCobrado: raw.monto_cobrado ?? null,
    score: raw.score,
    nivelRiesgo: raw.nivel_riesgo,
    factoresPrincipales: raw.factores_principales,
    dentroTopK: raw.dentro_top_k,
    gestionId: raw.gestion_id ?? null,
    gestionEstado: raw.gestion_estado ?? null,
    campaniaAsignada: raw.campania_asignada ?? null,
  }
}

function toLista(raw: ListaPriorizadaResponse): ListaPriorizada {
  return {
    id: raw.id,
    nombre: raw.nombre,
    modeloVersion: raw.modelo_version,
    fechaGeneracion: raw.fecha_generacion,
    creadaEn: new Date(raw.creada_en),
    horizonteDias: raw.horizonte_dias,
    topK: raw.top_k,
    umbralAlto: raw.umbral_alto,
    umbralMedio: raw.umbral_medio,
    advertenciaDatosAntiguos: raw.advertencia_datos_antiguos,
    items: raw.items.map(toPrediccion),
  }
}

function toListaResumen(raw: ListaResumenResponse): ListaResumen {
  return {
    id: raw.id,
    nombre: raw.nombre,
    fechaGeneracion: raw.fecha_generacion,
    creadaEn: new Date(raw.creada_en),
    modeloVersion: raw.modelo_version,
    horizonteDias: raw.horizonte_dias,
    topK: raw.top_k,
    totalItems: raw.total_items,
  }
}

function toGestion(raw: GestionResponse): Gestion {
  return {
    id: raw.id,
    prediccionId: raw.prediccion_id,
    socioNombre: raw.socio_nombre,
    plan: raw.plan,
    fechaVencimiento: raw.fecha_vencimiento,
    modeloVersion: raw.modelo_version,
    score: raw.score,
    nivelRiesgo: raw.nivel_riesgo,
    campaniaId: raw.campania_id ?? null,
    campaniaNombre: raw.campania_nombre ?? null,
    estado: raw.estado,
    fechaAsignacion: new Date(raw.fecha_asignacion),
    fechaSeguimiento: raw.fecha_seguimiento,
    responsable: raw.responsable ?? null,
    contactado: raw.contactado ?? null,
    campaniaOfrecida: raw.campania_ofrecida ?? null,
    campaniaAceptada: raw.campania_aceptada ?? null,
    renovoDeclarado: raw.renovo_declarado ?? null,
    fechaContacto: raw.fecha_contacto ?? null,
    observaciones: raw.observaciones ?? null,
    fechaCierre: raw.fecha_cierre ? new Date(raw.fecha_cierre) : null,
  }
}

function toGestionResumen(raw: GestionResumenResponse): GestionResumen {
  return {
    id: raw.id,
    socioNombre: raw.socio_nombre,
    celular: raw.celular ?? null,
    plan: raw.plan,
    fechaVencimiento: raw.fecha_vencimiento,
    fechaSeguimiento: raw.fecha_seguimiento,
    nivelRiesgo: raw.nivel_riesgo,
    campaniaNombre: raw.campania_nombre ?? null,
    responsable: raw.responsable ?? null,
    estado: raw.estado,
  }
}

function tieneMensajeDelServidor(body: unknown): boolean {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false
  const error = (body as { error: unknown }).error
  if (typeof error !== 'object' || error === null || !('message' in error)) return false
  const message = (error as { message: unknown }).message
  return typeof message === 'string' && message !== ''
}

/**
 * CU-04: genera una lista priorizada nueva. `nombre` solo viaja si llega (si no, el servidor
 * pone el nombre por defecto); un nombre invalido → `ApiError` 400 con el mensaje del servidor.
 * 409 → `SistemaNoListoError` y 422 (fecha anterior a hoy) → `FechaListaPasadaError`,
 * ambos con el mensaje del servidor.
 */
export async function generarLista(
  params: GenerarListaParams,
  signal?: AbortSignal,
): Promise<ListaPriorizada> {
  const body = {
    fecha_referencia: params.fechaReferencia ?? null,
    horizonte_dias: params.horizonteDias,
    top_k: params.topK,
    ...(params.nombre != null ? { nombre: params.nombre } : {}),
  }
  try {
    return toLista(await httpPost<ListaPriorizadaResponse>(LISTAS_PATH, body, { signal }))
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      const message = tieneMensajeDelServidor(error.body) ? error.message : MENSAJE_SISTEMA_NO_LISTO
      throw new SistemaNoListoError(message, error.body)
    }
    if (error instanceof ApiError && error.status === 422) {
      const message = tieneMensajeDelServidor(error.body) ? error.message : MENSAJE_FECHA_PASADA
      throw new FechaListaPasadaError(message, error.body)
    }
    throw error
  }
}

/** Ultima lista generada; `null` si aun no se ha generado ninguna (404). */
export async function obtenerUltima(signal?: AbortSignal): Promise<ListaPriorizada | null> {
  try {
    return toLista(await httpGet<ListaPriorizadaResponse>(`${LISTAS_PATH}/ultima`, { signal }))
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

export async function obtenerLista(id: number, signal?: AbortSignal): Promise<ListaPriorizada> {
  return toLista(await httpGet<ListaPriorizadaResponse>(`${LISTAS_PATH}/${id}`, { signal }))
}

/** Historial: resumen de las listas generadas, de la mas reciente a la mas antigua. */
export async function listarListas(signal?: AbortSignal): Promise<ListaResumen[]> {
  const raw = await httpGet<ListaResumenResponse[]>(LISTAS_PATH, { signal })
  return raw.map(toListaResumen)
}

/** Descarga la lista en Excel (.xlsx). */
export function descargarExcel(id: number, signal?: AbortSignal): Promise<Blob> {
  return httpGetBlob(`${LISTAS_PATH}/${id}/excel`, { signal })
}

/** CU-07: campañas activas que aplican al socio de la prediccion. */
export async function getCampaniasSugeridas(
  prediccionId: number,
  signal?: AbortSignal,
): Promise<CampaniaSugerida[]> {
  const raw = await httpGet<CampaniaResponse[]>(
    `/api/v1/predicciones/${prediccionId}/campanias-sugeridas`,
    { signal },
  )
  return raw.map((c) => ({
    id: c.id,
    nombre: c.nombre,
    descripcion: c.descripcion ?? null,
    prioridad: c.prioridad,
  }))
}

/** CU-08: asigna una gestion (con o sin campaña) a un socio de la lista. */
export async function crearGestion(
  params: CrearGestionParams,
  signal?: AbortSignal,
): Promise<Gestion> {
  const body = {
    prediccion_id: params.prediccionId,
    campania_id: params.campaniaId ?? null,
    fecha_seguimiento: params.fechaSeguimiento,
    responsable: params.responsable ?? null,
  }
  return toGestion(await httpPost<GestionResponse>(GESTIONES_PATH, body, { signal }))
}

/** CU-10: registra el resultado del seguimiento. */
export async function registrarResultado(
  gestionId: number,
  params: ResultadoGestionParams,
  signal?: AbortSignal,
): Promise<Gestion> {
  const body = {
    contactado: params.contactado,
    campania_ofrecida: params.campaniaOfrecida,
    campania_aceptada: params.campaniaAceptada,
    renovo_declarado: params.renovoDeclarado,
    fecha_contacto: params.fechaContacto ?? null,
    observaciones: params.observaciones ?? null,
    responsable: params.responsable ?? null,
    fecha_seguimiento: params.fechaSeguimiento ?? null,
  }
  return toGestion(
    await httpPut<GestionResponse>(`${GESTIONES_PATH}/${gestionId}/resultado`, body, { signal }),
  )
}

export async function getGestion(gestionId: number, signal?: AbortSignal): Promise<Gestion> {
  return toGestion(await httpGet<GestionResponse>(`${GESTIONES_PATH}/${gestionId}`, { signal }))
}

/** CU-09: gestiones pendientes de un grupo de alertas. */
export async function getGestiones(
  filtro: FiltroGestiones,
  signal?: AbortSignal,
): Promise<GestionResumen[]> {
  const query = new URLSearchParams({ filtro }).toString()
  const raw = await httpGet<GestionResumenResponse[]>(`${GESTIONES_PATH}?${query}`, { signal })
  return raw.map(toGestionResumen)
}
