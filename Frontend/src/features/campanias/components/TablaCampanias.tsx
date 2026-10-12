import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { Boton } from '../../../shared/ui/Diseno'
import type { Campania } from '../types'
import { NIVELES, PLANES, etiquetasDe } from './etiquetas'

/** Fila de la tabla: la campaña más una columna virtual de acciones. */
type Fila = Campania & { acciones?: undefined }

export interface TablaCampaniasProps {
  campanias: Campania[]
  deshabilitado: boolean
  onEditar: (campania: Campania) => void
  onInactivar: (campania: Campania) => void
  onActivar: (campania: Campania) => void
}

/** Botones de fila: `Boton` secundario compacto. */
const BOTON_FILA = 'px-3 py-1'

/** Tabla de campañas (CU-06): sin botón de eliminar; las inactivas se editan o se activan. */
export function TablaCampanias({
  campanias,
  deshabilitado,
  onEditar,
  onInactivar,
  onActivar,
}: TablaCampaniasProps) {
  const columnas: DataTableColumn<Fila>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      render: (c) => (
        <span className="flex flex-wrap items-center gap-2 font-medium">
          {c.nombre}
          {c.esEjemplo && (
            <span className="rounded-pill bg-brand/10 px-2 py-0.5 text-xs font-medium text-brand-strong">
              Ejemplo
            </span>
          )}
        </span>
      ),
    },
    {
      key: 'descripcion',
      header: 'Descripción',
      render: (c) => <span className="text-muted">{c.descripcion ?? '—'}</span>,
    },
    { key: 'nivelesRiesgo', header: 'Niveles', render: (c) => etiquetasDe(NIVELES, c.nivelesRiesgo) },
    { key: 'planes', header: 'Planes', render: (c) => etiquetasDe(PLANES, c.planes) },
    {
      key: 'prioridad',
      header: 'Prioridad',
      render: (c) => <span className="tabular-nums">{c.prioridad}</span>,
    },
    {
      key: 'activa',
      header: 'Estado',
      render: (c) => (
        <span
          className={`inline-flex whitespace-nowrap rounded-pill px-2.5 py-0.5 text-xs font-medium ${c.activa ? 'bg-ok/10 text-ink' : 'bg-canvas text-muted'}`}
        >
          {c.activa ? 'Activa' : 'Inactiva'}
        </span>
      ),
    },
    {
      key: 'acciones',
      header: 'Acciones',
      render: (c) => (
        <span className="flex flex-wrap gap-2">
          <Boton
            aria-label={`Editar ${c.nombre}`}
            disabled={deshabilitado}
            onClick={() => onEditar(c)}
            className={BOTON_FILA}
          >
            Editar
          </Boton>
          {c.activa ? (
            <Boton
              aria-label={`Inactivar ${c.nombre}`}
              disabled={deshabilitado}
              onClick={() => onInactivar(c)}
              className={BOTON_FILA}
            >
              Inactivar
            </Boton>
          ) : (
            <Boton
              aria-label={`Activar ${c.nombre}`}
              disabled={deshabilitado}
              onClick={() => onActivar(c)}
              className={BOTON_FILA}
            >
              Activar
            </Boton>
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
