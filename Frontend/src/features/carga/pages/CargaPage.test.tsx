/// <reference types="node" />
import { File as NodeFile } from 'node:buffer'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import CargaPage from './CargaPage'
import pageSource from './CargaPage.tsx?raw'
import vistaPreviaSource from '../components/VistaPreviaCarga.tsx?raw'

const VISTA_PREVIA_PATH = '*/api/v1/cargas/vista-previa'
const CARGAS_PATH = '*/api/v1/cargas'

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/**
 * Puente multipart: jsdom sustituye `FormData`/`File` por los suyos y el `fetch` nativo de Node
 * no sabe serializarlos (ver carga-api.test.ts). En esta prueba se usan las clases nativas de
 * Node (`File` de `node:buffer` y el `FormData` que produce el `Response` nativo), sin tocar el
 * codigo de produccion.
 */
beforeAll(async () => {
  const form = await new Response('a=1', {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  }).formData()
  vi.stubGlobal('FormData', form.constructor)
})

afterAll(() => {
  vi.unstubAllGlobals()
})

function archivo(contenido: string, nombre: string, type: string): File {
  return new NodeFile([contenido], nombre, { type }) as unknown as File
}

function xlsx(nombre: string): File {
  return archivo('contenido', nombre, XLSX_MIME)
}

function fecha(iso: string): string {
  return new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeZone: 'UTC' }).format(
    new Date(`${iso}T00:00:00Z`),
  )
}

function errorBody(code: string, message: string) {
  return { error: { code, message } }
}

/** `applyAccept: false` simula a un usuario que elige "Todos los archivos" en el dialogo. */
function setup() {
  return userEvent.setup({ applyAccept: false })
}

function input(): HTMLInputElement {
  return screen.getByLabelText(/archivo de la plantilla/i)
}

function botonConfirmar(): HTMLButtonElement {
  return screen.getByRole('button', { name: 'Confirmar' })
}

