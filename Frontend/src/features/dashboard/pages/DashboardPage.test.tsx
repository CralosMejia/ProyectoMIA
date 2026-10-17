/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import DashboardPage from './DashboardPage'
import appLayoutSource from '../../../core/layout/AppLayout.tsx?raw'
import pageSource from './DashboardPage.tsx?raw'

const DASHBOARD_PATH = '*/api/v1/dashboard'

function mesLocal(): string {
  const ahora = new Date()
  return `${ahora.getFullYear()}-${String(ahora.getMonth() + 1).padStart(2, '0')}`
}

/** Registra cada peticion (mes y senal) sin responder: cae al handler por defecto. */
function registrarPeticiones() {
  const registro = { meses: [] as (string | null)[], senales: [] as AbortSignal[] }
  server.use(
    http.get(DASHBOARD_PATH, ({ request }) => {
      registro.meses.push(new URL(request.url).searchParams.get('mes'))
      registro.senales.push(request.signal)
      return undefined
    }),
  )
  return registro
}

const VACIO = {
  embudo: { asignadas: 0, contactadas: 0, ofrecidas: 0, aceptadas: 0, renovaron: 0 },
  por_campania: [],
  estado_modelo: {
    version: 'v1',
    fecha_entrenamiento: '2026-09-28T14:30:00Z',
    ciclos_entrenamiento: 1843,
    proxima_fecha_reentrenamiento: '2027-03-28',
    ciclos_nuevos_evaluables: 0,
  },
}

/** Mes `YYYY-MM` local en palabras, como lo muestra la pagina. */
const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
]
function mesLocalEnPalabras(): string {
  const ahora = new Date()
  return `${MESES[ahora.getMonth()]} de ${ahora.getFullYear()}`
}

/** Clase de Tailwind que oculta el elemento al imprimir. */
const OCULTO_AL_IMPRIMIR = '.print\\:hidden'

function ocultoAlImprimir(elemento: Element): boolean {
  return elemento.closest(OCULTO_AL_IMPRIMIR) !== null
}

