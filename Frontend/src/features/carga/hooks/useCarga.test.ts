/// <reference types="node" />
import { File as NodeFile } from 'node:buffer'
import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { server } from '../../../mocks/server'
import { MENSAJES_CARGA } from '../api/carga-api.handlers'
import { useCarga } from './useCarga'

const VISTA_PREVIA_PATH = '*/api/v1/cargas/vista-previa'
const CARGAS_PATH = '*/api/v1/cargas'
const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
const MENSAJE_EXTENSION = 'Seleccione un archivo .xlsx con la plantilla oficial.'

const VISTA_PREVIA = {
  filas_leidas: 5,
  filas_validas: 5,
  filas_con_error: 0,
  filas_duplicadas: 0,
  vencimiento_desde: '2026-10-01',
  vencimiento_hasta: '2026-10-31',
  errores: [],
  puede_confirmar: true,
}

/** Puente multipart (ver CargaPage.test.tsx): `FormData` y `File` nativos de Node. */
beforeAll(async () => {
  const form = await new Response('a=1', {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  }).formData()
  vi.stubGlobal('FormData', form.constructor)
})

afterAll(() => {
  vi.unstubAllGlobals()
})

afterEach(() => {
  vi.restoreAllMocks()
})

function archivo(nombre: string, type = XLSX_MIME): File {
  return new NodeFile(['contenido'], nombre, { type }) as unknown as File
}

/** Cuenta las peticiones a la vista previa; `respuesta` decide que devuelve. */
function contarVistaPrevia(respuesta: () => Response | Promise<Response>) {
  const contador = { llamadas: 0 }
  server.use(
    http.post(VISTA_PREVIA_PATH, async () => {
      contador.llamadas += 1
      return respuesta()
    }),
  )
  return contador
}

function pendiente() {
  let liberar: () => void = () => {}
  const promesa = new Promise<void>((resolve) => {
    liberar = resolve
  })
  return { promesa, liberar: () => liberar() }
}

