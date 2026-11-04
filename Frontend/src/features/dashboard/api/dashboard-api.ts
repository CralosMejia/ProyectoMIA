import { httpGet } from '../../../core/http/http-client'
import type {
  Dashboard,
  Embudo,
  EstadoIndicador,
  IndicadorDias,
  IndicadoresPiloto,
  IndicadorProporcion,
  ResultadoCampania,
} from '../types'

const DASHBOARD_PATH = '/api/v1/dashboard'

/*
 * Formas crudas (snake_case) del backend. Solo se conocen en este archivo.
 * `tasa_renovacion` es decimal y llega como string: se conserva como string.
 */
interface ResultadoCampaniaResponse {
  campania_id: number | null
  nombre: string
  gestiones: number
  contactados: number
  renovaciones: number
  gestiones_cerradas: number
  tasa_renovacion: string | null
  casos_insuficientes: boolean
}

interface EstadoModeloResponse {
  version: string
  fecha_entrenamiento: string
  ciclos_entrenamiento: number
  proxima_fecha_reentrenamiento: string | null
  ciclos_nuevos_evaluables: number
}

interface IndicadorProporcionResponse {
  valor: string | null
  numerador: number
  denominador: number
  n: number
  pendientes: number
  estado: EstadoIndicador
}

/** R-022: `minimo`, `maximo` y `tramos` son aditivos; un backend anterior no los envia. */
interface IndicadorDiasResponse {
  valor: string | null
  n: number
  estado: EstadoIndicador
  minimo?: number | null
  maximo?: number | null
  tramos?: {
    quince_o_mas: number
    de_ocho_a_catorce: number
    de_uno_a_siete: number
    mismo_dia_o_despues: number
  } | null
}

interface PilotoResponse {
  estado: EstadoIndicador
  lista: { id: number; nombre: string; fecha_generacion: string } | null
  corte_verificacion: string | null
  n_top: number
  sin_dato: number
  precision_top25: IndicadorProporcionResponse
  contactados_antes_vencimiento: IndicadorProporcionResponse
  dias_anticipacion: IndicadorDiasResponse
  tasa_renovacion_contactados: IndicadorProporcionResponse
  monto_retenido: {
    total: string | null
    renovaciones: number
    renovaciones_sin_monto: number
    n: number
    pendientes: number
    estado: EstadoIndicador
  }
}

interface DashboardResponse {
  mes: string
  embudo: Embudo
  por_campania: ResultadoCampaniaResponse[]
  estado_modelo: EstadoModeloResponse | null
  /** Siempre presente desde R-018; una respuesta anterior sin el campo se trata como sin datos. */
  piloto?: PilotoResponse
}

function toResultado(raw: ResultadoCampaniaResponse): ResultadoCampania {
  return {
    campaniaId: raw.campania_id ?? null,
    nombre: raw.nombre,
    gestiones: raw.gestiones,
    contactados: raw.contactados,
    renovaciones: raw.renovaciones,
    gestionesCerradas: raw.gestiones_cerradas,
    tasaRenovacion: raw.tasa_renovacion ?? null,
    casosInsuficientes: raw.casos_insuficientes,
  }
}

function toProporcion(raw: IndicadorProporcionResponse): IndicadorProporcion {
  return {
    valor: raw.valor ?? null,
    numerador: raw.numerador,
    denominador: raw.denominador,
    n: raw.n,
    pendientes: raw.pendientes,
    estado: raw.estado,
  }
}

function toDias(raw: IndicadorDiasResponse): IndicadorDias {
  const tramos = raw.tramos ?? null
  return {
    valor: raw.valor ?? null,
    n: raw.n,
    estado: raw.estado,
    minimo: raw.minimo ?? null,
    maximo: raw.maximo ?? null,
    tramos: tramos && {
      quinceOMas: tramos.quince_o_mas,
      deOchoACatorce: tramos.de_ocho_a_catorce,
      deUnoASiete: tramos.de_uno_a_siete,
      mismoDiaODespues: tramos.mismo_dia_o_despues,
    },
  }
}

