import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { server } from '../../../mocks/server'
import { simularSeguimiento } from '../api/lista-api.handlers'
import SeguimientoPage from './SeguimientoPage'
import pageSource from './SeguimientoPage.tsx?raw'

const GESTIONES_PATH = '*/api/v1/gestiones'

function renderEn(ruta: string) {
  const router = createMemoryRouter(
    [
      { path: '/seguimiento', element: <SeguimientoPage /> },
      { path: '/', element: <p>pagina inicio</p> },
    ],
    { initialEntries: [ruta] },
  )
  render(<RouterProvider router={router} />)
  return router
}

/** Cuenta las peticiones a `GET /gestiones?filtro=` sin responderlas (cae al handler siguiente). */
function contarConsultas() {
  const registro = { filtros: [] as (string | null)[] }
  server.use(
    http.get(GESTIONES_PATH, ({ request }) => {
      registro.filtros.push(new URL(request.url).searchParams.get('filtro'))
      return undefined
    }),
  )
  return registro
}

async function tabla() {
  return within(await screen.findByRole('table', { name: 'Gestiones pendientes' }))
}

function nombresDeSocios(t: ReturnType<typeof within>): string[] {
  return t
    .getAllByRole('row')
    .slice(1)
    .map((fila: HTMLElement) => within(fila).getAllByRole('cell')[0]?.textContent ?? '')
}

