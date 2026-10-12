import { Boton } from '../../../shared/ui/Diseno'
import { HealthStatusCard } from '../components/HealthStatusCard'
import { useHealth } from '../hooks/useHealth'

/** Pagina de ruta: conecta useHealth con los componentes presentacionales. */
export default function HealthPage() {
  const { data, error, isLoading, refetch } = useHealth()

  return (
    // AppLayout aporta el <main> y el fondo: aqui solo una region etiquetada.
    <section aria-labelledby="health-title" className="flex flex-col gap-6 font-sans text-ink">
      <h1 id="health-title" className="text-2xl font-semibold tracking-tight">
        Estado del sistema
      </h1>

      {isLoading && (
        <p role="status" className="text-sm text-muted">
          Consultando estado...
        </p>
      )}

      {!isLoading && error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-degraded/40 border-l-4 border-l-degraded bg-degraded/10 p-4"
        >
          <p>{error.message}</p>
          <Boton onClick={refetch}>Reintentar</Boton>
        </div>
      )}

      {!isLoading && !error && data && (
        <HealthStatusCard
          status={data.status}
          database={data.database}
          checkedAt={data.checkedAt}
        />
      )}
    </section>
  )
}