function proporcionSinDatos(): IndicadorProporcion {
  return { valor: null, numerador: 0, denominador: 0, n: 0, pendientes: 0, estado: 'SIN_DATOS' }
}

/** Mes sin lista: todo `SIN_DATOS`, valores null y conteos en 0 (igual que el backend). */
function pilotoSinDatos(): IndicadoresPiloto {
  return {
    estado: 'SIN_DATOS',
    lista: null,
    corteVerificacion: null,
    nTop: 0,
    sinDato: 0,
    precisionTop25: proporcionSinDatos(),
    contactadosAntesVencimiento: proporcionSinDatos(),
    diasAnticipacion: {
      valor: null,
      n: 0,
      estado: 'SIN_DATOS',
      minimo: null,
      maximo: null,
      tramos: null,
    },
    tasaRenovacionContactados: proporcionSinDatos(),
    montoRetenido: {
      total: null,
      renovaciones: 0,
      renovacionesSinMonto: 0,
      n: 0,
      pendientes: 0,
      estado: 'SIN_DATOS',
    },
  }
}

/** `piloto` (R-018): los decimales (`valor`, `total`) se conservan como `string`. */
function toPiloto(raw: PilotoResponse): IndicadoresPiloto {
  const { monto_retenido: monto } = raw
  return {
    estado: raw.estado,
    lista: raw.lista && {
      id: raw.lista.id,
      nombre: raw.lista.nombre,
      fechaGeneracion: raw.lista.fecha_generacion,
    },
    corteVerificacion: raw.corte_verificacion ?? null,
    nTop: raw.n_top,
    sinDato: raw.sin_dato,
    precisionTop25: toProporcion(raw.precision_top25),
    contactadosAntesVencimiento: toProporcion(raw.contactados_antes_vencimiento),
    diasAnticipacion: toDias(raw.dias_anticipacion),
    tasaRenovacionContactados: toProporcion(raw.tasa_renovacion_contactados),
    montoRetenido: {
      total: monto.total ?? null,
      renovaciones: monto.renovaciones,
      renovacionesSinMonto: monto.renovaciones_sin_monto,
      n: monto.n,
      pendientes: monto.pendientes,
      estado: monto.estado,
    },
  }
}

/**
 * CU-11: dashboard del mes `YYYY-MM`; sin mes no se envia el parametro y el backend usa el mes
 * actual. Un mes con formato invalido → `ApiError` 400 con el mensaje del servidor.
 */
export async function obtenerDashboard(mes?: string, signal?: AbortSignal): Promise<Dashboard> {
  const path = mes ? `${DASHBOARD_PATH}?${new URLSearchParams({ mes }).toString()}` : DASHBOARD_PATH
  const raw = await httpGet<DashboardResponse>(path, { signal })
  const modelo = raw.estado_modelo ?? null
  return {
    mes: raw.mes,
    embudo: {
      asignadas: raw.embudo.asignadas,
      contactadas: raw.embudo.contactadas,
      ofrecidas: raw.embudo.ofrecidas,
      aceptadas: raw.embudo.aceptadas,
      renovaron: raw.embudo.renovaron,
    },
    porCampania: raw.por_campania.map(toResultado),
    estadoModelo: modelo && {
      version: modelo.version,
      fechaEntrenamiento: new Date(modelo.fecha_entrenamiento),
      ciclosEntrenamiento: modelo.ciclos_entrenamiento,
      proximaFechaReentrenamiento: modelo.proxima_fecha_reentrenamiento ?? null,
      ciclosNuevosEvaluables: modelo.ciclos_nuevos_evaluables,
    },
    piloto: raw.piloto ? toPiloto(raw.piloto) : pilotoSinDatos(),
  }
}

/** Nombre anterior de `obtenerDashboard` (se conserva por compatibilidad). */
export const getDashboard = obtenerDashboard
