import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { EstadoSistemaPanel } from '../components/EstadoSistemaPanel'
import { useEstadoSistema } from '../hooks/useEstadoSistema'

/** Pagina de ruta: conecta useEstadoSistema con los componentes presentacionales. */
export default function InicioPage() {
  const { data, error, isLoading, refetch } = useEstadoSistema()

  return (
    <section aria-labelledby="inicio-title">
      <h1 id="inicio-title" className="mb-6 text-2xl font-semibold">
        Inicio
      </h1>

      {isLoading && <LoadingIndicator label="Consultando estado del sistema..." />}
      {!isLoading && error && <ErrorAlert message={error} onRetry={refetch} />}
      {!isLoading && !error && data && <EstadoSistemaPanel estado={data} />}
    </section>
  )
}
