import { http, HttpResponse } from 'msw'

/** Mes por defecto de los datos simulados cuando no llega `?mes=`. */
const MES_POR_DEFECTO = '2026-09'

const SIN_DATOS = {
  valor: null,
  numerador: 0,
  denominador: 0,
  n: 0,
  pendientes: 0,
  estado: 'SIN_DATOS',
}

/** Indicadores del piloto (R-018): agosto completo, septiembre parcial, octubre pendiente. */
const PILOTOS: Record<string, unknown> = {
  '2026-08': {
    estado: 'COMPLETO',
    lista: { id: 11, nombre: 'Ejemplo: Lista agosto', fecha_generacion: '2026-08-01' },
    corte_verificacion: '2026-10-28',
    n_top: 25,
    sin_dato: 0,
    precision_top25: {
      valor: '0.64000000',
      numerador: 16,
      denominador: 25,
      n: 25,
      pendientes: 0,
      estado: 'COMPLETO',
    },
    contactados_antes_vencimiento: {
      valor: '0.80000000',
      numerador: 20,
      denominador: 25,
      n: 25,
      pendientes: 0,
      estado: 'COMPLETO',
    },
    dias_anticipacion: { valor: '6.2', n: 20, estado: 'COMPLETO' },
    tasa_renovacion_contactados: {
      valor: '0.45000000',
      numerador: 9,
      denominador: 20,
      n: 20,
      pendientes: 0,
      estado: 'COMPLETO',
    },
    monto_retenido: {
      total: '1450.00',
      renovaciones: 9,
      renovaciones_sin_monto: 0,
      n: 20,
      pendientes: 0,
      estado: 'COMPLETO',
    },
  },
  '2026-09': {
    estado: 'PARCIAL',
    lista: { id: 12, nombre: 'Ejemplo: Lista septiembre', fecha_generacion: '2026-09-01' },
    corte_verificacion: '2026-10-28',
    n_top: 25,
    sin_dato: 0,
    precision_top25: {
      valor: '0.60000000',
      numerador: 12,
      denominador: 20,
      n: 25,
      pendientes: 5,
      estado: 'PARCIAL',
    },
    contactados_antes_vencimiento: {
      valor: '0.72000000',
      numerador: 18,
      denominador: 25,
      n: 25,
      pendientes: 0,
      estado: 'COMPLETO',
    },
    dias_anticipacion: { valor: '4.5', n: 19, estado: 'COMPLETO' },
    tasa_renovacion_contactados: {
      valor: '0.41176471',
      numerador: 7,
      denominador: 17,
      n: 21,
      pendientes: 4,
      estado: 'PARCIAL',
    },
    monto_retenido: {
      total: '312.50',
      renovaciones: 7,
      renovaciones_sin_monto: 1,
      n: 17,
      pendientes: 4,
      estado: 'PARCIAL',
    },
  },
  '2026-10': {
    estado: 'PENDIENTE',
    lista: { id: 13, nombre: 'Ejemplo: Lista octubre', fecha_generacion: '2026-10-01' },
    corte_verificacion: '2026-10-28',
    n_top: 25,
    sin_dato: 1,
    precision_top25: {
      valor: null,
      numerador: 0,
      denominador: 0,
      n: 24,
      pendientes: 24,
      estado: 'PENDIENTE',
    },
    contactados_antes_vencimiento: {
      valor: '0.33333333',
      numerador: 8,
      denominador: 24,
      n: 24,
      pendientes: 0,
      estado: 'COMPLETO',
    },
    dias_anticipacion: { valor: '3.0', n: 8, estado: 'COMPLETO' },
    tasa_renovacion_contactados: {
      valor: null,
      numerador: 0,
      denominador: 0,
      n: 8,
      pendientes: 8,
      estado: 'PENDIENTE',
    },
    monto_retenido: {
      total: null,
      renovaciones: 0,
      renovaciones_sin_monto: 0,
      n: 0,
      pendientes: 8,
      estado: 'PENDIENTE',
    },
  },
}

/** Mes sin lista: todo `SIN_DATOS`, valores null y conteos en 0. */
const PILOTO_SIN_DATOS = {
  estado: 'SIN_DATOS',
  lista: null,
  corte_verificacion: null,
  n_top: 0,
  sin_dato: 0,
  precision_top25: SIN_DATOS,
  contactados_antes_vencimiento: SIN_DATOS,
  dias_anticipacion: { valor: null, n: 0, estado: 'SIN_DATOS' },
  tasa_renovacion_contactados: SIN_DATOS,
  monto_retenido: {
    total: null,
    renovaciones: 0,
    renovaciones_sin_monto: 0,
    n: 0,
    pendientes: 0,
    estado: 'SIN_DATOS',
  },
}

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
    piloto: PILOTOS[mes] ?? PILOTO_SIN_DATOS,
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
