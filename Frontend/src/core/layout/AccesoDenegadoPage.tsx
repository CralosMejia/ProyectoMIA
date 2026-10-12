export const TITULO_ACCESO_DENEGADO = 'Acceso no permitido'
export const TEXTO_ACCESO_DENEGADO =
  'Este equipo no está autorizado para usar la aplicación. Pida al responsable técnico que lo añada a la lista de equipos permitidos.'

/** Aviso que sustituye a la aplicacion cuando el servidor rechaza este equipo (CU-00). */
export function AccesoDenegadoPage() {
  return (
    <section
      aria-labelledby="acceso-denegado-title"
      className="mx-auto flex max-w-xl flex-col gap-3 rounded-card border border-line border-t-4 border-t-degraded bg-surface p-8 font-sans text-ink shadow-sm"
    >
      <span aria-hidden="true" className="size-3 rounded-pill bg-degraded" />
      <h1 id="acceso-denegado-title" className="text-2xl font-semibold tracking-tight">
        {TITULO_ACCESO_DENEGADO}
      </h1>
      <p className="text-base leading-relaxed text-muted">{TEXTO_ACCESO_DENEGADO}</p>
    </section>
  )
}
