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
})
