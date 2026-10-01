import { Link } from 'react-router-dom'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { AlertasSeguimiento } from '../components/AlertasSeguimiento'
import { AyudaInicio } from '../components/AyudaInicio'
import { EstadoSistemaPanel } from '../components/EstadoSistemaPanel'
import { useAlertas } from '../hooks/useAlertas'
import { useEstadoSistema } from '../hooks/useEstadoSistema'

export const AVISO_DATOS_MES = 'Aún no se han cargado los datos de este mes.'

/** Pagina de ruta: conecta el estado del sistema y los seguimientos con los componentes. */
export default function InicioPage() {
  const { data, error, isLoading, refetch } = useEstadoSistema()
  const listo = !isLoading && !error && data?.estado === 'LISTO'
  const alertas = useAlertas(listo)

  return (
    <section aria-labelledby="inicio-title" className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 id="inicio-title" className="text-2xl font-semibold">
          Inicio
        </h1>
        {/* Siempre visible: tambien si el estado falla o el sistema no esta listo. */}
        <AyudaInicio />
      </div>

      {isLoading && <LoadingIndicator label="Consultando estado del sistema..." />}
      {!isLoading && error && <ErrorAlert message={error} onRetry={refetch} />}
      {!isLoading && !error && data && <EstadoSistemaPanel estado={data} />}

      {listo && data.datosMesCargados === false && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-degraded bg-degraded/10 p-4 font-sans text-ink">
          <p>{AVISO_DATOS_MES}</p>
          <Link
            to="/carga"
            className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface"
          >
            Ir a Carga
          </Link>
        </div>
      )}

      {listo && alertas.isLoading && (
        <p className="font-sans text-ink/70">Consultando seguimientos pendientes...</p>
      )}
      {listo && !alertas.isLoading && alertas.error && (
        <ErrorAlert message={alertas.error} onRetry={alertas.refetch} />
      )}
      {listo && !alertas.isLoading && !alertas.error && alertas.data && (
        <AlertasSeguimiento alertas={alertas.data} />
      )}
    </section>
  )
}
