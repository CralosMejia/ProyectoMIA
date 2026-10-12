import { Link } from 'react-router-dom'
import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { Boton, Tarjeta } from '../../../shared/ui/Diseno'
import type { CargaResumen, ErrorFila, VistaPreviaCarga as VistaPrevia } from '../types'

const FECHA = new Intl.DateTimeFormat('es-EC', {
  dateStyle: 'long',
  timeZone: 'UTC',
})

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
  {
    key: 'columna',
    header: 'Columna',
    render: (error) => error.columna ?? '—',
  },
  { key: 'motivo', header: 'Motivo' },
]

const CLASE_DATOS = 'grid gap-3 sm:grid-cols-2 lg:grid-cols-3'

/** Par termino/valor como mosaico: el `dd` sigue inmediatamente al `dt`. */
function Dato({ termino, valor }: { termino: string; valor: string | number }) {
  return (
    <div className="flex flex-col gap-1 rounded-card bg-canvas p-4">
      <dt className="text-sm text-muted">{termino}</dt>
      <dd
        className={
          typeof valor === 'number' ? 'text-2xl font-semibold tabular-nums' : 'font-medium'
        }
      >
        {valor}
      </dd>
    </div>
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
    <Tarjeta aria-labelledby="vista-previa-title">
      <h2 id="vista-previa-title" className="text-lg font-semibold">
        Vista previa
      </h2>
      <dl className={CLASE_DATOS}>
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
        <DataTable
          caption="Filas con error"
          columns={COLUMNAS_ERROR}
          rows={vistaPrevia.errores}
          getRowKey={(error) => `${error.fila}-${error.columna ?? ''}-${error.motivo}`}
          emptyMessage="Sin errores"
        />
      )}

      {!puedeConfirmar && !enviando && (
        <p className="rounded-card border border-degraded/40 border-l-4 border-l-degraded bg-degraded/10 p-4 text-sm">
          No se puede confirmar: corrija el archivo o verifique que tenga filas nuevas.
        </p>
      )}

      <Boton
        variante="primario"
        onClick={onConfirmar}
        disabled={!puedeConfirmar || enviando}
        className="self-end"
      >
        Confirmar carga
      </Boton>
    </Tarjeta>
  )
}

export interface ResumenCargaProps {
  resumen: CargaResumen
}

/** Presentacional: resultado de una carga confirmada, avisos para revisar y enlace a la lista. */
export function ResumenCarga({ resumen }: ResumenCargaProps) {
  return (
    <Tarjeta aria-labelledby="resumen-carga-title" className="border-t-4 border-t-ok">
      <h2 id="resumen-carga-title" className="text-lg font-semibold">
        Carga guardada
      </h2>
      <dl className={CLASE_DATOS}>
        <Dato termino="Archivo" valor={resumen.nombreArchivo} />
        <Dato termino="Filas leídas" valor={resumen.filasLeidas} />
        <Dato termino="Filas guardadas" valor={resumen.filasGuardadas} />
        <Dato termino="Filas duplicadas (no se guardaron)" valor={resumen.filasDuplicadas} />
        <Dato termino="Socios enlazados con su historia" valor={resumen.sociosEnlazados} />
      </dl>
      {resumen.avisosEnlace.length > 0 && (
        <section
          aria-labelledby="resumen-carga-revisar"
          className="flex flex-col gap-2 rounded-card border border-degraded/40 bg-degraded/10 p-4"
        >
          <h3 id="resumen-carga-revisar" className="text-base font-semibold">
            Para revisar
          </h3>
          <ul className="list-disc pl-6 text-sm">
            {resumen.avisosEnlace.map((aviso) => (
              <li key={aviso}>{aviso}</li>
            ))}
          </ul>
        </section>
      )}
      <Link
        to="/lista"
        className="self-start font-medium text-brand underline underline-offset-4 hover:text-brand-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        Ver la lista de socios por vencer
      </Link>
    </Tarjeta>
  )
}
