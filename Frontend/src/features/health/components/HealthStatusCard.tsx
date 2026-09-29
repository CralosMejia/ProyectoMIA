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

/** Presentacional: pinta el estado de salud recibido por props. */
export function HealthStatusCard({ status, database, checkedAt }: HealthStatusCardProps) {
  return (
    <section className="rounded-card border border-ink/10 bg-surface p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span aria-hidden="true" className={`size-3 rounded-pill ${STATUS_DOT[status]}`} />
        <h2 className="text-xl font-semibold text-ink">{STATUS_LABEL[status]}</h2>
      </div>
      <p className="mt-3 text-ink">{DATABASE_LABEL[database]}</p>
      <p className="mt-1 text-sm text-ink/60">
        Comprobado: <time dateTime={checkedAt.toISOString()}>{checkedAt.toLocaleString()}</time>
      </p>
    </section>
  )
}
