import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import { useDescargarExcel } from '../hooks/useDescargarExcel'
import ListaPage from '../pages/ListaPage'
import { DescargarExcelButton } from './DescargarExcelButton'
import buttonSource from './DescargarExcelButton.tsx?raw'

const EXCEL_PATH = '*/api/v1/listas/:id/excel'

/** Conecta el boton presentacional con su hook, como lo hace la pagina. */
function BotonConectado({ listaId }: { listaId: number | null }) {
  const { descargando, error, descargar } = useDescargarExcel()
  return (
    <DescargarExcelButton
      listaId={listaId}
      descargando={descargando}
      error={error}
      onDescargar={(id) => descargar(id, '2026-09-28')}
    />
  )
}

/** Registra las rutas pedidas al endpoint del Excel (cae al handler por defecto). */
function registrarDescargas() {
  const rutas: string[] = []
  server.use(
    http.get(EXCEL_PATH, ({ request }) => {
      rutas.push(new URL(request.url).pathname)
      return undefined
    }),
  )
  return rutas
}

describe('DescargarExcelButton', () => {
  const createObjectURL = vi.fn((blob: Blob) => (blob.size > 0 ? 'blob:lista' : 'blob:vacio'))
  const revokeObjectURL = vi.fn()
  const click = vi.fn()

  beforeEach(() => {
    createObjectURL.mockClear()
    revokeObjectURL.mockClear()
    click.mockClear()
    // jsdom no implementa URL.createObjectURL ni la navegacion de un <a download>.
    vi.stubGlobal(
      'URL',
      class extends URL {
        static createObjectURL = createObjectURL
        static revokeObjectURL = revokeObjectURL
      },
    )
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('el clic llama a GET /api/v1/listas/{id}/excel con el id de la lista mostrada', async () => {
    const rutas = registrarDescargas()
    const user = userEvent.setup()
    render(<BotonConectado listaId={41} />)

    await user.click(screen.getByRole('button', { name: 'Descargar Excel' }))

    await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(rutas).toEqual(['/api/v1/listas/41/excel'])
  })

  it('crea la descarga con URL.createObjectURL y la libera despues', async () => {
    const user = userEvent.setup()
    render(<BotonConectado listaId={42} />)

    await user.click(screen.getByRole('button', { name: 'Descargar Excel' }))

    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:lista'))
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const enlace = click.mock.contexts[0] as HTMLAnchorElement
    expect(enlace.download).toBe('lista_42_2026-09-28.xlsx')
    expect(enlace.href).toBe('blob:lista')
    expect(enlace.isConnected).toBe(false)
  })

  it('mientras descarga, el boton queda deshabilitado (sin doble descarga)', async () => {
    let llamadas = 0
    let responder: () => void = () => {}
    server.use(
      http.get(EXCEL_PATH, async () => {
        llamadas += 1
        await new Promise<void>((resolve) => {
          responder = resolve
        })
        return undefined
      }),
    )
    const user = userEvent.setup()
    render(<BotonConectado listaId={42} />)
    const boton = screen.getByRole('button', { name: 'Descargar Excel' })

    await user.click(boton)
    expect(boton).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Descargando Excel')
    await user.dblClick(boton)

    responder()
    await waitFor(() => expect(boton).toBeEnabled())
    expect(llamadas).toBe(1)
  })

  it('un error muestra ErrorAlert con el mensaje del servidor', async () => {
    server.use(
      http.get(EXCEL_PATH, () =>
        HttpResponse.json(
          { error: { code: 'not_found', message: 'La lista no existe.' } },
          { status: 404 },
        ),
      ),
    )
    const user = userEvent.setup()
    render(<BotonConectado listaId={42} />)

    await user.click(screen.getByRole('button', { name: 'Descargar Excel' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('La lista no existe.')
    expect(createObjectURL).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Descargar Excel' })).toBeEnabled()
  })

  it('sin lista, el boton no aparece', () => {
    render(<BotonConectado listaId={null} />)

    expect(screen.queryByRole('button', { name: 'Descargar Excel' })).not.toBeInTheDocument()
  })

  it('la pagina monta el boton y descarga la lista mostrada', async () => {
    const rutas = registrarDescargas()
    const user = userEvent.setup()
    render(<ListaPage />)

    await user.click(await screen.findByRole('button', { name: 'Descargar Excel' }))

    await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(rutas).toEqual(['/api/v1/listas/42/excel'])
  })

  it('arquitectura: el boton es presentacional (sin hooks ni api)', () => {
    expect(buttonSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(buttonSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
  })
})
