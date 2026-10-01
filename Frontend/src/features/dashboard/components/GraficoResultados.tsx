import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { porcentaje, type ResumenResultados } from '../hooks/presentacion'

export interface GraficoResultadosProps {
  resumen: ResumenResultados
}

interface Sector {
  clave: 'renovaron' | 'noRenovaron' | 'sinResultado'
  resultado: string
  numero: number
  porcentaje: string
  /** Clase de trazo del sector en el SVG (token). */
  trazo: string
  /** Clase de fondo de la muestra de la leyenda (mismo token). */
  muestra: string
}

const COLUMNAS: DataTableColumn<Sector>[] = [
  { key: 'resultado', header: 'Resultado' },
  { key: 'numero', header: 'Número' },
  { key: 'porcentaje', header: '%' },
]

/** Radio del anillo dentro de un viewBox de 120 × 120. */
const RADIO = 46
/** Separacion entre sectores, en unidades de `pathLength` (100 = vuelta completa). */
const SEPARACION = 0.8

function sectores(resumen: ResumenResultados): Sector[] {
  const { renovaron, noRenovaron, sinResultado, total } = resumen
  return [
    {
      clave: 'renovaron',
      resultado: 'Renovaron',
      numero: renovaron,
      porcentaje: porcentaje(renovaron, total),
      trazo: 'stroke-ok',
      muestra: 'bg-ok',
    },
    {
      clave: 'noRenovaron',
      resultado: 'No renovaron',
      numero: noRenovaron,
      porcentaje: porcentaje(noRenovaron, total),
      trazo: 'stroke-risk-high',
      muestra: 'bg-risk-high',
    },
    {
      clave: 'sinResultado',
      resultado: 'Sin resultado',
      numero: sinResultado,
      porcentaje: porcentaje(sinResultado, total),
      trazo: 'stroke-ink/30',
      muestra: 'bg-ink/30',
    },
  ]
}

/** Arcos del anillo: longitud y desplazamiento en unidades de `pathLength` (solo para dibujar). */
function arcos(lista: Sector[], total: number) {
  const visibles = lista.filter((s) => s.numero > 0)
  const separacion = visibles.length > 1 ? SEPARACION : 0
  let inicio = 0
  return visibles.map((sector) => {
    const largo = (sector.numero * 100) / total
    const arco = { sector, largo: Math.max(largo - separacion, 0.1), inicio }
    inicio += largo
    return arco
  })
}

/**
 * Presentacional: dona "Resultado de las gestiones del mes" en SVG propio (sin libreria).
 * Renovaron, no renovaron y sin resultado se dibujan por separado; leyenda y tabla equivalente.
 */
export function GraficoResultados({ resumen }: GraficoResultadosProps) {
  const lista = sectores(resumen)
  const vacio = resumen.total <= 0
  const resumenAccesible = `Resultado de las gestiones del mes: ${lista
    .map((s) => `${s.resultado.toLowerCase()} ${s.numero} (${s.porcentaje})`)
    .join(', ')}; total ${resumen.total}`

  return (
    <section
      aria-labelledby="resultados-title"
      className="flex flex-col gap-5 rounded-card border border-ink/10 bg-surface p-5 font-sans text-ink shadow-sm"
    >
      <header className="flex flex-col gap-1">
        <h2 id="resultados-title" className="text-lg font-semibold">
          Resultado de las gestiones del mes
        </h2>
        <p className="text-sm text-ink/60">Sin resultado: gestiones abiertas o sin campaña.</p>
      </header>

      {vacio ? (
        <p className="rounded-card bg-ink/5 p-4 text-center text-ink/70">Sin gestiones en este mes</p>
      ) : (
        <>
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
            <div role="img" aria-label={resumenAccesible} className="relative size-44 shrink-0">
              <svg viewBox="0 0 120 120" className="size-full" aria-hidden="true">
                <circle
                  cx="60"
                  cy="60"
                  r={RADIO}
                  fill="none"
                  strokeWidth="14"
                  className="stroke-ink/5"
                />
                {arcos(lista, resumen.total).map(({ sector, largo, inicio }) => (
                  <circle
                    key={sector.clave}
                    data-sector={sector.clave}
                    cx="60"
                    cy="60"
                    r={RADIO}
                    fill="none"
                    strokeWidth="14"
                    pathLength={100}
                    strokeDasharray={`${largo} ${100 - largo}`}
                    strokeDashoffset={-inicio}
                    transform="rotate(-90 60 60)"
                    className={sector.trazo}
                  />
                ))}
              </svg>
              <p className="absolute inset-0 flex flex-col items-center justify-center leading-tight">
                <span className="text-3xl font-bold tabular-nums">{resumen.total}</span>{' '}
                <span className="text-sm text-ink/60">
                  {resumen.total === 1 ? 'gestión' : 'gestiones'}
                </span>
              </p>
            </div>

            <ul aria-label="Leyenda" className="flex flex-col gap-3">
              {lista.map((s) => (
                <li key={s.clave} className="flex items-center gap-3">
                  <span aria-hidden="true" className={`size-3.5 shrink-0 rounded-pill ${s.muestra}`} />
                  <span className="text-sm">
                    <span className="font-medium">{s.resultado}</span>{' '}
                    <span className="font-semibold tabular-nums">{s.numero}</span>{' '}
                    <span className="text-ink/60 tabular-nums">{`(${s.porcentaje})`}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <DataTable
            caption="Datos del gráfico de resultados"
            columns={COLUMNAS}
            rows={lista}
            getRowKey={(s) => s.clave}
            emptyMessage="Sin gestiones en este mes"
          />
        </>
      )}
    </section>
  )
}
