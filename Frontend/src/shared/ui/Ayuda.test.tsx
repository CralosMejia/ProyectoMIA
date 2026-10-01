import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { BotonAyuda, SeccionAyuda } from './Ayuda'

const TITULO = '¿Cómo funciona X?'

function Ejemplo() {
  return (
    <BotonAyuda titulo={TITULO}>
      <SeccionAyuda titulo="Primera parte">
        <p>Texto de ejemplo.</p>
      </SeccionAyuda>
      <SeccionAyuda titulo="Segunda parte">
        <p>Otro texto.</p>
      </SeccionAyuda>
    </BotonAyuda>
  )
}

function boton(): HTMLButtonElement {
  return screen.getByRole('button', { name: TITULO })
}

describe('BotonAyuda / SeccionAyuda', () => {
  afterEach(() => {
    cleanup()
  })

  it('cerrado por defecto: solo el boton con el titulo', () => {
    render(<Ejemplo />)

    expect(boton()).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('al pulsar abre un dialogo con ese nombre, las secciones y el contenido desplazable', async () => {
    const user = userEvent.setup()
    render(<Ejemplo />)

    await user.click(boton())

    const dialogo = screen.getByRole('dialog', { name: TITULO })
    expect(dialogo).toHaveFocus()
    const titulos = within(dialogo)
      .getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent)
    expect(titulos).toEqual(['Primera parte', 'Segunda parte'])
    const seccion = within(dialogo).getByText('Texto de ejemplo.').closest('section')
    expect(seccion).toHaveTextContent('Primera parte')
    const contenedor = seccion?.parentElement
    expect(contenedor?.className).toMatch(/max-h-\[60vh\]/)
    expect(contenedor?.className).toMatch(/overflow-y-auto/)
  })

  it('"Cerrar" cierra el dialogo y devuelve el foco al boton', async () => {
    const user = userEvent.setup()
    render(<Ejemplo />)

    await user.click(boton())
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cerrar' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()
  })

  it('Escape cierra el dialogo y devuelve el foco al boton', async () => {
    const user = userEvent.setup()
    render(<Ejemplo />)

    await user.click(boton())
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()
  })

  it('reabrir tras cerrar vuelve a mostrar el contenido', async () => {
    const user = userEvent.setup()
    render(<Ejemplo />)

    await user.click(boton())
    await user.keyboard('{Escape}')
    await user.click(boton())

    expect(within(screen.getByRole('dialog', { name: TITULO })).getByText('Otro texto.')).toBeInTheDocument()
  })
})
