import { http, HttpResponse } from 'msw'

/** Nombre del archivo recibido en el campo multipart `archivo` (null si no llega). */
async function nombreArchivo(request: Request): Promise<string | null> {
  const archivo = (await request.formData()).get('archivo')
  return archivo !== null && typeof archivo !== 'string' ? archivo.name : null
}

const VISTA_PREVIA_VALIDA = {
  filas_leidas: 120,
  filas_validas: 118,
  filas_con_error: 0,
  filas_duplicadas: 2,
  vencimiento_desde: '2026-09-01',
  vencimiento_hasta: '2026-11-30',
  errores: [],
  puede_confirmar: true,
}

const ERRORES = [
  { fila: 7, columna: 'FECHA_VENCIMIENTO', motivo: 'La fecha no tiene un formato valido.' },
  { fila: 12, columna: 'PLAN', motivo: 'El plan no pertenece al catalogo.' },
]

const VISTA_PREVIA_CON_ERRORES = {
  ...VISTA_PREVIA_VALIDA,
  filas_validas: 116,
  filas_con_error: ERRORES.length,
  errores: ERRORES,
  puede_confirmar: false,
}

const SIN_ARCHIVO = {
  error: { code: 'validation_error', message: 'Debe adjuntar el archivo de la plantilla.' },
}

/** Vista previa valida o con errores segun el nombre del archivo (`con-errores*`). */
export const handlers = [
  http.post('*/api/v1/cargas/vista-previa', async ({ request }) => {
    const nombre = await nombreArchivo(request)
    if (nombre === null) return HttpResponse.json(SIN_ARCHIVO, { status: 422 })
    return HttpResponse.json(
      nombre.startsWith('con-errores') ? VISTA_PREVIA_CON_ERRORES : VISTA_PREVIA_VALIDA,
    )
  }),
  http.post('*/api/v1/cargas', async ({ request }) => {
    const nombre = await nombreArchivo(request)
    if (nombre === null) return HttpResponse.json(SIN_ARCHIVO, { status: 422 })
    return HttpResponse.json(
      {
        id: 12,
        fecha_carga: '2026-09-28T16:05:00Z',
        nombre_archivo: nombre,
        filas_leidas: 120,
        filas_guardadas: 118,
        filas_duplicadas: 2,
        socios_enlazados: 95,
        avisos_enlace: [],
      },
      { status: 201 },
    )
  }),
]
