import { http, HttpResponse } from 'msw'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import { getDashboard, obtenerDashboard } from './dashboard-api'
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

  it('obtenerDashboard("2026-09") → GET /dashboard?mes=2026-09; sin mes → sin query', async () => {
    const captura = capturarQuery()

    await obtenerDashboard('2026-09')
    expect(captura.search).toBe('?mes=2026-09')

    await obtenerDashboard()
    expect(captura.search).toBe('')
  })

  it('obtenerDashboard: tasa_renovacion sigue como string y "Sin campaña" al final', async () => {
    const { porCampania } = await obtenerDashboard('2026-09')

    expect(porCampania[0]).toMatchObject({ tasaRenovacion: '0.40000000', gestionesCerradas: 10 })
    expect(porCampania.at(-1)).toMatchObject({
      campaniaId: null,
      nombre: 'Sin campaña',
      tasaRenovacion: null,
      casosInsuficientes: true,
    })
  })

  it('obtenerDashboard con mes invalido en el mock → ApiError 400', async () => {
    const error = await obtenerDashboard('2026-13').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(400)
  })

  it('obtenerDashboard propaga la senal: abortar cancela la peticion', async () => {
    let senal: AbortSignal | null = null
    server.use(
      http.get('*/api/v1/dashboard', ({ request }) => {
        senal = request.signal
        return new Promise<Response>(() => {})
      }),
    )
    const controller = new AbortController()

    const promesa = obtenerDashboard('2026-09', controller.signal).catch((e: unknown) => e)
    await vi.waitFor(() => expect(senal).not.toBeNull())
    controller.abort()

    expect(((await promesa) as Error).name).toBe('AbortError')
    expect((senal as AbortSignal | null)?.aborted).toBe(true)
  })

  it('R-018: piloto del mes (parcial) mapeado a camelCase con los decimales como string', async () => {
    const { piloto } = await obtenerDashboard('2026-09')

    expect(piloto).toEqual({
      estado: 'PARCIAL',
      lista: { id: 12, nombre: 'Ejemplo: Lista septiembre', fechaGeneracion: '2026-09-01' },
      corteVerificacion: '2026-10-28',
      nTop: 25,
      sinDato: 0,
      precisionTop25: {
        valor: '0.60000000',
        numerador: 12,
        denominador: 20,
        n: 25,
        pendientes: 5,
        estado: 'PARCIAL',
      },
      contactadosAntesVencimiento: {
        valor: '0.72000000',
        numerador: 18,
        denominador: 25,
        n: 25,
        pendientes: 0,
        estado: 'COMPLETO',
      },
      diasAnticipacion: { valor: '4.5', n: 19, estado: 'COMPLETO' },
      tasaRenovacionContactados: {
        valor: '0.41176471',
        numerador: 7,
        denominador: 17,
        n: 21,
        pendientes: 4,
        estado: 'PARCIAL',
      },
      montoRetenido: {
        total: '312.50',
        renovaciones: 7,
        renovacionesSinMonto: 1,
        n: 17,
        pendientes: 4,
        estado: 'PARCIAL',
      },
    })
  })

  it('R-018: el mock devuelve un mes completo, uno pendiente y uno sin datos', async () => {
    const completo = (await obtenerDashboard('2026-08')).piloto
    expect(completo.estado).toBe('COMPLETO')
    expect(completo.precisionTop25).toMatchObject({ pendientes: 0, estado: 'COMPLETO' })

    const pendiente = (await obtenerDashboard('2026-10')).piloto
    expect(pendiente.estado).toBe('PENDIENTE')
    expect(pendiente.precisionTop25).toMatchObject({ valor: null, estado: 'PENDIENTE' })
    expect(pendiente.montoRetenido).toMatchObject({ total: null, estado: 'PENDIENTE' })

    const sinDatos = (await obtenerDashboard('2026-12')).piloto
    expect(sinDatos).toMatchObject({
      estado: 'SIN_DATOS',
      lista: null,
      corteVerificacion: null,
      nTop: 0,
      sinDato: 0,
      precisionTop25: { valor: null, n: 0, estado: 'SIN_DATOS' },
      diasAnticipacion: { valor: null, n: 0, estado: 'SIN_DATOS' },
      montoRetenido: { total: null, renovaciones: 0, renovacionesSinMonto: 0, estado: 'SIN_DATOS' },
    })
  })

  it('R-018: los decimales del piloto conservan todas sus cifras', async () => {
    const base = await obtenerDashboard('2026-09')
    server.use(
      http.get('*/api/v1/dashboard', () =>
        HttpResponse.json({
          mes: '2026-09',
          embudo: { asignadas: 0, contactadas: 0, ofrecidas: 0, aceptadas: 0, renovaron: 0 },
          por_campania: [],
          estado_modelo: null,
          piloto: {
            estado: 'COMPLETO',
            lista: { id: 1, nombre: 'L', fecha_generacion: '2026-09-01' },
            corte_verificacion: '2026-10-28',
            n_top: 3,
            sin_dato: 0,
            precision_top25: { valor: '0.33333333', numerador: 1, denominador: 3, n: 3, pendientes: 0, estado: 'COMPLETO' },
            contactados_antes_vencimiento: { valor: '0.66666667', numerador: 2, denominador: 3, n: 3, pendientes: 0, estado: 'COMPLETO' },
            dias_anticipacion: { valor: '-1.5', n: 2, estado: 'COMPLETO' },
            tasa_renovacion_contactados: { valor: '0.50000000', numerador: 1, denominador: 2, n: 2, pendientes: 0, estado: 'COMPLETO' },
            monto_retenido: { total: '1234567.89', renovaciones: 1, renovaciones_sin_monto: 0, n: 2, pendientes: 0, estado: 'COMPLETO' },
          },
        }),
      ),
    )

    const { piloto } = await obtenerDashboard('2026-09')
    expect(base.piloto.estado).toBe('PARCIAL')
    expect(piloto.contactadosAntesVencimiento.valor).toBe('0.66666667')
    expect(piloto.diasAnticipacion.valor).toBe('-1.5')
    expect(piloto.montoRetenido.total).toBe('1234567.89')
  })

  it('R-018: una respuesta sin "piloto" se trata como mes sin datos', async () => {
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

    const { piloto } = await obtenerDashboard('2026-09')
    expect(piloto).toMatchObject({ estado: 'SIN_DATOS', lista: null, nTop: 0 })
    expect(piloto.tasaRenovacionContactados.estado).toBe('SIN_DATOS')
  })

  it('no usa fetch directo ni convierte decimales a number', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).not.toMatch(/parseFloat|Number\(/)
  })
})
