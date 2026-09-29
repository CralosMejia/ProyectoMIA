import { http, HttpResponse } from 'msw'

/** Mes por defecto de los datos simulados cuando no llega `?mes=`. */
const MES_POR_DEFECTO = '2026-09'

function dashboard(mes: string) {
  return {
    mes,
    embudo: { asignadas: 40, contactadas: 32, ofrecidas: 25, aceptadas: 12, renovaron: 10 },
    por_campania: [
      {
        campania_id: 3,
        nombre: 'Renovacion anticipada',
        gestiones: 22,
        contactados: 19,
        renovaciones: 8,
        gestiones_cerradas: 16,
        tasa_renovacion: '0.50000000',
        casos_insuficientes: false,
      },
      {
        campania_id: null,
        nombre: 'Sin campana',
        gestiones: 3,
        contactados: 2,
        renovaciones: 1,
        gestiones_cerradas: 2,
        tasa_renovacion: null,
        casos_insuficientes: true,
      },
    ],
    estado_modelo: {
      version: 'v1',
      fecha_entrenamiento: '2026-09-28T14:30:00Z',
      ciclos_entrenamiento: 1843,
      proxima_fecha_reentrenamiento: '2026-10-28',
      ciclos_nuevos_evaluables: 57,
    },
  }
}

export const handlers = [
  http.get('*/api/v1/dashboard', ({ request }) => {
    const mes = new URL(request.url).searchParams.get('mes')
    if (mes !== null && !/^\d{4}-(0[1-9]|1[0-2])$/.test(mes)) {
      return HttpResponse.json(
        { error: { code: 'bad_request', message: 'El mes no tiene el formato YYYY-MM.' } },
        { status: 400 },
      )
    }
    return HttpResponse.json(dashboard(mes ?? MES_POR_DEFECTO))
  }),
]
