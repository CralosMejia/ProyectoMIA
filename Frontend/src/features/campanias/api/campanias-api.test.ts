import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import type { CampaniaEntrada, PlanCampania } from '../types'
import {
  activarCampania,
  crearCampania,
  editarCampania,
  inactivarCampania,
  listarCampanias,
} from './campanias-api'
import { MENSAJE_NO_EXISTE, reiniciarCampaniasSimuladas } from './campanias-api.handlers'
import source from './campanias-api.ts?raw'

const ENTRADA: CampaniaEntrada = {
  nombre: 'Clase de prueba',
  descripcion: 'Una clase gratis al renovar.',
  nivelesRiesgo: ['ALTO'],
  planes: ['MENSUAL', 'ANUAL'],
  prioridad: 3,
}

describe('campanias-api (contra MSW)', () => {
  beforeEach(() => {
    reiniciarCampaniasSimuladas()
  })

  it('listarCampanias → 3 campañas de ejemplo en camelCase', async () => {
    const campanias = await listarCampanias()

    expect(campanias).toHaveLength(3)
    expect(campanias.every((c) => c.esEjemplo)).toBe(true)
    expect(campanias[0]).toEqual({
      id: expect.any(Number),
      nombre: expect.any(String),
      descripcion: expect.anything(),
      activa: true,
      nivelesRiesgo: expect.any(Array),
      planes: expect.any(Array),
      prioridad: 1,
      esEjemplo: true,
    })
  })

  it('crearCampania envia snake_case y devuelve la creada (201)', async () => {
    let body: unknown = null
    let status = 0
    server.use(
      http.post('*/api/v1/campanias', async ({ request }) => {
        body = await request.clone().json()
        return undefined
      }),
    )
    server.events.on('response:mocked', ({ response }) => {
      status = response.status
    })

    const creada = await crearCampania(ENTRADA)
    server.events.removeAllListeners()

    expect(body).toEqual({
      nombre: 'Clase de prueba',
      descripcion: 'Una clase gratis al renovar.',
      niveles_riesgo: ['ALTO'],
      planes: ['MENSUAL', 'ANUAL'],
      prioridad: 3,
    })
    expect(status).toBe(201)
    expect(creada).toMatchObject({ ...ENTRADA, activa: true, esEjemplo: false })
    expect(creada.id).toEqual(expect.any(Number))
  })

  it('crearCampania sin descripcion → envia null', async () => {
    let body: Record<string, unknown> = {}
    server.use(
      http.post('*/api/v1/campanias', async ({ request }) => {
        body = (await request.clone().json()) as Record<string, unknown>
        return undefined
      }),
    )

    await crearCampania({ ...ENTRADA, descripcion: undefined })

    expect(body.descripcion).toBeNull()
  })

  it('editarCampania hace PUT /campanias/{id} y devuelve la editada', async () => {
    let method = ''
    server.use(
      http.put('*/api/v1/campanias/3', ({ request }) => {
        method = request.method
        return undefined
      }),
    )

    const editada = await editarCampania(3, ENTRADA)

    expect(method).toBe('PUT')
    expect(editada).toMatchObject({ id: 3, nombre: 'Clase de prueba', prioridad: 3 })
  })

  it('inactivarCampania hace POST /campanias/{id}/inactivar y devuelve activa false', async () => {
    let method = ''
    server.use(
      http.post('*/api/v1/campanias/3/inactivar', ({ request }) => {
        method = request.method
        return undefined
      }),
    )

    const campania = await inactivarCampania(3)

    expect(method).toBe('POST')
    expect(campania).toMatchObject({ id: 3, activa: false })
  })

  it('activarCampania hace POST /campanias/{id}/activar sin cuerpo y devuelve activa true', async () => {
    await inactivarCampania(3)
    let method = ''
    let cuerpo = 'sin leer'
    server.use(
      http.post('*/api/v1/campanias/3/activar', async ({ request }) => {
        method = request.method
        cuerpo = await request.clone().text()
        return undefined
      }),
    )

    const campania = await activarCampania(3)

    expect(method).toBe('POST')
    expect(['', 'null']).toContain(cuerpo)
    expect(campania).toMatchObject({ id: 3, activa: true, esEjemplo: true })
    expect((await listarCampanias()).find((c) => c.id === 3)?.activa).toBe(true)
  })

  it('activarCampania sobre una ya activa → 200 sin cambios (idempotente)', async () => {
    const campania = await activarCampania(1)

    expect(campania).toMatchObject({ id: 1, activa: true, esEjemplo: true })
  })

  it('activarCampania de una inexistente → ApiError 404 con el mensaje del servidor', async () => {
    const error = await activarCampania(999).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
    expect((error as ApiError).message).toBe(MENSAJE_NO_EXISTE)
  })

  it('activarCampania propaga la señal de cancelación', async () => {
    const controller = new AbortController()
    controller.abort()

    await expect(activarCampania(3, controller.signal)).rejects.toBeDefined()
  })

  it('400 simulado → ApiError 400 con el mensaje del servidor', async () => {
    server.use(
      http.post('*/api/v1/campanias', () =>
        HttpResponse.json(
          { error: { code: 'bad_request', message: 'El plan DIARIO no admite campanas.' } },
          { status: 400 },
        ),
      ),
    )

    const error = await crearCampania(ENTRADA).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(400)
    expect((error as ApiError).message).toBe('El plan DIARIO no admite campanas.')
  })

  it('los tipos no admiten "DIARIO" en planes', () => {
    // @ts-expect-error DIARIO no es un plan de campaña (lo comprueba `tsc` en el build).
    const plan: PlanCampania = 'DIARIO'
    expect(plan).toBe('DIARIO')
  })

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).toMatch(/core\/http\/http-client/)
  })
})
