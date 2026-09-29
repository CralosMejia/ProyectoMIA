import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Modal } from './Modal'

describe('Modal', () => {
  afterEach(() => {
    cleanup()
  })

  it('open=false → no hay dialog', () => {
    render(
      <Modal open={false} title="Confirmar" onClose={() => {}}>
        contenido
      </Modal>,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.queryByText('contenido')).not.toBeInTheDocument()
  })

  it('open=true → dialog modal cuyo nombre es el title, con el contenido', () => {
    render(
      <Modal open title="Confirmar" onClose={() => {}}>
        contenido
      </Modal>,
    )

    const dialog = screen.getByRole('dialog', { name: 'Confirmar' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(dialog).toHaveTextContent('contenido')
  })

  it('Escape → llama onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <Modal open title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )

    await user.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('boton "Cerrar" → llama onClose', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(
      <Modal open title="Confirmar" onClose={onClose}>
        contenido
      </Modal>,
    )

    await user.click(screen.getByRole('button', { name: 'Cerrar' }))

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('al abrir → el foco pasa al dialogo', () => {
    const { rerender } = render(
      <Modal open={false} title="Confirmar" onClose={() => {}}>
        contenido
      </Modal>,
    )

    rerender(
      <Modal open title="Confirmar" onClose={() => {}}>
        contenido
      </Modal>,
    )

    expect(screen.getByRole('dialog')).toHaveFocus()
  })
})
