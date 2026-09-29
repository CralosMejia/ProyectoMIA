import { http, HttpResponse } from 'msw'

/** Las dos campañas de ejemplo con las que arranca el sistema (datos simulados). */
const CAMPANIAS = [
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
    id: 4,
    nombre: 'Clase personalizada de regalo',
    descripcion: 'Una sesion con entrenador al renovar el plan.',
    activa: true,
    niveles_riesgo: ['BAJO'],
    planes: ['SEMESTRAL', 'ANUAL', 'OTRO'],
    prioridad: 2,
    es_ejemplo: true,
  },
]

const NUEVA_ID = 10

function buscar(id: unknown) {
  return CAMPANIAS.find((c) => String(c.id) === String(id))
}

const noExiste = () =>
  HttpResponse.json(
    { error: { code: 'not_found', message: 'La campana no existe.' } },
    { status: 404 },
  )

export const handlers = [
  http.get('*/api/v1/campanias', () => HttpResponse.json(CAMPANIAS)),
  http.post('*/api/v1/campanias', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json(
      { ...body, id: NUEVA_ID, activa: true, es_ejemplo: false },
      { status: 201 },
    )
  }),
  http.put('*/api/v1/campanias/:id', async ({ params, request }) => {
    const actual = buscar(params.id)
    if (!actual) return noExiste()
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ ...actual, ...body })
  }),
  http.post('*/api/v1/campanias/:id/inactivar', ({ params }) => {
    const actual = buscar(params.id)
    return actual ? HttpResponse.json({ ...actual, activa: false }) : noExiste()
  }),
]
