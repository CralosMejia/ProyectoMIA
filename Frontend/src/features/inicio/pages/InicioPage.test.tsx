import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { act } from 'react'
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import InicioPage from './InicioPage'
import pageSource from './InicioPage.tsx?raw'
import panelSource from '../components/EstadoSistemaPanel.tsx?raw'

const ESTADO_PATH = '*/api/v1/sistema/estado'
const ALERTAS_PATH = '*/api/v1/alertas'

/** Inicio usa enlaces del router (contadores y aviso de datos del mes): se monta dentro de uno. */
function renderInicio() {
  return render(<InicioPage />, { wrapper: MemoryRouter })
}

function estado(body: Record<string, unknown>) {
  return {
    estado: 'LISTO',
    migracion_historica: 'COMPLETADA',
    modelo_vigente: {
      version: 'v1',
      fecha_entrenamiento: '2026-09-28T14:30:00Z',
      ciclos_entrenamiento: 1843,
    },
    ultima_carga_en: '2026-09-27T16:05:00Z',
    proxima_fecha_reentrenamiento: '2026-10-28',
    ...body,
  }
}

function responderEstado(body: Record<string, unknown>) {
  server.use(http.get(ESTADO_PATH, () => HttpResponse.json(estado(body))))
}

function fechaEsEc(iso: string): string {
  return new Intl.DateTimeFormat('es-EC', { dateStyle: 'long' }).format(new Date(iso))
}

function esEc(iso: string): string {
  return new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeStyle: 'short' }).format(
    new Date(iso),
  )
}

