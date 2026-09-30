import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { AyudaLista } from './AyudaLista'
import source from './AyudaLista.tsx?raw'

const BOTON = '¿Cómo funciona esta lista?'

function boton(): HTMLButtonElement {
  return screen.getByRole('button', { name: BOTON })
}

describe('AyudaLista', () => {
  afterEach(() => {
    cleanup()
  })

  it('cerrado por defecto: solo el boton, sin dialogo', () => {
    render(<AyudaLista />)

    expect(boton()).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('al pulsar abre un dialogo con titulo y las secciones del resumen', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())

    const dialogo = screen.getByRole('dialog', { name: BOTON })
    const titulos = within(dialogo)
      .getAllByRole('heading', { level: 3 })
      .map((h) => h.textContent)
    expect(titulos).toEqual([
      'Qué hace la lista',
      'Socios prioritarios a contactar',
      'Niveles de riesgo: alto, medio y bajo',
      'Motivos',
    ])
    const texto = dialogo.textContent ?? ''
    expect(texto).toMatch(/alto/)
    expect(texto).toMatch(/medio/)
    expect(texto).toMatch(/bajo/)
    expect(texto).toMatch(/Sin factores de riesgo destacados/)
    expect(texto).not.toMatch(/Qué datos se muestran/)
    expect(texto).not.toMatch(/Casos frecuentes/)
    expect(texto).not.toMatch(/celular/i)
  })

  it('el texto no usa terminos tecnicos', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())

    const texto = screen.getByRole('dialog').textContent ?? ''
    expect(texto).not.toMatch(/score|top k|\btop\b|horizonte|percentil|modelo v1/i)
  })

  it('Motivos no dice que el Excel incluye los numeros de aporte', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())

    const texto = screen.getByRole('dialog').textContent ?? ''
    expect(texto).not.toMatch(/excel[^.]*(n[uú]mero|aporte|\()/i)
    expect(texto).not.toMatch(/\([+-]\d/)
  })

  it('"Cerrar" cierra el dialogo y devuelve el foco al boton', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cerrar' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()
  })

  it('Escape cierra el dialogo y devuelve el foco al boton', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())
    expect(screen.getByRole('dialog')).toHaveFocus()
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()
  })

  it('reabrir tras cerrar → vuelve a mostrar el dialogo completo', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())
    await user.keyboard('{Escape}')
    await user.click(boton())

    const dialogo = screen.getByRole('dialog', { name: BOTON })
    expect(within(dialogo).getAllByRole('heading', { level: 3 })).toHaveLength(4)
  })

  it('arquitectura: reutiliza el Modal de shared/ui y no llama a api/ ni hooks del feature', () => {
    expect(source).toMatch(/shared\/ui\/Modal/)
    expect(source).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(source).not.toMatch(/\.md['"]/)
  })
})
