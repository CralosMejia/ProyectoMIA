import { useEffect, useId, useRef, type ReactNode } from 'react'
import { Boton } from './Diseno'

export interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

/** Dialogo modal accesible: foco al abrir, cierre con Escape o con el boton "Cerrar". */
export function Modal({ open, title, onClose, children }: ModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    dialogRef.current?.focus()

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="w-full max-w-lg rounded-card border border-line bg-surface p-6 font-sans text-ink shadow-xl outline-none"
      >
        <div className="mb-5 flex items-center justify-between gap-4 border-b border-line pb-4">
          <h2 id={titleId} className="text-lg font-semibold tracking-tight">
            {title}
          </h2>
          <Boton onClick={onClose}>Cerrar</Boton>
        </div>
        {children}
      </div>
    </div>
  )
}