describe('InicioPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('mantiene el titulo "Inicio" como region etiquetada', async () => {
    renderInicio()

    expect(screen.getByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Inicio' })).toBeInTheDocument()
    await screen.findByText('Sistema listo')
  })

  it('mientras carga → LoadingIndicator (role="status")', async () => {
    renderInicio()

    expect(screen.getByRole('status')).toHaveTextContent('Consultando estado del sistema')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    await screen.findByText('Sistema listo')
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('Reintentar tras 500 → vuelve a mostrar el cargando y luego el estado', async () => {
    let llamadas = 0
    server.use(
      http.get(ESTADO_PATH, () => {
        llamadas += 1
        return llamadas === 1
          ? HttpResponse.json(
              { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
              { status: 500 },
            )
          : HttpResponse.json(estado({}))
      }),
    )
    const user = userEvent.setup()
    renderInicio()

    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  it('INICIALIZANDO → "Inicializando datos historicos" en role="status"', async () => {
    responderEstado({ estado: 'INICIALIZANDO', migracion_historica: 'EN_CURSO', modelo_vigente: null })

    renderInicio()

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Inicializando datos históricos'),
    )
  })

  it('FALTAN_DATOS_HISTORICOS → aviso con indicacion de revisar la carpeta, sin rutas', async () => {
    responderEstado({
      estado: 'FALTAN_DATOS_HISTORICOS',
      migracion_historica: 'PENDIENTE',
      modelo_vigente: null,
      ultima_carga_en: null,
    })

    renderInicio()

    const aviso = await screen.findByText(/Faltan los datos históricos/)
    const contenedor = aviso.closest('[role="alert"]')
    expect(contenedor).not.toBeNull()
    expect(contenedor).toHaveTextContent(/carpeta configurada/i)
    expect(contenedor?.textContent ?? '').not.toMatch(/[/\\]|\.xlsx/)
  })

  it('LISTO → "Sistema listo", "Modelo de predicción: activo desde <fecha>" y ultima carga en es-EC', async () => {
    renderInicio()

    expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
    expect(screen.getByText('Modelo de predicción')).toBeInTheDocument()
    expect(
      screen.getByText(`Activo desde ${fechaEsEc('2026-09-28T14:30:00Z')}`),
    ).toBeInTheDocument()
    expect(screen.getByText(esEc('2026-09-27T16:05:00Z'))).toBeInTheDocument()
    const texto = document.body.textContent ?? ''
    expect(texto).not.toMatch(/versi[oó]n del modelo|fecha de entrenamiento/i)
    expect(texto).not.toMatch(/\bv1\b/)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('LISTO sin modelo vigente → "El modelo de predicción aún no está disponible"', async () => {
    responderEstado({ modelo_vigente: null })

    renderInicio()

    expect(
      await screen.findByText('El modelo de predicción aún no está disponible'),
    ).toBeInTheDocument()
    expect(screen.getByText(esEc('2026-09-27T16:05:00Z'))).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/sin modelo vigente|versi[oó]n del modelo/i)
  })

  it('501 → ErrorAlert con el mensaje del servidor y "Reintentar" que vuelve a pedir', async () => {
    let llamadas = 0
    server.use(
      http.get(ESTADO_PATH, () => {
        llamadas += 1
        if (llamadas === 1) {
          return HttpResponse.json(
            { error: { code: 'not_implemented', message: 'Esta funcion aun no esta disponible.' } },
            { status: 501 },
          )
        }
        return HttpResponse.json(estado({}))
      }),
    )
    const user = userEvent.setup()

    renderInicio()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Esta funcion aun no esta disponible.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  it('500 → ErrorAlert sin exponer el detalle crudo', async () => {
    server.use(
      http.get(ESTADO_PATH, () =>
        HttpResponse.json(
          { error: { code: 'internal_error', message: 'Error interno del servidor.' }, detail: 'traza' },
          { status: 500 },
        ),
      ),
    )

    renderInicio()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Error interno del servidor.')
    expect(alerta).not.toHaveTextContent('traza')
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  describe('ayuda "¿Cómo funciona el inicio?" (R-012)', () => {
    const AYUDA = '¿Cómo funciona el inicio?'

    it('LISTO → el boton esta junto al titulo y abre su ayuda; al cerrar vuelve el foco', async () => {
      const user = userEvent.setup()
      renderInicio()
      await screen.findByText('Sistema listo')

      const boton = screen.getByRole('button', { name: AYUDA })
      await user.click(boton)
      expect(screen.getByRole('dialog', { name: AYUDA })).toHaveTextContent(
        'Seguimientos pendientes',
      )
      await user.keyboard('{Escape}')

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(boton).toHaveFocus()
    })

    it('con error del estado el boton sigue visible', async () => {
      server.use(
        http.get(ESTADO_PATH, () =>
          HttpResponse.json(
            { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
            { status: 500 },
          ),
        ),
      )
      renderInicio()

      await screen.findByRole('alert')
      expect(screen.getByRole('button', { name: AYUDA })).toBeInTheDocument()
    })

    it('mientras carga y con el sistema INICIALIZANDO el boton esta visible', async () => {
      responderEstado({ estado: 'INICIALIZANDO', migracion_historica: 'EN_CURSO' })
      renderInicio()

      expect(screen.getByRole('button', { name: AYUDA })).toBeInTheDocument()
      await screen.findByText(/Inicializando datos/i)
      expect(screen.getByRole('button', { name: AYUDA })).toBeInTheDocument()
    })
  })

  it('al desmontar antes de responder → aborta la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get(ESTADO_PATH, ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )

    const { unmount } = renderInicio()
    await waitFor(() => expect(senal).not.toBeNull())
    unmount()

    await waitFor(() => expect((senal as AbortSignal | null)?.aborted).toBe(true))
  })

  describe('consulta periodica mientras INICIALIZANDO', () => {
    afterEach(() => {
      vi.useRealTimers()
    })

    /** Responde en orden los estados dados (el ultimo se repite) y cuenta las llamadas. */
    function secuencia(estados: string[]) {
      const registro = { llamadas: 0, senales: [] as AbortSignal[] }
      server.use(
        http.get(ESTADO_PATH, ({ request }) => {
          registro.senales.push(request.signal)
          const actual = estados[Math.min(registro.llamadas, estados.length - 1)]
          registro.llamadas += 1
          return HttpResponse.json(
            actual === 'LISTO'
              ? estado({})
              : estado({ estado: actual, migracion_historica: 'EN_CURSO', modelo_vigente: null }),
          )
        }),
      )
      return registro
    }

    async function avanzar(ms: number) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(ms)
      })
    }

    it('vuelve a pedir cada 5 s hasta LISTO y entonces se detiene', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const registro = secuencia(['INICIALIZANDO', 'INICIALIZANDO', 'LISTO'])

      renderInicio()
      await screen.findByText(/Inicializando datos históricos/)
      expect(registro.llamadas).toBe(1)

      await avanzar(4900)
      expect(registro.llamadas).toBe(1)
      await avanzar(100)
      await waitFor(() => expect(registro.llamadas).toBe(2))
      expect(screen.getByRole('status')).toHaveTextContent('Inicializando datos históricos')

      await avanzar(5000)
      expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
      expect(registro.llamadas).toBe(3)

      await avanzar(20000)
      expect(registro.llamadas).toBe(3)
    })

    it('se detiene con FALTAN_DATOS_HISTORICOS', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const registro = secuencia(['INICIALIZANDO', 'FALTAN_DATOS_HISTORICOS'])

      renderInicio()
      await screen.findByText(/Inicializando datos históricos/)

      await avanzar(5000)
      expect(await screen.findByText(/Faltan los datos históricos/)).toBeInTheDocument()
      expect(registro.llamadas).toBe(2)

      await avanzar(20000)
      expect(registro.llamadas).toBe(2)
    })

    it('un error durante la consulta periodica muestra ErrorAlert y se detiene', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      let llamadas = 0
      server.use(
        http.get(ESTADO_PATH, () => {
          llamadas += 1
          return llamadas === 1
            ? HttpResponse.json(
                estado({ estado: 'INICIALIZANDO', migracion_historica: 'EN_CURSO', modelo_vigente: null }),
              )
            : HttpResponse.json(
                { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
                { status: 500 },
              )
        }),
      )

      renderInicio()
      await screen.findByText(/Inicializando datos históricos/)

      await avanzar(5000)
      expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
      expect(llamadas).toBe(2)

      await avanzar(20000)
      expect(llamadas).toBe(2)
    })

    it('con LISTO desde el principio no programa nuevas consultas', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const registro = secuencia(['LISTO'])

      renderInicio()
      await screen.findByText('Sistema listo')

      await avanzar(20000)
      expect(registro.llamadas).toBe(1)
    })

    it('al desmontar deja de consultar (clearTimeout y abort)', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const registro = secuencia(['INICIALIZANDO'])

      const { unmount } = renderInicio()
      await screen.findByText(/Inicializando datos históricos/)
      expect(vi.getTimerCount()).toBeGreaterThan(0)

      unmount()

      expect(vi.getTimerCount()).toBe(0)
      await avanzar(20000)
      expect(registro.llamadas).toBe(1)
      expect(registro.senales.every((s) => s.aborted)).toBe(true)
    })
  })

  describe('seguimientos pendientes y datos del mes (CU-09)', () => {
    function renderConRutas() {
      const router = createMemoryRouter(
        [
          { path: '/', element: <InicioPage /> },
          { path: '/seguimiento', element: <p>pagina seguimiento</p> },
          { path: '/carga', element: <p>pagina carga</p> },
        ],
        { initialEntries: ['/'] },
      )
      render(<RouterProvider router={router} />)
      return router
    }

    function responderAlertas(body: Record<string, number>) {
      server.use(http.get(ALERTAS_PATH, () => HttpResponse.json(body)))
    }

    it('muestra los tres contadores con sus numeros y enlaces a cada grupo', async () => {
      responderAlertas({ vencidas: 2, hoy: 1, proximos_7_dias: 3 })

      renderInicio()

      const vencidos = await screen.findByRole('link', { name: 'Vencidos 2' })
      expect(vencidos).toHaveAttribute('href', '/seguimiento?filtro=vencidas')
      expect(screen.getByRole('link', { name: 'Para hoy 1' })).toHaveAttribute(
        'href',
        '/seguimiento?filtro=hoy',
      )
      expect(screen.getByRole('link', { name: 'Próximos 7 días 3' })).toHaveAttribute(
        'href',
        '/seguimiento?filtro=proximas',
      )
    })

    it('pulsar "Para hoy" navega a /seguimiento?filtro=hoy', async () => {
      responderAlertas({ vencidas: 2, hoy: 1, proximos_7_dias: 3 })
      const user = userEvent.setup()
      const router = renderConRutas()

      await user.click(await screen.findByRole('link', { name: /Para hoy/ }))

      expect(router.state.location.pathname).toBe('/seguimiento')
      expect(router.state.location.search).toBe('?filtro=hoy')
      expect(await screen.findByText('pagina seguimiento')).toBeInTheDocument()
    })

    it('datosMesCargados false → aviso de datos del mes con enlace a Carga', async () => {
      responderEstado({ datos_mes_cargados: false })
      const user = userEvent.setup()
      const router = renderConRutas()

      expect(
        await screen.findByText('Aún no se han cargado los datos de este mes.'),
      ).toBeInTheDocument()
      await user.click(screen.getByRole('link', { name: 'Ir a Carga' }))
      expect(router.state.location.pathname).toBe('/carga')
    })

    it.each([true, null])('datosMesCargados %s → sin aviso de datos del mes', async (valor) => {
      responderEstado({ datos_mes_cargados: valor })

      renderInicio()

      await screen.findByRole('link', { name: /Para hoy/ })
      expect(screen.queryByText(/Aún no se han cargado los datos/)).not.toBeInTheDocument()
    })

    it('error de alertas → mensaje sin romper el resto de Inicio; Reintentar vuelve a pedir', async () => {
      let llamadas = 0
      server.use(
        http.get(ALERTAS_PATH, () => {
          llamadas += 1
          return llamadas === 1
            ? HttpResponse.json(
                { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
                { status: 500 },
              )
            : HttpResponse.json({ vencidas: 0, hoy: 4, proximos_7_dias: 0 })
        }),
      )
      const user = userEvent.setup()

      renderInicio()

      expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
      expect(screen.getByText('Sistema listo')).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Reintentar' }))
      expect(await screen.findByRole('link', { name: 'Para hoy 4' })).toBeInTheDocument()
      expect(llamadas).toBe(2)
    })

    it('mientras el sistema se inicializa no pide las alertas', async () => {
      let llamadas = 0
      server.use(
        http.get(ALERTAS_PATH, () => {
          llamadas += 1
          return HttpResponse.json({ vencidas: 0, hoy: 0, proximos_7_dias: 0 })
        }),
      )
      responderEstado({ estado: 'FALTAN_DATOS_HISTORICOS', migracion_historica: 'PENDIENTE' })

      renderInicio()

      await screen.findByText(/Faltan los datos históricos/)
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
      expect(llamadas).toBe(0)
    })
  })

  it('arquitectura: la pagina no importa api/ ni core/http ni usa fetch', () => {
    expect(pageSource).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(pageSource).not.toMatch(/core\/http/)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
  })

  it('arquitectura: el panel es presentacional (sin hooks ni api)', () => {
    expect(panelSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(panelSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
  })
})
