import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { confirmarCarga, previsualizarCarga } from '../api/carga-api'
import type { CargaResumen, VistaPreviaCarga } from '../types'

const EXTENSION_VALIDA = /\.xlsx$/i
const MENSAJE_EXTENSION = 'Seleccione un archivo .xlsx con la plantilla oficial.'
const MENSAJE_GENERICO = 'No se pudo procesar el archivo. Intente de nuevo.'
/** Fijo: un 413 puede venir de un proxy sin el cuerpo de error del backend. */
const MENSAJE_TAMANO = 'El archivo supera el tamaño máximo permitido.'
const PAYLOAD_TOO_LARGE = 413

export type EstadoCarga =
  | 'inicial'
  | 'seleccionado'
  | 'validando'
  | 'vista-previa'
  | 'enviando'
  | 'confirmada'

export interface UseCargaResult {
  estado: EstadoCarga
  /** Nombre del archivo elegido (null si no hay uno valido). */
  archivoSeleccionado: string | null
  vistaPrevia: VistaPreviaCarga | null
  resumen: CargaResumen | null
  /** Validacion local del archivo (no llega a la API). */
  errorArchivo: string | null
  /** Mensaje apto para la UI de un error de la API. */
  error: string | null
  puedeRevisar: boolean
  puedeConfirmar: boolean
  /** Solo guarda el archivo elegido: no llama a la API. */
  seleccionarArchivo: (file: File | null) => void
  /** Pide la vista previa del archivo elegido. */
  revisar: () => void
  confirmar: () => void
}

function toMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return MENSAJE_GENERICO
  return error.status === PAYLOAD_TOO_LARGE ? MENSAJE_TAMANO : error.message
}

/**
 * Carga en tres pasos (CU-01, R-008 (d)): elegir archivo → revisar (vista previa) → confirmar.
 * Con cancelacion de la peticion en curso y sin doble envio.
 */
export function useCarga(): UseCargaResult {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [estado, setEstado] = useState<EstadoCarga>('inicial')
  const [vistaPrevia, setVistaPrevia] = useState<VistaPreviaCarga | null>(null)
  const [resumen, setResumen] = useState<CargaResumen | null>(null)
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  // Guarda sincrona contra doble peticion (dos clics antes de que React vuelva a pintar).
  const ocupadoRef = useRef(false)

  useEffect(
    () => () => {
      controllerRef.current?.abort()
    },
    [],
  )

  /** Cancela la peticion en curso y devuelve un controlador nuevo. */
  const nuevaPeticion = (): AbortController => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    return controller
  }

  const seleccionarArchivo = (file: File | null) => {
    controllerRef.current?.abort()
    controllerRef.current = null
    ocupadoRef.current = false
    setVistaPrevia(null)
    setResumen(null)
    setError(null)
    setErrorArchivo(null)
    setArchivo(null)

    if (file === null) {
      setEstado('inicial')
      return
    }
    if (!EXTENSION_VALIDA.test(file.name)) {
      setErrorArchivo(MENSAJE_EXTENSION)
      setEstado('inicial')
      return
    }

    setArchivo(file)
    setEstado('seleccionado')
  }

  const puedeRevisar = archivo !== null && (estado === 'seleccionado' || estado === 'vista-previa')

  const revisar = () => {
    if (!puedeRevisar || archivo === null || ocupadoRef.current) return
    ocupadoRef.current = true
    const controller = nuevaPeticion()
    setVistaPrevia(null)
    setError(null)
    setEstado('validando')
    previsualizarCarga(archivo, controller.signal).then(
      (resultado) => {
        if (controller.signal.aborted) return
        ocupadoRef.current = false
        setVistaPrevia(resultado)
        setEstado('vista-previa')
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        ocupadoRef.current = false
        setError(toMessage(reason))
        setEstado('seleccionado')
      },
    )
  }

  const puedeConfirmar =
    estado === 'vista-previa' && archivo !== null && vistaPrevia?.puedeConfirmar === true

  const confirmar = () => {
    if (!puedeConfirmar || archivo === null || ocupadoRef.current) return
    ocupadoRef.current = true
    const controller = nuevaPeticion()
    setError(null)
    setEstado('enviando')
    confirmarCarga(archivo, controller.signal).then(
      (carga) => {
        if (controller.signal.aborted) return
        ocupadoRef.current = false
        setResumen(carga)
        setEstado('confirmada')
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        ocupadoRef.current = false
        setError(toMessage(reason))
        setEstado('vista-previa')
      },
    )
  }

  return {
    estado,
    archivoSeleccionado: archivo?.name ?? null,
    vistaPrevia,
    resumen,
    errorArchivo,
    error,
    puedeRevisar,
    puedeConfirmar,
    seleccionarArchivo,
    revisar,
    confirmar,
  }
}
