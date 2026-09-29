import { httpPostForm } from '../../../core/http/http-client'
import type { CargaResumen, ErrorFila, VistaPreviaCarga } from '../types'

const VISTA_PREVIA_PATH = '/api/v1/cargas/vista-previa'
const CARGAS_PATH = '/api/v1/cargas'
const CAMPO_ARCHIVO = 'archivo'

/** Formas crudas (snake_case) del backend. Solo se conocen en este archivo. */
interface VistaPreviaResponse {
  filas_leidas: number
  filas_validas: number
  filas_con_error: number
  filas_duplicadas: number
  vencimiento_desde: string | null
  vencimiento_hasta: string | null
  errores: { fila: number; columna: string | null; motivo: string }[]
  puede_confirmar: boolean
}

interface CargaResponse {
  id: number
  fecha_carga: string
  nombre_archivo: string
  filas_leidas: number
  filas_guardadas: number
  filas_duplicadas: number
  socios_enlazados: number
  avisos_enlace: string[]
}

function toForm(file: File): FormData {
  const form = new FormData()
  form.append(CAMPO_ARCHIVO, file)
  return form
}

function toErrorFila(raw: VistaPreviaResponse['errores'][number]): ErrorFila {
  return { fila: raw.fila, columna: raw.columna ?? null, motivo: raw.motivo }
}

/** Valida la plantilla sin guardar nada. */
export async function previsualizarCarga(
  file: File,
  signal?: AbortSignal,
): Promise<VistaPreviaCarga> {
  const raw = await httpPostForm<VistaPreviaResponse>(VISTA_PREVIA_PATH, toForm(file), { signal })
  return {
    filasLeidas: raw.filas_leidas,
    filasValidas: raw.filas_validas,
    filasConError: raw.filas_con_error,
    filasDuplicadas: raw.filas_duplicadas,
    vencimientoDesde: raw.vencimiento_desde ?? null,
    vencimientoHasta: raw.vencimiento_hasta ?? null,
    errores: raw.errores.map(toErrorFila),
    puedeConfirmar: raw.puede_confirmar,
  }
}

/** Confirma y guarda la plantilla. */
export async function confirmarCarga(file: File, signal?: AbortSignal): Promise<CargaResumen> {
  const raw = await httpPostForm<CargaResponse>(CARGAS_PATH, toForm(file), { signal })
  return {
    id: raw.id,
    fechaCarga: new Date(raw.fecha_carga),
    nombreArchivo: raw.nombre_archivo,
    filasLeidas: raw.filas_leidas,
    filasGuardadas: raw.filas_guardadas,
    filasDuplicadas: raw.filas_duplicadas,
    sociosEnlazados: raw.socios_enlazados,
    avisosEnlace: raw.avisos_enlace,
  }
}
