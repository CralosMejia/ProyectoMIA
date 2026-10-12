import { useRef, type ChangeEvent } from 'react'
import { Boton } from '../../../shared/ui/Diseno'

const ID_INPUT = 'carga-archivo'
const ID_AYUDA = 'carga-archivo-ayuda'
const ID_ERROR = 'carga-archivo-error'

export interface SelectorArchivoProps {
  /** Nombre del archivo elegido (null si no hay). */
  archivoSeleccionado: string | null
  /** Validacion local del archivo (extension). */
  errorArchivo: string | null
  /** Mientras valida o envia: no se puede cambiar de archivo. */
  deshabilitado: boolean
  puedeRevisar: boolean
  onSeleccionar: (file: File | null) => void
  onRevisar: () => void
}

/**
 * Presentacional: paso 1 (elegir archivo) y paso 2 ("Revisar archivo") de la carga (R-008 (d)).
 * El `input` real queda oculto y fuera del orden de tabulacion, asociado a su etiqueta; el control
 * visible y enfocable es un boton que abre el dialogo del sistema (Enter/Espacio por ser `button`).
 */
export function SelectorArchivo({
  archivoSeleccionado,
  errorArchivo,
  deshabilitado,
  puedeRevisar,
  onSeleccionar,
  onRevisar,
}: SelectorArchivoProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const descripcion = errorArchivo ? `${ID_AYUDA} ${ID_ERROR}` : ID_AYUDA

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    onSeleccionar(event.target.files?.[0] ?? null)
  }

  return (
    <div className="flex flex-col gap-4 rounded-card border border-line bg-surface p-5 font-sans text-ink shadow-sm">
      <div className="flex flex-col items-center gap-3 rounded-card border-2 border-dashed border-line bg-canvas px-4 py-8 text-center">
        <label htmlFor={ID_INPUT} className="text-base font-semibold">
          Archivo de la plantilla (.xlsx)
        </label>
        <input
          ref={inputRef}
          id={ID_INPUT}
          type="file"
          accept=".xlsx"
          hidden
          tabIndex={-1}
          onChange={onChange}
          disabled={deshabilitado}
          aria-describedby={descripcion}
        />
        <p id={ID_AYUDA} className="text-sm text-muted">
          Suba la plantilla oficial del mes.
        </p>
        <Boton
          onClick={() => inputRef.current?.click()}
          disabled={deshabilitado}
          aria-describedby={descripcion}
        >
          Seleccionar archivo de carga (.xlsx)
        </Boton>
        <p
          aria-live="polite"
          className={`text-sm ${archivoSeleccionado ? 'font-medium text-ink' : 'text-muted'}`}
        >
          {archivoSeleccionado
            ? `Archivo elegido: ${archivoSeleccionado}`
            : 'Ningún archivo seleccionado'}
        </p>
        {errorArchivo && (
          <p id={ID_ERROR} className="text-sm font-medium text-degraded">
            {errorArchivo}
          </p>
        )}
      </div>
      <Boton onClick={onRevisar} disabled={!puedeRevisar} className="self-end">
        Revisar archivo
      </Boton>
    </div>
  )
}
