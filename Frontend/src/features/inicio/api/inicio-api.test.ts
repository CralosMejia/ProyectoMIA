import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import { getAlertas, getEstadoSistema } from './inicio-api'
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

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).toMatch(/core\/http\/http-client/)
  })
})
