import { http, HttpResponse } from 'msw'

/** Forma cruda (snake_case) de `CampaniaDTO` en los datos simulados. */
interface CampaniaSimulada {
  id: number
  nombre: string
  descripcion: string | null
  activa: boolean
  niveles_riesgo: string[]
  planes: string[]
  prioridad: number
  es_ejemplo: boolean
}

/** Las 3 campañas de ejemplo con las que arranca el sistema (decisión (d) de R-009; ficticias). */
function campaniasDeEjemplo(): CampaniaSimulada[] {
  return [
    {
      id: 1,
      nombre: 'Ejemplo: Llamada personal antes del vencimiento',
      descripcion:
        'Llamar al socio antes de que venza su plan para recordarle sus avances y resolver dudas.',
      activa: true,
      niveles_riesgo: ['ALTO'],
      planes: ['MENSUAL', 'TRIMESTRAL', 'SEMESTRAL', 'ANUAL', 'OTRO'],
      prioridad: 1,
      es_ejemplo: true,
    },
    {
      id: 2,
      nombre: 'Ejemplo: Renovación anticipada',
      descripcion: 'Ofrecer renovar antes del vencimiento con el beneficio que Mtabolic defina.',
      activa: true,
      niveles_riesgo: ['ALTO', 'MEDIO'],
      planes: ['MENSUAL', 'TRIMESTRAL'],
      prioridad: 2,
      es_ejemplo: true,
    },
    {
      id: 3,
      nombre: 'Ejemplo: Recordatorio de renovación',
      descripcion: 'Enviar un recordatorio amable de la fecha de vencimiento.',
      activa: true,
      niveles_riesgo: ['MEDIO', 'BAJO'],
      planes: ['MENSUAL', 'TRIMESTRAL', 'SEMESTRAL', 'ANUAL', 'OTRO'],
      prioridad: 3,
      es_ejemplo: true,
    },
  ]
}

const PRIMERA_ID_NUEVA = 10

let campanias = campaniasDeEjemplo()
let siguienteId = PRIMERA_ID_NUEVA

/** Vuelve al estado inicial (3 de ejemplo). Las pruebas lo llaman antes de cada caso. */
export function reiniciarCampaniasSimuladas(): void {
  campanias = campaniasDeEjemplo()
  siguienteId = PRIMERA_ID_NUEVA
}

export const MENSAJE_NOMBRE_OBLIGATORIO = 'El nombre de la campana es obligatorio.'
export const MENSAJE_NO_EXISTE = 'La campana no existe.'

/** Mismo orden que `GET /campanias`: activa DESC, prioridad, lower(nombre), id. */
function ordenadas(): CampaniaSimulada[] {
  return [...campanias].sort(
    (a, b) =>
      Number(b.activa) - Number(a.activa) ||
      a.prioridad - b.prioridad ||
      a.nombre.toLowerCase().localeCompare(b.nombre.toLowerCase()) ||
      a.id - b.id,
  )
}

function buscar(id: unknown): CampaniaSimulada | undefined {
  return campanias.find((c) => String(c.id) === String(id))
}

const noExiste = () =>
  HttpResponse.json({ error: { code: 'not_found', message: MENSAJE_NO_EXISTE } }, { status: 404 })

const nombreVacio = () =>
  HttpResponse.json(
    { error: { code: 'validation_error', message: MENSAJE_NOMBRE_OBLIGATORIO } },
    { status: 400 },
  )

/** Campos editables de la entrada (`CampaniaEntradaDTO`), recortados como el backend. */
function datosDeEntrada(body: Record<string, unknown>) {
  const descripcion = typeof body.descripcion === 'string' ? body.descripcion.trim() : ''
  return {
    nombre: String(body.nombre ?? '').trim(),
    descripcion: descripcion === '' ? null : descripcion,
    niveles_riesgo: (body.niveles_riesgo as string[] | undefined) ?? [],
    planes: (body.planes as string[] | undefined) ?? [],
    prioridad: Number(body.prioridad),
  }
}

export const handlers = [
  http.get('*/api/v1/campanias', () => HttpResponse.json(ordenadas())),
  http.post('*/api/v1/campanias', async ({ request }) => {
    const datos = datosDeEntrada((await request.json()) as Record<string, unknown>)
    if (datos.nombre === '') return nombreVacio()
    const creada: CampaniaSimulada = { ...datos, id: siguienteId, activa: true, es_ejemplo: false }
    siguienteId += 1
    campanias = [...campanias, creada]
    return HttpResponse.json(creada, { status: 201 })
  }),
  http.put('*/api/v1/campanias/:id', async ({ params, request }) => {
    const actual = buscar(params.id)
    if (!actual) return noExiste()
    const datos = datosDeEntrada((await request.json()) as Record<string, unknown>)
    if (datos.nombre === '') return nombreVacio()
    // Editar no cambia `activa` ni `es_ejemplo` (decisión (e)).
    const editada: CampaniaSimulada = { ...actual, ...datos }
    campanias = campanias.map((c) => (c.id === actual.id ? editada : c))
    return HttpResponse.json(editada)
  }),
  http.post('*/api/v1/campanias/:id/inactivar', ({ params }) => {
    const actual = buscar(params.id)
    if (!actual) return noExiste()
    // Idempotente: inactivar una ya inactiva devuelve 200 sin cambios.
    const inactiva: CampaniaSimulada = { ...actual, activa: false }
    campanias = campanias.map((c) => (c.id === actual.id ? inactiva : c))
    return HttpResponse.json(inactiva)
  }),
  http.post('*/api/v1/campanias/:id/activar', ({ params }) => {
    const actual = buscar(params.id)
    if (!actual) return noExiste()
    // Idempotente: activar una ya activa devuelve 200 sin cambios. No toca `es_ejemplo`.
    const activa: CampaniaSimulada = { ...actual, activa: true }
    campanias = campanias.map((c) => (c.id === actual.id ? activa : c))
    return HttpResponse.json(activa)
  }),
]