describe('SeguimientoPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('filtro=vencidas → titulo "Seguimientos vencidos" y las filas del mock', async () => {
    const registro = contarConsultas()

    renderEn('/seguimiento?filtro=vencidas')

    expect(
      screen.getByRole('heading', { level: 1, name: 'Seguimientos vencidos' }),
    ).toBeInTheDocument()
    const t = await tabla()
    expect(nombresDeSocios(t)).toHaveLength(2)
    expect(t.getAllByRole('button', { name: /^Abrir gestión / })).toHaveLength(2)
    for (const encabezado of [
      'Socio',
      'Plan',
      'Vence',
      'Fecha de seguimiento',
      'Campaña',
      'Responsable',
    ]) {
      expect(t.getByRole('columnheader', { name: encabezado })).toBeInTheDocument()
    }
    expect(t.getByText('25 sep 2026')).toBeInTheDocument()
    expect(registro.filtros).toEqual(['vencidas'])
  })

  it.each([
    ['hoy', 'Seguimientos para hoy'],
    ['proximas', 'Seguimientos de los próximos 7 días'],
  ])('filtro=%s → titulo "%s"', async (filtro, titulo) => {
    renderEn(`/seguimiento?filtro=${filtro}`)

    expect(screen.getByRole('heading', { level: 1, name: titulo })).toBeInTheDocument()
    await tabla()
  })

  it.each(['/seguimiento', '/seguimiento?filtro=otro', '/seguimiento?filtro=HOY'])(
    '%s → no llama a la API, "Grupo de seguimiento no válido" y enlace a Inicio',
    async (ruta) => {
      const registro = contarConsultas()
      const user = userEvent.setup()
      const router = renderEn(ruta)

      expect(
        screen.getByRole('heading', { level: 1, name: 'Grupo de seguimiento no válido' }),
      ).toBeInTheDocument()
      await user.click(screen.getByRole('link', { name: 'Volver a Inicio' }))
      expect(router.state.location.pathname).toBe('/')
      expect(registro.filtros).toEqual([])
    },
  )

  it('lista vacia → "No hay gestiones en este grupo"', async () => {
    server.use(http.get(GESTIONES_PATH, () => HttpResponse.json([])))

    renderEn('/seguimiento?filtro=hoy')

    expect(await screen.findByText('No hay gestiones en este grupo')).toBeInTheDocument()
  })

  it('error del servidor → ErrorAlert con su mensaje y Reintentar vuelve a pedir', async () => {
    let llamadas = 0
    server.use(
      http.get(GESTIONES_PATH, () => {
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

    renderEn('/seguimiento?filtro=hoy')

    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    await tabla()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  it('"Abrir gestión" abre la ventana en "Registrar resultado"', async () => {
    server.use(...simularSeguimiento())
    const user = userEvent.setup()
    renderEn('/seguimiento?filtro=hoy')
    const t = await tabla()
    const socio = nombresDeSocios(t)[0] ?? ''

    await user.click(t.getByRole('button', { name: `Abrir gestión ${socio}` }))

    const dialogo = within(await screen.findByRole('dialog', { name: `Gestión de ${socio}` }))
    expect(
      await dialogo.findByRole('form', { name: 'Resultado del seguimiento' }),
    ).toBeInTheDocument()
    expect(dialogo.getByRole('button', { name: 'Guardar resultado' })).toBeInTheDocument()
    expect(dialogo.queryByRole('button', { name: 'Crear gestión' })).not.toBeInTheDocument()
  })

  it('guardar "¿Renovó? Sí" → la ventana se cierra, la lista se recarga y la fila desaparece', async () => {
    server.use(...simularSeguimiento())
    const registro = contarConsultas()
    const user = userEvent.setup()
    renderEn('/seguimiento?filtro=hoy')
    const t = await tabla()
    const antes = nombresDeSocios(t)
    expect(antes).toHaveLength(3)
    const boton = t.getAllByRole('button', { name: /^Abrir gestión / })[0]
    if (boton === undefined) throw new Error('sin filas')

    await user.click(boton)
    const dialogo = within(await screen.findByRole('dialog'))
    const contactado = within(await dialogo.findByRole('group', { name: '¿Se contactó al socio?' }))
    await user.click(contactado.getByRole('radio', { name: 'No' }))
    await user.click(
      within(dialogo.getByRole('group', { name: '¿Renovó?' })).getByRole('radio', { name: 'Sí' }),
    )
    await user.click(dialogo.getByRole('button', { name: 'Guardar resultado' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(async () => expect(nombresDeSocios(await tabla())).toHaveLength(2))
    expect(nombresDeSocios(await tabla())).toEqual(antes.slice(1))
    expect(registro.filtros).toEqual(['hoy', 'hoy'])
  })

  /** Abre la primera fila y responde Contactado No y Renovó `renovo` (sin guardar). */
  async function responderPrimeraFila(
    user: ReturnType<typeof userEvent.setup>,
    renovo: 'Sí' | 'No' | 'Pendiente',
  ) {
    const boton = (await tabla()).getAllByRole('button', { name: /^Abrir gestión / })[0]
    if (boton === undefined) throw new Error('sin filas')
    await user.click(boton)
    const dialogo = within(await screen.findByRole('dialog'))
    const contactado = within(await dialogo.findByRole('group', { name: '¿Se contactó al socio?' }))
    await user.click(contactado.getByRole('radio', { name: 'No' }))
    await user.click(
      within(dialogo.getByRole('group', { name: '¿Renovó?' })).getByRole('radio', { name: renovo }),
    )
    return dialogo
  }

  it('guardar "¿Renovó? Pendiente" con nueva fecha → la ventana se cierra y la lista se recarga', async () => {
    server.use(...simularSeguimiento())
    const registro = contarConsultas()
    const cuerpos: unknown[] = []
    server.use(
      http.put('*/api/v1/gestiones/:id/resultado', async ({ request }) => {
        cuerpos.push(await request.clone().json())
        return undefined
      }),
    )
    const user = userEvent.setup()
    renderEn('/seguimiento?filtro=hoy')
    await tabla()

    const dialogo = await responderPrimeraFila(user, 'Pendiente')
    const fecha = dialogo.getByLabelText('Fecha de seguimiento')
    const nueva = fecha.getAttribute('max') ?? ''
    expect(nueva).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    await user.clear(fecha)
    await user.type(fecha, nueva)
    await user.click(dialogo.getByRole('button', { name: 'Guardar resultado' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(registro.filtros).toEqual(['hoy', 'hoy']))
    expect(cuerpos).toHaveLength(1)
    expect(cuerpos[0]).toMatchObject({ renovo_declarado: 'PENDIENTE', fecha_seguimiento: nueva })
    await tabla()
  })

  it('error del servidor al guardar → la ventana sigue abierta con el mensaje', async () => {
    server.use(...simularSeguimiento())
    // Despues: los `server.use` posteriores tienen prioridad sobre la simulacion.
    server.use(
      http.put('*/api/v1/gestiones/:id/resultado', () =>
        HttpResponse.json(
          { error: { code: 'domain_rule_violated', message: 'Fallo simulado al guardar.' } },
          { status: 422 },
        ),
      ),
    )
    const user = userEvent.setup()
    renderEn('/seguimiento?filtro=hoy')
    await tabla()

    const dialogo = await responderPrimeraFila(user, 'Sí')
    await user.click(dialogo.getByRole('button', { name: 'Guardar resultado' }))

    expect(await dialogo.findByRole('alert')).toHaveTextContent('Fallo simulado al guardar.')
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(dialogo.getByRole('button', { name: 'Guardar resultado' })).toBeEnabled()
  })

  it('al desmontar antes de responder → aborta la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get(GESTIONES_PATH, ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )

    renderEn('/seguimiento?filtro=hoy')
    expect(screen.getByRole('status')).toHaveTextContent('Cargando seguimientos')
    await waitFor(() => expect(senal).not.toBeNull())
    cleanup()

    await waitFor(() => expect((senal as AbortSignal | null)?.aborted).toBe(true))
  })

  it('arquitectura: la pagina no importa api/ ni core/http ni usa fetch', () => {
    expect(pageSource).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(pageSource).not.toMatch(/core\/http/)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
  })
})
