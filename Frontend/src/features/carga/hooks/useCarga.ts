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

export type EstadoCarga = 'inicial' | 'validando' | 'vista-previa' | 'enviando' | 'confirmada'

export interface UseCargaResult {
  estado: EstadoCarga
  vistaPrevia: VistaPreviaCarga | null
  resumen: CargaResumen | null
  /** Validacion local del archivo (no llega a la API). */
  errorArchivo: string | null
  /** Mensaje apto para la UI de un error de la API. */
  error: string | null
  puedeConfirmar: boolean
  seleccionarArchivo: (file: File | null) => void
  confirmar: () => void
}

function toMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return MENSAJE_GENERICO
  return error.status === PAYLOAD_TOO_LARGE ? MENSAJE_TAMANO : error.message
}

/** Vista previa y confirmacion de una carga (CU-01), con cancelacion y sin doble envio. */
export function useCarga(): UseCargaResult {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [estado, setEstado] = useState<EstadoCarga>('inicial')
  const [vistaPrevia, setVistaPrevia] = useState<VistaPreviaCarga | null>(null)
  const [resumen, setResumen] = useState<CargaResumen | null>(null)
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  // Guarda sincrona contra doble envio (dos clics antes de que React vuelva a pintar).
  const enviandoRef = useRef(false)

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
    const controller = nuevaPeticion()
    enviandoRef.current = false
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
    setEstado('validando')
    previsualizarCarga(file, controller.signal).then(
      (resultado) => {
        if (controller.signal.aborted) return
        setVistaPrevia(resultado)
        setEstado('vista-previa')
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setError(toMessage(reason))
        setEstado('inicial')
      },
    )
  }

  const puedeConfirmar =
    estado === 'vista-previa' && archivo !== null && vistaPrevia?.puedeConfirmar === true

  const confirmar = () => {
    if (!puedeConfirmar || archivo === null || enviandoRef.current) return
    enviandoRef.current = true
    const controller = nuevaPeticion()
    setError(null)
    setEstado('enviando')
    confirmarCarga(archivo, controller.signal).then(
      (carga) => {
        if (controller.signal.aborted) return
        enviandoRef.current = false
        setResumen(carga)
        setEstado('confirmada')
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        enviandoRef.current = false
        setError(toMessage(reason))
        setEstado('vista-previa')
      },
    )
  }

  return {
    estado,
    vistaPrevia,
    resumen,
    errorArchivo,
    error,
    puedeConfirmar,
    seleccionarArchivo,
    confirmar,
  }
}
