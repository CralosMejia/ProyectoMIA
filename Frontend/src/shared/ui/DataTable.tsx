import type { Key, ReactNode } from 'react'

export interface DataTableColumn<T> {
  key: keyof T & string
  header: string
  /** Contenido personalizado de la celda; por defecto se pinta el valor de `row[key]`. */
  render?: (row: T) => ReactNode
}

export interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => Key
  emptyMessage: string
  caption?: string
}

function defaultCell<T>(row: T, key: keyof T & string): ReactNode {
  const value = row[key]
  return value === null || value === undefined ? '' : String(value)
}

/** Tabla presentacional generica: columnas declarativas, mensaje de vacio y caption accesible. */
export function DataTable<T>({ columns, rows, getRowKey, emptyMessage, caption }: DataTableProps<T>) {
  return (
    <table className="w-full border-collapse font-sans text-sm text-ink">
      {caption && <caption className="mb-2 text-left font-semibold">{caption}</caption>}
      <thead>
        <tr className="border-b border-ink/20">
          {columns.map((column) => (
            <th key={column.key} scope="col" className="px-3 py-2 text-left font-semibold">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={columns.length} className="px-3 py-6 text-center text-ink/60">
              {emptyMessage}
            </td>
          </tr>
        ) : (
          rows.map((row) => (
            <tr key={getRowKey(row)} className="border-b border-ink/10">
              {columns.map((column) => (
                <td key={column.key} className="px-3 py-2">
                  {column.render ? column.render(row) : defaultCell(row, column.key)}
                </td>
              ))}
            </tr>
          ))
        )}
      </tbody>
    </table>
  )
}
