import { http, HttpResponse } from 'msw'

/*
 * Datos simulados FICTICIOS (nombres, celulares y correos inventados; sin cedulas).
 * Los decimales se escriben como string y se calculan con enteros (puntos basicos),
 * sin aritmetica de coma flotante.
 */

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
const LISTA_ID = 42
const TOTAL_SOCIOS = 32
const UMBRAL_ALTO_PB = 7000
const UMBRAL_MEDIO_PB = 4000

const NOMBRES = ['Ana', 'Luis', 'Carla', 'Diego', 'Elena', 'Fabian', 'Gabriela', 'Hector']
const APELLIDOS = ['Prueba', 'Ejemplo', 'Ficticio', 'Demo']
const PLANES = ['MENSUAL', 'TRIMESTRAL', 'SEMESTRAL', 'ANUAL', 'OTRO'] as const
const FACTORES = [
  'Pocas renovaciones previas',
  'Plan de corta duracion',
  'Baja asistencia reciente',
]

const pad = (n: number, width: number) => String(n).padStart(width, '0')

/** Puntos basicos (0..10000) → decimal con 8 cifras, p. ej. 9500 → "0.95000000". */
function decimalDesdePuntosBasicos(pb: number): string {
  return pb >= 10000 ? '1.00000000' : `0.${pad(pb, 4)}0000`
}

function nivelDesdePuntosBasicos(pb: number): 'ALTO' | 'MEDIO' | 'BAJO' {
  if (pb >= UMBRAL_ALTO_PB) return 'ALTO'
  if (pb >= UMBRAL_MEDIO_PB) return 'MEDIO'
  return 'BAJO'
}

function prediccion(i: number, topK: number) {
  const pb = 9500 - i * 300
  const dia = 1 + (i % 28)
  return {
    prediccion_id: 1501 + i,
    prioridad: i + 1,
    socio_nombre: `${NOMBRES[i % NOMBRES.length]} ${APELLIDOS[Math.floor(i / NOMBRES.length) % APELLIDOS.length]}`,
    celular: `0990000${pad(i, 3)}`,
    correo: `socio${i + 1}@ejemplo.test`,
    plan: PLANES[i % PLANES.length],
    fecha_vencimiento: `2026-10-${pad(dia, 2)}`,
    dias_para_vencer: dia + 3,
    score: decimalDesdePuntosBasicos(pb),
    nivel_riesgo: nivelDesdePuntosBasicos(pb),
    factores_principales: FACTORES.slice(0, 1 + (i % FACTORES.length)),
    dentro_top_k: i < topK,
    gestion_estado: i === 0 ? 'PENDIENTE' : null,
    campania_asignada: i === 0 ? 'Renovacion anticipada' : null,
  }
}

function lista(horizonteDias = 30, topK = 25) {
  return {
    id: LISTA_ID,
    modelo_version: 'v1',
    fecha_generacion: '2026-09-28T15:00:00Z',
    horizonte_dias: horizonteDias,
    top_k: topK,
    umbral_alto: decimalDesdePuntosBasicos(UMBRAL_ALTO_PB),
    umbral_medio: decimalDesdePuntosBasicos(UMBRAL_MEDIO_PB),
    advertencia_datos_antiguos: false,
    items: Array.from({ length: TOTAL_SOCIOS }, (_, i) => prediccion(i, topK)),
  }
}

const GESTION = {
  id: 9,
  prediccion_id: 1501,
  socio_nombre: 'Ana Prueba',
  plan: 'MENSUAL',
  fecha_vencimiento: '2026-10-01',
  modelo_version: 'v1',
  score: '0.95000000',
  nivel_riesgo: 'ALTO',
  campania_id: 3,
  campania_nombre: 'Renovacion anticipada',
  estado: 'PENDIENTE',
  fecha_asignacion: '2026-09-28T15:30:00Z',
  fecha_seguimiento: '2026-10-25',
  responsable: 'Andrea',
  contactado: null,
  campania_ofrecida: null,
  campania_aceptada: null,
  renovo_declarado: null,
  fecha_contacto: null,
  observaciones: null,
  fecha_cierre: null,
}

