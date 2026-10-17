import { Tarjeta } from '../../../shared/ui/Diseno'
import {
  decimalConComa,
  fechaEnPalabras,
  montoUsd,
  porcentajeDecimal,
} from '../hooks/presentacion'
import type {
  EstadoIndicador,
  IndicadoresPiloto as DatosPiloto,
  IndicadorProporcion,
} from '../types'

export interface IndicadoresPilotoProps {
  piloto: DatosPiloto
}

export const AVISO_SESGO_PILOTO =
  'Los socios del top 25 se contactan; por eso la precisión observada puede quedar por debajo de la real.'
export const AVISO_NO_CAUSAL = 'Cifras observadas, no causales.'
export const POCOS_CASOS = 'Pocos casos: léase con cuidado'
/** El `n` del monto cuenta solo a los contactados que ya cumplieron los 30 días. */
export const CASOS_MONTO = 'contactados ya verificados'

const SIN_CIFRA = 'Sin cifra'
/** Debajo de este numero de casos se avisa que la cifra es fragil. */
const MINIMO_CASOS = 10

/** Estado traducido para el usuario; nunca se muestra el nombre interno. */
function textoEstado(estado: EstadoIndicador, n: number, pendientes?: number): string {
  switch (estado) {
    case 'COMPLETO':
      return 'Completo'
    case 'PARCIAL':
      return pendientes === undefined
        ? 'Parcial'
        : `Parcial: faltan ${pendientes} por verificar (${n - pendientes} de ${n} verificados)`
    case 'PENDIENTE':
      return 'Pendiente: aún no se puede verificar (se verifica 30 días después del vencimiento)'
    case 'SIN_DATOS':
      return 'Sin datos'
  }
}

const CLASE_ESTADO: Record<EstadoIndicador, string> = {
  COMPLETO: 'bg-ok/10',
  PARCIAL: 'bg-degraded/10',
  PENDIENTE: 'bg-degraded/10',
  SIN_DATOS: 'bg-canvas',
}

interface IndicadorProps {
  nombre: string
  valor: string
  detalle?: string
  n: number
  /** Aclara qué cuenta el `n` cuando no es obvio (p. ej. el monto). */
  casos?: string
  estado: EstadoIndicador
  pendientes?: number
}

/** Un indicador: `dt` con el nombre y sus `dd` (valor, detalle, n, estado y aviso de pocos casos). */
function Indicador({ nombre, valor, detalle, n, casos, estado, pendientes }: IndicadorProps) {
  return (
    <div className="flex break-inside-avoid flex-col gap-1 rounded-card border border-line bg-canvas px-4 py-3">
      <dt className="text-xs font-medium text-muted">{nombre}</dt>
      <dd className="text-2xl font-semibold tabular-nums">{valor}</dd>
      {detalle !== undefined && <dd className="text-sm text-muted tabular-nums">{detalle}</dd>}
      <dd className="text-sm tabular-nums">{casos === undefined ? `n = ${n}` : `n = ${n} ${casos}`}</dd>
      <dd className={`w-fit rounded-pill px-3 py-1 text-xs font-medium ${CLASE_ESTADO[estado]}`}>
        {textoEstado(estado, n, pendientes)}
      </dd>
      {n > 0 && n < MINIMO_CASOS && (
        <dd className="text-xs font-medium text-ink">{POCOS_CASOS}</dd>
      )}
    </div>
  )
}

function Proporcion({ nombre, datos }: { nombre: string; datos: IndicadorProporcion }) {
  return (
    <Indicador
      nombre={nombre}
      valor={datos.valor === null ? SIN_CIFRA : porcentajeDecimal(datos.valor)}
      detalle={datos.denominador > 0 ? `${datos.numerador} de ${datos.denominador}` : undefined}
      n={datos.n}
      estado={datos.estado}
      pendientes={datos.pendientes}
    />
  )
}

function plural(cantidad: number, singular: string, varios: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : varios}`
}

/**
 * Presentacional (R-018 / M04): indicadores del top 25 de la ultima lista del mes. Se imprime con
 * el PDF del dashboard (no lleva la clase que oculta al imprimir) y no se corta entre paginas.
 */
export function IndicadoresPiloto({ piloto }: IndicadoresPilotoProps) {
  const { lista, montoRetenido: monto, diasAnticipacion: dias } = piloto
  const detalleMonto =
    monto.total === null
      ? undefined
      : `${plural(monto.renovaciones, 'renovación', 'renovaciones')}${
          monto.renovacionesSinMonto > 0
            ? `; ${monto.renovacionesSinMonto} sin monto registrado`
            : ''
        }`

  return (
    <Tarjeta aria-labelledby="piloto-title" className="break-inside-avoid">
      <h2 id="piloto-title" className="text-lg font-semibold">
        Indicadores del piloto
      </h2>
      <div className="flex flex-col gap-1 text-sm text-muted">
        {lista === null ? (
          <p>No hay una lista generada en este mes.</p>
        ) : (
          <>
            <p>{`Lista del mes: ${lista.nombre}, generada el ${fechaEnPalabras(lista.fechaGeneracion)}.`}</p>
            <p>
              {piloto.corteVerificacion === null
                ? 'Aún no hay fecha de corte para verificar: todo queda pendiente.'
                : `Verificado con datos hasta el ${fechaEnPalabras(piloto.corteVerificacion)}.`}
            </p>
          </>
        )}
        {piloto.sinDato > 0 && (
          <p>
            {piloto.sinDato === 1
              ? '1 socio del top 25 sin datos de membresía: no cuenta en los casos.'
              : `${piloto.sinDato} socios del top 25 sin datos de membresía: no cuentan en los casos.`}
          </p>
        )}
      </div>

      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Proporcion nombre="Precisión del top 25" datos={piloto.precisionTop25} />
        <Proporcion
          nombre="Contactados antes del vencimiento"
          datos={piloto.contactadosAntesVencimiento}
        />
        <Indicador
          nombre="Días de anticipación"
          valor={dias.valor === null ? SIN_CIFRA : `${decimalConComa(dias.valor)} días`}
          n={dias.n}
          estado={dias.estado}
        />
        <Proporcion
          nombre="Renovación de los contactados"
          datos={piloto.tasaRenovacionContactados}
        />
        <Indicador
          nombre="Monto retenido"
          valor={monto.total === null ? SIN_CIFRA : montoUsd(monto.total)}
          detalle={detalleMonto}
          n={monto.n}
          casos={CASOS_MONTO}
          estado={monto.estado}
          pendientes={monto.pendientes}
        />
      </dl>

      <div className="flex flex-col gap-1 rounded-card bg-degraded/10 px-4 py-3 text-sm text-ink">
        <p>{AVISO_SESGO_PILOTO}</p>
        <p>{AVISO_NO_CAUSAL}</p>
      </div>
    </Tarjeta>
  )
}
