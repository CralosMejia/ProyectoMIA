import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import ListaPage from '../pages/ListaPage'
import { HistorialListas } from './HistorialListas'
import componentSource from './HistorialListas.tsx?raw'

const OPCION_RECIENTE = 'Lista del 28 sep 2026 · 25 prioritarios'
const OPCION_ANTERIOR = 'Lista del 31 ago 2026 · 10 prioritarios'

function selector(): HTMLSelectElement {
  return screen.getByLabelText('Listas anteriores')
}

async function opcionesCargadas(): Promise<string[]> {
  await waitFor(() => expect(within(selector()).getAllByRole('option')).toHaveLength(2))
  return within(selector())
    .getAllByRole('option')
    .map((o) => o.textContent ?? '')
}

const MESES: Record<string, string> = { '08': 'ago', '09': 'sep', '10': 'oct' }

/** Nombre por defecto como el del servidor, p. ej. "2026-10-01" → "Lista del 1 oct 2026". */
function nombrePorDefecto(fecha: string): string {
  const [anio, mes, dia] = fecha.split('-')
  return `Lista del ${Number(dia)} ${MESES[mes ?? ''] ?? ''} ${anio}`
}

function resumen(id: number, fecha: string, creadaEn: string, topK = 25) {
  return {
    id,
    nombre: nombrePorDefecto(fecha),
    fecha_generacion: fecha,
    creada_en: creadaEn,
    modelo_version: 'v1',
    horizonte_dias: 30,
    top_k: topK,
    total_items: 32,
  }
}

