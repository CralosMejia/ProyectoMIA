import type { ChangeEvent } from 'react'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { ResumenCarga, VistaPreviaCarga } from '../components/VistaPreviaCarga'
import { useCarga } from '../hooks/useCarga'

/** Pagina de ruta: conecta useCarga con los componentes presentacionales (CU-01). */
export default function CargaPage() {
  const {
    estado,
    vistaPrevia,
    resumen,
    errorArchivo,
    error,
    puedeConfirmar,
    seleccionarArchivo,
    confirmar,
  } = useCarga()

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    seleccionarArchivo(event.target.files?.[0] ?? null)
  }

  return (
    <section aria-labelledby="carga-title" className="flex flex-col gap-6">
      <h1 id="carga-title" className="text-2xl font-semibold">
        Carga de datos
      </h1>

      <div className="flex flex-col gap-2 font-sans text-ink">
        <label htmlFor="carga-archivo" className="font-medium">
          Archivo de la plantilla (.xlsx)
        </label>
        <input
          id="carga-archivo"
          type="file"
          accept=".xlsx"
          onChange={onChange}
          disabled={estado === 'validando' || estado === 'enviando'}
          aria-describedby={errorArchivo ? 'carga-archivo-error' : undefined}
        />
        {errorArchivo && (
          <p id="carga-archivo-error" className="text-degraded">
            {errorArchivo}
          </p>
        )}
      </div>

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
