import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import {
  escenariosGestion,
  GESTION_CERRADA_ID,
  GESTION_PENDIENTE_ID,
  MENSAJE_CAMPANIA_NO_APLICA,
  MENSAJE_GESTION_CERRADA,
  MENSAJE_GESTION_DUPLICADA,
} from '../api/lista-api.handlers'
import type { Prediccion } from '../types'
import { useGestion } from './useGestion'
import source from './useGestion.ts?raw'

const SUGERIDAS_PATH = '*/api/v1/predicciones/:id/campanias-sugeridas'
const GESTION_PATH = '*/api/v1/gestiones/:id'

function prediccion(extra: Partial<Prediccion> = {}): Prediccion {
  return {
    prediccionId: 1503,
    prioridad: 3,
    socioNombre: 'Socio Ficticio',
    celular: null,
    cedula: '0000000002',
    plan: 'MENSUAL',
    fechaVencimiento: '2026-10-05',
    diasParaVencer: 6,
    montoCobrado: '30.00',
    score: '0.89000000',
    nivelRiesgo: 'ALTO',
    factoresPrincipales: [],
    dentroTopK: true,
    gestionId: null,
    gestionEstado: null,
    campaniaAsignada: null,
    ...extra,
  }
}

/** Cuenta las peticiones de `metodo` a `ruta` sin responder (cae al handler por defecto). */
function contar(metodo: 'get' | 'post' | 'put', ruta: string) {
  const contador = { llamadas: 0 }
  server.use(
    http[metodo](ruta, () => {
      contador.llamadas += 1
      return undefined
    }),
  )
  return contador
}

const RESULTADO = {
  contactado: true,
  campaniaOfrecida: 'SI',
  campaniaAceptada: 'PENDIENTE',
  renovoDeclarado: 'PENDIENTE',
  fechaContacto: '2026-09-29',
} as const

