import { EncabezadoPagina } from '../../../shared/ui/Diseno'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { SelectorArchivo } from '../components/SelectorArchivo'
import { ResumenCarga, VistaPreviaCarga } from '../components/VistaPreviaCarga'
import { useCarga } from '../hooks/useCarga'

const TITULO = 'Carga de datos'

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
    // EncabezadoPagina no expone el id del h1: la region se nombra con el mismo texto.
    <section aria-label={TITULO} className="flex flex-col gap-6">
      <EncabezadoPagina titulo={TITULO} />

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
