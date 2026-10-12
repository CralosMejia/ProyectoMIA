import { Link } from 'react-router-dom'
import { claseBoton } from '../../../shared/ui/clases'
import { EncabezadoPagina } from '../../../shared/ui/Diseno'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { AlertasSeguimiento } from '../components/AlertasSeguimiento'
import { AyudaInicio } from '../components/AyudaInicio'
import { EstadoSistemaPanel } from '../components/EstadoSistemaPanel'
import { useAlertas } from '../hooks/useAlertas'
import { useEstadoSistema } from '../hooks/useEstadoSistema'

export const AVISO_DATOS_MES = 'Aún no se han cargado los datos de este mes.'

const TITULO = 'Inicio'

/** Pagina de ruta: conecta el estado del sistema y los seguimientos con los componentes. */
export default function InicioPage() {
  const { data, error, isLoading, refetch } = useEstadoSistema()
  const listo = !isLoading && !error && data?.estado === 'LISTO'
  const alertas = useAlertas(listo)

  return (
    // EncabezadoPagina no expone el id del h1: la region se nombra con el mismo texto.
    <section aria-label={TITULO} className="flex flex-col gap-6">
      {/* La ayuda queda siempre visible: tambien si el estado falla o el sistema no esta listo. */}
      <EncabezadoPagina titulo={TITULO} acciones={<AyudaInicio />} />

      {isLoading && <LoadingIndicator label="Consultando estado del sistema..." />}
      {!isLoading && error && <ErrorAlert message={error} onRetry={refetch} />}
      {!isLoading && !error && data && <EstadoSistemaPanel estado={data} />}

      {listo && data.datosMesCargados === false && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-degraded/40 border-l-4 border-l-degraded bg-degraded/10 p-4 font-sans text-sm text-ink">
          <p className="font-medium">{AVISO_DATOS_MES}</p>
          <Link
            to="/carga"
            className={claseBoton('primario')}
          >
            Ir a Carga
          </Link>
        </div>
      )}

      {listo && alertas.isLoading && (
        <p className="font-sans text-sm text-muted">Consultando seguimientos pendientes...</p>
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
