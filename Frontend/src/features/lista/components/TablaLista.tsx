import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { RiskBadge } from '../../../shared/ui/RiskBadge'
import type { ListaPriorizada, Prediccion } from '../types'
import { rangoFechas } from './formatoFechas'

export const SIN_FACTORES = 'Sin factores de riesgo destacados'
export const TITULO_PRIORITARIOS = 'Socios prioritarios a contactar'
export const TITULO_OTROS = 'Otros socios por vencer'
export const SIN_GESTION = 'Sin gestión'
export const SIN_CAMPANIA = 'Sin campaña'

const FECHA_CORTA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'medium', timeZone: 'UTC' })
/** Aporte numerico al final del texto de un factor, p. ej. " (+0,12)". */
const APORTE_FINAL = /\s*\([^()]*\)\s*$/

/** Fecha `YYYY-MM-DD` en es-EC sin desplazamiento por zona horaria. */
function formatearFecha(iso: string, formato: Intl.DateTimeFormat): string {
  return formato.format(new Date(`${iso}T00:00:00Z`))
}

/** Quita el aporte entre parentesis del final: "Plan: TRIMESTRAL (+0,09)" → "Plan: TRIMESTRAL". */
function sinAporte(factor: string): string {
  return factor.replace(APORTE_FINAL, '')
}

function Factores({ factores }: { factores: string[] }) {
  if (factores.length === 0) return <span className="text-ink/60">{SIN_FACTORES}</span>
  return (
    <ul className="list-disc pl-4">
      {factores.map((factor, i) => (
        <li key={`${i}-${factor}`}>{sinAporte(factor)}</li>
      ))}
    </ul>
  )
}

const TEXTO_ESTADO: Record<NonNullable<Prediccion['gestionEstado']>, string> = {
  PENDIENTE: 'Pendiente',
  CERRADA: 'Cerrada',
}

/** Accion segun la gestion: crearla, registrar su resultado o verla (cerrada, solo lectura). */
function accion(p: Prediccion): string {
  if (p.gestionEstado === 'CERRADA') return 'Ver gestión'
  if (p.gestionEstado === 'PENDIENTE') return 'Registrar resultado'
  return 'Gestionar'
}

/** Sin gestion → "—"; gestion sin campaña → "Sin campaña"; si no, el nombre guardado al asignarla. */
function campania(p: Prediccion): string {
  if (p.gestionEstado === null) return '—'
  return p.campaniaAsignada ?? SIN_CAMPANIA
}

function BotonGestion({ prediccion, onGestionar }: { prediccion: Prediccion; onGestionar?: (p: Prediccion) => void }) {
  const texto = accion(prediccion)
  // El nombre accesible lleva la prioridad (unica en la lista), no el nombre del socio.
  return (
    <button
      type="button"
      aria-label={`${texto} prioridad ${prediccion.prioridad}`}
      onClick={() => onGestionar?.(prediccion)}
      className="whitespace-nowrap rounded-pill border border-ink/20 px-3 py-1 text-sm font-medium"
    >
      {texto}
    </button>
  )
}

const COLUMNAS: DataTableColumn<Prediccion>[] = [
  { key: 'prioridad', header: 'Prioridad' },
  { key: 'socioNombre', header: 'Nombre' },
  { key: 'cedula', header: 'Cédula', render: (p) => p.cedula ?? '—' },
  { key: 'plan', header: 'Plan' },
  {
    key: 'fechaVencimiento',
    header: 'Vence el',
    render: (p) => formatearFecha(p.fechaVencimiento, FECHA_CORTA),
  },
  { key: 'diasParaVencer', header: 'Días para vencer' },
  {
    key: 'nivelRiesgo',
    header: 'Nivel de riesgo',
    render: (p) => <RiskBadge nivel={p.nivelRiesgo} />,
  },
  {
    key: 'factoresPrincipales',
    header: 'Motivos principales',
    render: (p) => <Factores factores={p.factoresPrincipales} />,
  },
  {
    key: 'gestionEstado',
    header: 'Gestión',
    render: (p) => (p.gestionEstado === null ? SIN_GESTION : TEXTO_ESTADO[p.gestionEstado]),
  },
  { key: 'campaniaAsignada', header: 'Campaña', render: campania },
]

function columnas(onGestionar?: (p: Prediccion) => void): DataTableColumn<Prediccion>[] {
  return [
    ...COLUMNAS,
    {
      key: 'gestionId',
      header: 'Acción',
      render: (p) => <BotonGestion prediccion={p} onGestionar={onGestionar} />,
    },
  ]
}

function porPrioridad(a: Prediccion, b: Prediccion): number {
  return a.prioridad - b.prioridad
}

interface TablaProps {
  titulo: string
  filas: Prediccion[]
  onGestionar?: (p: Prediccion) => void
}

function Tabla({ titulo, filas, onGestionar }: TablaProps) {
  return (
    <div className="overflow-x-auto">
      <DataTable
        caption={titulo}
        columns={columnas(onGestionar)}
        rows={filas}
        getRowKey={(p) => p.prediccionId}
        emptyMessage="No hay socios cuya membresía venza en esos días."
      />
    </div>
  )
}

export interface TablaListaProps {
  lista: ListaPriorizada
  /** Boton de la fila: gestionar, registrar el resultado o ver la gestion del socio. */
  onGestionar?: (prediccion: Prediccion) => void
}

/**
 * Presentacional: resumen de la lista y dos tablas, los socios prioritarios a contactar
 * (`dentroTopK`) y el resto de socios por vencer, ambas en orden de prioridad, con el estado
 * de la gestion, su campaña y el boton de accion (emite `onGestionar`).
 */
export function TablaLista({ lista, onGestionar }: TablaListaProps) {
  const ordenados = [...lista.items].sort(porPrioridad)
  const prioritarios = ordenados.filter((p) => p.dentroTopK)
  const otros = ordenados.filter((p) => !p.dentroTopK)

  return (
    <section aria-labelledby="tabla-lista-title" className="flex flex-col gap-4 font-sans text-ink">
      <h2 id="tabla-lista-title" className="text-lg font-semibold">
        {lista.nombre}
      </h2>
      <div className="flex flex-col gap-1">
        <p>{`Rango de fechas: ${rangoFechas(lista.fechaGeneracion, lista.horizonteDias)}`}</p>
        <p>{`Socios priorizados para campañas: ${prioritarios.length}`}</p>
      </div>
      <Tabla titulo={TITULO_PRIORITARIOS} filas={prioritarios} onGestionar={onGestionar} />
      {otros.length > 0 && <Tabla titulo={TITULO_OTROS} filas={otros} onGestionar={onGestionar} />}
    </section>
  )
}
