import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { SelectorArchivo } from '../components/SelectorArchivo'
import { ResumenCarga, VistaPreviaCarga } from '../components/VistaPreviaCarga'
import { useCarga } from '../hooks/useCarga'

/** Pagina de ruta: conecta useCarga con los componentes presentacionales (CU-01). */
export default function CargaPage() {
  const {
    estado,
    archivoSeleccionado,
    vistaPrevia,
    resumen,
    errorArchivo,
    error,
    puedeRevisar,
    puedeConfirmar,
    seleccionarArchivo,
    revisar,
    confirmar,
  } = useCarga()

  const ocupado = estado === 'validando' || estado === 'enviando'

  return (
    <section aria-labelledby="carga-title" className="flex flex-col gap-6">
      <h1 id="carga-title" className="text-2xl font-semibold">
        Carga de datos
      </h1>

      <SelectorArchivo
        archivoSeleccionado={archivoSeleccionado}
        errorArchivo={errorArchivo}
        deshabilitado={ocupado}
        puedeRevisar={puedeRevisar && !ocupado}
        onSeleccionar={seleccionarArchivo}
        onRevisar={revisar}
      />

      {estado === 'validando' && <LoadingIndicator label="Validando archivo..." />}
      {error && <ErrorAlert message={error} />}
      {vistaPrevia && (estado === 'vista-previa' || estado === 'enviando') && (
        <VistaPreviaCarga
          vistaPrevia={vistaPrevia}
          puedeConfirmar={puedeConfirmar}
          enviando={estado === 'enviando'}
          onConfirmar={confirmar}
        />
      )}
      {estado === 'enviando' && <LoadingIndicator label="Guardando carga..." />}
      {resumen && estado === 'confirmada' && <ResumenCarga resumen={resumen} />}
    </section>
  )
}
