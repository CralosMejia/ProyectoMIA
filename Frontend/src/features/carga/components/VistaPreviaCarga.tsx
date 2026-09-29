import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import type { CargaResumen, ErrorFila, VistaPreviaCarga as VistaPrevia } from '../types'

const FECHA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeZone: 'UTC' })

/** Fecha `YYYY-MM-DD` formateada en es-EC sin desplazamiento por zona horaria. */
function formatearFecha(iso: string): string {
  return FECHA.format(new Date(`${iso}T00:00:00Z`))
}

function rango(desde: string | null, hasta: string | null): string {
  if (desde === null || hasta === null) return 'Sin vencimientos'
  return `${formatearFecha(desde)} – ${formatearFecha(hasta)}`
}

const COLUMNAS_ERROR: DataTableColumn<ErrorFila>[] = [
  { key: 'fila', header: 'Fila' },
  { key: 'columna', header: 'Columna', render: (error) => error.columna ?? '—' },
  { key: 'motivo', header: 'Motivo' },
]

function Dato({ termino, valor }: { termino: string; valor: string | number }) {
  return (
    <>
      <dt className="text-ink/70">{termino}</dt>
      <dd>{valor}</dd>
    </>
  )
}

export interface VistaPreviaCargaProps {
  vistaPrevia: VistaPrevia
  puedeConfirmar: boolean
  enviando: boolean
  onConfirmar: () => void
}

/** Presentacional: conteos de la vista previa, tabla de errores y boton de confirmacion. */
export function VistaPreviaCarga({
  vistaPrevia,
  puedeConfirmar,
  enviando,
  onConfirmar,
}: VistaPreviaCargaProps) {
  return (
    <section
      aria-labelledby="vista-previa-title"
      className="rounded-card border border-ink/20 p-4 font-sans text-ink"
    >
      <h2 id="vista-previa-title" className="mb-4 text-lg font-semibold">
        Vista previa
      </h2>
      <dl className="mb-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
        <Dato termino="Filas leídas" valor={vistaPrevia.filasLeidas} />
        <Dato termino="Filas válidas" valor={vistaPrevia.filasValidas} />
        <Dato termino="Filas con error" valor={vistaPrevia.filasConError} />
        <Dato termino="Filas duplicadas" valor={vistaPrevia.filasDuplicadas} />
        <Dato
          termino="Rango de vencimientos"
          valor={rango(vistaPrevia.vencimientoDesde, vistaPrevia.vencimientoHasta)}
        />
      </dl>

      {vistaPrevia.errores.length > 0 && (
        <div className="mb-4">
          <DataTable
            caption="Filas con error"
            columns={COLUMNAS_ERROR}
            rows={vistaPrevia.errores}
            getRowKey={(error) => `${error.fila}-${error.columna ?? ''}-${error.motivo}`}
            emptyMessage="Sin errores"
          />
        </div>
      )}

      {!puedeConfirmar && !enviando && (
        <p className="mb-4 text-ink/70">
          No se puede confirmar: corrija el archivo o verifique que tenga filas nuevas.
        </p>
      )}

      <button
        type="button"
        onClick={onConfirmar}
        disabled={!puedeConfirmar || enviando}
        className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:opacity-50"
      >
        Confirmar
      </button>
    </section>
  )
}

export interface ResumenCargaProps {
  resumen: CargaResumen
}

/** Presentacional: resultado de una carga confirmada. */
export function ResumenCarga({ resumen }: ResumenCargaProps) {
  return (
    <section
      aria-labelledby="resumen-carga-title"
      className="rounded-card border border-ink/20 p-4 font-sans text-ink"
    >
      <h2 id="resumen-carga-title" className="mb-4 text-lg font-semibold">
        Carga guardada
      </h2>
      <dl className="mb-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
        <Dato termino="Archivo" valor={resumen.nombreArchivo} />
        <Dato termino="Filas guardadas" valor={resumen.filasGuardadas} />
        <Dato termino="Filas duplicadas" valor={resumen.filasDuplicadas} />
        <Dato termino="Socios enlazados" valor={resumen.sociosEnlazados} />
      </dl>
      {resumen.avisosEnlace.length > 0 && (
        <>
          <h3 className="mb-2 font-semibold">Avisos de enlace</h3>
          <ul className="list-disc pl-6">
            {resumen.avisosEnlace.map((aviso) => (
              <li key={aviso}>{aviso}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
