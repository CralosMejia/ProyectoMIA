// @vitest-environment node
// El puente de Blob/FormData de jsdom con el fetch de Node falla al serializar multipart,
// asi que esta prueba corre en Node. Node no resuelve URLs relativas: se fija una base
// absoluta antes de cargar el servicio (los handlers usan el comodin de origen `*`).
import { http, HttpResponse } from 'msw'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { server } from '../../../mocks/server'
import source from './carga-api.ts?raw'

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

  it('no usa fetch directo: pasa por core/http', () => {
    expect(source).not.toMatch(/\bfetch\s*\(/)
    expect(source).toMatch(/httpPostForm/)
  })
})