describe('CargaPage', () => {
  afterEach(() => {
    cleanup()
  })

  it('mantiene el titulo y ofrece un input .xlsx con etiqueta accesible', () => {
    render(<CargaPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Carga de datos' })).toBeInTheDocument()
    const campo = input()
    expect(campo).toHaveAttribute('type', 'file')
    expect(campo).toHaveAttribute('accept', '.xlsx')
  })

  it('archivo no .xlsx → mensaje local sin llamar a la API', async () => {
    let llamadas = 0
    server.use(
      http.post(VISTA_PREVIA_PATH, () => {
        llamadas += 1
        return HttpResponse.json({}, { status: 500 })
      }),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), archivo('a,b', 'datos.csv', 'text/csv'))

    expect(await screen.findByText(/archivo \.xlsx/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
    expect(llamadas).toBe(0)
  })

  it('valida.xlsx → conteos, rango de vencimientos y "Confirmar" habilitado', async () => {
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('valida.xlsx'))

    const resumen = await screen.findByRole('region', { name: 'Vista previa' })
    const conteo = (termino: string) =>
      within(resumen).getByText(termino).nextElementSibling?.textContent
    expect(conteo('Filas leídas')).toBe('120')
    expect(conteo('Filas válidas')).toBe('118')
    expect(conteo('Filas con error')).toBe('0')
    expect(conteo('Filas duplicadas')).toBe('2')
    expect(conteo('Rango de vencimientos')).toBe(
      `${fecha('2026-09-01')} – ${fecha('2026-11-30')}`,
    )
    expect(within(resumen).queryByRole('table')).not.toBeInTheDocument()
    expect(botonConfirmar()).toBeEnabled()
  })

  it('con-errores.xlsx → tabla con una fila por error y "Confirmar" deshabilitado', async () => {
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('con-errores.xlsx'))

    const tabla = await screen.findByRole('table')
    const encabezados = within(tabla)
      .getAllByRole('columnheader')
      .map((th) => th.textContent)
    expect(encabezados).toEqual(['Fila', 'Columna', 'Motivo'])
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas).toHaveLength(2)
    expect(filas[0]).toHaveTextContent('7')
    expect(filas[0]).toHaveTextContent('FECHA_VENCIMIENTO')
    expect(filas[0]).toHaveTextContent('La fecha no tiene un formato valido.')
    expect(filas[1]).toHaveTextContent('El plan no pertenece al catalogo.')
    expect(botonConfirmar()).toBeDisabled()
  })

  it('puedeConfirmar false sin errores (todo duplicado) → "Confirmar" deshabilitado', async () => {
    server.use(
      http.post(VISTA_PREVIA_PATH, () =>
        HttpResponse.json({
          filas_leidas: 3,
          filas_validas: 0,
          filas_con_error: 0,
          filas_duplicadas: 3,
          vencimiento_desde: null,
          vencimiento_hasta: null,
          errores: [],
          puede_confirmar: false,
        }),
      ),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('duplicada.xlsx'))

    await screen.findByRole('region', { name: 'Vista previa' })
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(botonConfirmar()).toBeDisabled()
  })

  it('error del servidor en la vista previa → ErrorAlert con su mensaje', async () => {
    server.use(
      http.post(VISTA_PREVIA_PATH, () =>
        HttpResponse.json(errorBody('validation_error', 'El archivo no tiene la hoja Registros.'), {
          status: 400,
        }),
      ),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('otra.xlsx'))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El archivo no tiene la hoja Registros.',
    )
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
  })

  it('Confirmar → POST /api/v1/cargas y resumen de la carga', async () => {
    let recibido: string | null = null
    server.use(
      http.post(CARGAS_PATH, async ({ request }) => {
        const archivo = (await request.formData()).get('archivo')
        recibido = archivo !== null && typeof archivo !== 'string' ? archivo.name : null
        return HttpResponse.json(
          {
            id: 12,
            fecha_carga: '2026-09-28T16:05:00Z',
            nombre_archivo: 'valida.xlsx',
            filas_leidas: 120,
            filas_guardadas: 118,
            filas_duplicadas: 2,
            socios_enlazados: 95,
            avisos_enlace: ['Nombre repetido en el historico: se creo un socio nuevo (fila 9).'],
          },
          { status: 201 },
        )
      }),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('valida.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Confirmar' }))

    const resumen = await screen.findByRole('region', { name: 'Carga guardada' })
    const valor = (termino: string) =>
      within(resumen).getByText(termino).nextElementSibling?.textContent
    expect(valor('Filas guardadas')).toBe('118')
    expect(valor('Filas duplicadas')).toBe('2')
    expect(
      within(resumen).getByText(
        'Nombre repetido en el historico: se creo un socio nuevo (fila 9).',
      ),
    ).toBeInTheDocument()
    expect(recibido).toBe('valida.xlsx')
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
  })

  it.each([
    [422, 'validation_error', 'El archivo tiene filas con error.'],
    [409, 'conflict', 'La migracion historica aun no termina.'],
    [400, 'validation_error', 'El archivo supera las 500 filas.'],
  ])('Confirmar con %i → ErrorAlert con el mensaje del servidor', async (status, code, message) => {
    server.use(
      http.post(CARGAS_PATH, () => HttpResponse.json(errorBody(code, message), { status })),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('valida.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Confirmar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(screen.queryByRole('region', { name: 'Carga guardada' })).not.toBeInTheDocument()
  })

  it('mientras envia → "Confirmar" deshabilitado y sin doble envio', async () => {
    let llamadas = 0
    let liberar: () => void = () => {}
    const pendiente = new Promise<void>((resolve) => {
      liberar = resolve
    })
    server.use(
      http.post(CARGAS_PATH, async () => {
        llamadas += 1
        await pendiente
        return HttpResponse.json(
          {
            id: 1,
            fecha_carga: '2026-09-28T16:05:00Z',
            nombre_archivo: 'valida.xlsx',
            filas_leidas: 120,
            filas_guardadas: 118,
            filas_duplicadas: 2,
            socios_enlazados: 95,
            avisos_enlace: [],
          },
          { status: 201 },
        )
      }),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('valida.xlsx'))
    const boton = await screen.findByRole('button', { name: 'Confirmar' })
    await user.click(boton)

    await waitFor(() => expect(boton).toBeDisabled())
    await user.click(boton)
    liberar()

    await screen.findByRole('region', { name: 'Carga guardada' })
    expect(llamadas).toBe(1)
  })

  it('cambiar de archivo limpia la vista previa anterior', async () => {
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('con-errores.xlsx'))
    await screen.findByRole('table')

    await user.upload(input(), archivo('x', 'notas.txt', 'text/plain'))

    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Vista previa' })).not.toBeInTheDocument()

    await user.upload(input(), xlsx('valida.xlsx'))
    await screen.findByRole('region', { name: 'Vista previa' })
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(botonConfirmar()).toBeEnabled()
  })

  it('Confirmar falla con 409 → conserva la vista previa y permite reintentar', async () => {
    let llamadas = 0
    server.use(
      http.post(CARGAS_PATH, () => {
        llamadas += 1
        return HttpResponse.json(errorBody('conflict', 'La migracion historica aun no termina.'), {
          status: 409,
        })
      }),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('valida.xlsx'))
    await user.click(await screen.findByRole('button', { name: 'Confirmar' }))
    await screen.findByRole('alert')

    expect(screen.getByRole('region', { name: 'Vista previa' })).toBeInTheDocument()
    expect(botonConfirmar()).toBeEnabled()
    await user.click(botonConfirmar())
    await waitFor(() => expect(llamadas).toBe(2))
  })

  it('mientras valida la vista previa → input de archivo deshabilitado', async () => {
    let liberar: () => void = () => {}
    const pendiente = new Promise<void>((resolve) => {
      liberar = resolve
    })
    server.use(
      http.post(VISTA_PREVIA_PATH, async () => {
        await pendiente
        return HttpResponse.json({
          filas_leidas: 5,
          filas_validas: 5,
          filas_con_error: 0,
          filas_duplicadas: 0,
          vencimiento_desde: '2026-10-01',
          vencimiento_hasta: '2026-10-31',
          errores: [],
          puede_confirmar: true,
        })
      }),
    )
    const user = setup()
    render(<CargaPage />)

    await user.upload(input(), xlsx('lenta.xlsx'))

    await waitFor(() => expect(input()).toBeDisabled())
    expect(screen.getByRole('status')).toBeInTheDocument()
    liberar()
    await screen.findByRole('region', { name: 'Vista previa' })
    expect(input()).toBeEnabled()
  })

  it('arquitectura: la pagina no importa api/ ni core/http ni usa fetch', () => {
    expect(pageSource).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(pageSource).not.toMatch(/core\/http/)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
  })

  it('arquitectura: VistaPreviaCarga es presentacional y reutiliza DataTable', () => {
    expect(vistaPreviaSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(vistaPreviaSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
    expect(vistaPreviaSource).toMatch(/shared\/ui\/DataTable/)
  })
})
