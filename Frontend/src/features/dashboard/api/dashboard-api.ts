import { httpGet } from '../../../core/http/http-client'
import type { Dashboard, Embudo, ResultadoCampania } from '../types'

const DASHBOARD_PATH = '/api/v1/dashboard'

/*
 * Formas crudas (snake_case) del backend. Solo se conocen en este archivo.
 * `tasa_renovacion` es decimal y llega como string: se conserva como string.
 */
interface ResultadoCampaniaResponse {
  campania_id: number | null
  nombre: string
  gestiones: number
  contactados: number
  renovaciones: number
  gestiones_cerradas: number
  tasa_renovacion: string | null
  casos_insuficientes: boolean
}

interface EstadoModeloResponse {
  version: string
  fecha_entrenamiento: string
  ciclos_entrenamiento: number
  proxima_fecha_reentrenamiento: string | null
  ciclos_nuevos_evaluables: number
}

interface DashboardResponse {
  mes: string
  embudo: Embudo
  por_campania: ResultadoCampaniaResponse[]
  estado_modelo: EstadoModeloResponse | null
}

function toResultado(raw: ResultadoCampaniaResponse): ResultadoCampania {
  return {
    campaniaId: raw.campania_id ?? null,
    nombre: raw.nombre,
    gestiones: raw.gestiones,
    contactados: raw.contactados,
    renovaciones: raw.renovaciones,
    gestionesCerradas: raw.gestiones_cerradas,
    tasaRenovacion: raw.tasa_renovacion ?? null,
    casosInsuficientes: raw.casos_insuficientes,
  }
}

/**
 * CU-11: dashboard del mes `YYYY-MM`; sin mes no se envia el parametro y el backend usa el mes
 * actual. Un mes con formato invalido → `ApiError` 400 con el mensaje del servidor.
 */
export async function obtenerDashboard(mes?: string, signal?: AbortSignal): Promise<Dashboard> {
  const path = mes ? `${DASHBOARD_PATH}?${new URLSearchParams({ mes }).toString()}` : DASHBOARD_PATH
  const raw = await httpGet<DashboardResponse>(path, { signal })
  const modelo = raw.estado_modelo ?? null
  return {
    mes: raw.mes,
    embudo: {
      asignadas: raw.embudo.asignadas,
      contactadas: raw.embudo.contactadas,
      ofrecidas: raw.embudo.ofrecidas,
      aceptadas: raw.embudo.aceptadas,
      renovaron: raw.embudo.renovaron,
    },
    porCampania: raw.por_campania.map(toResultado),
    estadoModelo: modelo && {
      version: modelo.version,
      fechaEntrenamiento: new Date(modelo.fecha_entrenamiento),
      ciclosEntrenamiento: modelo.ciclos_entrenamiento,
      proximaFechaReentrenamiento: modelo.proxima_fecha_reentrenamiento ?? null,
      ciclosNuevosEvaluables: modelo.ciclos_nuevos_evaluables,
    },
  }
}

/** Nombre anterior de `obtenerDashboard` (se conserva por compatibilidad). */
export const getDashboard = obtenerDashboard
