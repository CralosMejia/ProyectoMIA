import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { porcentaje } from '../hooks/presentacion'
import type { Embudo } from '../types'

export interface EmbudoGestionProps {
  embudo: Embudo
}

interface Etapa {
  clave: keyof Embudo
  etiqueta: string
  /** Palabra corta para el texto accesible del grafico. */
  corta: string
}

const ETAPAS: Etapa[] = [
  { clave: 'asignadas', etiqueta: 'Gestiones asignadas', corta: 'asignadas' },
  { clave: 'contactadas', etiqueta: 'Socios contactados', corta: 'contactadas' },
  { clave: 'ofrecidas', etiqueta: 'Campaña ofrecida', corta: 'ofrecidas' },
  { clave: 'aceptadas', etiqueta: 'Campaña aceptada', corta: 'aceptadas' },
  { clave: 'renovaron', etiqueta: 'Renovaron', corta: 'renovaron' },
]

interface FilaEmbudo {
  clave: keyof Embudo
  etapa: string
  numero: number
  porcentaje: string
}

const COLUMNAS: DataTableColumn<FilaEmbudo>[] = [
  { key: 'etapa', header: 'Etapa' },
  { key: 'numero', header: 'Número' },
  { key: 'porcentaje', header: '% de asignadas' },
]

/** Ancho de la barra en % entero sobre las asignadas (solo para dibujar; 0 si no hay asignadas). */
function ancho(valor: number, asignadas: number): number {
  if (asignadas <= 0 || valor <= 0) return 0
  return Math.min(100, Math.round((valor * 100) / asignadas))
}

/**
 * Presentacional: embudo de la gestion del mes en barras horizontales (sin libreria de graficos).
 * Cada etapa muestra su numero y el % sobre las asignadas; el grafico es una imagen accesible con
 * un resumen de las cifras y debajo va una tabla equivalente.
 */
export function EmbudoGestion({ embudo }: EmbudoGestionProps) {
  const filas: FilaEmbudo[] = ETAPAS.map(({ clave, etiqueta }) => ({
    clave,
    etapa: etiqueta,
    numero: embudo[clave],
    porcentaje: porcentaje(embudo[clave], embudo.asignadas),
  }))
  const resumen = `Embudo del mes: ${ETAPAS.map(({ clave, corta }) => `${corta} ${embudo[clave]}`).join(', ')}`

  return (
    <section
      aria-labelledby="embudo-title"
      className="flex flex-col gap-5 rounded-card border border-line bg-surface p-5 font-sans text-ink shadow-sm"
    >
      <header className="flex flex-col gap-1">
        <h2 id="embudo-title" className="text-lg font-semibold">
          Avance de las gestiones con campaña
        </h2>
        <p className="text-sm text-muted">Porcentaje sobre las gestiones asignadas</p>
      </header>

      <div role="img" aria-label={resumen} className="flex flex-col gap-4">
        {filas.map((fila) => (
          <div key={fila.clave} data-etapa={fila.clave} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium text-ink">{fila.etapa}</span>
              <span className="tabular-nums">
                <span className="text-base font-semibold">{fila.numero}</span>
                <span className="text-muted">{` · ${fila.porcentaje}`}</span>
              </span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-pill bg-ink/10">
              <div
                data-barra
                className={`h-full rounded-pill transition-[width] duration-500 ${fila.clave === 'renovaron' ? 'bg-ok' : 'bg-brand'}`}
                // Unico valor dinamico: el ancho depende del dato y no puede ser una clase fija.
                style={{ width: `${ancho(fila.numero, embudo.asignadas)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <DataTable
        caption="Datos del embudo"
        columns={COLUMNAS}
        rows={filas}
        getRowKey={(fila) => fila.clave}
        emptyMessage="Sin datos"
      />
    </section>
  )
}