describe('HistorialListas', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('con dos listas simuladas → 2 opciones (nombre y prioritarios), la mas reciente primero', async () => {
    render(<ListaPage />)

    const opciones = await opcionesCargadas()
    expect(opciones).toEqual([OPCION_RECIENTE, OPCION_ANTERIOR])
    for (const opcion of opciones) {
      expect(opcion).not.toMatch(/modelo|v1|\bK\b/i)
      expect(opcion).not.toMatch(/socios/i)
    }
    await waitFor(() => expect(selector()).toHaveValue('42'))
  })

  it('ordena de la mas reciente a la mas antigua aunque el servidor las mande al reves', async () => {
    server.use(
      http.get('*/api/v1/listas', () =>
        HttpResponse.json([
          resumen(41, '2026-08-31', '2026-08-31T14:00:00Z', 10),
          resumen(42, '2026-09-28', '2026-09-28T15:00:00Z'),
        ]),
      ),
    )
    render(<ListaPage />)

    expect(await opcionesCargadas()).toEqual([OPCION_RECIENTE, OPCION_ANTERIOR])
  })

  it('elegir la anterior → GET /listas/{id}; la tabla y el Excel pasan a esa lista', async () => {
    const pedidas: string[] = []
    server.use(
      http.get('*/api/v1/listas/:id', ({ params }) => {
        if (params.id !== 'ultima') pedidas.push(String(params.id))
        return undefined
      }),
      http.get('*/api/v1/listas/:id/excel', ({ params }) => {
        pedidas.push(`excel ${String(params.id)}`)
        return undefined
      }),
    )
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.stubGlobal(
      'URL',
      class extends URL {
        static createObjectURL = vi.fn(() => 'blob:x')
        static revokeObjectURL = vi.fn()
      },
    )
    const user = userEvent.setup()
    render(<ListaPage />)
    await opcionesCargadas()
    await screen.findByText('Ana Prueba')

    await user.selectOptions(selector(), OPCION_ANTERIOR)

    // La lista anterior empieza por otro socio y trae el aviso de datos antiguos.
    expect(await screen.findByText('Diego Prueba')).toBeInTheDocument()
    expect(screen.queryByText('Ana Prueba')).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/desactualizados/)
    expect(selector()).toHaveValue('41')

    await user.click(screen.getByRole('button', { name: 'Descargar Excel' }))
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1))
    expect(pedidas).toEqual(['41', 'excel 41'])
  })

  it('tras generar una lista nueva, el historial se refresca y la selecciona', async () => {
    let generada = false
    const nueva = resumen(43, '2026-10-01', '2026-10-01T09:00:00Z', 5)
    server.use(
      http.get('*/api/v1/listas', () =>
        HttpResponse.json([
          ...(generada ? [nueva] : []),
          resumen(42, '2026-09-28', '2026-09-28T15:00:00Z'),
          resumen(41, '2026-08-31', '2026-08-31T14:00:00Z', 10),
        ]),
      ),
      http.post('*/api/v1/listas', async ({ request }) => {
        const cuerpo = (await request.clone().json()) as { top_k: number }
        generada = true
        return HttpResponse.json(
          {
            id: 43,
            nombre: nueva.nombre,
            modelo_version: 'v1',
            fecha_generacion: '2026-10-01',
            creada_en: nueva.creada_en,
            horizonte_dias: 30,
            top_k: cuerpo.top_k,
            umbral_alto: '0.70000000',
            umbral_medio: '0.40000000',
            advertencia_datos_antiguos: false,
            items: [],
          },
          { status: 201 },
        )
      }),
    )
    const user = userEvent.setup()
    render(<ListaPage />)
    await opcionesCargadas()

    await user.clear(screen.getByLabelText(/socios prioritarios a contactar/i))
    await user.type(screen.getByLabelText(/socios prioritarios a contactar/i), '5')
    await user.click(screen.getByRole('button', { name: 'Generar lista' }))

    await waitFor(() => expect(within(selector()).getAllByRole('option')).toHaveLength(3))
    const opciones = within(selector())
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(opciones[0]).toBe('Lista del 1 oct 2026 · 5 prioritarios')
    expect(selector()).toHaveValue('43')
  })

  it('elegir una lista que falla → ErrorAlert y se conserva la lista mostrada', async () => {
    server.use(
      http.get('*/api/v1/listas/41', () =>
        HttpResponse.json(
          { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
          { status: 500 },
        ),
      ),
    )
    const user = userEvent.setup()
    render(<ListaPage />)
    await opcionesCargadas()
    await screen.findByText('Ana Prueba')

    await user.selectOptions(selector(), OPCION_ANTERIOR)

    expect(await screen.findByRole('alert')).toHaveTextContent('Error interno del servidor.')
    expect(screen.getByText('Ana Prueba')).toBeInTheDocument()
    expect(selector()).toHaveValue('42')
  })

  it('historial con error → ErrorAlert con Reintentar que vuelve a pedir', async () => {
    let llamadas = 0
    server.use(
      http.get('*/api/v1/listas', () => {
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

    expect(await opcionesCargadas()).toEqual([OPCION_RECIENTE, OPCION_ANTERIOR])
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  describe('componente', () => {
    const listas = [
      {
        id: 42,
        nombre: 'Lista del 28 sep 2026',
        fechaGeneracion: '2026-09-28',
        creadaEn: new Date('2026-09-28T15:00:00Z'),
        modeloVersion: 'v1',
        horizonteDias: 30,
        topK: 25,
        totalItems: 32,
      },
      {
        id: 41,
        nombre: 'Lista del 31 ago 2026',
        fechaGeneracion: '2026-08-31',
        creadaEn: new Date('2026-08-31T14:00:00Z'),
        modeloVersion: 'v1',
        horizonteDias: 30,
        topK: 10,
        totalItems: 12,
      },
    ]
    const onSeleccionar = vi.fn()

    beforeEach(() => {
      onSeleccionar.mockClear()
    })

    it('sin listas no se muestra', () => {
      render(<HistorialListas listas={[]} seleccionadaId={null} onSeleccionar={onSeleccionar} />)

      expect(screen.queryByLabelText('Listas anteriores')).not.toBeInTheDocument()
    })

    it('emite el id elegido', async () => {
      const user = userEvent.setup()
      render(<HistorialListas listas={listas} seleccionadaId={42} onSeleccionar={onSeleccionar} />)

      await user.selectOptions(selector(), OPCION_ANTERIOR)

      expect(onSeleccionar).toHaveBeenCalledWith(41)
    })

    it.each([
      [25, 30, 'Lista del 29 sep 2026 · 25 prioritarios'],
      [1, 30, 'Lista del 29 sep 2026 · 1 prioritario'],
      [25, 3, 'Lista del 29 sep 2026 · 3 prioritarios'],
      [25, 1, 'Lista del 29 sep 2026 · 1 prioritario'],
      [25, 0, 'Lista del 29 sep 2026 · 0 prioritarios'],
    ])('topK %i y totalItems %i → %j', (topK, totalItems, esperado) => {
      render(
        <HistorialListas
          listas={[
            {
              ...listas[0]!,
              nombre: 'Lista del 29 sep 2026',
              fechaGeneracion: '2026-09-29',
              topK,
              totalItems,
            },
          ]}
          seleccionadaId={42}
          onSeleccionar={onSeleccionar}
        />,
      )

      expect(within(selector()).getByRole('option').textContent).toBe(esperado)
    })

    it('nombre editado → "<nombre> · <n> prioritarios", como texto literal', () => {
      render(
        <HistorialListas
          listas={[{ ...listas[0]!, nombre: '<b>Campaña octubre</b>' }]}
          seleccionadaId={42}
          onSeleccionar={onSeleccionar}
        />,
      )

      const opcion = within(selector()).getByRole('option')
      expect(opcion.textContent).toBe('<b>Campaña octubre</b> · 25 prioritarios')
      expect(opcion.querySelector('b')).toBeNull()
    })

    it('respeta el orden recibido y mantiene la etiqueta "Listas anteriores"', () => {
      render(<HistorialListas listas={listas} seleccionadaId={42} onSeleccionar={onSeleccionar} />)

      expect(screen.getByText('Listas anteriores')).toBeInTheDocument()
      expect(
        within(selector())
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual([OPCION_RECIENTE, OPCION_ANTERIOR])
    })

    it('deshabilitado → el selector no se puede usar', () => {
      render(
        <HistorialListas
          listas={listas}
          seleccionadaId={42}
          deshabilitado
          onSeleccionar={onSeleccionar}
        />,
      )

      expect(selector()).toBeDisabled()
    })
  })

  it('arquitectura: el selector es presentacional (sin hooks ni api)', () => {
    expect(componentSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(componentSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
  })
})
