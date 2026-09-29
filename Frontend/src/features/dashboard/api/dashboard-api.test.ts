import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import { getDashboard } from './dashboard-api'
import source from './dashboard-api.ts?raw'

function capturarQuery(): { search: string | null } {
  const captura: { search: string | null } = { search: null }
  server.use(
    http.get('*/api/v1/dashboard', ({ request }) => {
      captura.search = new URL(request.url).search
      return undefined
    }),
  )
  return captura
}

describe('dashboard-api (contra MSW)', () => {
  it('getDashboard("2026-09") envia ?mes=2026-09 y mapea embudo, porCampania y estadoModelo', async () => {
    const captura = capturarQuery()

    const dashboard = await getDashboard('2026-09')

    expect(captura.search).toBe('?mes=2026-09')
    expect(dashboard.mes).toBe('2026-09')
    expect(dashboard.embudo).toEqual({
      asignadas: expect.any(Number),
      contactadas: expect.any(Number),
      ofrecidas: expect.any(Number),
      aceptadas: expect.any(Number),
      renovaron: expect.any(Number),
    })
    expect(dashboard.estadoModelo).toEqual({
      version: 'v1',
      fechaEntrenamiento: new Date('2026-09-28T14:30:00Z'),
      ciclosEntrenamiento: 1843,
      proximaFechaReentrenamiento: '2026-10-28',
      ciclosNuevosEvaluables: 57,
    })
  })

  it('porCampania: tasaRenovacion string decimal o null; casosInsuficientes', async () => {
    const { porCampania } = await getDashboard('2026-09')

    const suficiente = porCampania.find((c) => !c.casosInsuficientes)
    const insuficiente = porCampania.find((c) => c.casosInsuficientes)
    expect(suficiente?.gestionesCerradas).toBeGreaterThanOrEqual(10)
    expect(typeof suficiente?.tasaRenovacion).toBe('string')
    expect(suficiente?.tasaRenovacion).toMatch(/^\d+(\.\d+)?$/)
    expect(insuficiente).toMatchObject({ tasaRenovacion: null, casosInsuficientes: true })
    expect(porCampania.some((c) => c.campaniaId === null)).toBe(true)
  })

  it('sin mes no envia el parametro', async () => {
    const captura = capturarQuery()

    await getDashboard()

    expect(captura.search).toBe('')
  })

  it('sin modelo vigente → estadoModelo null', async () => {
    server.use(
      http.get('*/api/v1/dashboard', () =>
        HttpResponse.json({
          mes: '2026-09',
          embudo: { asignadas: 0, contactadas: 0, ofrecidas: 0, aceptadas: 0, renovaron: 0 },
          por_campania: [],
          estado_modelo: null,
        }),
      ),
    )

    await expect(getDashboard('2026-09')).resolves.toMatchObject({
      porCampania: [],
      estadoModelo: null,
    })
  })

  it('501 simulado → ApiError 501', async () => {
    server.use(
      http.get('*/api/v1/dashboard', () =>
        HttpResponse.json(
          { error: { code: 'not_implemented', message: 'Esta funcion aun no esta disponible.' } },
          { status: 501 },
        ),
      ),
    )

    const error = await getDashboard('2026-09').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(501)
  })

  it('mes con formato invalido (400 del servidor) → ApiError 400 con su mensaje', async () => {
    server.use(
      http.get('*/api/v1/dashboard', () =>
        HttpResponse.json(
          { error: { code: 'bad_request', message: 'El mes no tiene el formato YYYY-MM.' } },
          { status: 400 },
        ),
      ),
    )

    const error = await getDashboard('2026-13').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 400, message: 'El mes no tiene el formato YYYY-MM.' })
  })

  it('tasaRenovacion conserva todas las cifras del decimal', async () => {
    server.use(
      http.get('*/api/v1/dashboard', () =>
        HttpResponse.json({
          mes: '2026-09',
          embudo: { asignadas: 1, contactadas: 1, ofrecidas: 1, aceptadas: 1, renovaron: 1 },
          por_campania: [
            {
              campania_id: 3,
              nombre: 'Renovacion anticipada',
              gestiones: 12,
              contactados: 12,
              renovaciones: 1,
              gestiones_cerradas: 12,
              tasa_renovacion: '0.08333333333333333333',
              casos_insuficientes: false,
            },
          ],
          estado_modelo: null,
        }),
      ),
    )

    const { porCampania } = await getDashboard('2026-09')
    expect(porCampania[0]?.tasaRenovacion).toBe('0.08333333333333333333')
  })

  it('no usa fetch directo ni convierte decimales a number', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).not.toMatch(/parseFloat|Number\(/)
  })
})
