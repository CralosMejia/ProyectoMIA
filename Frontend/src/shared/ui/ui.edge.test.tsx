import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DataTable, type DataTableColumn } from './DataTable'
import { ErrorAlert } from './ErrorAlert'
import { LoadingIndicator } from './LoadingIndicator'
import { Modal } from './Modal'

interface Fila {
  id: string
  nombre: string | null
  cantidad: number
}

const COLUMNAS: DataTableColumn<Fila>[] = [
  { key: 'nombre', header: 'Nombre' },
  { key: 'cantidad', header: 'Cantidad' },
]

afterEach(() => {
  cleanup()
})

describe('DataTable (bordes)', () => {
  it('valor null sin render → celda vacia, no el texto "null"', () => {
    render(
      <DataTable
        columns={COLUMNAS}
        rows={[{ id: 'a', nombre: null, cantidad: 0 }]}
        getRowKey={(r) => r.id}
        emptyMessage="Sin datos"
      />,
    )

    const celdas = screen.getAllByRole('cell')
    expect(celdas[0]).toHaveTextContent('')
    expect(celdas[0]?.textContent).toBe('')
    expect(celdas[1]).toHaveTextContent('0')
  })

  it('rows = [] → el mensaje vacio ocupa todas las columnas y hay 2 rows', () => {
    render(<DataTable columns={COLUMNAS} rows={[]} getRowKey={(r) => r.id} emptyMessage="Nada" />)

    expect(screen.getAllByRole('row')).toHaveLength(2)
    expect(screen.getByRole('cell', { name: 'Nada' })).toHaveAttribute('colspan', '2')
  })

  it('sin caption → no renderiza caption y la tabla sigue accesible', () => {
    const { container } = render(
      <DataTable columns={COLUMNAS} rows={[]} getRowKey={(r) => r.id} emptyMessage="Nada" />,
    )

    expect(container.querySelector('caption')).toBeNull()
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it('una fila → 2 rows y las celdas en el orden de las columnas', () => {
    render(
      <DataTable
        columns={COLUMNAS}
        rows={[{ id: 'a', nombre: 'Ana', cantidad: 3 }]}
        getRowKey={(r) => r.id}
        emptyMessage="Nada"
      />,
    )

    const filas = screen.getAllByRole('row')
    expect(filas).toHaveLength(2)
    const fila = filas[1]
    if (!fila) throw new Error('fila no encontrada')
    expect(within(fila).getAllByRole('cell').map((c) => c.textContent)).toEqual(['Ana', '3'])
  })
})

describe('LoadingIndicator (bordes)', () => {
  it('el nombre accesible del status es el label', () => {
    render(<LoadingIndicator label="Procesando archivo" />)

    expect(screen.getByRole('status')).toHaveTextContent(/^Procesando archivo$/)
  })
})

describe('ErrorAlert (bordes)', () => {
  it('dentro de un formulario → clic en "Reintentar" no envia el formulario', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    const onRetry = vi.fn()
    render(
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmit()
        }}
      >
        <ErrorAlert message="Fallo" onRetry={onRetry} />
      </form>,
    )

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('sin clic → onRetry no se llama', () => {
    const onRetry = vi.fn()
    render(<ErrorAlert message="Fallo" onRetry={onRetry} />)

    expect(onRetry).not.toHaveBeenCalled()
  })
})

describe('Modal (bordes)', () => {
  it('open=false → Escape no llama onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <Modal open={false} title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )

    await user.keyboard('{Escape}')

    expect(onClose).not.toHaveBeenCalled()
  })

  it('tras cerrarse (open pasa a false) → Escape ya no llama onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    const { rerender } = render(
      <Modal open title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )
    rerender(
      <Modal open={false} title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )

    await user.keyboard('{Escape}')

    expect(onClose).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('montado directamente con open=true → el foco esta en el dialogo', () => {
    render(
      <Modal open title="Confirmar" onClose={() => {}}>
        contenido
      </Modal>,
    )

    expect(screen.getByRole('dialog', { name: 'Confirmar' })).toHaveFocus()
  })

  it('aria-labelledby apunta al titulo', () => {
    render(
      <Modal open title="Borrar campaña" onClose={() => {}}>
        contenido
      </Modal>,
    )

    const dialog = screen.getByRole('dialog')
    const id = dialog.getAttribute('aria-labelledby')
    expect(id).toBeTruthy()
    expect(document.getElementById(id ?? '')).toHaveTextContent('Borrar campaña')
  })

  it('otra tecla distinta de Escape → no llama onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <Modal open title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )

    await user.keyboard('{Enter}a')

    expect(onClose).not.toHaveBeenCalled()
  })
})
