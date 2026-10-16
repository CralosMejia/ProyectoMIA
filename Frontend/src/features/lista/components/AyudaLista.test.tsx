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
      'Campañas',
      'Gestionar a un socio',
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
    expect(within(dialogo).getAllByRole('heading', { level: 3 })).toHaveLength(6)
  })

  /** Texto de la seccion con ese titulo (espacios y saltos de linea colapsados). */
  async function textoDeLaSeccion(titulo: string): Promise<string> {
    const user = userEvent.setup()
    render(<AyudaLista />)
    await user.click(boton())
    const seccion = within(screen.getByRole('dialog'))
      .getByRole('heading', { level: 3, name: titulo })
      .closest('section')
    return (seccion?.textContent ?? '').replace(/\s+/g, ' ')
  }

  it('seccion "Niveles de riesgo": cortes fijos 70 % y 50 %, sin porcentajes de socios (M01)', async () => {
    const texto = await textoDeLaSeccion('Niveles de riesgo: alto, medio y bajo')

    expect(texto).toMatch(/alto si esa probabilidad es de 70 % o más/)
    expect(texto).toMatch(/medio si está entre 50 % y 70 %/)
    expect(texto).toMatch(/bajo si es menor de 50 %/)
    expect(texto).toMatch(/no cambian según cuántos prioritarios pidas/)
    expect(texto).not.toMatch(/20 %|30 %|el resto/)
  })

  it('seccion "Motivos": hasta 3 datos que mas suben el riesgo, sin mes, sin causa y listas anteriores (M03)', async () => {
    const texto = await textoDeLaSeccion('Motivos')

    expect(texto).toMatch(/hasta 3 motivos/)
    expect(texto).toMatch(/los datos del socio que más suben su probabilidad de no renovar/)
    expect(texto).toMatch(/comparado con un socio promedio/)
    expect(texto).toMatch(/El mes en que vence la membresía no se muestra como motivo/)
    expect(texto).toMatch(/no son la causa de que el socio deje de venir/)
    expect(texto).toMatch(/Las listas que ya habías guardado conservan los motivos que tenían/)
    expect(texto).toMatch(/Se muestran sin números, en pantalla y en el Excel/)
    expect(texto).toMatch(/Sin factores de riesgo destacados/)
    expect(texto).not.toMatch(/shap|valor base|one-hot|valor típico|referencia/i)
  })

  it('seccion "Campañas": donde se administran, que se puede hacer y para que sirve cada dato', async () => {
    const texto = await textoDeLaSeccion('Campañas')

    expect(texto).toMatch(/Se crean y administran en la página «Campañas»/)
    expect(texto).toMatch(/crear una campaña, editarla, inactivarla y volver a activarla/)
    expect(texto).toMatch(/Las campañas no se borran/)
    expect(texto).toMatch(
      /Los niveles de riesgo y los planes que marcas en una campaña deciden a qué socios se les sugiere/,
    )
    expect(texto).toMatch(/La prioridad ordena las sugerencias: la campaña con prioridad 1 sale primero/)
    expect(texto).toMatch(/Una campaña inactiva deja de sugerirse hasta que la actives de nuevo/)
  })

  it('seccion "Gestionar a un socio": boton, campaña, seguimiento, preguntas y fecha del contacto', async () => {
    const texto = await textoDeLaSeccion('Gestionar a un socio')

    expect(texto).toMatch(/En la fila de cada socio está el botón «Gestionar»/)
    expect(texto).toMatch(/una de las campañas sugeridas para ese socio o «No asignar campaña»/)
    expect(texto).toMatch(/La fecha de seguimiento es el día en que volverás a revisar a ese socio/)
    expect(texto).toMatch(/«Registrar resultado»/)
    // R-012: al guardar la ventana se cierra; el resultado se anota despues desde la fila.
    expect(texto).toMatch(/Al pulsar «Crear gestión», la ventana se cierra y la lista se actualiza/)
    expect(texto).toMatch(
      /El resultado se anota después con «Registrar resultado» en la fila del socio/,
    )
    expect(texto).toMatch(/Al guardar el resultado, la ventana también se cierra/)
    for (const pregunta of [
      '¿Se contactó al socio?',
      '¿Se ofreció la campaña?',
      '¿Aceptó la campaña?',
      '¿Renovó?',
    ]) {
      expect(texto).toContain(`«${pregunta}»: `)
    }
    expect(texto).toMatch(/«Sí» o «No» cierran la gestión/)
    expect(texto).toMatch(/«Pendiente» la deja abierta/)
    expect(texto).toMatch(
      /La fecha del contacto debe estar entre el día en que se creó la gestión y hoy/,
    )
    expect(texto).toMatch(
      /Si eliges «No asignar campaña», la gestión queda cerrada desde el inicio.*solo se puede consultar/,
    )
  })

  it('las secciones nuevas tampoco usan palabras tecnicas ni codigos', async () => {
    const user = userEvent.setup()
    render(<AyudaLista />)

    await user.click(boton())

    const texto = screen.getByRole('dialog').textContent ?? ''
    for (const prohibida of [
      'API',
      'endpoint',
      'null',
      'PENDIENTE',
      'CERRADA',
      'NO_APLICA',
      '409',
      '422',
    ]) {
      expect(texto).not.toContain(prohibida)
    }
    expect(texto).not.toMatch(/\bestado\b/i)
  })

  it('arquitectura: reutiliza la ayuda compartida de shared/ui y no llama a api/ ni hooks del feature', () => {
    // Desde R-012 el boton y el Modal llegan a traves de shared/ui/Ayuda.
    expect(source).toMatch(/shared\/ui\/Ayuda/)
    expect(source).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(source).not.toMatch(/\.md['"]/)
  })
})
