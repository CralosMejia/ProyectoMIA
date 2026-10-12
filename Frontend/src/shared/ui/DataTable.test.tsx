import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { DataTable, type DataTableColumn } from './DataTable'

interface Socio {
  id: number
  nombre: string
  score: string
}

const ROWS: Socio[] = [
  { id: 1, nombre: 'Ana', score: '0.91' },
  { id: 2, nombre: 'Luis', score: '0.45' },
  { id: 3, nombre: 'Marta', score: '0.12' },
]

const COLUMNS: DataTableColumn<Socio>[] = [
  { key: 'nombre', header: 'Nombre' },
  { key: 'score', header: 'Score', render: (row) => <strong>score {row.score}</strong> },
]

describe('DataTable', () => {
  afterEach(() => {
    cleanup()
  })

  it('3 filas → 4 rows (cabecera + 3) y columnheader con los titulos', () => {
    render(
      <DataTable caption="Socios" columns={COLUMNS} rows={ROWS} getRowKey={(r) => r.id} emptyMessage="Sin datos" />,
    )

    expect(screen.getByRole('table', { name: 'Socios' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(4)
    expect(screen.getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Nombre', 'Score'])
    expect(screen.getByRole('cell', { name: 'Ana' })).toBeInTheDocument()
    expect(screen.queryByText('Sin datos')).not.toBeInTheDocument()
  })

  it('rows = [] → muestra emptyMessage', () => {
    render(
      <DataTable caption="Socios" columns={COLUMNS} rows={[]} getRowKey={(r) => r.id} emptyMessage="Sin datos" />,
    )

    expect(screen.getByText('Sin datos')).toBeInTheDocument()
    expect(screen.getAllByRole('columnheader')).toHaveLength(2)
  })

  it('render personalizado → se usa en su celda', () => {
    render(
      <DataTable caption="Socios" columns={COLUMNS} rows={ROWS} getRowKey={(r) => r.id} emptyMessage="Sin datos" />,
    )

    const fila = screen.getAllByRole('row')[1]
    if (!fila) throw new Error('fila no encontrada')
    const celdas = within(fila).getAllByRole('cell')
    expect(celdas[0]).toHaveTextContent('Ana')
    const celdaScore = celdas[1]
    if (!celdaScore) throw new Error('celda no encontrada')
    expect(within(celdaScore).getByText('score 0.91').tagName).toBe('STRONG')
  })

  it("columna con className 'w-40' → su th y cada td la llevan; la otra no", () => {
    const columnas: DataTableColumn<Socio>[] = [
      { key: 'nombre', header: 'Nombre', className: 'w-40' },
      { key: 'score', header: 'Score' },
    ]
    render(
      <DataTable caption="Socios" columns={columnas} rows={ROWS} getRowKey={(r) => r.id} emptyMessage="Sin datos" />,
    )

    const [thNombre, thScore] = screen.getAllByRole('columnheader')
    expect(thNombre).toHaveClass('w-40')
    expect(thScore).not.toHaveClass('w-40')
    const filas = screen.getAllByRole('row').slice(1)
    expect(filas).toHaveLength(3)
    for (const fila of filas) {
      const [celdaNombre, celdaScore] = within(fila).getAllByRole('cell')
      expect(celdaNombre).toHaveClass('w-40')
      expect(celdaScore).not.toHaveClass('w-40')
    }
  })

  it('sin className → th y td con las clases base (px-3, cabecera partible y alineada arriba)', () => {
    const { container } = render(
      <DataTable caption="Socios" columns={COLUMNS} rows={ROWS} getRowKey={(r) => r.id} emptyMessage="Sin datos" />,
    )

    const [thNombre, thScore] = screen.getAllByRole('columnheader')
    if (!thNombre || !thScore) throw new Error('cabeceras no encontradas')
    expect(thNombre.className).toBe(thScore.className)
    expect(thNombre).toHaveClass('px-3', 'align-top')
    expect(thNombre).not.toHaveClass('px-4')
    expect(thNombre).not.toHaveClass('whitespace-nowrap')
    expect(thNombre.className).not.toMatch(/undefined/)
    const [celdaNombre, celdaScore] = within(screen.getAllByRole('row')[1] as HTMLElement).getAllByRole('cell')
    if (!celdaNombre || !celdaScore) throw new Error('celdas no encontradas')
    expect(celdaNombre.className).toBe(celdaScore.className)
    expect(celdaNombre).toHaveClass('px-3')
    expect(celdaNombre).not.toHaveClass('px-4')
    expect(celdaNombre.className).not.toMatch(/undefined/)

    const contenedor = container.firstElementChild
    expect(contenedor).toHaveClass(
      'overflow-x-auto',
      'print:overflow-visible',
      'border-line',
      'rounded-card',
      'shadow-sm',
    )
  })
})
