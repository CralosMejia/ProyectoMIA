import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import {
  escenariosGestion,
  escenariosLista,
  MENSAJE_GESTION_DUPLICADA,
  simularGestiones,
} from '../api/lista-api.handlers'
import ListaPage from './ListaPage'
import pageSource from './ListaPage.tsx?raw'
import tablaSource from '../components/TablaLista.tsx?raw'

const LISTAS_PATH = '*/api/v1/listas'
const MENSAJE_409 = 'El sistema se esta inicializando; intente de nuevo en unos minutos.'
const MENSAJE_422 = 'La fecha de la lista debe ser hoy o posterior.'
const HOY = '2026-09-29'
const PRIORITARIOS = 'Socios prioritarios a contactar'
const OTROS = 'Otros socios por vencer'

const FECHA = /fecha de la lista/i
const DIAS = /buscar socios que vencen en los próximos/i
const K = /socios prioritarios a contactar/i
const NOMBRE = /nombre de la lista/i
const SUGERIDO_HOY = 'Lista del 29 sep 2026'

function fechaCorta(iso: string): string {
  return new Intl.DateTimeFormat('es-EC', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${iso}T00:00:00Z`),
  )
}

/** Registra cada POST /listas (sin responder: cae al handler por defecto del feature). */
function registrarPosts() {
  const cuerpos: unknown[] = []
  server.use(
    http.post(LISTAS_PATH, async ({ request }) => {
      cuerpos.push(await request.clone().json())
      return undefined
    }),
  )
  return cuerpos
}

function campo(nombre: RegExp): HTMLInputElement {
  return screen.getByLabelText(nombre)
}

function botonGenerar(): HTMLButtonElement {
  return screen.getByRole('button', { name: 'Generar lista' })
}

/** Espera a que se pinte la lista y devuelve la tabla indicada (por defecto, la de prioritarios). */
async function tablaCargada(nombre = PRIORITARIOS) {
  return within(await screen.findByRole('table', { name: nombre }))
}

async function filasDe(nombre: string): Promise<HTMLElement[]> {
  return (await tablaCargada(nombre)).getAllByRole('row').slice(1)
}

describe('ListaPage', () => {
  beforeEach(() => {
    // Solo se simula la fecha: MSW y user-event siguen con temporizadores reales.
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 8, 29, 12, 0, 0))
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('titulo y campos con etiqueta amigable: fecha = hoy (min hoy), dias 30 (max 31), prioritarios 25', async () => {
    render(<ListaPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeInTheDocument()
    expect(campo(FECHA)).toHaveAttribute('type', 'date')
    expect(campo(FECHA)).toHaveValue(HOY)
    expect(campo(FECHA)).toHaveAttribute('min', HOY)
    expect(campo(DIAS)).toHaveValue(30)
    expect(campo(DIAS)).toHaveAttribute('max', '31')
    expect(campo(K)).toHaveValue(25)
    await tablaCargada()
  })

  it('la pagina no muestra "Top K", "Horizonte", "score" ni "Versión del modelo"', async () => {
    render(<ListaPage />)
    await tablaCargada()

    const texto = document.body.textContent ?? ''
    expect(texto).not.toMatch(/top k|horizonte|score|versi[oó]n del modelo/i)
    expect(texto).not.toMatch(/\bv1\b/)
    expect(texto).not.toContain('0.95000000')
  })

  it('al entrar carga GET /listas/ultima y pinta prioritarios y otros socios', async () => {
    render(<ListaPage />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando la última lista')
    // 32 socios simulados: 25 prioritarios + 7 otros.
    expect(await filasDe(PRIORITARIOS)).toHaveLength(25)
    expect(await filasDe(OTROS)).toHaveLength(7)
    expect(screen.getByText('Rango de fechas: 28 sep – 28 oct 2026')).toBeInTheDocument()
    expect(screen.getByText('Socios priorizados para campañas: 25')).toBeInTheDocument()
  })

  it('/ultima con 404 → estado vacio, sin tabla ni boton de Excel', async () => {
    server.use(...escenariosLista.sinListas)

    render(<ListaPage />)

    expect(await screen.findByText(/Aún no se ha generado ninguna lista/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Descargar Excel' })).not.toBeInTheDocument()
  })

  it('la tabla muestra columnas con cedula, vencimiento es-EC y nivel, sin score ni Top', async () => {
    render(<ListaPage />)
    const tabla = await tablaCargada()

    const cabeceras = tabla.getAllByRole('columnheader').map((th) => th.textContent)
    expect(cabeceras).toEqual([
      'Prioridad',
      'Nombre',
      'Cédula',
      'Plan',
      'Vence el',
      'Días para vencer',
      'Nivel de riesgo',
      'Motivos principales',
      'Gestión',
      'Campaña',
      'Acción',
    ])
    const otrosCabeceras = (await tablaCargada(OTROS))
      .getAllByRole('columnheader')
      .map((th) => th.textContent)
    expect(otrosCabeceras).toEqual(cabeceras)

    const filas = tabla.getAllByRole('row').slice(1)
    const primera = within(filas[0] as HTMLElement)
    expect(primera.getByText('Ana Prueba')).toBeInTheDocument()
    expect(primera.getByText('0000000000')).toBeInTheDocument()
    // El celular sigue en la API y el Excel, pero no se muestra en pantalla.
    expect(primera.queryByText('0990000000')).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/celular|099000\d{4}/i)
    expect(primera.getByText(fechaCorta('2026-10-01'))).toBeInTheDocument()
    expect(primera.getByText('Alto')).toBeInTheDocument()
    expect(primera.queryByText('0.95000000')).not.toBeInTheDocument()

    // La prioridad 26 (primera fuera de los 25) abre la tabla de otros socios.
    const otros = await filasDe(OTROS)
    expect(within(otros[0] as HTMLElement).getAllByRole('cell')[0]).toHaveTextContent(/^26$/)
  })

  it('factores [] → "Sin factores de riesgo destacados"', async () => {
    render(<ListaPage />)
    const filas = await filasDe(PRIORITARIOS)

    // En los datos simulados cada septimo socio (prioridad 7) no tiene factores.
    expect(within(filas[6] as HTMLElement).getByText('Sin factores de riesgo destacados')).toBeInTheDocument()
  })

  it('una lista antigua con un socio sin cedula muestra "—"', async () => {
    server.use(escenariosLista.ultimaConDatosAntiguos)
    render(<ListaPage />)

    // Lista anterior: 10 prioritarios; el tercero no tiene cedula.
    const filas = await filasDe(PRIORITARIOS)
    expect(within(filas[2] as HTMLElement).getAllByRole('cell')[2]).toHaveTextContent(/^—$/)
  })

  it('Generar lista → POST con los parametros y la tabla muestra la lista generada', async () => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.clear(campo(DIAS))
    await user.type(campo(DIAS), '20')
    await user.clear(campo(K))
    await user.type(campo(K), '10')
    await user.clear(campo(FECHA))
    await user.type(campo(FECHA), '2026-10-15')
    await user.click(botonGenerar())

    await waitFor(() =>
      expect(screen.getByText('Socios priorizados para campañas: 10')).toBeInTheDocument(),
    )
    expect(await filasDe(PRIORITARIOS)).toHaveLength(10)
    expect(screen.getByText('Rango de fechas: 15 oct – 4 nov 2026')).toBeInTheDocument()
    expect(cuerpos).toEqual([
      {
        fecha_referencia: '2026-10-15',
        horizonte_dias: 20,
        top_k: 10,
        nombre: 'Lista del 15 oct 2026',
      },
    ])
  })

  it('sin tocar la fecha → envia la de hoy (nunca null)', async () => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())

    await waitFor(() => expect(cuerpos).toHaveLength(1))
    expect(cuerpos[0]).toEqual({
      fecha_referencia: HOY,
      horizonte_dias: 30,
      top_k: 25,
      nombre: SUGERIDO_HOY,
    })
  })

  it.each([
    ['fecha anterior a hoy', FECHA, '2026-09-28', 'La fecha debe ser hoy o posterior.'],
    ['fecha vacia', FECHA, '', 'Indique la fecha de la lista.'],
    ['dias 0', DIAS, '0', 'Entre 1 y 31 días.'],
    ['dias 32', DIAS, '32', 'Entre 1 y 31 días.'],
    ['dias vacio', DIAS, '', 'Entre 1 y 31 días.'],
    ['prioritarios 0', K, '0', /mayor o igual a 1/],
    ['prioritarios vacio', K, '', /mayor o igual a 1/],
  ])('%s → mensaje local y no llama a la API', async (_caso, etiqueta, valor, mensaje) => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.clear(campo(etiqueta))
    if (valor !== '') await user.type(campo(etiqueta), valor)
    await user.click(botonGenerar())

    expect(await screen.findByText(mensaje)).toBeInTheDocument()
    expect(campo(etiqueta)).toHaveAttribute('aria-invalid', 'true')
    expect(cuerpos).toHaveLength(0)
  })

  it.each([
    ['dias 1 (minimo)', HOY, '1', '25', { fecha_referencia: HOY, horizonte_dias: 1, top_k: 25, nombre: SUGERIDO_HOY }],
    ['dias 31 (maximo)', HOY, '31', '25', { fecha_referencia: HOY, horizonte_dias: 31, top_k: 25, nombre: SUGERIDO_HOY }],
    ['prioritarios 1 (minimo)', HOY, '30', '1', { fecha_referencia: HOY, horizonte_dias: 30, top_k: 1, nombre: SUGERIDO_HOY }],
    ['fecha futura', '2026-12-31', '30', '25', { fecha_referencia: '2026-12-31', horizonte_dias: 30, top_k: 25, nombre: 'Lista del 31 dic 2026' }],
  ])('frontera valida %s → se acepta y llama a la API', async (_caso, fecha, dias, k, esperado) => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    if (fecha !== HOY) {
      await user.clear(campo(FECHA))
      await user.type(campo(FECHA), fecha)
    }
    await user.clear(campo(DIAS))
    await user.type(campo(DIAS), dias)
    await user.clear(campo(K))
    await user.type(campo(K), k)
    await user.click(botonGenerar())

    await waitFor(() => expect(cuerpos).toHaveLength(1))
    expect(cuerpos[0]).toEqual(esperado)
    expect(campo(FECHA)).not.toHaveAttribute('aria-invalid')
    expect(campo(DIAS)).not.toHaveAttribute('aria-invalid')
    expect(campo(K)).not.toHaveAttribute('aria-invalid')
  })

  describe('nombre de la lista', () => {
    it('al entrar es el sugerido para hoy, es el primer campo y tiene maxLength 80', async () => {
      render(<ListaPage />)

      expect(campo(NOMBRE)).toHaveValue(SUGERIDO_HOY)
      expect(campo(NOMBRE)).toHaveAttribute('type', 'text')
      expect(campo(NOMBRE)).toHaveAttribute('maxLength', '80')
      const formulario = screen.getByRole('form', { name: 'Parámetros de la lista' })
      expect(within(formulario).getAllByRole('textbox')[0]).toBe(campo(NOMBRE))
      await tablaCargada()
    })

    it('sin tocar el nombre, sigue a la fecha', async () => {
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.clear(campo(FECHA))
      await user.type(campo(FECHA), '2026-10-02')

      expect(campo(NOMBRE)).toHaveValue('Lista del 2 oct 2026')
    })

    it('editado a mano se respeta al cambiar la fecha; si vuelve a la sugerencia, la sigue otra vez', async () => {
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.clear(campo(NOMBRE))
      await user.type(campo(NOMBRE), 'Campaña octubre')
      await user.clear(campo(FECHA))
      await user.type(campo(FECHA), '2026-10-02')
      expect(campo(NOMBRE)).toHaveValue('Campaña octubre')

      await user.clear(campo(NOMBRE))
      await user.type(campo(NOMBRE), 'Lista del 2 oct 2026')
      await user.clear(campo(FECHA))
      await user.type(campo(FECHA), '2026-10-05')
      expect(campo(NOMBRE)).toHaveValue('Lista del 5 oct 2026')
    })

    it.each([
      ['vacio', ''],
      ['solo espacios', '   '],
    ])('%s → "Escriba un nombre para la lista." y no llama a la API', async (_caso, valor) => {
      const cuerpos = registrarPosts()
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.clear(campo(NOMBRE))
      if (valor !== '') await user.type(campo(NOMBRE), valor)
      await user.click(botonGenerar())

      const mensaje = await screen.findByText('Escriba un nombre para la lista.')
      expect(campo(NOMBRE)).toHaveAttribute('aria-invalid', 'true')
      expect(campo(NOMBRE).getAttribute('aria-describedby')).toContain(mensaje.id)
      expect(cuerpos).toHaveLength(0)
    })

    it('mas de 80 no se puede escribir; si llegara → "El nombre puede tener hasta 80 caracteres."', async () => {
      const cuerpos = registrarPosts()
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.clear(campo(NOMBRE))
      await user.type(campo(NOMBRE), 'x'.repeat(85))
      expect(campo(NOMBRE)).toHaveValue('x'.repeat(80))

      fireEvent.change(campo(NOMBRE), { target: { value: 'x'.repeat(81) } })
      await user.click(botonGenerar())

      expect(await screen.findByText('El nombre puede tener hasta 80 caracteres.')).toBeInTheDocument()
      expect(campo(NOMBRE)).toHaveAttribute('aria-invalid', 'true')
      expect(cuerpos).toHaveLength(0)
    })

    it('Generar lista envia el nombre recortado y la lista generada lo muestra como titulo', async () => {
      const cuerpos = registrarPosts()
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.clear(campo(NOMBRE))
      await user.type(campo(NOMBRE), '  Campaña octubre  ')
      await user.click(botonGenerar())

      expect(
        await screen.findByRole('heading', { level: 2, name: 'Campaña octubre' }),
      ).toBeInTheDocument()
      expect(cuerpos).toEqual([
        { fecha_referencia: HOY, horizonte_dias: 30, top_k: 25, nombre: 'Campaña octubre' },
      ])
    })

    it('400 del servidor → ErrorAlert con su mensaje', async () => {
      server.use(
        http.post(LISTAS_PATH, () =>
          HttpResponse.json(
            { error: { code: 'validation_error', message: 'El nombre no es valido.' } },
            { status: 400 },
          ),
        ),
      )
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()

      await user.click(botonGenerar())

      expect(await screen.findByRole('alert')).toHaveTextContent('El nombre no es valido.')
      expect(botonGenerar()).toBeEnabled()
    })

    it('la ultima lista muestra su nombre como titulo', async () => {
      render(<ListaPage />)

      expect(
        await screen.findByRole('heading', { level: 2, name: 'Lista del 28 sep 2026' }),
      ).toBeInTheDocument()
    })
  })

  it('corregir un valor invalido quita el mensaje local', async () => {
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.clear(campo(DIAS))
    await user.type(campo(DIAS), '32')
    await user.click(botonGenerar())
    expect(await screen.findByText('Entre 1 y 31 días.')).toBeInTheDocument()

    await user.clear(campo(DIAS))
    await user.type(campo(DIAS), '30')

    expect(screen.queryByText('Entre 1 y 31 días.')).not.toBeInTheDocument()
    expect(campo(DIAS)).not.toHaveAttribute('aria-invalid')
  })

  it('422 del servidor → ErrorAlert con su mensaje y se conserva la lista', async () => {
    server.use(escenariosLista.fechaPasada)
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())

    expect(await screen.findByRole('alert')).toHaveTextContent(MENSAJE_422)
    expect(await filasDe(PRIORITARIOS)).toHaveLength(25)
    expect(botonGenerar()).toBeEnabled()
  })

  it('409 al generar → la lista mostrada antes se conserva', async () => {
    server.use(escenariosLista.sistemaInicializando)
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())

    expect(await screen.findByRole('alert')).toHaveTextContent(MENSAJE_409)
    expect(await filasDe(PRIORITARIOS)).toHaveLength(25)
    expect(await filasDe(OTROS)).toHaveLength(7)
    expect(screen.getByText('Ana Prueba')).toBeInTheDocument()
  })

  it('prioritarios decimal (2.5) → mensaje local y no llama a la API', async () => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.clear(campo(K))
    await user.type(campo(K), '2.5')
    await user.click(botonGenerar())

    expect(await screen.findByText(/mayor o igual a 1/)).toBeInTheDocument()
    expect(cuerpos).toHaveLength(0)
  })

  it('el boton se deshabilita mientras envia (sin doble envio)', async () => {
    let llamadas = 0
    let responder: () => void = () => {}
    server.use(
      http.post(LISTAS_PATH, async () => {
        llamadas += 1
        await new Promise<void>((resolve) => {
          responder = resolve
        })
        return undefined
      }),
    )
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())
    expect(botonGenerar()).toBeDisabled()
    await user.dblClick(botonGenerar())
    expect(await screen.findByText('Generando lista...')).toBeInTheDocument()

    responder()
    await waitFor(() => expect(botonGenerar()).toBeEnabled())
    expect(llamadas).toBe(1)
  })

  it('409 → "El sistema se esta inicializando…" con role="alert"', async () => {
    server.use(escenariosLista.sistemaInicializando)
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())

    expect(await screen.findByRole('alert')).toHaveTextContent(MENSAJE_409)
    expect(botonGenerar()).toBeEnabled()
  })

  it('advertenciaDatosAntiguos → aviso sin tecnicismos: carga de mas de 30 dias y faltan datos del mes', async () => {
    server.use(escenariosLista.ultimaConDatosAntiguos)
    render(<ListaPage />)

    const aviso = await screen.findByRole('alert')
    expect(aviso).toHaveTextContent(/datos pueden estar desactualizados/i)
    expect(aviso).toHaveTextContent(/la última carga de datos tiene más de 30 días/i)
    expect(aviso).toHaveTextContent(/faltan los datos del mes/i)
    expect(aviso.textContent ?? '').not.toMatch(/referencia|horizonte|modelo|score/i)
  })

  it('sin advertencia → no hay aviso', async () => {
    render(<ListaPage />)
    await tablaCargada()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('/ultima con 500 → ErrorAlert con Reintentar que vuelve a pedir', async () => {
    let llamadas = 0
    server.use(
      http.get('*/api/v1/listas/ultima', () => {
        llamadas += 1
        return llamadas === 1
          ? HttpResponse.json(
              { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
              { status: 500 },
            )
          : undefined
      }),
    )
    const user = userEvent.setup()
    render(<ListaPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    await tablaCargada()
    expect(llamadas).toBe(2)
  })

  it('con lista generada → boton "¿Cómo funciona esta lista?" abre la ayuda y "Cerrar" devuelve el foco', async () => {
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    const ayuda = screen.getByRole('button', { name: '¿Cómo funciona esta lista?' })
    await user.click(ayuda)

    const dialogo = screen.getByRole('dialog', { name: '¿Cómo funciona esta lista?' })
    expect(within(dialogo).getByRole('heading', { name: 'Qué hace la lista' })).toBeInTheDocument()
    expect(within(dialogo).queryByRole('heading', { name: 'Casos frecuentes' })).toBeNull()
    expect(within(dialogo).queryByRole('heading', { name: 'Qué datos se muestran' })).toBeNull()
    await user.click(within(dialogo).getByRole('button', { name: 'Cerrar' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(ayuda).toHaveFocus()
  })

  it('sin listas → el boton de ayuda tambien esta y cierra con Escape', async () => {
    server.use(...escenariosLista.sinListas)
    const user = userEvent.setup()
    render(<ListaPage />)
    await screen.findByText(/Aún no se ha generado ninguna lista/)

    const ayuda = screen.getByRole('button', { name: '¿Cómo funciona esta lista?' })
    await user.click(ayuda)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(ayuda).toHaveFocus()
  })

  describe('gestion desde la fila (D5-FE-02, D5-FE-03)', () => {
    /** Celdas "Gestión" y "Campaña" de la fila con esa prioridad (tabla de prioritarios). */
    async function gestionDeLaFila(prioridad: number): Promise<string[]> {
      const fila = (await filasDe(PRIORITARIOS))[prioridad - 1] as HTMLElement
      return within(fila)
        .getAllByRole('cell')
        .slice(8, 10)
        .map((c) => c.textContent ?? '')
    }

    it('estado inicial de las filas: pendiente con campaña, cerrada sin campaña y sin gestion', async () => {
      render(<ListaPage />)

      expect(await gestionDeLaFila(1)).toEqual(['Pendiente', 'Ejemplo: Renovación anticipada'])
      expect(await gestionDeLaFila(2)).toEqual(['Cerrada', 'Sin campaña'])
      expect(await gestionDeLaFila(3)).toEqual(['Sin gestión', '—'])
      const tabla = await tablaCargada()
      expect(
        tabla.getByRole('button', { name: 'Registrar resultado prioridad 1' }),
      ).toBeInTheDocument()
      expect(tabla.getByRole('button', { name: 'Ver gestión prioridad 2' })).toBeInTheDocument()
      expect(tabla.getByRole('button', { name: 'Gestionar prioridad 3' })).toBeInTheDocument()
      expect(
        (await tablaCargada(OTROS)).getByRole('button', { name: 'Gestionar prioridad 26' }),
      ).toBeInTheDocument()
    })

    /** Abre "Registrar resultado prioridad N", responde Contactado No y Renovó `renovo`, y guarda. */
    async function registrarResultadoDeLaFila(
      user: ReturnType<typeof userEvent.setup>,
      prioridad: number,
      renovo: 'Sí' | 'No' | 'Pendiente',
    ) {
      await user.click(
        (await tablaCargada()).getByRole('button', {
          name: `Registrar resultado prioridad ${prioridad}`,
        }),
      )
      const dialogo = within(
        await screen.findByRole('dialog', { name: `Gestión de la prioridad ${prioridad}` }),
      )
      expect(
        await dialogo.findByRole('form', { name: 'Resultado del seguimiento' }),
      ).toBeInTheDocument()
      await user.click(
        within(dialogo.getByRole('group', { name: '¿Se contactó al socio?' })).getByRole('radio', {
          name: 'No',
        }),
      )
      await user.click(
        within(dialogo.getByRole('group', { name: '¿Renovó?' })).getByRole('radio', {
          name: renovo,
        }),
      )
      await user.click(dialogo.getByRole('button', { name: 'Guardar resultado' }))
      return dialogo
    }

    it('Gestionar → campaña → Crear gestión: la ventana se cierra, la lista se recarga y la fila queda "Pendiente"; luego Registrar resultado Renovó Sí → "Cerrada"', async () => {
      server.use(...simularGestiones())
      const recargas = { llamadas: 0 }
      const user = userEvent.setup()
      render(<ListaPage />)
      const boton = (await tablaCargada()).getByRole('button', { name: 'Gestionar prioridad 3' })

      await user.click(boton)
      const dialogo = within(
        await screen.findByRole('dialog', { name: 'Gestión de la prioridad 3' }),
      )
      const campania = await dialogo.findByRole('radio', { name: 'Ejemplo: Renovación anticipada' })
      expect(dialogo.getByRole('radio', { name: 'No asignar campaña' })).not.toBeChecked()
      // Vencimiento simulado 2026-10-03: sugerida = vencimiento + 25.
      expect(dialogo.getByLabelText('Fecha de seguimiento')).toHaveValue('2026-10-28')
      server.use(
        http.get(`${LISTAS_PATH}/:id`, () => {
          recargas.llamadas += 1
          return undefined
        }),
      )
      await user.click(campania)
      await user.click(dialogo.getByRole('button', { name: 'Crear gestión' }))

      // La ventana se cierra sola: nunca pasa a "Resultado del seguimiento".
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(
        screen.queryByRole('form', { name: 'Resultado del seguimiento' }),
      ).not.toBeInTheDocument()
      await waitFor(async () =>
        expect(await gestionDeLaFila(3)).toEqual(['Pendiente', 'Ejemplo: Renovación anticipada']),
      )
      expect(recargas.llamadas).toBe(1)
      expect(
        (await tablaCargada()).getByRole('button', { name: 'Registrar resultado prioridad 3' }),
      ).toBeInTheDocument()

      await registrarResultadoDeLaFila(user, 3, 'Sí')

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      await waitFor(async () => expect((await gestionDeLaFila(3))[0]).toBe('Cerrada'))
      expect(
        (await tablaCargada()).getByRole('button', { name: 'Ver gestión prioridad 3' }),
      ).toBeInTheDocument()
    })

    it('Registrar resultado con Renovó = No → la ventana se cierra y la fila pasa a "Cerrada"', async () => {
      server.use(...simularGestiones())
      const user = userEvent.setup()
      render(<ListaPage />)

      await registrarResultadoDeLaFila(user, 1, 'No')

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      await waitFor(async () => expect((await gestionDeLaFila(1))[0]).toBe('Cerrada'))
      expect(
        (await tablaCargada()).getByRole('button', { name: 'Ver gestión prioridad 1' }),
      ).toBeInTheDocument()
    })

    it('Registrar resultado con Renovó = Pendiente → la ventana se cierra, la lista se recarga y la fila sigue "Pendiente"', async () => {
      server.use(...simularGestiones())
      const recargas = { llamadas: 0 }
      server.use(
        http.get(`${LISTAS_PATH}/:id`, () => {
          recargas.llamadas += 1
          return undefined
        }),
      )
      const user = userEvent.setup()
      render(<ListaPage />)
      await tablaCargada()
      const antes = recargas.llamadas

      await registrarResultadoDeLaFila(user, 1, 'Pendiente')

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      await waitFor(() => expect(recargas.llamadas).toBe(antes + 1))
      expect((await gestionDeLaFila(1))[0]).toBe('Pendiente')
      expect(
        (await tablaCargada()).getByRole('button', { name: 'Registrar resultado prioridad 1' }),
      ).toBeInTheDocument()
    })

    it('error del servidor al guardar el resultado → la ventana sigue abierta con el mensaje', async () => {
      server.use(
        http.put('*/api/v1/gestiones/:id/resultado', () =>
          HttpResponse.json(
            { error: { code: 'domain_rule_violated', message: 'Fallo simulado al guardar.' } },
            { status: 422 },
          ),
        ),
      )
      const user = userEvent.setup()
      render(<ListaPage />)

      const dialogo = await registrarResultadoDeLaFila(user, 1, 'No')

      expect(await dialogo.findByRole('alert')).toHaveTextContent('Fallo simulado al guardar.')
      expect(screen.getByRole('dialog', { name: 'Gestión de la prioridad 1' })).toBeInTheDocument()
      expect(dialogo.getByRole('button', { name: 'Guardar resultado' })).toBeEnabled()
    })

    it('409 del servidor al crear → ErrorAlert con su mensaje y el formulario sigue abierto', async () => {
      server.use(escenariosGestion.duplicada)
      const user = userEvent.setup()
      render(<ListaPage />)
      await user.click(
        (await tablaCargada()).getByRole('button', { name: 'Gestionar prioridad 3' }),
      )
      const dialogo = within(await screen.findByRole('dialog'))

      await user.click(await dialogo.findByRole('radio', { name: 'No asignar campaña' }))
      await user.click(dialogo.getByRole('button', { name: 'Crear gestión' }))

      expect(await dialogo.findByRole('alert')).toHaveTextContent(MENSAJE_GESTION_DUPLICADA)
      expect(dialogo.getByRole('button', { name: 'Crear gestión' })).toBeEnabled()
    })

    it('Ver gestión de una cerrada con campaña → solo lectura, sin guardar', async () => {
      server.use(...simularGestiones())
      const user = userEvent.setup()
      render(<ListaPage />)
      await registrarResultadoDeLaFila(user, 1, 'No')
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())

      await user.click(
        await (await tablaCargada()).findByRole('button', { name: 'Ver gestión prioridad 1' }),
      )
      const dialogo = within(
        await screen.findByRole('dialog', { name: 'Gestión de la prioridad 1' }),
      )

      expect(await dialogo.findByText('Gestión cerrada: no se puede modificar.')).toBeInTheDocument()
      expect(dialogo.queryByText('No se le asignó campaña')).not.toBeInTheDocument()
      expect(dialogo.queryByRole('button', { name: 'Guardar resultado' })).not.toBeInTheDocument()
      const radios = dialogo.getAllByRole('radio')
      expect(radios.length).toBeGreaterThan(0)
      for (const radio of radios) expect(radio).toBeDisabled()
      await user.click(dialogo.getByRole('button', { name: 'Cerrar' }))
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('Ver gestión de una cerrada sin campaña → solo "No se le asignó campaña"; al cerrar, el foco vuelve a la fila', async () => {
      const user = userEvent.setup()
      render(<ListaPage />)
      const boton = (await tablaCargada()).getByRole('button', { name: 'Ver gestión prioridad 2' })

      await user.click(boton)
      const dialogo = within(
        await screen.findByRole('dialog', { name: 'Gestión de la prioridad 2' }),
      )

      expect(await dialogo.findByText('No se le asignó campaña')).toBeInTheDocument()
      expect(
        screen.queryByRole('form', { name: 'Resultado del seguimiento' }),
      ).not.toBeInTheDocument()
      expect(dialogo.queryAllByRole('radio')).toHaveLength(0)
      expect(dialogo.queryAllByRole('textbox')).toHaveLength(0)
      expect(dialogo.queryByRole('button', { name: 'Guardar resultado' })).not.toBeInTheDocument()
      expect(dialogo.getAllByRole('button').map((b) => b.textContent)).toEqual(['Cerrar'])

      await user.click(dialogo.getByRole('button', { name: 'Cerrar' }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(boton).toHaveFocus()
    })

    it('Gestionar → "No asignar campaña" → Crear gestión: la ventana se cierra y la fila queda "Cerrada", "Sin campaña" y solo "Ver gestión"', async () => {
      server.use(...simularGestiones())
      const cuerpos: unknown[] = []
      const recargas = { llamadas: 0 }
      server.use(
        http.post('*/api/v1/gestiones', async ({ request }) => {
          cuerpos.push(await request.clone().json())
          return undefined
        }),
      )
      const user = userEvent.setup()
      render(<ListaPage />)
      await user.click(
        (await tablaCargada()).getByRole('button', { name: 'Gestionar prioridad 3' }),
      )
      const dialogo = within(
        await screen.findByRole('dialog', { name: 'Gestión de la prioridad 3' }),
      )
      server.use(
        http.get(`${LISTAS_PATH}/:id`, () => {
          recargas.llamadas += 1
          return undefined
        }),
      )

      await user.click(await dialogo.findByRole('radio', { name: 'No asignar campaña' }))
      expect(dialogo.queryByLabelText('Fecha de seguimiento')).not.toBeInTheDocument()
      expect(dialogo.queryByLabelText('Responsable (opcional)')).not.toBeInTheDocument()
      await user.click(dialogo.getByRole('button', { name: 'Crear gestión' }))

      // La ventana se cierra sola: nunca pasa a "Registrar resultado".
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
      expect(
        screen.queryByRole('form', { name: 'Resultado del seguimiento' }),
      ).not.toBeInTheDocument()
      await waitFor(async () =>
        expect(await gestionDeLaFila(3)).toEqual(['Cerrada', 'Sin campaña']),
      )
      expect(recargas.llamadas).toBe(1)
      expect(cuerpos).toEqual([
        { prediccion_id: 1503, campania_id: null, fecha_seguimiento: null, responsable: null },
      ])
      const fila = (await filasDe(PRIORITARIOS))[2] as HTMLElement
      expect(
        within(fila)
          .getAllByRole('button')
          .map((b) => b.getAttribute('aria-label')),
      ).toEqual(['Ver gestión prioridad 3'])
      const tabla = await tablaCargada()
      expect(
        tabla.queryByRole('button', { name: 'Registrar resultado prioridad 3' }),
      ).not.toBeInTheDocument()
      expect(tabla.queryByRole('button', { name: 'Gestionar prioridad 3' })).not.toBeInTheDocument()

      // Al abrirla solo se lee que no se le asigno campaña; al cerrar, el foco vuelve a la fila.
      const ver = tabla.getByRole('button', { name: 'Ver gestión prioridad 3' })
      await user.click(ver)
      const consulta = within(
        await screen.findByRole('dialog', { name: 'Gestión de la prioridad 3' }),
      )
      expect(await consulta.findByText('No se le asignó campaña')).toBeInTheDocument()
      expect(consulta.queryAllByRole('radio')).toHaveLength(0)
      expect(consulta.queryByRole('button', { name: 'Guardar resultado' })).not.toBeInTheDocument()
      await user.click(consulta.getByRole('button', { name: 'Cerrar' }))

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(ver).toHaveFocus()
    })
  })

  it('arquitectura: la pagina no importa api/ ni core/http ni usa fetch', () => {
    expect(pageSource).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(pageSource).not.toMatch(/core\/http/)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
  })

  it('arquitectura: la tabla es presentacional y no convierte el score a numero', () => {
    expect(tablaSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(tablaSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
    expect(tablaSource).not.toMatch(/parseFloat|Number\(/)
  })
})
