import { useRef, type ChangeEvent } from 'react'

const ID_INPUT = 'carga-archivo'
const ID_AYUDA = 'carga-archivo-ayuda'
const ID_ERROR = 'carga-archivo-error'

const BOTON =
  'rounded-pill px-4 py-2 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink disabled:opacity-50'

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
    <div className="flex flex-col gap-3 rounded-card border-2 border-dashed border-ink/30 p-6 font-sans text-ink">
      <label htmlFor={ID_INPUT} className="font-medium">
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
      <div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={deshabilitado}
          aria-describedby={descripcion}
          className={`${BOTON} bg-ink text-surface`}
        >
          Seleccionar archivo de carga (.xlsx)
        </button>
      </div>
      <p id={ID_AYUDA} className="text-sm text-ink/70">
        Suba la plantilla oficial del mes.
      </p>
      <p aria-live="polite" className="text-sm">
        {archivoSeleccionado ? `Archivo elegido: ${archivoSeleccionado}` : 'Ningún archivo seleccionado'}
      </p>
      {errorArchivo && (
        <p id={ID_ERROR} className="text-degraded">
          {errorArchivo}
        </p>
      )}
      <div>
        <button
          type="button"
          onClick={onRevisar}
          disabled={!puedeRevisar}
          className={`${BOTON} border border-ink`}
        >
          Revisar archivo
        </button>
      </div>
    </div>
  )
}