describe('useGestion', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 8, 29, 12, 0, 0))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('cerrado al montar: sin peticiones ni prediccion', () => {
    const sugeridas = contar('get', SUGERIDAS_PATH)
    const { result } = renderHook(() => useGestion())

    expect(result.current.prediccion).toBeNull()
    expect(result.current.estado).toBe('inactivo')
    expect(sugeridas.llamadas).toBe(0)
  })

  it('abrir sin gestion → 1 peticion a las sugeridas y ninguna a la gestion; hoy local', async () => {
    const sugeridas = contar('get', SUGERIDAS_PATH)
    const gestiones = contar('get', GESTION_PATH)
    const { result } = renderHook(() => useGestion())

    act(() => result.current.abrir(prediccion()))

    expect(result.current.estado).toBe('cargando')
    await waitFor(() => expect(result.current.estado).toBe('listo'))
    expect(result.current.sugeridas.map((c) => c.nombre)).toEqual([
      'Ejemplo: Llamada personal antes del vencimiento',
      'Ejemplo: Renovación anticipada',
    ])
    expect(result.current.gestion).toBeNull()
    expect(result.current.hoy).toBe('2026-09-29')
    expect(sugeridas.llamadas).toBe(1)
    expect(gestiones.llamadas).toBe(0)
  })

  it('abrir con gestionId → 1 peticion a GET /gestiones/{id} y ninguna a las sugeridas', async () => {
    const sugeridas = contar('get', SUGERIDAS_PATH)
    const gestiones = contar('get', GESTION_PATH)
    const { result } = renderHook(() => useGestion())

    act(() => result.current.abrir(prediccion({ gestionId: GESTION_PENDIENTE_ID, gestionEstado: 'PENDIENTE' })))

    await waitFor(() => expect(result.current.estado).toBe('listo'))
    expect(result.current.gestion).toMatchObject({ id: GESTION_PENDIENTE_ID, estado: 'PENDIENTE' })
    expect(gestiones.llamadas).toBe(1)
    expect(sugeridas.llamadas).toBe(0)
  })

  it('error al cargar → estado error con el mensaje; reintentar vuelve a pedir', async () => {
    let fallar = true
    server.use(
      http.get(SUGERIDAS_PATH, () =>
        fallar
          ? HttpResponse.json({ error: { code: 'x', message: 'Fallo simulado.' } }, { status: 500 })
          : undefined,
      ),
    )
    const { result } = renderHook(() => useGestion())

    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('error'))
    expect(result.current.error).toBe('Fallo simulado.')

    fallar = false
    act(() => result.current.reintentar())
    await waitFor(() => expect(result.current.estado).toBe('listo'))
    expect(result.current.error).toBeNull()
  })

  it('crear exitoso → devuelve la gestion, queda en el estado y avisa a onGuardada', async () => {
    const onGuardada = vi.fn()
    const { result } = renderHook(() => useGestion({ onGuardada }))
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    let creada: unknown
    await act(async () => {
      creada = await result.current.crear({
        campaniaId: 2,
        fechaSeguimiento: '2026-10-30',
        responsable: 'Andrea',
      })
    })

    expect(creada).toMatchObject({ prediccionId: 1503, campaniaId: 2, estado: 'PENDIENTE' })
    expect(result.current.gestion).toBe(creada)
    expect(result.current.estado).toBe('listo')
    // Con campaña la ventana sigue abierta, en la parte 2.
    expect(result.current.prediccion).not.toBeNull()
    expect(onGuardada).toHaveBeenCalledWith(creada)
  })

  it('crear sin campaña → la gestion nace cerrada: la ventana se cierra y avisa a onGuardada una vez', async () => {
    const onGuardada = vi.fn()
    const gestiones: unknown[] = []
    const { result } = renderHook(() => {
      const ventana = useGestion({ onGuardada })
      // Cada render: la gestion nunca debe llegar a la ventana (no se pinta la parte 2).
      gestiones.push(ventana.gestion)
      return ventana
    })
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    let creada: unknown
    await act(async () => {
      creada = await result.current.crear({
        campaniaId: null,
        fechaSeguimiento: null,
        responsable: null,
      })
    })

    expect(creada).toMatchObject({ prediccionId: 1503, campaniaId: null, estado: 'CERRADA' })
    expect(result.current.prediccion).toBeNull()
    expect(result.current.estado).toBe('inactivo')
    expect(result.current.gestion).toBeNull()
    expect(result.current.error).toBeNull()
    expect(gestiones.every((g) => g === null)).toBe(true)
    expect(onGuardada).toHaveBeenCalledTimes(1)
    expect(onGuardada).toHaveBeenCalledWith(creada)
  })

  it('tras crear sin campaña se puede abrir y crear la gestion de otro socio', async () => {
    const posts = contar('post', '*/api/v1/gestiones')
    const { result } = renderHook(() => useGestion())
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))
    await act(async () => {
      await result.current.crear({ campaniaId: null, fechaSeguimiento: null, responsable: null })
    })

    act(() => result.current.abrir(prediccion({ prediccionId: 1504, prioridad: 4 })))
    await waitFor(() => expect(result.current.estado).toBe('listo'))
    await act(async () => {
      await result.current.crear({ campaniaId: 2, fechaSeguimiento: '2026-10-30' })
    })

    expect(posts.llamadas).toBe(2)
    expect(result.current.prediccion?.prediccionId).toBe(1504)
    expect(result.current.gestion).toMatchObject({ estado: 'PENDIENTE', campaniaId: 2 })
  })

  it.each([
    ['422', escenariosGestion.campaniaNoAplica, MENSAJE_CAMPANIA_NO_APLICA],
    ['409', escenariosGestion.duplicada, MENSAJE_GESTION_DUPLICADA],
  ])('crear con %s → error con el mensaje del servidor, sin gestion ni onGuardada', async (_s, escenario, mensaje) => {
    server.use(escenario)
    const onGuardada = vi.fn()
    const { result } = renderHook(() => useGestion({ onGuardada }))
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    let creada: unknown = 'sin llamar'
    await act(async () => {
      creada = await result.current.crear({ campaniaId: null, fechaSeguimiento: '2026-10-30' })
    })

    expect(creada).toBeNull()
    expect(result.current.error).toBe(mensaje)
    expect(result.current.estado).toBe('listo')
    expect(result.current.gestion).toBeNull()
    expect(onGuardada).not.toHaveBeenCalled()
  })

  it('no hay doble envio mientras enviando', async () => {
    const posts = contar('post', '*/api/v1/gestiones')
    const { result } = renderHook(() => useGestion())
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    let segunda: unknown = 'sin llamar'
    await act(async () => {
      const primera = result.current.crear({ campaniaId: null, fechaSeguimiento: '2026-10-30' })
      segunda = await result.current.crear({ campaniaId: null, fechaSeguimiento: '2026-10-30' })
      await primera
    })

    expect(segunda).toBeNull()
    expect(posts.llamadas).toBe(1)
  })

  it('registrar sobre la pendiente → gestion actualizada y onGuardada', async () => {
    const onGuardada = vi.fn()
    const { result } = renderHook(() => useGestion({ onGuardada }))
    act(() => result.current.abrir(prediccion({ gestionId: GESTION_PENDIENTE_ID })))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    await act(async () => {
      await result.current.registrar({ ...RESULTADO, renovoDeclarado: 'NO' })
    })

    expect(result.current.gestion).toMatchObject({ estado: 'CERRADA', renovoDeclarado: 'NO' })
    expect(onGuardada).toHaveBeenCalledTimes(1)
  })

  it('registrar sobre una cerrada (409) → error con el mensaje del servidor', async () => {
    const { result } = renderHook(() => useGestion())
    act(() => result.current.abrir(prediccion({ gestionId: GESTION_CERRADA_ID })))
    await waitFor(() => expect(result.current.estado).toBe('listo'))

    await act(async () => {
      await result.current.registrar(RESULTADO)
    })

    expect(result.current.error).toBe(MENSAJE_GESTION_CERRADA)
    expect(result.current.gestion).toMatchObject({ estado: 'CERRADA' })
  })

  it('cerrar y desmontar abortan la peticion en curso', async () => {
    const señales: AbortSignal[] = []
    server.use(
      http.get(SUGERIDAS_PATH, async ({ request }) => {
        señales.push(request.signal)
        await new Promise(() => {})
      }),
    )
    const { result, unmount } = renderHook(() => useGestion())

    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(señales).toHaveLength(1))
    act(() => result.current.cerrar())
    expect(señales[0]?.aborted).toBe(true)
    expect(result.current.prediccion).toBeNull()
    expect(result.current.estado).toBe('inactivo')

    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(señales).toHaveLength(2))
    unmount()
    expect(señales[1]?.aborted).toBe(true)
  })

  it('cerrar es estable entre renders (el Modal no recoloca el foco al repintar)', async () => {
    const { result, rerender } = renderHook(() => useGestion())
    const cerrar = result.current.cerrar
    act(() => result.current.abrir(prediccion()))
    await waitFor(() => expect(result.current.estado).toBe('listo'))
    rerender()

    expect(result.current.cerrar).toBe(cerrar)
  })

  it('arquitectura: sin JSX ni fetch directo', () => {
    expect(source).not.toMatch(/\bfetch\s*\(|core\/http\/http-client/)
    expect(source).not.toMatch(/return\s*\(?\s*<[A-Za-z]/)
  })
})
