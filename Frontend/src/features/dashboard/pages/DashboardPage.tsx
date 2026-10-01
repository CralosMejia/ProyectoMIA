import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { AyudaDashboard } from '../components/AyudaDashboard'
import { EmbudoGestion } from '../components/EmbudoGestion'
import { EstadoModeloCard } from '../components/EstadoModeloCard'
import { GraficoResultados } from '../components/GraficoResultados'
import { TablaResultadosCampania } from '../components/TablaResultadosCampania'
import { useDashboard } from '../hooks/useDashboard'

/**
 * Pagina de ruta del dashboard del mes (CU-11): filtro por mes, embudo, resultado de las
 * gestiones, campañas y modelo. Desde R-012: "Resultados de <mes>", ayuda y "Imprimir / Guardar
 * PDF" (`window.print()`; lo que lleva `print:hidden` no sale en papel).
 */
export default function DashboardPage() {
  const { mes, cambiarMes, datos, nombreMes, resumen, cargando, error, reintentar } =
    useDashboard()

  return (
    <section aria-labelledby="dashboard-title" className="flex flex-col gap-6 font-sans text-ink">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 id="dashboard-title" className="text-2xl font-semibold">
            Dashboard
          </h1>
          <p className="text-lg text-ink/70">{`Resultados de ${nombreMes}`}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <AyudaDashboard />
          <button
            type="button"
            onClick={() => window.print()}
            disabled={datos === null}
            className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            Imprimir / Guardar PDF
          </button>
        </div>
      </header>

      <div className="flex flex-col gap-1 print:hidden">
        <label htmlFor="dashboard-mes" className="font-medium">
          Mes
        </label>
        <input
          id="dashboard-mes"
          type="month"
          value={mes}
          onChange={(event) => cambiarMes(event.target.value)}
          className="w-fit rounded-card border border-ink/30 px-3 py-2"
        />
      </div>

      {cargando && <LoadingIndicator label="Cargando el dashboard..." />}
      {error && (
        <div className="print:hidden">
          <ErrorAlert message={error} onRetry={reintentar} />
        </div>
      )}

      {datos && (
        <>
          {datos.porCampania.length === 0 || resumen === null ? (
            <p className="rounded-card border border-ink/20 p-4">
              No hay gestiones asignadas en este mes
            </p>
          ) : (
            <>
              <div className="grid gap-6 lg:grid-cols-2">
                <EmbudoGestion embudo={datos.embudo} />
                <GraficoResultados resumen={resumen} />
              </div>
              <div className="rounded-card border border-ink/10 bg-surface p-5 shadow-sm">
                <TablaResultadosCampania filas={datos.porCampania} />
              </div>
            </>
          )}
          <EstadoModeloCard estadoModelo={datos.estadoModelo} />
        </>
      )}
    </section>
  )
}
