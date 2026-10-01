import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { obtenerDashboard } from '../api/dashboard-api'
import type { Dashboard } from '../types'
import { nombreDelMes, resumenResultados, type ResumenResultados } from './presentacion'

const MENSAJE_GENERICO = 'No se pudo cargar el dashboard. Intente de nuevo.'
const MES_VALIDO = /^\d{4}-(0[1-9]|1[0-2])$/

/** Mes local actual `YYYY-MM` (el del navegador; el servidor valida el formato). */
export function mesActualLocal(ahora: Date = new Date()): string {
  return `${ahora.getFullYear()}-${String(ahora.getMonth() + 1).padStart(2, '0')}`
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

interface Resultado {
  clave: string
  datos: Dashboard | null
  error: string | null
}

export interface UseDashboardResult {
  /** Mes elegido `YYYY-MM`. */
  mes: string
  /** Ignora valores vacios o con otro formato (el campo a medio escribir). */
  cambiarMes: (mes: string) => void
  datos: Dashboard | null
  /** Mes elegido en palabras ("septiembre de 2026"), para el titulo de resultados. */
  nombreMes: string
  /** Cifras del grafico de resultados del mes; null sin datos. */
  resumen: ResumenResultados | null
  cargando: boolean
  error: string | null
  reintentar: () => void
}

/**
 * Dashboard del mes elegido (CU-11); empieza en el mes local actual. Cambiar de mes cancela la
 * peticion anterior; al desmontar tambien se cancela.
 */
export function useDashboard(): UseDashboardResult {
  const [mes, setMes] = useState(() => mesActualLocal())
  const [peticion, setPeticion] = useState(0)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const clave = `${mes}#${peticion}`

  useEffect(() => {
    const controller = new AbortController()
    obtenerDashboard(mes, controller.signal).then(
      (datos) => {
        if (!controller.signal.aborted) setResultado({ clave, datos, error: null })
      },
      (reason: unknown) => {
        if (!controller.signal.aborted) {
          setResultado({ clave, datos: null, error: toMessage(reason) })
        }
      },
    )
    return () => {
      controller.abort()
    }
  }, [mes, clave])

  const cambiarMes = (valor: string) => {
    if (MES_VALIDO.test(valor)) setMes(valor)
  }

  const actual = resultado?.clave === clave ? resultado : null
  const datos = actual?.datos ?? null

  return {
    mes,
    cambiarMes,
    datos,
    nombreMes: nombreDelMes(mes),
    resumen: datos === null ? null : resumenResultados(datos.porCampania),
    cargando: actual === null,
    error: actual?.error ?? null,
    reintentar: () => setPeticion((n) => n + 1),
  }
}
