import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import {
  crearGestion,
  descargarExcel,
  FechaListaPasadaError,
  generarLista,
  MENSAJE_FECHA_PASADA,
  getCampaniasSugeridas,
  getGestion,
  getGestiones,
  listarListas,
  obtenerLista,
  obtenerUltima,
  registrarResultado,
  SistemaNoListoError,
} from './lista-api'
import { escenariosLista } from './lista-api.handlers'
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
            fecha_generacion: '2026-09-28',
            creada_en: '2026-09-28T15:00:00Z',
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
    expect(lista.fechaGeneracion).toBe('2026-09-28')
    expect(lista.creadaEn).toEqual(new Date('2026-09-28T15:00:00Z'))
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
          fecha_generacion: '2026-08-31',
          creada_en: '2026-08-31T14:00:00Z',
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
              cedula: '0912345678',
              plan: 'MENSUAL',
              fecha_vencimiento: '2026-10-05',
              dias_para_vencer: 7,
              monto_cobrado: '39.50',
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

    const lista = await obtenerLista(7)

    expect(lista.advertenciaDatosAntiguos).toBe(true)
    expect(lista.items[0]).toEqual({
      prediccionId: 1501,
      prioridad: 1,
      socioNombre: 'Socio Ficticio',
      celular: null,
      cedula: '0912345678',
      plan: 'MENSUAL',
      fechaVencimiento: '2026-10-05',
      diasParaVencer: 7,
      montoCobrado: '39.50',
      score: '0.12345678901234567890',
      nivelRiesgo: 'BAJO',
      factoresPrincipales: ['Pocas renovaciones previas'],
      dentroTopK: true,
      gestionEstado: 'PENDIENTE',
      campaniaAsignada: 'Renovacion anticipada',
    })
  })

  it('la cedula se mapea como texto (cero inicial) y null se conserva; no hay correo', async () => {
    const item = (cedula: string | null) => ({
      prediccion_id: 1,
      prioridad: 1,
      socio_nombre: 'Socio Ficticio',
      celular: null,
      cedula,
      plan: 'MENSUAL',
      fecha_vencimiento: '2026-10-05',
      dias_para_vencer: 7,
      monto_cobrado: null,
      score: '0.50000000',
      nivel_riesgo: 'MEDIO',
      factores_principales: [],
      dentro_top_k: true,
      gestion_estado: null,
      campania_asignada: null,
    })
    server.use(
      http.get('*/api/v1/listas/8', () =>
        HttpResponse.json({
          id: 8,
          modelo_version: 'v1',
          fecha_generacion: '2026-08-31',
          creada_en: '2026-08-31T14:00:00Z',
          horizonte_dias: 120,
          top_k: 25,
          umbral_alto: '0.70000000',
          umbral_medio: '0.40000000',
          advertencia_datos_antiguos: false,
          items: [item('0012345678'), { ...item(null), prediccion_id: 2, prioridad: 2 }],
        }),
      ),
    )

    const lista = await obtenerLista(8)

    expect(lista.items.map((i) => i.cedula)).toEqual(['0012345678', null])
    for (const i of lista.items) expect(Object.keys(i)).not.toContain('correo')
  })

  it('generarLista con 422 → FechaListaPasadaError (ApiError 422) con el mensaje del servidor', async () => {
    server.use(
      http.post('*/api/v1/listas', () =>
        HttpResponse.json(errorBody('domain_rule_violated', 'Mensaje del servidor.'), {
          status: 422,
        }),
      ),
    )

    const error = await generarLista({
      fechaReferencia: '2026-09-28',
      horizonteDias: 30,
      topK: 25,
    }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(FechaListaPasadaError)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, message: 'Mensaje del servidor.' })
  })

  it('generarLista con 422 sin mensaje → mensaje amigable por defecto', async () => {
    server.use(http.post('*/api/v1/listas', () => new HttpResponse(null, { status: 422 })))

    const error = await generarLista({ horizonteDias: 30, topK: 25 }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(FechaListaPasadaError)
    expect((error as ApiError).message).toBe(MENSAJE_FECHA_PASADA)
    expect(MENSAJE_FECHA_PASADA).toBe('La fecha de la lista debe ser hoy o posterior.')
  })

  it('handlers: fecha anterior a hoy → 422 con el mensaje real; hoy → 201 con esa fecha', async () => {
    const hoy = new Date()
    const iso = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const ayer = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1)

    const error = await generarLista({ fechaReferencia: iso(ayer), horizonteDias: 30, topK: 25 }).catch(
      (e: unknown) => e,
    )
    expect(error).toBeInstanceOf(FechaListaPasadaError)
    expect((error as ApiError).message).toBe('La fecha de la lista debe ser hoy o posterior.')

    const lista = await generarLista({ fechaReferencia: iso(hoy), horizonteDias: 31, topK: 25 })
    expect(lista.fechaGeneracion).toBe(iso(hoy))
    expect(lista.horizonteDias).toBe(31)

    server.use(escenariosLista.fechaPasada)
    await expect(generarLista({ horizonteDias: 30, topK: 25 })).rejects.toBeInstanceOf(
      FechaListaPasadaError,
    )
  })

  it('obtenerUltima → la lista; con 404 → null', async () => {
    await expect(obtenerUltima()).resolves.toMatchObject({ id: 42 })

    server.use(...escenariosLista.sinListas)
    await expect(obtenerUltima()).resolves.toBeNull()
  })

  it('listarListas → dos resumenes en camelCase, de la mas reciente a la mas antigua', async () => {
    const listas = await listarListas()

    expect(listas).toEqual([
      {
        id: 42,
        fechaGeneracion: '2026-09-28',
        creadaEn: new Date('2026-09-28T15:00:00Z'),
        modeloVersion: 'v1',
        horizonteDias: 30,
        topK: 25,
        totalItems: 32,
      },
      {
        id: 41,
        fechaGeneracion: '2026-08-31',
        creadaEn: new Date('2026-08-31T14:00:00Z'),
        modeloVersion: 'v1',
        horizonteDias: 30,
        topK: 10,
        totalItems: 12,
      },
    ])
  })

  it('listarListas sin listas → []', async () => {
    server.use(...escenariosLista.sinListas)
    await expect(listarListas()).resolves.toEqual([])
  })

  it('handlers: la lista anterior trae advertenciaDatosAntiguos y monto como string o null', async () => {
    const anterior = await obtenerLista(41)
    const reciente = await obtenerLista(42)

    expect(anterior.advertenciaDatosAntiguos).toBe(true)
    expect(reciente.advertenciaDatosAntiguos).toBe(false)
    expect(anterior.items[0]?.socioNombre).not.toBe(reciente.items[0]?.socioNombre)
    for (const item of reciente.items) {
      if (item.montoCobrado !== null) expect(item.montoCobrado).toMatch(DECIMAL)
    }
    expect(reciente.items.some((i) => i.montoCobrado === null)).toBe(true)
    expect(reciente.items.some((i) => i.factoresPrincipales.length === 0)).toBe(true)
  })

  it('generarLista con 409 → SistemaNoListoError (ApiError 409) con el mensaje del servidor', async () => {
    server.use(escenariosLista.sistemaInicializando)

    const error = await generarLista({ horizonteDias: 30, topK: 25 }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(SistemaNoListoError)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 409,
      message: 'El sistema se esta inicializando; intente de nuevo en unos minutos.',
    })
  })

  it('generarLista con 409 sin mensaje → mensaje por defecto', async () => {
    server.use(http.post('*/api/v1/listas', () => new HttpResponse(null, { status: 409 })))

    const error = await generarLista({ horizonteDias: 30, topK: 25 }).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(SistemaNoListoError)
    expect((error as ApiError).message).toBe(
      'El sistema se esta inicializando; intente de nuevo en unos minutos.',
    )
  })

  it('obtenerUltima con otro error → ApiError', async () => {
    server.use(
      http.get('*/api/v1/listas/ultima', () =>
        HttpResponse.json(errorBody('not_implemented', 'No disponible.'), { status: 501 }),
      ),
    )
    const error = await obtenerUltima().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(501)
  })

  it('getLista con 404 → ApiError 404', async () => {
    const error = await obtenerLista(999).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(404)
  })

  it('descargarExcel → GET /api/v1/listas/{id}/excel y Blob con tipo xlsx', async () => {
    let url = ''
    server.use(
      http.get('*/api/v1/listas/:id/excel', ({ request }) => {
        url = new URL(request.url).pathname
        return undefined
      }),
    )

    const blob = await descargarExcel(41)

    expect(url).toBe('/api/v1/listas/41/excel')
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

  it('datos simulados ficticios: cedulas imposibles (provincia 00 o 99) y ningun correo', async () => {
    const recienteRaw = (await (await fetch('http://localhost/api/v1/listas/ultima')).json()) as {
      items: Record<string, unknown>[]
    }
    const anteriorRaw = (await (await fetch('http://localhost/api/v1/listas/41')).json()) as {
      items: Record<string, unknown>[]
    }
    const lista = await generarLista({ horizonteDias: 30, topK: 25 })
    const anterior = await obtenerLista(41)
    const gestiones = await getGestiones('proximas')

    for (const raw of [...recienteRaw.items, ...anteriorRaw.items]) {
      expect(Object.keys(raw)).not.toContain('correo')
      expect(Object.keys(raw)).toContain('cedula')
    }
    expect(JSON.stringify([recienteRaw, anteriorRaw, lista, anterior, gestiones])).not.toMatch(
      /correo|@/i,
    )
    for (const item of lista.items) {
      expect(item.cedula).toMatch(/^(00|99)\d{8}$/)
    }
    expect(lista.items.some((i) => i.cedula?.startsWith('0'))).toBe(true)
    // La lista antigua conserva un socio sin cedula.
    expect(anterior.items.filter((i) => i.cedula === null)).toHaveLength(1)
  })

  it('snake_case del contrato solo en api/: types, hooks, components y pages no lo usan', () => {
    const fuera = import.meta.glob(
      ['../types.ts', '../hooks/*.ts', '../components/*.tsx', '../pages/*.tsx', '!../**/*.test.*'],
      { query: '?raw', import: 'default', eager: true },
    ) as Record<string, string>
    const campos = /\b(prediccion_id|socio_nombre|fecha_vencimiento|dias_para_vencer|monto_cobrado|nivel_riesgo|factores_principales|dentro_top_k|gestion_estado|campania_asignada|modelo_version|fecha_generacion|creada_en|horizonte_dias|top_k|umbral_alto|umbral_medio|advertencia_datos_antiguos|total_items|fecha_referencia)\b/

    expect(Object.keys(fuera).length).toBeGreaterThanOrEqual(8)
    for (const [ruta, codigo] of Object.entries(fuera)) {
      expect({ ruta, usa: campos.exec(codigo)?.[0] ?? null }).toEqual({ ruta, usa: null })
    }
  })

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).not.toMatch(/parseFloat|Number\(/)
  })
})
