import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { descargarExcel } from '../api/lista-api'

const MENSAJE_GENERICO = 'No se pudo descargar el Excel. Intente de nuevo.'

export interface UseDescargarExcelResult {
  descargando: boolean
  error: string | null
  /** Descarga el Excel de la lista `id`; el nombre no lleva datos personales. */
  descargar: (id: number, fechaGeneracion: string) => void
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

/** Entrega el Blob al navegador como descarga y libera la URL temporal despues. */
function guardarArchivo(blob: Blob, nombre: string): void {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  enlace.style.display = 'none'
  document.body.appendChild(enlace)
  try {
    enlace.click()
  } finally {
    enlace.remove()
    // Se libera en la siguiente vuelta para que el navegador ya haya tomado la descarga.
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}

/** Descarga del Excel de una lista (CU-12) sin doble envio y con cancelacion al desmontar. */
export function useDescargarExcel(): UseDescargarExcelResult {
  const [descargando, setDescargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const descargandoRef = useRef(false)

  useEffect(
    () => () => {
      controllerRef.current?.abort()
    },
    [],
  )

  const descargar = (id: number, fechaGeneracion: string) => {
    if (descargandoRef.current) return
    descargandoRef.current = true
    const controller = new AbortController()
    controllerRef.current = controller
    setError(null)
    setDescargando(true)
    descargarExcel(id, controller.signal).then(
      (blob) => {
        descargandoRef.current = false
        if (controller.signal.aborted) return
        guardarArchivo(blob, `lista_${id}_${fechaGeneracion}.xlsx`)
        setDescargando(false)
      },
      (reason: unknown) => {
        descargandoRef.current = false
        if (controller.signal.aborted) return
        setError(toMessage(reason))
        setDescargando(false)
      },
    )
  }

  return { descargando, error, descargar }
}
