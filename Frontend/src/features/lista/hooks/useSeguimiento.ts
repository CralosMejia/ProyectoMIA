import { useEffect, useState } from 'react'
import { ApiError } from '../../../core/http/api-error'
import { listarGestionesPorAlerta } from '../api/lista-api'
import type { FiltroAlerta, GestionResumen, Prediccion } from '../types'
import { type UseGestionResult, useGestion } from './useGestion'

const MENSAJE_GENERICO = 'No se pudieron cargar los seguimientos. Intente de nuevo.'
const FILTROS: readonly FiltroAlerta[] = ['vencidas', 'hoy', 'proximas']

/** Valida el parametro de la URL: solo los tres grupos conocidos; cualquier otro valor → `null`. */
export function filtroAlerta(valor: string | null): FiltroAlerta | null {
  return FILTROS.find((f) => f === valor) ?? null
}

/**
 * La ventana de gestion trabaja con la fila de la lista (`Prediccion`). Desde Seguimiento solo se
 * conoce el resumen de la gestion: se completa con lo necesario para abrirla en "registrar
 * resultado" (la gestion existe y esta pendiente). Prioridad, score y factores no se muestran.
 */
function comoPrediccion(g: GestionResumen): Prediccion {
  return {
    prediccionId: g.prediccionId,
    prioridad: 0,
    socioNombre: g.socioNombre,
    celular: g.celular,
    cedula: null,
    plan: g.plan,
    fechaVencimiento: g.fechaVencimiento,
    diasParaVencer: 0,
    montoCobrado: null,
    score: '',
    nivelRiesgo: g.nivelRiesgo,
    factoresPrincipales: [],
    dentroTopK: false,
    gestionId: g.id,
    gestionEstado: g.estado,
    campaniaAsignada: g.campaniaNombre,
  }
}

interface Resultado {
  filtro: FiltroAlerta
  filas: GestionResumen[] | null
  error: string | null
}

function toMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : MENSAJE_GENERICO
}

export interface UseSeguimientoResult {
  /** Grupo pedido; `null` si el parametro falta o no es valido (no se consulta la API). */
  filtro: FiltroAlerta | null
  gestiones: GestionResumen[] | null
  cargando: boolean
  error: string | null
  reintentar: () => void
  /** Ventana de gestion (CU-10) del socio abierto. */
  ventana: UseGestionResult
  /** Socio cuya ventana esta abierta, para el titulo. */
  abierta: GestionResumen | null
  abrir: (gestion: GestionResumen) => void
}

/**
 * Lista de seguimientos pendientes de un grupo de alertas (CU-09) y ventana de gestion de cada
 * fila. Al guardar un resultado se recarga la lista; si la gestion queda cerrada la ventana se
 * cierra y la fila desaparece. Cambiar de grupo o desmontar cancela la consulta pendiente.
 */
export function useSeguimiento(parametro: string | null): UseSeguimientoResult {
  const filtro = filtroAlerta(parametro)
  // El resultado recuerda su grupo: al cambiar de grupo no se muestran las filas del anterior.
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [recargando, setRecargando] = useState(false)
  const [peticion, setPeticion] = useState(0)
  const [abierta, setAbierta] = useState<GestionResumen | null>(null)

  const recargar = () => {
    setRecargando(true)
    setPeticion((n) => n + 1)
  }

  const ventana = useGestion({ onGuardada: recargar })

  useEffect(() => {
    if (filtro === null) return undefined
    const controller = new AbortController()
    listarGestionesPorAlerta(filtro, controller.signal).then(
      (filas) => {
        if (controller.signal.aborted) return
        setResultado({ filtro, filas, error: null })
        setRecargando(false)
      },
      (reason: unknown) => {
        if (controller.signal.aborted) return
        setResultado({ filtro, filas: null, error: toMessage(reason) })
        setRecargando(false)
      },
    )
    return () => {
      controller.abort()
    }
  }, [filtro, peticion])

  const abrir = (gestion: GestionResumen) => {
    setAbierta(gestion)
    ventana.abrir(comoPrediccion(gestion))
  }

  const actual = filtro !== null && resultado?.filtro === filtro ? resultado : null

  return {
    filtro,
    gestiones: actual?.filas ?? null,
    cargando: filtro !== null && (recargando || actual === null),
    error: recargando ? null : (actual?.error ?? null),
    reintentar: recargar,
    ventana,
    abierta: ventana.prediccion === null ? null : abierta,
    abrir,
  }
}
