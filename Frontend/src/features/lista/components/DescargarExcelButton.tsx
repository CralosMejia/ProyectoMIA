import { Boton } from '../../../shared/ui/Diseno'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'

export interface DescargarExcelButtonProps {
  /** Id de la lista mostrada; `null` = no hay lista y el boton no aparece. */
  listaId: number | null
  descargando: boolean
  error: string | null
  onDescargar: (listaId: number) => void
}

/** Presentacional: boton de descarga del Excel y su error. */
export function DescargarExcelButton({
  listaId,
  descargando,
  error,
  onDescargar,
}: DescargarExcelButtonProps) {
  if (listaId === null) return null
  return (
    <div className="flex flex-col gap-2">
      <div>
        <Boton onClick={() => onDescargar(listaId)} disabled={descargando} aria-busy={descargando}>
          Descargar Excel
        </Boton>
      </div>
      {descargando && <LoadingIndicator label="Descargando Excel..." />}
      {error && <ErrorAlert message={error} />}
    </div>
  )
}
