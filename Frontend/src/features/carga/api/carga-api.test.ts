// @vitest-environment node
// El puente de Blob/FormData de jsdom con el fetch de Node falla al serializar multipart,
// asi que esta prueba corre en Node. Node no resuelve URLs relativas: se fija una base
// absoluta antes de cargar el servicio (los handlers usan el comodin de origen `*`).
import { http, HttpResponse } from 'msw'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import { MENSAJES_CARGA } from './carga-api.handlers'
import source from './carga-api.ts?raw'
import handlersSource from './carga-api.handlers.ts?raw'

let previsualizarCarga: typeof import('./carga-api').previsualizarCarga
let confirmarCarga: typeof import('./carga-api').confirmarCarga

beforeAll(async () => {
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost')
  ;({ previsualizarCarga, confirmarCarga } = await import('./carga-api'))
})

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

function archivo(nombre: string): File {
  return new File(['contenido'], nombre, { type: XLSX })
}

describe('carga-api (contra MSW)', () => {
  it('valida.xlsx → puedeConfirmar true y sin errores', async () => {
    const vista = await previsualizarCarga(archivo('valida.xlsx'))

    expect(vista.puedeConfirmar).toBe(true)
    expect(vista.errores).toEqual([])
    expect(vista.filasLeidas).toBeGreaterThan(0)
    expect(vista.vencimientoDesde).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('con-errores.xlsx → puedeConfirmar false y errores con { fila, columna, motivo }', async () => {
    const vista = await previsualizarCarga(archivo('con-errores.xlsx'))

    expect(vista.puedeConfirmar).toBe(false)
    expect(vista.errores[0]).toEqual({
      fila: expect.any(Number),
      columna: expect.any(String),
      motivo: expect.any(String),
    })
    expect(vista.filasConError).toBe(vista.errores.length)
  })

  it('confirmarCarga → CargaResumen con filasGuardadas y fechaCarga Date', async () => {
    const resumen = await confirmarCarga(archivo('valida.xlsx'))

    expect(resumen.filasGuardadas).toBeGreaterThan(0)
    expect(resumen.nombreArchivo).toBe('valida.xlsx')
    expect(resumen.fechaCarga).toBeInstanceOf(Date)
    expect(resumen.avisosEnlace).toEqual(expect.any(Array))
  })

  it('el archivo viaja como FormData en el campo "archivo"', async () => {
    let recibido: FormDataEntryValue | null = null
    server.use(
      http.post('*/api/v1/cargas/vista-previa', async ({ request }) => {
        recibido = (await request.formData()).get('archivo')
        return HttpResponse.json({
          filas_leidas: 0,
          filas_validas: 0,
          filas_con_error: 0,
          filas_duplicadas: 0,
          vencimiento_desde: null,
          vencimiento_hasta: null,
          errores: [],
          puede_confirmar: false,
        })
      }),
    )

    const vista = await previsualizarCarga(archivo('plantilla.xlsx'))

    expect(recibido).not.toBeNull()
    expect(typeof recibido).not.toBe('string')
    expect((recibido as unknown as File).name).toBe('plantilla.xlsx')
    expect(vista.vencimientoDesde).toBeNull()
  })

  it('la peticion va como multipart/form-data con boundary', async () => {
    let contentType: string | null = null
    server.use(
      http.post('*/api/v1/cargas', ({ request }) => {
        contentType = request.headers.get('Content-Type')
        return undefined
      }),
    )

    await confirmarCarga(archivo('valida.xlsx'))

    expect(contentType).toMatch(/^multipart\/form-data; boundary=/)
  })

  it('422 en la vista previa → ApiError con status 422 y el mensaje', async () => {
    server.use(
      http.post('*/api/v1/cargas/vista-previa', () =>
        HttpResponse.json(
          { error: { code: 'validation_error', message: 'La hoja Registros no existe.' } },
          { status: 422 },
        ),
      ),
    )

    const error = await previsualizarCarga(archivo('valida.xlsx')).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, message: 'La hoja Registros no existe.' })
  })

  it('422 simulado → ApiError con status 422', async () => {
    server.use(
      http.post('*/api/v1/cargas', () =>
        HttpResponse.json(
          { error: { code: 'validation_error', message: 'El archivo no es valido.' } },
          { status: 422 },
        ),
      ),
    )

    const error = await confirmarCarga(archivo('valida.xlsx')).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(422)
    expect((error as ApiError).message).toBe('El archivo no es valido.')
  })

  it('handler por defecto coherente con (a): guardadas = validas − duplicadas', async () => {
    const vista = await previsualizarCarga(archivo('valida.xlsx'))
    const resumen = await confirmarCarga(archivo('valida.xlsx'))

    expect(resumen.filasLeidas).toBe(vista.filasLeidas)
    expect(resumen.filasDuplicadas).toBe(vista.filasDuplicadas)
    expect(resumen.filasGuardadas).toBe(vista.filasValidas - vista.filasDuplicadas)
  })

  it('duplicada.xlsx → vista previa sin errores pero no confirmable (todo duplicado)', async () => {
    const vista = await previsualizarCarga(archivo('duplicada.xlsx'))

    expect(vista.filasConError).toBe(0)
    expect(vista.filasDuplicadas).toBe(vista.filasValidas)
    expect(vista.puedeConfirmar).toBe(false)
  })

  it.each([
    ['grande.xlsx', 413, 'payload_too_large', MENSAJES_CARGA.tamano],
    ['antiguo.xlsx', 400, 'validation_error', MENSAJES_CARGA.formatoAntiguo],
    ['sin-registros.xlsx', 400, 'validation_error', MENSAJES_CARGA.sinRegistros],
    ['pendiente.xlsx', 409, 'conflict', MENSAJES_CARGA.migracionPendiente],
  ])('vista previa de %s → ApiError %i (%s)', async (nombre, status, code, message) => {
    const error = await previsualizarCarga(archivo(nombre)).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status, message, body: { error: { code, message } } })
  })

  it.each([
    ['con-errores.xlsx', MENSAJES_CARGA.filasConError],
    ['duplicada.xlsx', MENSAJES_CARGA.sinFilasNuevas],
  ])('confirmar %s → 422 domain_rule_violated', async (nombre, message) => {
    const error = await confirmarCarga(archivo(nombre)).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 422,
      message,
      body: { error: { code: 'domain_rule_violated', message } },
    })
  })

  it('handlers sin datos personales: ni cédulas, ni celulares, ni correos, ni nombres', () => {
    // Cedula/celular ecuatorianos: 10 digitos seguidos; correos con @.
    expect(handlersSource).not.toMatch(/\b\d{10}\b/)
    expect(handlersSource).not.toMatch(/[\w.+-]+@[\w-]+\.[\w.]+/)
    expect(handlersSource).not.toMatch(/\b(nombre|cedula|celular|correo)\s*:\s*['"`]/i)
  })

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).toMatch(/httpPostForm/)
  })
})
