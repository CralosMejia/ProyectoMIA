import type { Key, ReactNode } from 'react'

export interface DataTableColumn<T> {
  key: keyof T & string
  header: string
  /** Contenido personalizado de la celda; por defecto se pinta el valor de `row[key]`. */
  render?: (row: T) => ReactNode
  /** Clases extra (ancho, salto de linea) para el `th` y los `td` de esta columna. */
  className?: string
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => Key
  emptyMessage: string
  caption?: string
}

const CLASE_TH = 'px-3 py-3 text-left align-top text-xs font-semibold tracking-wide text-muted uppercase'
const CLASE_TD = 'px-3 py-3 align-middle'

/** Clases base de la celda mas las de la columna, si las tiene. */
function conClase(base: string, extra?: string): string {
  return extra ? `${base} ${extra}` : base
}

function defaultCell<T>(row: T, key: keyof T & string): ReactNode {
  const value = row[key]
  return value === null || value === undefined ? '' : String(value)
}

/**
 * Tabla presentacional generica: columnas declarativas, mensaje de vacio y caption accesible.
 * Contenedor con borde `line` y desplazamiento horizontal (sin recorte al imprimir); cabecera en
 * `canvas`, partible en varias lineas, y filas alternas. Cada columna puede anadir `className`.
 */
export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage,
  caption,
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-sm print:overflow-visible">
      <table className="w-full border-collapse font-sans text-sm text-ink">
        {caption && (
          <caption className="border-b border-line px-4 py-3 text-left text-base font-semibold">
            {caption}
          </caption>
        )}
        <thead className="bg-canvas">
          <tr className="border-b border-line">
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={conClase(CLASE_TH, column.className)}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={getRowKey(row)}
                className="border-b border-line last:border-b-0 even:bg-canvas/60 hover:bg-brand/5"
              >
                {columns.map((column) => (
                  <td key={column.key} className={conClase(CLASE_TD, column.className)}>
                    {column.render ? column.render(row) : defaultCell(row, column.key)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
