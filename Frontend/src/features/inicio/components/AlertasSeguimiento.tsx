import { Link } from 'react-router-dom'
import { Tarjeta } from '../../../shared/ui/Diseno'
import type { Alertas } from '../types'

export interface AlertasSeguimientoProps {
  alertas: Alertas
}

const CLASE_ENLACE =
  'flex h-full flex-col gap-2 rounded-card border border-line border-l-4 bg-surface p-4 transition-colors hover:bg-canvas focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

/** Acento de cada grupo: lo vencido destaca en peligro; lo de hoy, en aviso; lo proximo, marca. */
const ACENTO = {
  vencidas: 'border-l-danger',
  hoy: 'border-l-degraded',
  proximas: 'border-l-brand',
} as const

/**
 * Presentacional: tres contadores de seguimientos pendientes (CU-09), cada uno enlaza a la lista
 * del grupo en `/seguimiento?filtro=…`.
 */
export function AlertasSeguimiento({ alertas }: AlertasSeguimientoProps) {
  const grupos = [
    { filtro: 'vencidas', etiqueta: 'Vencidos', total: alertas.vencidas },
    { filtro: 'hoy', etiqueta: 'Para hoy', total: alertas.hoy },
    {
      filtro: 'proximas',
      etiqueta: 'Próximos 7 días',
      total: alertas.proximos7Dias,
    },
  ] as const

  return (
    <Tarjeta aria-labelledby="alertas-title">
      <h2 id="alertas-title" className="text-lg font-semibold">
        Seguimientos pendientes
      </h2>
      <ul className="grid gap-4 sm:grid-cols-3">
        {grupos.map(({ filtro, etiqueta, total }) => (
          <li key={filtro}>
            <Link
              to={`/seguimiento?filtro=${filtro}`}
              className={`${CLASE_ENLACE} ${ACENTO[filtro]}`}
            >
              <span className="text-sm font-medium text-muted">{etiqueta}</span>{' '}
              <span className="text-3xl font-semibold tabular-nums">{total}</span>
            </Link>
          </li>
        ))}
      </ul>
    </Tarjeta>
  )
}
