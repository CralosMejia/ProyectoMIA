import type { DatabaseStatus, HealthStatus } from '../types'

export interface HealthStatusCardProps {
  status: HealthStatus
  database: DatabaseStatus
  checkedAt: Date
}

const STATUS_LABEL: Record<HealthStatus, string> = {
  ok: 'Sistema operativo',
  degraded: 'Servicio degradado',
}

const DATABASE_LABEL: Record<DatabaseStatus, string> = {
  up: 'Base de datos: conectada',
  down: 'Base de datos: sin conexión',
}

const STATUS_DOT: Record<HealthStatus, string> = {
  ok: 'bg-ok',
  degraded: 'bg-degraded',
}

const STATUS_HALO: Record<HealthStatus, string> = {
  ok: 'bg-ok/15',
  degraded: 'bg-degraded/15',
}

/** Presentacional: pinta el estado de salud recibido por props. */
export function HealthStatusCard({ status, database, checkedAt }: HealthStatusCardProps) {
  return (
    <section className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5 font-sans shadow-sm">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className={`flex size-6 items-center justify-center rounded-pill ${STATUS_HALO[status]}`}
        >
          <span className={`size-3 rounded-pill ${STATUS_DOT[status]}`} />
        </span>
        <h2 className="text-lg font-semibold text-ink">{STATUS_LABEL[status]}</h2>
      </div>
      <div className="flex flex-col gap-1 border-t border-line pt-4">
        <p className="text-base text-ink">{DATABASE_LABEL[database]}</p>
        <p className="text-sm text-muted">
          Comprobado:{' '}
          <time dateTime={checkedAt.toISOString()} className="tabular-nums">
            {checkedAt.toLocaleString()}
          </time>
        </p>
      </div>
    </section>
  )
}
