import { CLASE_CAMPO } from '../../../shared/ui/clases'
import { Boton, EncabezadoPagina, Tarjeta } from '../../../shared/ui/Diseno'
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
    <section aria-label="Dashboard" className="flex flex-col gap-6 font-sans text-ink">
      <EncabezadoPagina
        titulo="Dashboard"
        subtitulo={`Resultados de ${nombreMes}`}
        acciones={
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <AyudaDashboard />
            <Boton variante="primario" onClick={() => window.print()} disabled={datos === null}>
              Imprimir / Guardar PDF
            </Boton>
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface px-5 py-3 shadow-sm print:hidden">
        <label htmlFor="dashboard-mes" className="text-sm font-semibold">
          Mes
        </label>
        <input
          id="dashboard-mes"
          type="month"
          value={mes}
          onChange={(event) => cambiarMes(event.target.value)}
          className={`${CLASE_CAMPO} w-fit`}
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
            <Tarjeta>
              <p className="text-sm text-muted">No hay gestiones asignadas en este mes</p>
            </Tarjeta>
          ) : (
            <>
              <div className="grid gap-6 lg:grid-cols-2">
                <EmbudoGestion embudo={datos.embudo} />
                <GraficoResultados resumen={resumen} />
              </div>
              <TablaResultadosCampania filas={datos.porCampania} />
            </>
          )}
          <EstadoModeloCard estadoModelo={datos.estadoModelo} />
        </>
      )}
    </section>
  )
}
