import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { server } from '../../../mocks/server'
import InicioPage from './InicioPage'
import pageSource from './InicioPage.tsx?raw'
import panelSource from '../components/EstadoSistemaPanel.tsx?raw'

const ESTADO_PATH = '*/api/v1/sistema/estado'

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
    render(<InicioPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Inicio' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Inicio' })).toBeInTheDocument()
    await screen.findByText('Sistema listo')
  })

  it('mientras carga → LoadingIndicator (role="status")', async () => {
    render(<InicioPage />)

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
    render(<InicioPage />)

    await user.click(await screen.findByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  it('INICIALIZANDO → "Inicializando datos historicos" en role="status"', async () => {
    responderEstado({ estado: 'INICIALIZANDO', migracion_historica: 'EN_CURSO', modelo_vigente: null })

    render(<InicioPage />)

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

    render(<InicioPage />)

    const aviso = await screen.findByText(/Faltan los datos históricos/)
    const contenedor = aviso.closest('[role="alert"]')
    expect(contenedor).not.toBeNull()
    expect(contenedor).toHaveTextContent(/carpeta configurada/i)
    expect(contenedor?.textContent ?? '').not.toMatch(/[/\\]|\.xlsx/)
  })

  it('LISTO → "Sistema listo", version del modelo y fechas en es-EC', async () => {
    render(<InicioPage />)

    expect(await screen.findByText('Sistema listo')).toBeInTheDocument()
    expect(screen.getByText('v1')).toBeInTheDocument()
    expect(screen.getByText(esEc('2026-09-28T14:30:00Z'))).toBeInTheDocument()
    expect(screen.getByText(esEc('2026-09-27T16:05:00Z'))).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('LISTO sin modelo vigente → "Sin modelo vigente"', async () => {
    responderEstado({ modelo_vigente: null })

    render(<InicioPage />)

    expect(await screen.findByText('Sin modelo vigente')).toBeInTheDocument()
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

    render(<InicioPage />)

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

    render(<InicioPage />)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Error interno del servidor.')
    expect(alerta).not.toHaveTextContent('traza')
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('al desmontar antes de responder → aborta la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get(ESTADO_PATH, ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )

    const { unmount } = render(<InicioPage />)
    await waitFor(() => expect(senal).not.toBeNull())
    unmount()

    await waitFor(() => expect((senal as AbortSignal | null)?.aborted).toBe(true))
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
