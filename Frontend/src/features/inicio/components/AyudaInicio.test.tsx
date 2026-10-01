import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { AyudaInicio } from './AyudaInicio'
import source from './AyudaInicio.tsx?raw'

const BOTON = '¿Cómo funciona el inicio?'

function boton(): HTMLButtonElement {
  return screen.getByRole('button', { name: BOTON })
}

async function abrir() {
  const user = userEvent.setup()
  render(<AyudaInicio />)
  await user.click(boton())
  return { user, dialogo: screen.getByRole('dialog', { name: BOTON }) }
}

/** Texto de la seccion con ese titulo (espacios colapsados). */
function textoDeLaSeccion(dialogo: HTMLElement, titulo: string): string {
  const seccion = within(dialogo).getByRole('heading', { level: 3, name: titulo }).closest('section')
  return (seccion?.textContent ?? '').replace(/\s+/g, ' ')
}

describe('AyudaInicio', () => {
  afterEach(() => {
    cleanup()
  })

  it('cerrado por defecto: solo el boton', () => {
    render(<AyudaInicio />)

    expect(boton()).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('al pulsar abre el dialogo con sus tres secciones', async () => {
    const { dialogo } = await abrir()

    expect(
      within(dialogo)
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(['Seguimientos pendientes', 'Qué hacer al pulsar un número', 'Aviso de datos del mes'])
  })

  it('"Seguimientos pendientes": los tres grupos y que solo cuentan las abiertas con campaña', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'Seguimientos pendientes')

    expect(texto).toMatch(/«Vencidos»: la fecha de seguimiento ya pasó/)
    expect(texto).toMatch(/«Para hoy»: la fecha de seguimiento es hoy/)
    expect(texto).toMatch(/«Próximos 7 días»: la fecha de seguimiento es de mañana a 7 días/)
    expect(texto).toMatch(/Solo cuentan las gestiones abiertas que tienen campaña/)
    expect(texto).toMatch(/Las gestiones cerradas y las que se crearon sin campaña no cuentan/)
  })

  it('"Qué hacer al pulsar un número": Seguimiento, «Abrir gestión» y la ventana que se cierra', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'Qué hacer al pulsar un número')

    expect(texto).toMatch(/se abre la página «Seguimiento» con esos socios/)
    expect(texto).toMatch(/«Abrir gestión» abre la ventana para anotar el resultado/)
    expect(texto).toMatch(/Al guardar, la ventana se cierra y la lista se actualiza/)
  })

  it('"Aviso de datos del mes": cuando sale, cuando desaparece y que el historico no cuenta', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'Aviso de datos del mes')

    expect(texto).toMatch(/este mes todavía no se subió la plantilla en la página «Carga»/)
    expect(texto).toMatch(/«Aún no se han cargado los datos de este mes\.»/)
    expect(texto).toMatch(/desaparece cuando se confirma la primera carga del mes/)
    expect(texto).toMatch(/Los datos históricos .* no cuentan/)
  })

  it('el texto no usa palabras tecnicas ni codigos', async () => {
    const { dialogo } = await abrir()
    const texto = dialogo.textContent ?? ''

    for (const prohibida of ['API', 'endpoint', 'null', 'PENDIENTE', 'CERRADA', 'NO_APLICA']) {
      expect(texto).not.toContain(prohibida)
    }
    expect(texto).not.toMatch(/\bSI\b|\bNO\b|\b\d{3}\b/)
  })

  it('"Cerrar" y Escape cierran el dialogo y devuelven el foco al boton', async () => {
    const { user, dialogo } = await abrir()

    await user.click(within(dialogo).getByRole('button', { name: 'Cerrar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()

    await user.click(boton())
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(boton()).toHaveFocus()
  })

  it('arquitectura: usa la ayuda compartida y no llama a api/ ni hooks', () => {
    expect(source).toMatch(/shared\/ui\/Ayuda/)
    expect(source).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
  })
})
