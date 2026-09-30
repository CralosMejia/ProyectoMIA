import { http, HttpResponse } from 'msw'

/*
 * Datos simulados FICTICIOS (nombres y celulares inventados; sin correos). Las cedulas son
 * imposibles a proposito (provincia 00 o 99, que no existen), la mitad con cero inicial.
 * Los decimales se escriben como string y se calculan con enteros (puntos basicos),
 * sin aritmetica de coma flotante.
 */

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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

/** Monto en dolares como decimal string; cada noveno socio sin monto registrado. */
function montoCobrado(i: number): string | null {
  return i % 9 === 8 ? null : `${30 + (i % 5) * 5}.00`
}

/** Cada septimo socio sin factores destacados (la UI muestra el texto por defecto). */
function factores(i: number): string[] {
  return i % 7 === 6 ? [] : FACTORES.slice(0, 1 + (i % FACTORES.length))
}

/** Cedula ficticia de 10 digitos: pares `00000nnnnn` (cero inicial), impares `99nnnnnnnn`. */
function cedula(n: number): string | null {
  return n % 2 === 0 ? `00000${pad(n, 5)}` : `99${pad(n, 8)}`
}

/** Fecha local de hoy `YYYY-MM-DD` (la misma que propone el formulario). */
function hoyLocal(): string {
  const ahora = new Date()
  return `${ahora.getFullYear()}-${pad(ahora.getMonth() + 1, 2)}-${pad(ahora.getDate(), 2)}`
}

/** `desfase` cambia los socios de la lista (la mas antigua empieza por otro nombre). */
function prediccion(i: number, topK: number, desfase = 0, mesVencimiento = '2026-10') {
  const pb = 9500 - i * 300
  const dia = 1 + (i % 28)
  const n = i + desfase
  return {
    prediccion_id: 1501 + desfase * 100 + i,
    prioridad: i + 1,
    socio_nombre: `${NOMBRES[n % NOMBRES.length]} ${APELLIDOS[Math.floor(n / NOMBRES.length) % APELLIDOS.length]}`,
    celular: `0990000${pad(n, 3)}`,
    cedula: cedula(n),
    plan: PLANES[n % PLANES.length],
    fecha_vencimiento: `${mesVencimiento}-${pad(dia, 2)}`,
    dias_para_vencer: dia + 3,
    monto_cobrado: montoCobrado(i),
    score: decimalDesdePuntosBasicos(pb),
    nivel_riesgo: nivelDesdePuntosBasicos(pb),
    factores_principales: factores(i),
    dentro_top_k: i < topK,
    gestion_estado: i === 0 && desfase === 0 ? 'PENDIENTE' : null,
    campania_asignada: i === 0 && desfase === 0 ? 'Renovacion anticipada' : null,
  }
}

/** Lista mas reciente (la que devuelve `/ultima`), sin advertencia de datos antiguos. */
export const LISTA_RECIENTE_ID = 42
/**
 * Lista anterior, con `advertencia_datos_antiguos: true`. Es antigua e inmutable: su tercer socio
 * no tiene cedula (`null`), como las listas generadas antes de excluir a los socios sin cedula.
 */
export const LISTA_ANTERIOR_ID = 41

function listaReciente(horizonteDias = 30, topK = 25, fechaGeneracion = '2026-09-28') {
  return {
    id: LISTA_RECIENTE_ID,
    modelo_version: 'v1',
    fecha_generacion: fechaGeneracion,
    creada_en: '2026-09-28T15:00:00Z',
    horizonte_dias: horizonteDias,
    top_k: topK,
    umbral_alto: decimalDesdePuntosBasicos(UMBRAL_ALTO_PB),
    umbral_medio: decimalDesdePuntosBasicos(UMBRAL_MEDIO_PB),
    advertencia_datos_antiguos: false,
    items: Array.from({ length: 32 }, (_, i) => prediccion(i, topK)),
  }
}

