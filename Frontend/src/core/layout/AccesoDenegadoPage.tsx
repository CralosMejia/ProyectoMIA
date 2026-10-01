export const TITULO_ACCESO_DENEGADO = 'Acceso no permitido'
export const TEXTO_ACCESO_DENEGADO =
  'Este equipo no está autorizado para usar la aplicación. Pida al responsable técnico que lo añada a la lista de equipos permitidos.'

/** Aviso que sustituye a la aplicacion cuando el servidor rechaza este equipo (CU-00). */
export function AccesoDenegadoPage() {
  return (
    <section
      aria-labelledby="acceso-denegado-title"
      className="mx-auto max-w-xl rounded-card border border-degraded bg-degraded/10 p-6 font-sans text-ink"
    >
      <h1 id="acceso-denegado-title" className="mb-4 text-2xl font-semibold">
        {TITULO_ACCESO_DENEGADO}
      </h1>
      <p>{TEXTO_ACCESO_DENEGADO}</p>
    </section>
  )
}
