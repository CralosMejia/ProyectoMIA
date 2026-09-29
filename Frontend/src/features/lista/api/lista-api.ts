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
  correo: string | null
  plan: Plan
  fecha_vencimiento: string
  dias_para_vencer: number
  score: string
  nivel_riesgo: NivelRiesgo
  factores_principales: string[]
  dentro_top_k: boolean
  gestion_estado: EstadoGestion | null
  campania_asignada: string | null
}

interface ListaPriorizadaResponse {
  id: number
  modelo_version: string
  fecha_generacion: string
  horizonte_dias: number
  top_k: number
  umbral_alto: string
  umbral_medio: string
  advertencia_datos_antiguos: boolean
  items: PrediccionResponse[]
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
    correo: raw.correo ?? null,
    plan: raw.plan,
    fechaVencimiento: raw.fecha_vencimiento,
    diasParaVencer: raw.dias_para_vencer,
    score: raw.score,
    nivelRiesgo: raw.nivel_riesgo,
    factoresPrincipales: raw.factores_principales,
    dentroTopK: raw.dentro_top_k,
    gestionEstado: raw.gestion_estado ?? null,
    campaniaAsignada: raw.campania_asignada ?? null,
  }
}

function toLista(raw: ListaPriorizadaResponse): ListaPriorizada {
  return {
    id: raw.id,
    modeloVersion: raw.modelo_version,
    fechaGeneracion: new Date(raw.fecha_generacion),
    horizonteDias: raw.horizonte_dias,
    topK: raw.top_k,
    umbralAlto: raw.umbral_alto,
    umbralMedio: raw.umbral_medio,
    advertenciaDatosAntiguos: raw.advertencia_datos_antiguos,
    items: raw.items.map(toPrediccion),
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

/** CU-04: genera una lista priorizada nueva. */
export async function generarLista(
  params: GenerarListaParams,
  signal?: AbortSignal,
): Promise<ListaPriorizada> {
  const body = {
    fecha_referencia: params.fechaReferencia ?? null,
    horizonte_dias: params.horizonteDias,
    top_k: params.topK,
  }
  return toLista(await httpPost<ListaPriorizadaResponse>(LISTAS_PATH, body, { signal }))
}

/** Ultima lista generada; `null` si aun no se ha generado ninguna (404). */
export async function getUltimaLista(signal?: AbortSignal): Promise<ListaPriorizada | null> {
  try {
    return toLista(await httpGet<ListaPriorizadaResponse>(`${LISTAS_PATH}/ultima`, { signal }))
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null
    throw error
  }
}

export async function getLista(id: number, signal?: AbortSignal): Promise<ListaPriorizada> {
  return toLista(await httpGet<ListaPriorizadaResponse>(`${LISTAS_PATH}/${id}`, { signal }))
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
