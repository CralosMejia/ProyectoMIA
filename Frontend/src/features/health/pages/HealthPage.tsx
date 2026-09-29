import { HealthStatusCard } from '../components/HealthStatusCard'
import { useHealth } from '../hooks/useHealth'

/** Pagina de ruta: conecta useHealth con los componentes presentacionales. */
export default function HealthPage() {
  const { data, error, isLoading, refetch } = useHealth()

  return (
    // AppLayout aporta el <main> y el fondo: aqui solo una region etiquetada.
    <section aria-labelledby="health-title">
      <h1 id="health-title" className="mb-6 text-2xl font-semibold">
        Estado del sistema
      </h1>

      {isLoading && (
        <p role="status" className="text-ink/70">
          Consultando estado...
        </p>
      )}

      {!isLoading && error && (
        <div
          role="alert"
          className="flex items-center justify-between gap-4 rounded-card border border-degraded bg-degraded/10 p-4"
        >
          <p>{error.message}</p>
          <button
            type="button"
            onClick={refetch}
            className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface"
          >
            Reintentar
          </button>
        </div>
      )}

      {!isLoading && !error && data && (
        <HealthStatusCard status={data.status} database={data.database} checkedAt={data.checkedAt} />
      )}
    </section>
  )
}
