import type { ChangeEvent } from 'react'
import type { ListaResumen } from '../types'

const FECHA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeZone: 'UTC' })

/** Texto de una opcion: "Lista del <fecha larga es-EC> · <K> socios prioritarios". */
function etiquetaLista(lista: ListaResumen): string {
  const fecha = FECHA.format(new Date(`${lista.fechaGeneracion}T00:00:00Z`))
  const prioritarios =
    lista.topK === 1 ? '1 socio prioritario' : `${lista.topK} socios prioritarios`
  return `Lista del ${fecha} · ${prioritarios}`
}

export interface HistorialListasProps {
  /** Ya ordenadas de la mas reciente a la mas antigua. */
  listas: ListaResumen[]
  seleccionadaId: number | null
  deshabilitado?: boolean
  onSeleccionar: (id: number) => void
}

/** Presentacional: selector del historial de listas generadas. */
export function HistorialListas({
  listas,
  seleccionadaId,
  deshabilitado = false,
  onSeleccionar,
}: HistorialListasProps) {
  if (listas.length === 0) return null

  const onChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const elegida = listas.find((l) => String(l.id) === event.target.value)
    if (elegida) onSeleccionar(elegida.id)
  }

  const conocida = listas.some((l) => l.id === seleccionadaId)

  return (
    <div className="flex flex-col gap-2 font-sans text-ink">
      <label htmlFor="historial-listas" className="font-medium">
        Listas anteriores
      </label>
      <select
        id="historial-listas"
        value={conocida ? String(seleccionadaId) : ''}
        onChange={onChange}
        disabled={deshabilitado}
        className="max-w-md rounded-card border border-ink/30 px-3 py-2"
      >
        {!conocida && (
          <option value="" disabled>
            Seleccione una lista
          </option>
        )}
        {listas.map((lista) => (
          <option key={lista.id} value={String(lista.id)}>
            {etiquetaLista(lista)}
          </option>
        ))}
      </select>
    </div>
  )
}