const SEGUIMIENTO_POR_FILTRO: Record<string, string[]> = {
  vencidas: ['2026-09-25', '2026-09-26'],
  hoy: ['2026-09-28', '2026-09-28', '2026-09-28'],
  proximas: ['2026-09-30', '2026-10-01', '2026-10-02', '2026-10-03', '2026-10-05'],
}

function gestionesResumen(filtro: string) {
  return (SEGUIMIENTO_POR_FILTRO[filtro] ?? []).map((fecha, i) => {
    const p = prediccion(i, 25)
    return {
      id: 100 + i,
      socio_nombre: p.socio_nombre,
      celular: p.celular,
      plan: p.plan,
      fecha_vencimiento: p.fecha_vencimiento,
      fecha_seguimiento: fecha,
      nivel_riesgo: p.nivel_riesgo,
      campania_nombre: i % 2 === 0 ? 'Renovacion anticipada' : null,
      responsable: 'Andrea',
      estado: 'PENDIENTE',
    }
  })
}

const CAMPANIAS_SUGERIDAS = [
  {
    id: 3,
    nombre: 'Renovacion anticipada',
    descripcion: '10% de descuento si renueva antes del vencimiento.',
    activa: true,
    niveles_riesgo: ['ALTO', 'MEDIO'],
    planes: ['MENSUAL', 'TRIMESTRAL'],
    prioridad: 1,
    es_ejemplo: true,
  },
  {
    id: 5,
    nombre: 'Llamada de bienvenida',
    descripcion: null,
    activa: true,
    niveles_riesgo: ['ALTO'],
    planes: ['MENSUAL'],
    prioridad: 2,
    es_ejemplo: false,
  },
]

const noEncontrado = (message: string) =>
  HttpResponse.json({ error: { code: 'not_found', message } }, { status: 404 })

interface GenerarBody {
  horizonte_dias?: number
  top_k?: number
}

export const handlers = [
  http.post('*/api/v1/listas', async ({ request }) => {
    const body = (await request.json()) as GenerarBody
    return HttpResponse.json(lista(body.horizonte_dias, body.top_k), { status: 201 })
  }),
  http.get('*/api/v1/listas/ultima', () => HttpResponse.json(lista())),
  http.get('*/api/v1/listas/:id/excel', ({ params }) =>
    params.id === String(LISTA_ID)
      ? new HttpResponse(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
          headers: {
            'Content-Type': XLSX,
            'Content-Disposition': `attachment; filename="lista-priorizada-${LISTA_ID}.xlsx"`,
          },
        })
      : noEncontrado('La lista no existe.'),
  ),
  http.get('*/api/v1/listas/:id', ({ params }) =>
    params.id === String(LISTA_ID) ? HttpResponse.json(lista()) : noEncontrado('La lista no existe.'),
  ),
  http.get('*/api/v1/predicciones/:id/campanias-sugeridas', () =>
    HttpResponse.json(CAMPANIAS_SUGERIDAS),
  ),
  http.post('*/api/v1/gestiones', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json(
      {
        ...GESTION,
        prediccion_id: body.prediccion_id,
        campania_id: body.campania_id ?? null,
        campania_nombre: body.campania_id ? GESTION.campania_nombre : null,
        fecha_seguimiento: body.fecha_seguimiento,
        responsable: body.responsable ?? null,
      },
      { status: 201 },
    )
  }),
  http.get('*/api/v1/gestiones', ({ request }) =>
    HttpResponse.json(gestionesResumen(new URL(request.url).searchParams.get('filtro') ?? '')),
  ),
  http.get('*/api/v1/gestiones/:id', ({ params }) =>
    HttpResponse.json({ ...GESTION, id: Number.parseInt(String(params.id), 10) }),
  ),
  http.put('*/api/v1/gestiones/:id/resultado', async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    const cierra = body.renovo_declarado === 'SI' || body.renovo_declarado === 'NO'
    return HttpResponse.json({
      ...GESTION,
      ...body,
      id: Number.parseInt(String(params.id), 10),
      responsable: body.responsable ?? GESTION.responsable,
      fecha_seguimiento: body.fecha_seguimiento ?? GESTION.fecha_seguimiento,
      estado: cierra ? 'CERRADA' : 'PENDIENTE',
      fecha_cierre: cierra ? '2026-10-20T18:00:00Z' : null,
    })
  }),
]
