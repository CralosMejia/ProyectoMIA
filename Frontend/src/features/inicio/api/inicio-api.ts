import { httpGet } from '../../../core/http/http-client'
import type { Alertas, EstadoGeneral, EstadoMigracion, EstadoSistema } from '../types'

const ESTADO_PATH = '/api/v1/sistema/estado'
const ALERTAS_PATH = '/api/v1/alertas'

/** Formas crudas (snake_case) del backend. Solo se conocen en este archivo. */
interface ModeloVigenteResponse {
  version: string
  fecha_entrenamiento: string
  ciclos_entrenamiento: number
}

interface EstadoSistemaResponse {
  estado: EstadoGeneral
  migracion_historica: EstadoMigracion
  modelo_vigente: ModeloVigenteResponse | null
  ultima_carga_en: string | null
  proxima_fecha_reentrenamiento: string | null
}

interface AlertasResponse {
  vencidas: number
  hoy: number
  proximos_7_dias: number
}

export async function getEstadoSistema(signal?: AbortSignal): Promise<EstadoSistema> {
  const raw = await httpGet<EstadoSistemaResponse>(ESTADO_PATH, { signal })
  const modelo = raw.modelo_vigente ?? null
  return {
    estado: raw.estado,
    migracionHistorica: raw.migracion_historica,
    modeloVigente: modelo && {
      version: modelo.version,
      fechaEntrenamiento: new Date(modelo.fecha_entrenamiento),
      ciclosEntrenamiento: modelo.ciclos_entrenamiento,
    },
    ultimaCargaEn: raw.ultima_carga_en ? new Date(raw.ultima_carga_en) : null,
    proximaFechaReentrenamiento: raw.proxima_fecha_reentrenamiento ?? null,
  }
}

export async function getAlertas(signal?: AbortSignal): Promise<Alertas> {
  const raw = await httpGet<AlertasResponse>(ALERTAS_PATH, { signal })
  return { vencidas: raw.vencidas, hoy: raw.hoy, proximos7Dias: raw.proximos_7_dias }
}
