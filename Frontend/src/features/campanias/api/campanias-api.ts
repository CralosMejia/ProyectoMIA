import { httpGet, httpPost, httpPut } from '../../../core/http/http-client'
import type { Campania, CampaniaEntrada, NivelRiesgo, PlanCampania } from '../types'

const CAMPANIAS_PATH = '/api/v1/campanias'

/** Formas crudas (snake_case) del backend. Solo se conocen en este archivo. */
interface CampaniaResponse {
  id: number
  nombre: string
  descripcion: string | null
  activa: boolean
  niveles_riesgo: NivelRiesgo[]
  planes: PlanCampania[]
  prioridad: number
  es_ejemplo: boolean
}

function toCampania(raw: CampaniaResponse): Campania {
  return {
    id: raw.id,
    nombre: raw.nombre,
    descripcion: raw.descripcion ?? null,
    activa: raw.activa,
    nivelesRiesgo: raw.niveles_riesgo,
    planes: raw.planes,
    prioridad: raw.prioridad,
    esEjemplo: raw.es_ejemplo,
  }
}

function toBody(entrada: CampaniaEntrada) {
  return {
    nombre: entrada.nombre,
    descripcion: entrada.descripcion ?? null,
    niveles_riesgo: entrada.nivelesRiesgo,
    planes: entrada.planes,
    prioridad: entrada.prioridad,
  }
}

export async function listarCampanias(signal?: AbortSignal): Promise<Campania[]> {
  return (await httpGet<CampaniaResponse[]>(CAMPANIAS_PATH, { signal })).map(toCampania)
}

export async function crearCampania(
  entrada: CampaniaEntrada,
  signal?: AbortSignal,
): Promise<Campania> {
  return toCampania(await httpPost<CampaniaResponse>(CAMPANIAS_PATH, toBody(entrada), { signal }))
}

export async function editarCampania(
  id: number,
  entrada: CampaniaEntrada,
  signal?: AbortSignal,
): Promise<Campania> {
  return toCampania(
    await httpPut<CampaniaResponse>(`${CAMPANIAS_PATH}/${id}`, toBody(entrada), { signal }),
  )
}

/** Una campaña no se borra: se inactiva. */
export async function inactivarCampania(id: number, signal?: AbortSignal): Promise<Campania> {
  return toCampania(
    await httpPost<CampaniaResponse>(`${CAMPANIAS_PATH}/${id}/inactivar`, null, { signal }),
  )
}

/** Vuelve a activar una campaña inactiva: se sugiere de nuevo a los socios compatibles. */
export async function activarCampania(id: number, signal?: AbortSignal): Promise<Campania> {
  return toCampania(
    await httpPost<CampaniaResponse>(`${CAMPANIAS_PATH}/${id}/activar`, null, { signal }),
  )
}
