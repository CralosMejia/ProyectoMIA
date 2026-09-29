import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import {
  crearGestion,
  descargarExcel,
  generarLista,
  getCampaniasSugeridas,
  getGestion,
  getGestiones,
  getLista,
  getUltimaLista,
  registrarResultado,
} from './lista-api'
import source from './lista-api.ts?raw'

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
const DECIMAL = /^\d+(\.\d+)?$/

function errorBody(code: string, message: string) {
  return { error: { code, message } }
}

describe('lista-api (contra MSW)', () => {
  it('generarLista envia snake_case con fecha_referencia null', async () => {
    let body: string | null = null
    server.use(
      http.post('*/api/v1/listas', async ({ request }) => {
        body = await request.text()
        return HttpResponse.json(
          {
            id: 1,
            modelo_version: 'v1',
            fecha_generacion: '2026-09-28T15:00:00Z',
            horizonte_dias: 30,
            top_k: 25,
            umbral_alto: '0.70000000',
            umbral_medio: '0.40000000',
            advertencia_datos_antiguos: false,
            items: [],
          },
          { status: 201 },
        )
      }),
    )

    await generarLista({ horizonteDias: 30, topK: 25 })

    expect(body).toBe('{"fecha_referencia":null,"horizonte_dias":30,"top_k":25}')
  })

  it('generarLista → items con score string decimal exacto y nivelRiesgo tipado', async () => {
    const lista = await generarLista({ horizonteDias: 30, topK: 25 })

    expect(lista.items.length).toBeGreaterThanOrEqual(30)
    expect(lista.fechaGeneracion).toBeInstanceOf(Date)
    expect(lista.umbralAlto).toBe('0.70000000')
    expect(lista.umbralMedio).toBe('0.40000000')
    for (const item of lista.items) {
      expect(typeof item.score).toBe('string')
      expect(item.score).toMatch(DECIMAL)
      expect(['ALTO', 'MEDIO', 'BAJO']).toContain(item.nivelRiesgo)
    }
    expect(new Set(lista.items.map((i) => i.nivelRiesgo))).toEqual(
      new Set(['ALTO', 'MEDIO', 'BAJO']),
    )
    const primero = lista.items[0]
    expect(primero).toMatchObject({ prioridad: 1, score: '0.95000000', dentroTopK: true })
    expect(lista.items.filter((i) => i.dentroTopK)).toHaveLength(25)
  })

  it('el score no pierde precision (no pasa por number)', async () => {
    server.use(
      http.get('*/api/v1/listas/7', () =>
        HttpResponse.json({
          id: 7,
          modelo_version: 'v1',
          fecha_generacion: '2026-09-28T15:00:00Z',
          horizonte_dias: 30,
          top_k: 25,
          umbral_alto: '0.70000000',
          umbral_medio: '0.40000000',
          advertencia_datos_antiguos: true,
          items: [
            {
              prediccion_id: 1501,
              prioridad: 1,
              socio_nombre: 'Socio Ficticio',
              celular: null,
              correo: null,
              plan: 'MENSUAL',
              fecha_vencimiento: '2026-10-05',
              dias_para_vencer: 7,
              score: '0.12345678901234567890',
              nivel_riesgo: 'BAJO',
              factores_principales: ['Pocas renovaciones previas'],
              dentro_top_k: true,
              gestion_estado: 'PENDIENTE',
              campania_asignada: 'Renovacion anticipada',
            },
          ],
        }),
      ),
    )

    const lista = await getLista(7)

    expect(lista.advertenciaDatosAntiguos).toBe(true)
    expect(lista.items[0]).toEqual({
      prediccionId: 1501,
      prioridad: 1,
      socioNombre: 'Socio Ficticio',
      celular: null,
      correo: null,
      plan: 'MENSUAL',
      fechaVencimiento: '2026-10-05',
      diasParaVencer: 7,
      score: '0.12345678901234567890',
      nivelRiesgo: 'BAJO',
      factoresPrincipales: ['Pocas renovaciones previas'],
      dentroTopK: true,
      gestionEstado: 'PENDIENTE',
      campaniaAsignada: 'Renovacion anticipada',
    })
  })

  it('getUltimaLista → la lista; con 404 → null', async () => {
    await expect(getUltimaLista()).resolves.toMatchObject({ id: 42 })

    server.use(
      http.get('*/api/v1/listas/ultima', () =>
        HttpResponse.json(errorBody('not_found', 'Aun no se ha generado ninguna lista.'), {
          status: 404,
        }),
      ),
    )
    await expect(getUltimaLista()).resolves.toBeNull()
  })

  it('getUltimaLista con otro error → ApiError', async () => {
    server.use(
      http.get('*/api/v1/listas/ultima', () =>
        HttpResponse.json(errorBody('not_implemented', 'No disponible.'), { status: 501 }),
      ),
    )
    const error = await getUltimaLista().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(501)
  })

  it('getLista con 404 → ApiError 404', async () => {
    const error = await getLista(999).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('descargarExcel → Blob con tipo xlsx', async () => {
    const blob = await descargarExcel(42)

    expect(blob.type).toBe(XLSX)
    expect(blob.size).toBeGreaterThan(0)
  })

  it('getCampaniasSugeridas → campañas de la prediccion', async () => {
    const campanias = await getCampaniasSugeridas(1501)

    expect(campanias.length).toBeGreaterThan(0)
    expect(campanias[0]).toEqual({
      id: expect.any(Number),
      nombre: expect.any(String),
      descripcion: expect.anything(),
      prioridad: 1,
    })
  })

  it('crearGestion envia snake_case y devuelve la gestion creada', async () => {
    let body: unknown = null
    // Sin retorno el handler cae al handler por defecto del feature (solo captura el cuerpo).
    server.use(
      http.post('*/api/v1/gestiones', async ({ request }) => {
        body = await request.clone().json()
        return undefined
      }),
    )

    const gestion = await crearGestion({
      prediccionId: 1501,
      campaniaId: 3,
      fechaSeguimiento: '2026-10-25',
      responsable: 'Andrea',
    })

    expect(body).toEqual({
      prediccion_id: 1501,
      campania_id: 3,
      fecha_seguimiento: '2026-10-25',
      responsable: 'Andrea',
    })
    expect(gestion).toMatchObject({
      prediccionId: 1501,
      campaniaId: 3,
      estado: 'PENDIENTE',
      fechaSeguimiento: '2026-10-25',
      responsable: 'Andrea',
    })
    expect(typeof gestion.score).toBe('string')
    expect(gestion.fechaAsignacion).toBeInstanceOf(Date)
    expect(gestion.fechaCierre).toBeNull()
  })

  it('crearGestion sin campaña ni responsable → envia null', async () => {
    let body: unknown = null
    server.use(
      http.post('*/api/v1/gestiones', async ({ request }) => {
        body = await request.clone().json()
        return undefined
      }),
    )

    await crearGestion({ prediccionId: 1501, fechaSeguimiento: '2026-10-25' })

    expect(body).toEqual({
      prediccion_id: 1501,
      campania_id: null,
      fecha_seguimiento: '2026-10-25',
      responsable: null,
    })
  })

  it('crearGestion con 409 → ApiError 409', async () => {
    server.use(
      http.post('*/api/v1/gestiones', () =>
        HttpResponse.json(errorBody('conflict', 'El ciclo de membresia ya tiene una gestion.'), {
          status: 409,
        }),
      ),
    )

    const error = await crearGestion({ prediccionId: 1501, fechaSeguimiento: '2026-10-25' }).catch(
      (e: unknown) => e,
    )
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(409)
    expect((error as ApiError).message).toBe('El ciclo de membresia ya tiene una gestion.')
  })

  it('registrarResultado hace PUT /gestiones/{id}/resultado con snake_case', async () => {
    let body: unknown = null
    let method = ''
    server.use(
      http.put('*/api/v1/gestiones/9/resultado', async ({ request }) => {
        method = request.method
        body = await request.clone().json()
        return undefined
      }),
    )

    const gestion = await registrarResultado(9, {
      contactado: true,
      campaniaOfrecida: 'SI',
      campaniaAceptada: 'SI',
      renovoDeclarado: 'SI',
      fechaContacto: '2026-10-20',
      observaciones: 'Renueva.',
    })

    expect(method).toBe('PUT')
    expect(body).toEqual({
      contactado: true,
      campania_ofrecida: 'SI',
      campania_aceptada: 'SI',
      renovo_declarado: 'SI',
      fecha_contacto: '2026-10-20',
      observaciones: 'Renueva.',
      responsable: null,
      fecha_seguimiento: null,
    })
    expect(gestion).toMatchObject({ id: 9, renovoDeclarado: 'SI', estado: 'CERRADA' })
    expect(gestion.fechaCierre).toBeInstanceOf(Date)
  })

  it('getGestion → la gestion por id', async () => {
    await expect(getGestion(9)).resolves.toMatchObject({ id: 9, socioNombre: expect.any(String) })
  })

  it('getGestiones("vencidas") envia ?filtro=vencidas', async () => {
    let filtro: string | null = null
    server.use(
      http.get('*/api/v1/gestiones', ({ request }) => {
        filtro = new URL(request.url).searchParams.get('filtro')
        return undefined
      }),
    )

    const gestiones = await getGestiones('vencidas')

    expect(filtro).toBe('vencidas')
    expect(gestiones.length).toBeGreaterThan(0)
    expect(gestiones[0]).toMatchObject({
      id: expect.any(Number),
      socioNombre: expect.any(String),
      fechaSeguimiento: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      estado: 'PENDIENTE',
    })
  })

  it.each(['hoy', 'proximas'] as const)('getGestiones("%s") envia ?filtro=%s', async (valor) => {
    let filtro: string | null = null
    server.use(
      http.get('*/api/v1/gestiones', ({ request }) => {
        filtro = new URL(request.url).searchParams.get('filtro')
        return undefined
      }),
    )

    const gestiones = await getGestiones(valor)

    expect(filtro).toBe(valor)
    expect(gestiones.every((g) => g.estado === 'PENDIENTE')).toBe(true)
  })

  it('getGestiones con filtro rechazado (400) → ApiError 400', async () => {
    server.use(
      http.get('*/api/v1/gestiones', () =>
        HttpResponse.json(errorBody('bad_request', 'Filtro ausente o no permitido.'), {
          status: 400,
        }),
      ),
    )

    const error = await getGestiones('vencidas').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 400, message: 'Filtro ausente o no permitido.' })
  })

  it('descargarExcel de una lista inexistente → ApiError 404', async () => {
    const error = await descargarExcel(999).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('datos simulados ficticios: sin cedulas ni correos reales', async () => {
    const lista = await generarLista({ horizonteDias: 30, topK: 25 })
    const gestiones = await getGestiones('proximas')
    const json = JSON.stringify([lista, gestiones])

    expect(json).not.toMatch(/c[eé]dula|identificacion|documento/i)
    for (const item of lista.items) {
      expect(Object.keys(item)).not.toContain('cedula')
      expect(item.correo ?? '').toMatch(/@ejemplo\.test$/)
    }
  })

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).not.toMatch(/parseFloat|Number\(/)
  })
})
