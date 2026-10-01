import { http, HttpResponse } from 'msw'

/** Mes por defecto de los datos simulados cuando no llega `?mes=`. */
const MES_POR_DEFECTO = '2026-09'

/**
 * Datos simulados del mes: "asignadas" cuenta solo gestiones con campaña; una campaña con 10
 * gestiones cerradas con resultado (tasa visible), otra con 9 (casos insuficientes) y la fila
 * "Sin campaña" al final, sin resultado.
 */
function dashboard(mes: string) {
  return {
    mes,
    embudo: { asignadas: 21, contactadas: 17, ofrecidas: 14, aceptadas: 8, renovaron: 6 },
    por_campania: [
      {
        campania_id: 2,
        nombre: 'Ejemplo: Renovación anticipada',
        gestiones: 12,
        contactados: 10,
        renovaciones: 4,
        gestiones_cerradas: 10,
        tasa_renovacion: '0.40000000',
        casos_insuficientes: false,
      },
      {
        campania_id: 1,
        nombre: 'Ejemplo: Llamada personal antes del vencimiento',
        gestiones: 9,
        contactados: 7,
        renovaciones: 2,
        gestiones_cerradas: 9,
        tasa_renovacion: null,
        casos_insuficientes: true,
      },
      {
        campania_id: null,
        nombre: 'Sin campaña',
        gestiones: 3,
        contactados: 0,
        renovaciones: 0,
        gestiones_cerradas: 0,
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
        { error: { code: 'validation_error', message: 'El mes no tiene el formato YYYY-MM.' } },
        { status: 400 },
      )
    }
    return HttpResponse.json(dashboard(mes ?? MES_POR_DEFECTO))
  }),
]
