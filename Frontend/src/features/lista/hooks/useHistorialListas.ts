import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { listarListas } from '../api/lista-api'
import type { ListaResumen } from '../types'

const MENSAJE_GENERICO = 'No se pudo consultar el historial de listas.'

export interface UseHistorialListasResult {
  /** De la mas reciente a la mas antigua. */
  listas: ListaResumen[]
  error: string | null
  refrescar: () => void
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

/** Mas reciente primero (por `creadaEn` y, en empate, por id), sin depender del orden recibido. */
function masRecientePrimero(a: ListaResumen, b: ListaResumen): number {
  return b.creadaEn.getTime() - a.creadaEn.getTime() || b.id - a.id
}

/** Historial de listas generadas (D3-FE-03) con cancelacion al desmontar y refresco. */
export function useHistorialListas(): UseHistorialListasResult {
  const [listas, setListas] = useState<ListaResumen[]>([])
  const [error, setError] = useState<string | null>(null)
  const [consulta, setConsulta] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    listarListas(controller.signal).then(
      (resumenes) => {
        if (controller.signal.aborted) return
        setListas([...resumenes].sort(masRecientePrimero))
        setError(null)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setError(toMessage(reason))
      },
    )
    return () => {
      controller.abort()
    }
  }, [consulta])

  const refrescar = () => {
    setConsulta((n) => n + 1)
  }

  return { listas, error, refrescar }
}
