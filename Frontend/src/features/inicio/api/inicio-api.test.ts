import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import { getAlertas, getEstadoSistema, obtenerAlertas } from './inicio-api'
import source from './inicio-api.ts?raw'

const NOT_IMPLEMENTED = {
  error: { code: 'not_implemented', message: 'Esta funcion aun no esta disponible.' },
}

describe('inicio-api (contra MSW)', () => {
  it('getEstadoSistema → mapea snake_case a camelCase con fechas Date', async () => {
    const estado = await getEstadoSistema()

    expect(estado).toEqual({
      estado: 'LISTO',
      migracionHistorica: 'COMPLETADA',
      modeloVigente: {
        version: 'v1',
        fechaEntrenamiento: new Date('2026-09-28T14:30:00Z'),
        ciclosEntrenamiento: 1843,
      },
      ultimaCargaEn: new Date('2026-09-27T16:05:00Z'),
      proximaFechaReentrenamiento: '2026-10-28',
      datosMesCargados: true,
    })
    expect(estado.modeloVigente?.fechaEntrenamiento).toBeInstanceOf(Date)
  })

  it('getEstadoSistema sin modelo ni cargas → nulos', async () => {
    server.use(
      http.get('*/api/v1/sistema/estado', () =>
        HttpResponse.json({
          estado: 'FALTAN_DATOS_HISTORICOS',
          migracion_historica: 'PENDIENTE',
          modelo_vigente: null,
          ultima_carga_en: null,
          proxima_fecha_reentrenamiento: null,
        }),
      ),
    )

    await expect(getEstadoSistema()).resolves.toEqual({
      estado: 'FALTAN_DATOS_HISTORICOS',
      migracionHistorica: 'PENDIENTE',
      modeloVigente: null,
      ultimaCargaEn: null,
      proximaFechaReentrenamiento: null,
      datosMesCargados: null,
    })
  })

  it('getAlertas → { vencidas, hoy, proximos7Dias }', async () => {
    await expect(getAlertas()).resolves.toEqual({ vencidas: 2, hoy: 3, proximos7Dias: 5 })
  })

  it('501 → ApiError con status 501 y el mensaje del servidor', async () => {
    server.use(
      http.get('*/api/v1/sistema/estado', () =>
        HttpResponse.json(NOT_IMPLEMENTED, { status: 501 }),
      ),
      http.get('*/api/v1/alertas', () => HttpResponse.json(NOT_IMPLEMENTED, { status: 501 })),
    )

    for (const call of [getEstadoSistema, getAlertas]) {
      const error = await call().catch((e: unknown) => e)
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).status).toBe(501)
      expect((error as ApiError).message).toBe('Esta funcion aun no esta disponible.')
    }
  })

  it('senal abortada → AbortError (no ApiError)', async () => {
    const controller = new AbortController()
    controller.abort()

    const error = await getEstadoSistema(controller.signal).catch((e: unknown) => e)
    expect(error).not.toBeInstanceOf(ApiError)
    expect((error as Error).name).toBe('AbortError')
  })

  it('obtenerAlertas: {vencidas:2,hoy:1,proximos_7_dias:3} → {vencidas:2, hoy:1, proximos7Dias:3}', async () => {
    server.use(
      http.get('*/api/v1/alertas', () =>
        HttpResponse.json({ vencidas: 2, hoy: 1, proximos_7_dias: 3 }),
      ),
    )

    await expect(obtenerAlertas()).resolves.toEqual({ vencidas: 2, hoy: 1, proximos7Dias: 3 })
  })

  it('obtenerAlertas: error del servidor → ApiError con su status y mensaje', async () => {
    server.use(
      http.get('*/api/v1/alertas', () =>
        HttpResponse.json(
          { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
          { status: 500 },
        ),
      ),
    )

    const error = await obtenerAlertas().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 500, message: 'Error interno del servidor.' })
  })

  it('obtenerAlertas propaga la senal: abortar cancela la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get('*/api/v1/alertas', ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )
    const controller = new AbortController()

    const promesa = obtenerAlertas(controller.signal).catch((e: unknown) => e)
    await vi.waitFor(() => expect(senal).not.toBeNull())
    controller.abort()

    const error = await promesa
    expect((error as Error).name).toBe('AbortError')
    expect((senal as AbortSignal | null)?.aborted).toBe(true)
  })

  it.each([
    [true, true],
    [false, false],
    [null, null],
  ])('datos_mes_cargados %s → datosMesCargados %s', async (crudo, esperado) => {
    server.use(
      http.get('*/api/v1/sistema/estado', () =>
        HttpResponse.json({
          estado: crudo === null ? 'INICIALIZANDO' : 'LISTO',
          migracion_historica: crudo === null ? 'EN_CURSO' : 'COMPLETADA',
          modelo_vigente: null,
          ultima_carga_en: null,
          proxima_fecha_reentrenamiento: null,
          datos_mes_cargados: crudo,
        }),
      ),
    )

    const estado = await getEstadoSistema()
    expect(estado.datosMesCargados).toBe(esperado)
  })

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).toMatch(/core\/http\/http-client/)
  })
})
