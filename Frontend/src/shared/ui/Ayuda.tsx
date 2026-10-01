import { useCallback, useRef, useState, type ReactNode } from 'react'
import { Modal } from './Modal'

/**
 * Ventanas de ayuda compartidas (R-012, decision (f)). API estable para todas las ayudas:
 *
 * - `BotonAyuda({ titulo, children })`: boton con el texto `titulo`; al pulsarlo abre un `Modal`
 *   con ese mismo titulo y `children` como contenido desplazable (`max-h-[60vh]`). "Cerrar" o
 *   `Escape` cierran la ventana y devuelven el foco al boton.
 * - `SeccionAyuda({ titulo, children })`: `<section>` con un `h3` (`titulo`) y su contenido.
 *
 * El texto lo pone cada feature; este modulo no conoce ningun feature.
 */

export interface BotonAyudaProps {
  /** Texto del boton y titulo (nombre accesible) de la ventana. */
  titulo: string
  /** Contenido de la ventana, normalmente varias `SeccionAyuda`. */
  children: ReactNode
}

export interface SeccionAyudaProps {
  /** Titulo de la seccion (`h3`). */
  titulo: string
  children: ReactNode
}

/** Seccion de una ventana de ayuda: titulo `h3` y su contenido. */
export function SeccionAyuda({ titulo, children }: SeccionAyudaProps) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="font-semibold">{titulo}</h3>
      {children}
    </section>
  )
}

/** Boton que abre la ventana de ayuda y devuelve el foco al cerrarla. */
export function BotonAyuda({ titulo, children }: BotonAyudaProps) {
  const [abierta, setAbierta] = useState(false)
  const botonRef = useRef<HTMLButtonElement>(null)

  // Estable: el `Modal` vuelve a enfocar el dialogo cada vez que cambia su `onClose`.
  const cerrar = useCallback(() => {
    setAbierta(false)
    botonRef.current?.focus()
  }, [])

  return (
    <>
      <button
        ref={botonRef}
        type="button"
        onClick={() => setAbierta(true)}
        className="self-start rounded-pill border border-ink/20 px-4 py-2 text-sm font-medium"
      >
        {titulo}
      </button>
      <Modal open={abierta} title={titulo} onClose={cerrar}>
        <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto pr-2 text-sm">
          {children}
        </div>
      </Modal>
    </>
  )
}