describe('DashboardPage', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('al abrir: filtro "Mes" con el mes actual local y datos de ese mes', async () => {
    const registro = registrarPeticiones()

    render(<DashboardPage />)

    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    const mes = screen.getByLabelText('Mes')
    expect(mes).toHaveAttribute('type', 'month')
    expect(mes).toHaveValue(mesLocal())
    expect(screen.getByRole('status')).toHaveTextContent('Cargando el dashboard')

    expect(await screen.findByRole('table', { name: 'Resultados por campaña' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /^Embudo del mes: / })).toBeInTheDocument()
    expect(screen.getByText('Versión v1')).toBeInTheDocument()
    expect(
      screen.getByText(
        'Las cifras son resultados observados; no demuestran que la campaña causó la renovación.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(registro.meses).toEqual([mesLocal()])
  })

  it('cambiar a 2026-08 → nueva peticion con mes=2026-08 y cancela la anterior', async () => {
    const registro = { meses: [] as (string | null)[], senales: [] as AbortSignal[] }
    server.use(
      http.get(DASHBOARD_PATH, ({ request }) => {
        const mes = new URL(request.url).searchParams.get('mes')
        registro.meses.push(mes)
        registro.senales.push(request.signal)
        // La primera (mes actual) no responde: se queda pendiente hasta que se cancele.
        return mes === '2026-08' ? undefined : new Promise<Response>(() => {})
      }),
    )

    render(<DashboardPage />)
    await waitFor(() => expect(registro.meses).toHaveLength(1))
    fireEvent.change(screen.getByLabelText('Mes'), { target: { value: '2026-08' } })

    await waitFor(() => expect(registro.meses).toEqual([mesLocal(), '2026-08']))
    expect(registro.senales[0]?.aborted).toBe(true)
    expect(screen.getByLabelText('Mes')).toHaveValue('2026-08')
    expect(await screen.findByRole('table', { name: 'Resultados por campaña' })).toBeInTheDocument()
  })

  it('un valor de mes vacio no lanza otra peticion', async () => {
    const registro = registrarPeticiones()
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    fireEvent.change(screen.getByLabelText('Mes'), { target: { value: '' } })

    expect(registro.meses).toHaveLength(1)
  })

  it('error → ErrorAlert con el mensaje del servidor y Reintentar vuelve a pedir', async () => {
    let llamadas = 0
    server.use(
      http.get(DASHBOARD_PATH, () => {
        llamadas += 1
        return llamadas === 1
          ? HttpResponse.json(
              { error: { code: 'validation_error', message: 'El mes no tiene el formato YYYY-MM.' } },
              { status: 400 },
            )
          : undefined
      }),
    )
    const user = userEvent.setup()

    render(<DashboardPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('El mes no tiene el formato YYYY-MM.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('table', { name: 'Resultados por campaña' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(llamadas).toBe(2)
  })

  it('mes sin gestiones → "No hay gestiones asignadas en este mes" y la tarjeta del modelo visible', async () => {
    server.use(
      http.get(DASHBOARD_PATH, ({ request }) =>
        HttpResponse.json({ mes: new URL(request.url).searchParams.get('mes'), ...VACIO }),
      ),
    )

    render(<DashboardPage />)

    expect(await screen.findByText('No hay gestiones asignadas en este mes')).toBeInTheDocument()
    expect(screen.getByText('Versión v1')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('sin modelo vigente → "Aún no hay un modelo vigente"', async () => {
    server.use(
      http.get(DASHBOARD_PATH, () =>
        HttpResponse.json({ mes: '2026-09', ...VACIO, estado_modelo: null }),
      ),
    )

    render(<DashboardPage />)

    expect(await screen.findByText('Aún no hay un modelo vigente')).toBeInTheDocument()
  })

  it('al desmontar antes de responder → aborta la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get(DASHBOARD_PATH, ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )

    const { unmount } = render(<DashboardPage />)
    await waitFor(() => expect(senal).not.toBeNull())
    unmount()

    await waitFor(() => expect((senal as AbortSignal | null)?.aborted).toBe(true))
  })

  it('R-012: "Resultados de <mes>", embudo y dona con las cifras del mes, tabla y tarjeta', async () => {
    render(<DashboardPage />)

    expect(screen.getByText(`Resultados de ${mesLocalEnPalabras()}`)).toBeInTheDocument()
    await screen.findByRole('table', { name: 'Resultados por campaña' })
    expect(screen.getByRole('img', { name: /^Embudo del mes: / })).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Resultado de las gestiones del mes' }),
    ).toBeInTheDocument()
    // Mock: A {12, 10, 4}, B {9, 9, 2}, Sin campaña {3, 0, 0} → 6 / 13 / 5 de 24.
    const leyenda = within(screen.getByRole('list', { name: 'Leyenda' })).getAllByRole('listitem')
    expect(leyenda.map((li) => li.textContent)).toEqual([
      'Renovaron 6 (25,0 %)',
      'No renovaron 13 (54,2 %)',
      'Sin resultado 5 (20,8 %)',
    ])
    expect(screen.getByText('Versión v1')).toBeInTheDocument()
  })

  it('R-012: cambiar a 2026-08 → "Resultados de agosto de 2026"', async () => {
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    fireEvent.change(screen.getByLabelText('Mes'), { target: { value: '2026-08' } })

    expect(await screen.findByText('Resultados de agosto de 2026')).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Resultados por campaña' })).toBeInTheDocument()
  })

  it('R-012: mes sin gestiones → sin graficos', async () => {
    server.use(
      http.get(DASHBOARD_PATH, ({ request }) =>
        HttpResponse.json({ mes: new URL(request.url).searchParams.get('mes'), ...VACIO }),
      ),
    )

    render(<DashboardPage />)

    expect(await screen.findByText('No hay gestiones asignadas en este mes')).toBeInTheDocument()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Resultado de las gestiones del mes' }),
    ).not.toBeInTheDocument()
  })

  it('R-012: "¿Cómo funciona el dashboard?" abre su ayuda', async () => {
    const user = userEvent.setup()
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    await user.click(screen.getByRole('button', { name: '¿Cómo funciona el dashboard?' }))

    expect(screen.getByRole('dialog', { name: '¿Cómo funciona el dashboard?' })).toBeInTheDocument()
  })

  it('R-012: "Imprimir / Guardar PDF" deshabilitado mientras carga y llama a window.print una vez', async () => {
    const imprimir = vi.spyOn(window, 'print').mockImplementation(() => {})
    const registro = registrarPeticiones()
    const user = userEvent.setup()

    render(<DashboardPage />)

    const boton = screen.getByRole('button', { name: 'Imprimir / Guardar PDF' })
    expect(boton).toBeDisabled()
    await screen.findByRole('table', { name: 'Resultados por campaña' })
    expect(boton).toBeEnabled()

    await user.click(boton)

    expect(imprimir).toHaveBeenCalledTimes(1)
    expect(registro.meses).toHaveLength(1)
  })

  it('R-012: con error → "Imprimir / Guardar PDF" deshabilitado', async () => {
    server.use(
      http.get(DASHBOARD_PATH, () =>
        HttpResponse.json(
          { error: { code: 'validation_error', message: 'El mes no tiene el formato YYYY-MM.' } },
          { status: 400 },
        ),
      ),
    )

    render(<DashboardPage />)

    await screen.findByRole('alert')
    expect(screen.getByRole('button', { name: 'Imprimir / Guardar PDF' })).toBeDisabled()
    expect(ocultoAlImprimir(screen.getByRole('button', { name: 'Reintentar' }))).toBe(true)
  })

  it('R-012: al imprimir se ocultan botones y filtro; se ven titulo, mes, graficos, tablas, tarjeta y aviso', async () => {
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    for (const nombre of ['Imprimir / Guardar PDF', '¿Cómo funciona el dashboard?']) {
      expect(ocultoAlImprimir(screen.getByRole('button', { name: nombre }))).toBe(true)
    }
    expect(ocultoAlImprimir(screen.getByLabelText('Mes'))).toBe(true)

    const visibles = [
      screen.getByRole('heading', { level: 1, name: 'Dashboard' }),
      screen.getByText(`Resultados de ${mesLocalEnPalabras()}`),
      ...screen.getAllByRole('img'),
      ...screen.getAllByRole('table'),
      screen.getByRole('heading', { name: 'Modelo de predicción' }),
      screen.getByText(
        'Las cifras son resultados observados; no demuestran que la campaña causó la renovación.',
      ),
    ]
    expect(screen.getAllByRole('img')).toHaveLength(2)
    expect(screen.getAllByRole('table')).toHaveLength(3)
    for (const elemento of visibles) {
      expect(ocultoAlImprimir(elemento)).toBe(false)
    }
  })

  it('R-012: la cabecera de la app no se imprime e index.css tiene estilos de impresion', () => {
    // Vitest procesa los .css (un import ?raw de index.css llega vacio): se lee del disco,
    // relativo a la raiz de Frontend (en jsdom `import.meta.url` no es una ruta de archivo).
    const indexCss = readFileSync(join(process.cwd(), 'src', 'index.css'), 'utf8')

    expect(appLayoutSource).toMatch(/<header className="[^"]*print:hidden/)
    expect(appLayoutSource).toMatch(/<main className="[^"]*print:p-0/)
    expect(indexCss).toMatch(/@media print\s*\{[\s\S]*print-color-adjust:\s*exact/)
    expect(pageSource).toMatch(/window\.print\(\)/)
  })

  it('R-018: "Indicadores del piloto" del mes (parcial) con lista, n y estados traducidos', async () => {
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    fireEvent.change(screen.getByLabelText('Mes'), { target: { value: '2026-09' } })

    const region = await screen.findByRole('region', { name: 'Indicadores del piloto' })
    expect(
      await within(region).findByText(
        'Lista del mes: Ejemplo: Lista septiembre, generada el 1 de septiembre de 2026.',
      ),
    ).toBeInTheDocument()
    expect(within(region).getByText('60,0 %')).toBeInTheDocument()
    expect(within(region).getByText('$312,50')).toBeInTheDocument()
    expect(
      within(region).getByText('Parcial: faltan 5 por verificar (20 de 25 verificados)'),
    ).toBeInTheDocument()
    // Cuatro n sin aclarar y el del monto, que cuenta solo a los contactados ya verificados.
    expect(within(region).getAllByText(/^n = \d+$/)).toHaveLength(4)
    expect(within(region).getAllByText(/^n = \d+ contactados ya verificados$/)).toHaveLength(1)
    expect(within(region).queryByText(/PARCIAL|COMPLETO|PENDIENTE|SIN_DATOS/)).not.toBeInTheDocument()
  })

  it('R-018: mes sin gestiones ni lista → indicadores del piloto "Sin datos" visibles', async () => {
    server.use(
      http.get(DASHBOARD_PATH, ({ request }) =>
        HttpResponse.json({ mes: new URL(request.url).searchParams.get('mes'), ...VACIO }),
      ),
    )

    render(<DashboardPage />)

    expect(await screen.findByText('No hay gestiones asignadas en este mes')).toBeInTheDocument()
    const region = screen.getByRole('region', { name: 'Indicadores del piloto' })
    expect(within(region).getByText('No hay una lista generada en este mes.')).toBeInTheDocument()
    expect(within(region).getAllByText('Sin datos')).toHaveLength(5)
  })

  it('R-018: los indicadores del piloto se imprimen, con sus avisos, y no se cortan', async () => {
    render(<DashboardPage />)
    await screen.findByRole('table', { name: 'Resultados por campaña' })

    const region = screen.getByRole('region', { name: 'Indicadores del piloto' })
    expect(ocultoAlImprimir(region)).toBe(false)
    expect(region.querySelector(OCULTO_AL_IMPRIMIR)).toBeNull()
    expect(region.className).toMatch(/\bbreak-inside-avoid\b/)
    for (const aviso of [
      'Los socios del top 25 se contactan; por eso la precisión observada puede quedar por debajo de la real.',
      'Cifras observadas, no causales.',
    ]) {
      expect(ocultoAlImprimir(within(region).getByText(aviso))).toBe(false)
    }
  })

  it('arquitectura: la pagina no importa api/ ni core/http ni usa fetch', () => {
    expect(pageSource).not.toMatch(/from\s+['"][^'"]*\/api\//)
    expect(pageSource).not.toMatch(/core\/http/)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
  })
})
