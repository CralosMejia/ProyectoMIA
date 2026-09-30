import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import { escenariosLista } from '../api/lista-api.handlers'
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
    expect(screen.getByText('Socios por vencer en los próximos 30 días: 32')).toBeInTheDocument()
    expect(screen.getByText('Socios prioritarios a contactar: 25')).toBeInTheDocument()
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
      'Celular',
      'Plan',
      'Vence el',
      'Días para vencer',
      'Nivel de riesgo',
      'Motivos principales',
    ])

    const filas = tabla.getAllByRole('row').slice(1)
    const primera = within(filas[0] as HTMLElement)
    expect(primera.getByText('Ana Prueba')).toBeInTheDocument()
    expect(primera.getByText('0000000000')).toBeInTheDocument()
    expect(primera.getByText('0990000000')).toBeInTheDocument()
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
      expect(screen.getByText('Socios prioritarios a contactar: 10')).toBeInTheDocument(),
    )
    expect(await filasDe(PRIORITARIOS)).toHaveLength(10)
    expect(screen.getByText('Socios por vencer en los próximos 20 días: 32')).toBeInTheDocument()
    expect(cuerpos).toEqual([{ fecha_referencia: '2026-10-15', horizonte_dias: 20, top_k: 10 }])
  })

  it('sin tocar la fecha → envia la de hoy (nunca null)', async () => {
    const cuerpos = registrarPosts()
    const user = userEvent.setup()
    render(<ListaPage />)
    await tablaCargada()

    await user.click(botonGenerar())

    await waitFor(() => expect(cuerpos).toHaveLength(1))
    expect(cuerpos[0]).toEqual({ fecha_referencia: HOY, horizonte_dias: 30, top_k: 25 })
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
    ['dias 1 (minimo)', HOY, '1', '25', { fecha_referencia: HOY, horizonte_dias: 1, top_k: 25 }],
    ['dias 31 (maximo)', HOY, '31', '25', { fecha_referencia: HOY, horizonte_dias: 31, top_k: 25 }],
    ['prioritarios 1 (minimo)', HOY, '30', '1', { fecha_referencia: HOY, horizonte_dias: 30, top_k: 1 }],
    ['fecha futura', '2026-12-31', '30', '25', { fecha_referencia: '2026-12-31', horizonte_dias: 30, top_k: 25 }],
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
