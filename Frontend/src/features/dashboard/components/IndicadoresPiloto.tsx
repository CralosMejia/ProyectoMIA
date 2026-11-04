import type { ReactNode } from 'react'
import { BotonAyuda } from '../../../shared/ui/Ayuda'
import { Tarjeta } from '../../../shared/ui/Diseno'
import {
  anticipacionPiloto,
  detalleAnticipacion,
  embudoPiloto,
  fechaEnPalabras,
  textoEstadoPiloto,
} from '../hooks/presentacion'
import type { IndicadoresPiloto as DatosPiloto } from '../types'
import { DefinicionesPiloto } from './AyudaDashboard'

export interface IndicadoresPilotoProps {
  piloto: DatosPiloto
}

export const TITULO_PILOTO = '¿Cómo le fue a la lista del mes?'
export const AVISO_NO_CAUSAL =
  'Estas cifras cuentan lo que pasó; no prueban que la llamada haya causado la renovación.'
export const POCOS_CASOS = 'Son pocos socios todavía: tómalo con cuidado'

/** Debajo de este numero de casos se avisa que la cifra es fragil. */
const MINIMO_CASOS = 10

/** "1 socio" / "N socios" (y en general: singular solo con 1). */
function contar(cantidad: number, singular: string, plural: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural}`
}

function socios(cantidad: number): string {
  return contar(cantidad, 'socio', 'socios')
}

/** Bloque de un grafico: `h3`, dibujo y textos; no se corta entre paginas. */
function Grafico({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <section
      aria-labelledby={id}
      className="flex min-w-0 break-inside-avoid flex-col gap-3 rounded-card border border-line bg-canvas px-4 py-3"
    >
      <h3 id={id} className="text-base font-semibold">
        {titulo}
      </h3>
      {children}
    </section>
  )
}

function Estado({ texto }: { texto: string }) {
  return <p className="text-sm font-medium text-ink">{texto}</p>
}

function PocosCasos({ n }: { n: number }) {
  return n > 0 && n < MINIMO_CASOS ? (
    <p className="text-xs font-medium text-ink">{POCOS_CASOS}</p>
  ) : null
}

/** Muestra de la leyenda con la misma forma que en el dibujo. */
function Muestra({ forma }: { forma: string }) {
  return <span aria-hidden="true" className={`inline-block size-3.5 shrink-0 ${forma}`} />
}

function ItemLeyenda({
  forma,
  etiqueta,
  numero,
}: {
  forma: string
  etiqueta: string
  numero: number
}) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <Muestra forma={forma} />
      <span>
        {etiqueta} <span className="font-semibold tabular-nums">{numero}</span>
      </span>
    </li>
  )
}

const FORMA_RENOVARON = 'rounded-pill bg-ok'
const FORMA_POR_CONFIRMAR = 'rounded-pill rayado'

function EmbudoPiloto({ piloto }: IndicadoresPilotoProps) {
  const [lista, contactados, renovaron] = embudoPiloto(piloto)
  const tasa = piloto.tasaRenovacionContactados
  const resumen = `${socios(lista.numero)} en la lista del mes, ${contar(contactados.numero, 'contactado', 'contactados')}, ${contactados.antesVencimiento} antes del vencimiento, ${contar(renovaron.numero, 'renovó', 'renovaron')} y ${renovaron.porConfirmar} por confirmar`

  return (
    <Grafico id="piloto-embudo-title" titulo="¿Cuántos contactamos y cuántos renovaron?">
      <div role="img" aria-label={resumen} className="flex flex-col gap-3">
        <Barra etiqueta={lista.etapa} numero={lista.numero}>
          <div
            data-barra="lista"
            className="h-full rounded-pill bg-brand"
            // Unico valor dinamico: el ancho depende del dato.
            style={{ width: `${lista.ancho}%` }}
          />
        </Barra>
        <Barra
          etiqueta={contactados.etapa}
          numero={contactados.numero}
          detalle={`${contactados.antesVencimiento} antes del vencimiento`}
        >
          <div
            data-barra="contactados"
            className="h-full rounded-pill bg-brand"
            style={{ width: `${contactados.ancho}%` }}
          />
        </Barra>
        <Barra
          etiqueta={renovaron.etapa}
          numero={renovaron.numero}
          detalle={
            renovaron.porcentaje === null
              ? undefined
              : `${renovaron.porcentaje} de los contactados ya confirmados`
          }
        >
          <div
            data-barra="renovaron"
            className="h-full bg-ok"
            style={{ width: `${renovaron.ancho}%` }}
          />
          <div
            data-barra="por-confirmar"
            className="rayado h-full"
            style={{ width: `${renovaron.anchoPorConfirmar}%` }}
          />
        </Barra>
      </div>
      <ul aria-label="Leyenda del embudo" className="flex flex-wrap gap-x-4 gap-y-1">
        <ItemLeyenda forma={FORMA_RENOVARON} etiqueta="Renovaron" numero={renovaron.numero} />
        <ItemLeyenda
          forma={FORMA_POR_CONFIRMAR}
          etiqueta="Por confirmar"
          numero={renovaron.porConfirmar}
        />
      </ul>
      <Estado texto={textoEstadoPiloto(tasa.estado, tasa.pendientes)} />
      <PocosCasos n={tasa.n} />
    </Grafico>
  )
}

function Barra({
  etiqueta,
  numero,
  detalle,
  children,
}: {
  etiqueta: string
  numero: number
  detalle?: string
  children: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">{etiqueta}</span>
        <span className="text-base font-semibold tabular-nums">{numero}</span>
      </div>
      <div className="flex h-3 overflow-hidden rounded-pill bg-ink/10">{children}</div>
      {detalle !== undefined && <span className="text-xs text-muted tabular-nums">{detalle}</span>}
    </div>
  )
}

/** Forma de cada tramo: los de "antes" en color de marca y "el mismo día o después" rayado. */
const FORMA_TRAMO = ['bg-brand', 'bg-brand', 'bg-brand', 'rayado'] as const

function LineaAnticipacion({ piloto }: IndicadoresPilotoProps) {
  const dias = piloto.diasAnticipacion
  const linea = anticipacionPiloto(dias.valor)
  const detalle = detalleAnticipacion(piloto)
  const conLlamadas = dias.n > 0
  const promedio = detalle.posicionPromedio

  return (
    <Grafico id="piloto-anticipacion-title" titulo="¿Con cuánta anticipación?">
      <div role="img" aria-label={detalle.resumen} className="px-10 pt-7 pb-2">
        <div data-linea-anticipacion className="relative border-t-2 border-current text-ink">
          {detalle.marcas.map((marca) =>
            marca.vence ? (
              <Marca
                key={marca.etiqueta}
                id="Vencimiento"
                etiqueta={marca.etiqueta}
                posicion={marca.posicion}
                forma="h-5 border-l-4 border-current"
                negrita
              />
            ) : (
              <Marca
                key={marca.etiqueta}
                id={marca.etiqueta}
                etiqueta={marca.etiqueta}
                posicion={marca.posicion}
                forma="h-2.5 border-l-2 border-current"
              />
            ),
          )}
          {promedio !== null && detalle.etiquetaPromedio !== null && (
            <Marca
              id="Llamada"
              etiqueta={detalle.etiquetaPromedio}
              posicion={promedio}
              forma="size-3.5 rounded-pill bg-brand"
              arriba
              alinear={promedio < 50 ? 'inicio' : 'fin'}
            />
          )}
        </div>
        <div className="h-5" />
      </div>
      <p className="text-sm tabular-nums">{linea.frase}</p>
      {detalle.fraseConteo !== null && (
        <p className="text-sm tabular-nums">{`${detalle.fraseConteo}.`}</p>
      )}
      {detalle.fraseRango !== null && (
        <p className="text-sm tabular-nums">{`${detalle.fraseRango}.`}</p>
      )}
      {conLlamadas && detalle.tramos !== null && (
        <ul aria-label="Llamadas según los días antes del vencimiento" className="flex flex-col gap-2">
          {detalle.tramos.map((tramo, i) => (
            <li key={tramo.etiqueta}>
              <Barra etiqueta={tramo.etiqueta} numero={tramo.numero}>
                <div
                  data-tramo
                  className={`h-full rounded-pill ${FORMA_TRAMO[i] ?? 'bg-brand'}`}
                  style={{ width: `${tramo.ancho}%` }}
                />
              </Barra>
            </li>
          ))}
        </ul>
      )}
      {conLlamadas && <p className="text-xs text-muted">{detalle.lectura}</p>}
      {dias.estado === 'SIN_DATOS' ? (
        <Estado texto={textoEstadoPiloto(dias.estado, 0)} />
      ) : (
        conLlamadas && (
          <p className="text-xs text-muted">{`Promedio de ${contar(dias.n, 'socio llamado', 'socios llamados')}.`}</p>
        )
      )}
      <PocosCasos n={dias.n} />
    </Grafico>
  )
}

const ALINEACION = {
  centro: 'left-1/2 -translate-x-1/2',
  inicio: 'left-0',
  fin: 'right-0',
} as const

/**
 * Marca sobre la escala en dias; `posicion` 0..100 (solo para dibujar). La etiqueta va debajo
 * (o arriba, la del promedio) y se alinea hacia dentro para no salirse de la tarjeta.
 */
function Marca({
  id,
  etiqueta,
  posicion,
  forma,
  arriba = false,
  negrita = false,
  alinear = 'centro',
}: {
  id: string
  etiqueta: string
  posicion: number
  forma: string
  arriba?: boolean
  negrita?: boolean
  alinear?: keyof typeof ALINEACION
}) {
  return (
    <span
      data-marca={id}
      className="absolute top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
      // Unico valor dinamico: la posicion depende del dato.
      style={{ left: `${posicion}%` }}
    >
      <span aria-hidden="true" data-forma-anticipacion className={forma} />
      <span
        className={`absolute whitespace-nowrap text-xs ${negrita ? 'font-semibold' : 'font-medium'} ${ALINEACION[alinear]} ${arriba ? 'bottom-full mb-1' : 'top-full mt-1'}`}
      >
        {etiqueta}
      </span>
    </span>
  )
}

/**
 * Presentacional (R-018 / R-021 / R-022): como le fue a la ultima lista del mes, en dos graficos en
 * lenguaje simple y sin dinero. Las cifras salen de `hooks/presentacion`; se imprime con el PDF
 * del dashboard y no se corta entre paginas.
 */
export function IndicadoresPiloto({ piloto }: IndicadoresPilotoProps) {
  const { lista } = piloto

  return (
    <Tarjeta aria-labelledby="piloto-title" className="break-inside-avoid">
      <h2 id="piloto-title" className="text-lg font-semibold">
        {TITULO_PILOTO}
      </h2>
      <div className="flex flex-col gap-1 text-sm text-muted">
        {lista === null ? (
          <p>No hay una lista generada en este mes.</p>
        ) : (
          <>
            <p>{`Lista del mes: ${lista.nombre}, generada el ${fechaEnPalabras(lista.fechaGeneracion)}.`}</p>
            <p>
              {piloto.corteVerificacion === null
                ? 'Todavía no hay datos para confirmar resultados.'
                : `Resultados confirmados con datos hasta el ${fechaEnPalabras(piloto.corteVerificacion)}.`}
            </p>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <EmbudoPiloto piloto={piloto} />
        <LineaAnticipacion piloto={piloto} />
      </div>

      <div className="flex flex-col gap-1 rounded-card bg-degraded/10 px-4 py-3 text-sm text-ink">
        <p>{AVISO_NO_CAUSAL}</p>
      </div>

      {/* Las definiciones exactas no van al papel; el resto de la tarjeta si. */}
      <div className="flex print:hidden">
        <BotonAyuda titulo="¿Cómo se calcula?">
          <DefinicionesPiloto />
        </BotonAyuda>
      </div>
    </Tarjeta>
  )
}
