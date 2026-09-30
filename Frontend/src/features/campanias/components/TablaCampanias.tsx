import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import type { Campania } from '../types'
import { NIVELES, PLANES, etiquetasDe } from './etiquetas'

/** Fila de la tabla: la campaña más una columna virtual de acciones. */
type Fila = Campania & { acciones?: undefined }

export interface TablaCampaniasProps {
  campanias: Campania[]
  deshabilitado: boolean
  onEditar: (campania: Campania) => void
  onInactivar: (campania: Campania) => void
}

const BOTON = 'rounded-pill border border-ink/20 px-3 py-1 text-sm font-medium disabled:opacity-50'

/** Tabla de campañas (CU-06): sin botón de eliminar; las inactivas solo se editan. */
export function TablaCampanias({
  campanias,
  deshabilitado,
  onEditar,
  onInactivar,
}: TablaCampaniasProps) {
  const columnas: DataTableColumn<Fila>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      render: (c) => (
        <span className="flex flex-wrap items-center gap-2">
          {c.nombre}
          {c.esEjemplo && (
            <span className="rounded-pill border border-ink/20 px-2 text-xs text-ink/70">
              Ejemplo
            </span>
          )}
        </span>
      ),
    },
    { key: 'descripcion', header: 'Descripción', render: (c) => c.descripcion ?? '—' },
    { key: 'nivelesRiesgo', header: 'Niveles', render: (c) => etiquetasDe(NIVELES, c.nivelesRiesgo) },
    { key: 'planes', header: 'Planes', render: (c) => etiquetasDe(PLANES, c.planes) },
    { key: 'prioridad', header: 'Prioridad' },
    { key: 'activa', header: 'Estado', render: (c) => (c.activa ? 'Activa' : 'Inactiva') },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (c) => (
        <span className="flex flex-wrap gap-2">
          <button
            type="button"
            aria-label={`Editar ${c.nombre}`}
            disabled={deshabilitado}
            onClick={() => onEditar(c)}
            className={BOTON}
          >
            Editar
          </button>
          {c.activa && (
            <button
              type="button"
              aria-label={`Inactivar ${c.nombre}`}
              disabled={deshabilitado}
              onClick={() => onInactivar(c)}
              className={BOTON}
            >
              Inactivar
            </button>
          )}
        </span>
      ),
    },
  ]

  return (
    <DataTable
      columns={columnas}
      rows={campanias}
      getRowKey={(c) => c.id}
      emptyMessage="Aún no hay campañas. Pulse «Nueva campaña» para crear la primera."
      caption="Campañas de retención"
    />
  )
}
