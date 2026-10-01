import { Link } from 'react-router-dom'
import type { Alertas } from '../types'

export interface AlertasSeguimientoProps {
  alertas: Alertas
}

const CLASE_ENLACE =
  'flex min-w-40 flex-col gap-1 rounded-card border border-ink/20 p-4 hover:bg-ink/5'

/**
 * Presentacional: tres contadores de seguimientos pendientes (CU-09), cada uno enlaza a la lista
 * del grupo en `/seguimiento?filtro=…`.
 */
export function AlertasSeguimiento({ alertas }: AlertasSeguimientoProps) {
  const grupos = [
    { filtro: 'vencidas', etiqueta: 'Vencidos', total: alertas.vencidas },
    { filtro: 'hoy', etiqueta: 'Para hoy', total: alertas.hoy },
    { filtro: 'proximas', etiqueta: 'Próximos 7 días', total: alertas.proximos7Dias },
  ]

  return (
    <section aria-labelledby="alertas-title" className="flex flex-col gap-3 font-sans text-ink">
      <h2 id="alertas-title" className="text-lg font-semibold">
        Seguimientos pendientes
      </h2>
      <ul className="flex flex-wrap gap-4">
        {grupos.map(({ filtro, etiqueta, total }) => (
          <li key={filtro}>
            <Link to={`/seguimiento?filtro=${filtro}`} className={CLASE_ENLACE}>
              <span className="text-sm text-ink/70">{etiqueta}</span>{' '}
              <span className="text-2xl font-semibold">{total}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
