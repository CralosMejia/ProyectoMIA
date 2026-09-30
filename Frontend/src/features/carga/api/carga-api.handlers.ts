import { http, HttpResponse } from 'msw'

/**
 * Handlers MSW de cargas (CU-01), fieles al contrato de R-007 (decisiones (a) y (k)).
 * Datos ficticios: ningun nombre, cedula ni valor procede de datos reales. El escenario se
 * elige por el prefijo del nombre del archivo:
 *
 * | Prefijo          | Vista previa                          | Confirmar                    |
 * |------------------|---------------------------------------|------------------------------|
 * | (cualquier otro) | 120 leidas, 118 validas, 2 duplicadas | 201, 116 guardadas, 1 aviso  |
 * | `con-errores`    | 2 filas con error, no confirmable     | 422 filas con error          |
 * | `duplicada`      | todo duplicado, no confirmable        | 422 sin filas nuevas         |
 * | `grande`         | 413                                   | 413                          |
 * | `antiguo`        | 400 formato antiguo                   | 400 formato antiguo          |
 * | `sin-registros`  | 400 sin hoja Registros                | 400 sin hoja Registros       |
 * | `pendiente`      | 409 migracion no completada           | 409 migracion no completada  |
 * | (sin `archivo`)  | 400 validation_error                  | 400 validation_error         |
 */

/** Nombre del archivo recibido en el campo multipart `archivo` (null si no llega). */
async function nombreArchivo(request: Request): Promise<string | null> {
  const archivo = (await request.formData()).get('archivo')
  return archivo !== null && typeof archivo !== 'string' ? archivo.name : null
}

function errorBody(code: string, message: string) {
  return { error: { code, message } }
}

export const MENSAJES_CARGA = {
  sinArchivo: 'La solicitud contiene datos invalidos o incompletos.',
  tamano: 'El archivo supera el tamaño máximo permitido.',
  formatoAntiguo:
    'El archivo tiene el formato antiguo de hojas mensuales; use la plantilla oficial de carga.',
  sinRegistros: 'El archivo no tiene la hoja Registros.',
  migracionPendiente: 'La migracion del historico aun no se ha completado.',
  filasConError: 'Hay filas con error; corrija el archivo y vuelva a subirlo.',
  sinFilasNuevas: 'El archivo no tiene filas nuevas para guardar.',
} as const

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
  {
    fila: 7,
    columna: 'H',
    motivo: 'La fecha de vencimiento debe ser posterior a la de inicio.',
  },
  { fila: 12, columna: 'C', motivo: 'La cédula no tiene un dígito verificador válido.' },
]

const VISTA_PREVIA_CON_ERRORES = {
  ...VISTA_PREVIA_VALIDA,
  filas_validas: 116,
  filas_con_error: ERRORES.length,
  errores: ERRORES,
  puede_confirmar: false,
}

/** Todas las filas validas ya existen: `filas_duplicadas` ⊆ validas y no hay nuevas. */
const VISTA_PREVIA_DUPLICADA = {
  filas_leidas: 3,
  filas_validas: 3,
  filas_con_error: 0,
  filas_duplicadas: 3,
  vencimiento_desde: '2026-10-01',
  vencimiento_hasta: '2026-10-15',
  errores: [],
  puede_confirmar: false,
}

/** nuevas = validas (118) − duplicadas (2) = filas_guardadas (116). */
function cargaGuardada(nombre: string) {
  return {
    id: 12,
    fecha_carga: '2026-09-28T16:05:00Z',
    nombre_archivo: nombre,
    filas_leidas: 120,
    filas_guardadas: 116,
    filas_duplicadas: 2,
    socios_enlazados: 95,
    avisos_enlace: [
      'Fila 22: hay varios socios históricos con el mismo nombre; se creó un socio nuevo.',
    ],
  }
}

function sinArchivo() {
  return HttpResponse.json(errorBody('validation_error', MENSAJES_CARGA.sinArchivo), {
    status: 400,
  })
}

/** Errores de archivo comunes a vista previa y confirmacion (null si el archivo pasa). */
function errorDeArchivo(nombre: string): Response | null {
  if (nombre.startsWith('grande')) {
    return HttpResponse.json(errorBody('payload_too_large', MENSAJES_CARGA.tamano), {
      status: 413,
    })
  }
  if (nombre.startsWith('antiguo')) {
    return HttpResponse.json(errorBody('validation_error', MENSAJES_CARGA.formatoAntiguo), {
      status: 400,
    })
  }
  if (nombre.startsWith('sin-registros')) {
    return HttpResponse.json(errorBody('validation_error', MENSAJES_CARGA.sinRegistros), {
      status: 400,
    })
  }
  if (nombre.startsWith('pendiente')) {
    return HttpResponse.json(errorBody('conflict', MENSAJES_CARGA.migracionPendiente), {
      status: 409,
    })
  }
  return null
}

export const handlers = [
  http.post('*/api/v1/cargas/vista-previa', async ({ request }) => {
    const nombre = await nombreArchivo(request)
    if (nombre === null) return sinArchivo()
    const error = errorDeArchivo(nombre)
    if (error !== null) return error
    if (nombre.startsWith('con-errores')) return HttpResponse.json(VISTA_PREVIA_CON_ERRORES)
    if (nombre.startsWith('duplicada')) return HttpResponse.json(VISTA_PREVIA_DUPLICADA)
    return HttpResponse.json(VISTA_PREVIA_VALIDA)
  }),
  http.post('*/api/v1/cargas', async ({ request }) => {
    const nombre = await nombreArchivo(request)
    if (nombre === null) return sinArchivo()
    const error = errorDeArchivo(nombre)
    if (error !== null) return error
    if (nombre.startsWith('con-errores')) {
      return HttpResponse.json(errorBody('domain_rule_violated', MENSAJES_CARGA.filasConError), {
        status: 422,
      })
    }
    if (nombre.startsWith('duplicada')) {
      return HttpResponse.json(errorBody('domain_rule_violated', MENSAJES_CARGA.sinFilasNuevas), {
        status: 422,
      })
    }
    return HttpResponse.json(cargaGuardada(nombre), { status: 201 })
  }),
]