function listaAnterior() {
  const topK = 10
  return {
    id: LISTA_ANTERIOR_ID,
    modelo_version: 'v1',
    fecha_generacion: '2026-08-31',
    creada_en: '2026-08-31T14:00:00Z',
    horizonte_dias: 30,
    top_k: topK,
    umbral_alto: decimalDesdePuntosBasicos(UMBRAL_ALTO_PB),
    umbral_medio: decimalDesdePuntosBasicos(UMBRAL_MEDIO_PB),
    advertencia_datos_antiguos: true,
    items: Array.from({ length: 12 }, (_, i) => {
      const p = prediccion(i, topK, 3, '2026-09')
      return i === 2 ? { ...p, cedula: null } : p
    }),
  }
}

type ListaSimulada = ReturnType<typeof listaReciente>

function resumen(lista: ListaSimulada) {
  return {
    id: lista.id,
    fecha_generacion: lista.fecha_generacion,
    creada_en: lista.creada_en,
    modelo_version: lista.modelo_version,
    horizonte_dias: lista.horizonte_dias,
    top_k: lista.top_k,
    total_items: lista.items.length,
  }
}

function listaPorId(id: unknown): ListaSimulada | null {
  if (id === String(LISTA_RECIENTE_ID)) return listaReciente()
  if (id === String(LISTA_ANTERIOR_ID)) return listaAnterior()
  return null
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

const errorBody = (code: string, message: string) => ({ error: { code, message } })

const noEncontrado = (message: string) =>
  HttpResponse.json(errorBody('not_found', message), { status: 404 })

interface GenerarBody {
  fecha_referencia?: string | null
  horizonte_dias?: number
  top_k?: number
}

const fechaPasada = () =>
  HttpResponse.json(
    errorBody('domain_rule_violated', 'La fecha de la lista debe ser hoy o posterior.'),
    { status: 422 },
  )

/**
 * Escenarios de error para `server.use(...)` en las pruebas (no se registran por defecto):
 * 409 al generar mientras el sistema se inicializa, 422 por fecha anterior a hoy, 404 cuando
 * aun no hay listas y una ultima lista con datos antiguos.
 */
export const escenariosLista = {
  sistemaInicializando: http.post('*/api/v1/listas', () =>
    HttpResponse.json(
      errorBody(
        'conflict',
        'El sistema se esta inicializando; intente de nuevo en unos minutos.',
      ),
      { status: 409 },
    ),
  ),
  /** `POST /listas` responde siempre 422 (fecha anterior a hoy segun el servidor). */
  fechaPasada: http.post('*/api/v1/listas', fechaPasada),
  /** `/ultima` devuelve la lista anterior (con `advertencia_datos_antiguos: true`). */
  ultimaConDatosAntiguos: http.get('*/api/v1/listas/ultima', () =>
    HttpResponse.json(listaAnterior()),
  ),
  sinListas: [
    http.get('*/api/v1/listas/ultima', () =>
      noEncontrado('Aun no se ha generado ninguna lista.'),
    ),
    http.get('*/api/v1/listas', () => HttpResponse.json([])),
  ],
}

export const handlers = [
  http.post('*/api/v1/listas', async ({ request }) => {
    const body = (await request.json()) as GenerarBody
    const fecha = body.fecha_referencia ?? undefined
    // Comparacion lexicografica valida para `YYYY-MM-DD`.
    if (fecha !== undefined && fecha < hoyLocal()) return fechaPasada()
    return HttpResponse.json(listaReciente(body.horizonte_dias, body.top_k, fecha), {
      status: 201,
    })
  }),
  http.get('*/api/v1/listas', () =>
    HttpResponse.json([resumen(listaReciente()), resumen(listaAnterior())]),
  ),
  http.get('*/api/v1/listas/ultima', () => HttpResponse.json(listaReciente())),
  http.get('*/api/v1/listas/:id/excel', ({ params }) => {
    const lista = listaPorId(params.id)
    return lista
      ? new HttpResponse(new Uint8Array([0x50, 0x4b, 0x03, 0x04]), {
          headers: {
            'Content-Type': XLSX,
            'Content-Disposition': `attachment; filename="lista_${lista.id}_${lista.fecha_generacion}.xlsx"`,
          },
        })
      : noEncontrado('La lista no existe.')
  }),
  http.get('*/api/v1/listas/:id', ({ params }) => {
    const lista = listaPorId(params.id)
    return lista ? HttpResponse.json(lista) : noEncontrado('La lista no existe.')
  }),
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
