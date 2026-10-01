import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { AyudaDashboard } from './AyudaDashboard'
import source from './AyudaDashboard.tsx?raw'

const BOTON = '¿Cómo funciona el dashboard?'

function boton(): HTMLButtonElement {
  return screen.getByRole('button', { name: BOTON })
}

async function abrir() {
  const user = userEvent.setup()
  render(<AyudaDashboard />)
  await user.click(boton())
  return { user, dialogo: screen.getByRole('dialog', { name: BOTON }) }
}

/** Texto de la seccion con ese titulo (espacios colapsados). */
function textoDeLaSeccion(dialogo: HTMLElement, titulo: string): string {
  const seccion = within(dialogo).getByRole('heading', { level: 3, name: titulo }).closest('section')
  return (seccion?.textContent ?? '').replace(/\s+/g, ' ')
}

describe('AyudaDashboard', () => {
  afterEach(() => {
    cleanup()
  })

  it('cerrado por defecto: solo el boton', () => {
    render(<AyudaDashboard />)

    expect(boton()).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('al pulsar abre el dialogo con sus nueve secciones en orden', async () => {
    const { dialogo } = await abrir()

    expect(
      within(dialogo)
        .getAllByRole('heading', { level: 3 })
        .map((h) => h.textContent),
    ).toEqual([
      'El filtro por mes',
      'El embudo',
      'Resultado de las gestiones',
      'La tabla por campaña',
      'Tasa de renovación y de no renovación',
      'Casos insuficientes',
      'La fila «Sin campaña»',
      'La tarjeta del modelo',
      'Qué significan las cifras',
    ])
  })

  it('"El filtro por mes": se cuentan las gestiones creadas en ese mes', async () => {
    const { dialogo } = await abrir()

    expect(textoDeLaSeccion(dialogo, 'El filtro por mes')).toMatch(
      /las gestiones que se crearon en ese mes/,
    )
  })

  it('"El embudo": las cinco etapas y que solo cuenta gestiones con campaña', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'El embudo')

    expect(texto).toMatch(/Solo cuenta las gestiones que tienen campaña/)
    for (const etapa of [
      '«Gestiones asignadas»',
      '«Socios contactados»',
      '«Campaña ofrecida»',
      '«Campaña aceptada»',
      '«Renovaron»',
    ]) {
      expect(texto).toContain(etapa)
    }
  })

  it('"Resultado de las gestiones": renovaron, no renovaron y sin resultado', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'Resultado de las gestiones')

    expect(texto).toMatch(/«Renovaron»: gestiones cerradas en las que el socio renovó/)
    expect(texto).toMatch(/«No renovaron»: gestiones cerradas en las que el socio no renovó/)
    expect(texto).toMatch(/«Sin resultado»: gestiones que siguen abiertas o que se crearon sin campaña/)
  })

  it('"La tabla por campaña": gestiones, contactados y renovaciones', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'La tabla por campaña')

    expect(texto).toMatch(/cuántas gestiones tuvo en el mes/)
    expect(texto).toMatch(/a cuántos socios se contactó/)
    expect(texto).toMatch(/cuántos renovaron/)
  })

  it('"Tasa de renovación y de no renovación": base y ejemplo 4 de 10', async () => {
    const { dialogo } = await abrir()
    const texto = textoDeLaSeccion(dialogo, 'Tasa de renovación y de no renovación')

    expect(texto).toMatch(/solo con las gestiones cerradas con respuesta «Sí» o «No» en «¿Renovó\?»/)
    expect(texto).toMatch(/de 10 gestiones cerradas 4 son «Sí»/)
    expect(texto).toMatch(/tasa de renovación es 40 % y la de no renovación es 60 %/)
  })

  it('"Casos insuficientes", "Sin campaña", tarjeta del modelo y cifras observadas', async () => {
    const { dialogo } = await abrir()

    expect(textoDeLaSeccion(dialogo, 'Casos insuficientes')).toMatch(
      /menos de 10 gestiones cerradas con respuesta/,
    )
    const sinCampania = textoDeLaSeccion(dialogo, 'La fila «Sin campaña»')
    expect(sinCampania).toMatch(/se gestionaron sin asignarles una campaña/)
    expect(sinCampania).toMatch(/nunca tiene tasa/)
    const modelo = textoDeLaSeccion(dialogo, 'La tarjeta del modelo')
    for (const dato of ['versión', 'fecha en que se entrenó', 'ciclos', 'próxima revisión', 'ciclos nuevos']) {
      expect(modelo).toContain(dato)
    }
    expect(textoDeLaSeccion(dialogo, 'Qué significan las cifras')).toMatch(
      /resultados observados.*no demuestran que la campaña causó la renovación/,
    )
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