function esperar(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

describe('useCarga (tres pasos)', () => {
  it('estado inicial sin archivo, sin revisar ni confirmar', () => {
    const { result } = renderHook(() => useCarga())

    expect(result.current.estado).toBe('inicial')
    expect(result.current.archivoSeleccionado).toBeNull()
    expect(result.current.puedeRevisar).toBe(false)
    expect(result.current.puedeConfirmar).toBe(false)
  })

  it('elegir un .xlsx → "seleccionado", expone el nombre y no llama a la API', async () => {
    const contador = contarVistaPrevia(() => HttpResponse.json(VISTA_PREVIA))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))

    expect(result.current.estado).toBe('seleccionado')
    expect(result.current.archivoSeleccionado).toBe('plantilla.xlsx')
    expect(result.current.puedeRevisar).toBe(true)
    expect(result.current.vistaPrevia).toBeNull()
    await esperar(20)
    expect(contador.llamadas).toBe(0)
  })

  it('.csv → error de extension, estado "inicial" y sin peticion', async () => {
    const contador = contarVistaPrevia(() => HttpResponse.json(VISTA_PREVIA))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('datos.csv', 'text/csv')))

    expect(result.current.errorArchivo).toBe(MENSAJE_EXTENSION)
    expect(result.current.estado).toBe('inicial')
    expect(result.current.archivoSeleccionado).toBeNull()
    act(() => result.current.revisar())
    await esperar(20)
    expect(contador.llamadas).toBe(0)
  })

  it('null → vuelve a "inicial" y olvida el archivo', () => {
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.seleccionarArchivo(null))

    expect(result.current.estado).toBe('inicial')
    expect(result.current.archivoSeleccionado).toBeNull()
  })

  it('revisar() sin archivo → no hace nada', async () => {
    const contador = contarVistaPrevia(() => HttpResponse.json(VISTA_PREVIA))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.revisar())

    expect(result.current.estado).toBe('inicial')
    await esperar(20)
    expect(contador.llamadas).toBe(0)
  })

  it('revisar() → "validando" → "vista-previa" con una sola peticion', async () => {
    const espera = pendiente()
    const contador = contarVistaPrevia(async () => {
      await espera.promesa
      return HttpResponse.json(VISTA_PREVIA)
    })
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.revisar())

    expect(result.current.estado).toBe('validando')
    expect(result.current.puedeRevisar).toBe(false)
    espera.liberar()
    await waitFor(() => expect(result.current.estado).toBe('vista-previa'))
    expect(result.current.vistaPrevia?.filasLeidas).toBe(5)
    expect(result.current.puedeConfirmar).toBe(true)
    expect(contador.llamadas).toBe(1)
  })

  it('revisar() repetido mientras valida → una sola peticion', async () => {
    const espera = pendiente()
    const contador = contarVistaPrevia(async () => {
      await espera.promesa
      return HttpResponse.json(VISTA_PREVIA)
    })
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => {
      result.current.revisar()
      result.current.revisar()
    })
    act(() => result.current.revisar())

    espera.liberar()
    await waitFor(() => expect(result.current.estado).toBe('vista-previa'))
    expect(contador.llamadas).toBe(1)
  })

  it('error de la API → mensaje y vuelve a "seleccionado"; se puede reintentar', async () => {
    let fallar = true
    const contador = contarVistaPrevia(() =>
      fallar
        ? HttpResponse.json(
            { error: { code: 'validation_error', message: MENSAJES_CARGA.sinRegistros } },
            { status: 400 },
          )
        : HttpResponse.json(VISTA_PREVIA),
    )
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.revisar())
    await waitFor(() => expect(result.current.error).toBe(MENSAJES_CARGA.sinRegistros))
    expect(result.current.estado).toBe('seleccionado')
    expect(result.current.archivoSeleccionado).toBe('plantilla.xlsx')
    expect(result.current.puedeRevisar).toBe(true)

    fallar = false
    act(() => result.current.revisar())
    await waitFor(() => expect(result.current.estado).toBe('vista-previa'))
    expect(result.current.error).toBeNull()
    expect(contador.llamadas).toBe(2)
  })

  it('413 → mensaje fijo de tamaño', async () => {
    contarVistaPrevia(() => new HttpResponse(null, { status: 413 }))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.revisar())

    await waitFor(() =>
      expect(result.current.error).toBe('El archivo supera el tamaño máximo permitido.'),
    )
    expect(result.current.estado).toBe('seleccionado')
  })

  it('elegir otro archivo mientras valida → aborta la peticion y limpia todo', async () => {
    const espera = pendiente()
    contarVistaPrevia(async () => {
      await espera.promesa
      return HttpResponse.json(VISTA_PREVIA)
    })
    const abort = vi.spyOn(AbortController.prototype, 'abort')
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('primera.xlsx')))
    act(() => result.current.revisar())
    expect(result.current.estado).toBe('validando')
    abort.mockClear()

    act(() => result.current.seleccionarArchivo(archivo('segunda.xlsx')))

    expect(abort).toHaveBeenCalled()
    expect(result.current.estado).toBe('seleccionado')
    expect(result.current.archivoSeleccionado).toBe('segunda.xlsx')
    expect(result.current.vistaPrevia).toBeNull()
    expect(result.current.resumen).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.errorArchivo).toBeNull()

    // La respuesta de la peticion anterior no se aplica.
    espera.liberar()
    await esperar(50)
    expect(result.current.estado).toBe('seleccionado')
    expect(result.current.vistaPrevia).toBeNull()
  })

  it('confirmar() sin doble envio y resumen al terminar', async () => {
    let envios = 0
    const espera = pendiente()
    server.use(
      http.post(CARGAS_PATH, async () => {
        envios += 1
        await espera.promesa
        return HttpResponse.json(
          {
            id: 1,
            fecha_carga: '2026-09-28T16:05:00Z',
            nombre_archivo: 'plantilla.xlsx',
            filas_leidas: 5,
            filas_guardadas: 5,
            filas_duplicadas: 0,
            socios_enlazados: 2,
            avisos_enlace: [],
          },
          { status: 201 },
        )
      }),
    )
    contarVistaPrevia(() => HttpResponse.json(VISTA_PREVIA))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.revisar())
    await waitFor(() => expect(result.current.puedeConfirmar).toBe(true))
    act(() => {
      result.current.confirmar()
      result.current.confirmar()
    })
    expect(result.current.estado).toBe('enviando')
    act(() => result.current.revisar())
    expect(result.current.estado).toBe('enviando')

    espera.liberar()
    await waitFor(() => expect(result.current.estado).toBe('confirmada'))
    expect(result.current.resumen?.filasGuardadas).toBe(5)
    expect(envios).toBe(1)
  })

  it('confirmar() con 422 → mensaje del servidor y vuelve a "vista-previa"', async () => {
    server.use(
      http.post(CARGAS_PATH, () =>
        HttpResponse.json(
          { error: { code: 'domain_rule_violated', message: MENSAJES_CARGA.sinFilasNuevas } },
          { status: 422 },
        ),
      ),
    )
    contarVistaPrevia(() => HttpResponse.json(VISTA_PREVIA))
    const { result } = renderHook(() => useCarga())

    act(() => result.current.seleccionarArchivo(archivo('plantilla.xlsx')))
    act(() => result.current.revisar())
    await waitFor(() => expect(result.current.puedeConfirmar).toBe(true))
    act(() => result.current.confirmar())

    await waitFor(() => expect(result.current.error).toBe(MENSAJES_CARGA.sinFilasNuevas))
    expect(result.current.estado).toBe('vista-previa')
    expect(result.current.vistaPrevia).not.toBeNull()
    expect(result.current.resumen).toBeNull()
  })
})
