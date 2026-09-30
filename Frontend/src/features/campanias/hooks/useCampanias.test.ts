import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../../mocks/server'
import {
  MENSAJE_NOMBRE_OBLIGATORIO,
  reiniciarCampaniasSimuladas,
} from '../api/campanias-api.handlers'
import type { CampaniaEntrada } from '../types'
import { useCampanias } from './useCampanias'

const CAMPANIAS_PATH = '*/api/v1/campanias'

const ENTRADA: CampaniaEntrada = {
  nombre: 'Clase de prueba',
  descripcion: 'Una clase gratis al renovar.',
  nivelesRiesgo: ['ALTO'],
  planes: ['MENSUAL'],
  prioridad: 5,
}

/** Cuenta los GET a /campanias sin cambiar la respuesta del handler por defecto. */
function contarListados() {
  const contador = { llamadas: 0 }
  server.use(
    http.get(CAMPANIAS_PATH, () => {
      contador.llamadas += 1
      return undefined
    }),
  )
  return contador
}

async function montado() {
  const vista = renderHook(() => useCampanias())
  await waitFor(() => expect(vista.result.current.cargando).toBe(false))
  return vista
}

describe('useCampanias', () => {
  beforeEach(() => {
    reiniciarCampaniasSimuladas()
  })

  afterEach(() => {
    cleanup()
  })

  it('al montar carga la lista con una sola petición', async () => {
    const contador = contarListados()

    const { result } = await montado()

    expect(contador.llamadas).toBe(1)
    expect(result.current.campanias).toHaveLength(3)
    expect(result.current.campanias.every((c) => c.esEjemplo)).toBe(true)
    expect(result.current.errorCarga).toBeNull()
  })

  it('crear exitoso → devuelve true, recarga y la campaña aparece', async () => {
    const { result } = await montado()
    const contador = contarListados()

    let ok = false
    await act(async () => {
      ok = await result.current.crear(ENTRADA)
    })

    expect(ok).toBe(true)
    await waitFor(() => expect(result.current.campanias).toHaveLength(4))
    expect(contador.llamadas).toBe(1)
    expect(result.current.campanias.find((c) => c.nombre === 'Clase de prueba')).toMatchObject({
      activa: true,
      esEjemplo: false,
    })
    expect(result.current.error).toBeNull()
  })

  it('400 al crear → error con el mensaje del servidor y sin cambios', async () => {
    const { result } = await montado()
    const antes = result.current.campanias

    let ok = true
    await act(async () => {
      ok = await result.current.crear({ ...ENTRADA, nombre: '   ' })
    })

    expect(ok).toBe(false)
    expect(result.current.error).toBe(MENSAJE_NOMBRE_OBLIGATORIO)
    expect(result.current.campanias).toEqual(antes)
    expect(result.current.guardando).toBe(false)
  })

  it('editar → PUT y la campaña queda con los datos nuevos', async () => {
    const { result } = await montado()

    await act(async () => {
      await result.current.editar(2, { ...ENTRADA, nombre: 'Renovación editada' })
    })

    await waitFor(() =>
      expect(result.current.campanias.find((c) => c.id === 2)?.nombre).toBe('Renovación editada'),
    )
  })

  it('editar una inexistente → error 404 del servidor', async () => {
    const { result } = await montado()

    await act(async () => {
      await result.current.editar(999, ENTRADA)
    })

    expect(result.current.error).toBe('La campana no existe.')
  })

  it('inactivar → activa:false en el estado', async () => {
    const { result } = await montado()

    let ok = false
    await act(async () => {
      ok = await result.current.inactivar(1)
    })

    expect(ok).toBe(true)
    expect(result.current.campanias.find((c) => c.id === 1)?.activa).toBe(false)
  })

  it('error al cargar → errorCarga; recargar vuelve a pedir', async () => {
    server.use(
      http.get(
        CAMPANIAS_PATH,
        () =>
          HttpResponse.json(
            { error: { code: 'internal_error', message: 'Falla simulada.' } },
            { status: 500 },
          ),
        { once: true },
      ),
    )
    const { result } = await montado()
    expect(result.current.errorCarga).toBe('Falla simulada.')

    act(() => {
      result.current.recargar()
    })

    await waitFor(() => expect(result.current.campanias).toHaveLength(3))
    expect(result.current.errorCarga).toBeNull()
  })

  it('desmontar aborta la petición en curso', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get(CAMPANIAS_PATH, async ({ request }) => {
        senal = request.signal
        await new Promise((resolve) => setTimeout(resolve, 200))
        return HttpResponse.json([])
      }),
    )
    const { unmount } = renderHook(() => useCampanias())
    await waitFor(() => expect(senal).not.toBeNull())

    unmount()

    expect((senal as AbortSignal | null)?.aborted).toBe(true)
  })

  it('desmontar aborta también una operación en curso', async () => {
    const { result, unmount } = await montado()
    let senal: AbortSignal | null = null
    server.use(
      http.post(CAMPANIAS_PATH, async ({ request }) => {
        senal = request.signal
        await new Promise((resolve) => setTimeout(resolve, 200))
        return HttpResponse.json({}, { status: 201 })
      }),
    )

    let promesa: Promise<boolean> = Promise.resolve(true)
    act(() => {
      promesa = result.current.crear(ENTRADA)
    })
    await waitFor(() => expect(senal).not.toBeNull())
    unmount()

    expect((senal as AbortSignal | null)?.aborted).toBe(true)
    await expect(promesa).resolves.toBe(false)
  })
})
