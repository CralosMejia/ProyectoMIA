import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import type { ResultadoCampania } from '../types'

export interface TablaResultadosCampaniaProps {
  filas: ResultadoCampania[]
}

export const CASOS_INSUFICIENTES = 'Casos insuficientes'
export const AVISO_RESULTADOS_OBSERVADOS =
  'Las cifras son resultados observados; no demuestran que la campaña causó la renovación.'

/**
 * Decimal exacto 0..1 como texto → porcentaje con un decimal y coma: "0.40000000" → "40,0 %".
 * Se opera con los digitos (enteros), nunca con coma flotante; redondeo a la mitad hacia arriba.
 */
function porcentaje(decimal: string): string {
  const [entero = '0', fraccion = ''] = decimal.trim().split('.')
  const digitos = fraccion.padEnd(4, '0')
  // Decimas de punto porcentual: valor × 1000.
  let decimas = Number.parseInt(`${entero}${digitos.slice(0, 3)}`, 10)
  if ((digitos[3] ?? '0') >= '5') decimas += 1
  return `${Math.floor(decimas / 10)},${decimas % 10} %`
}

function Tasa({ fila }: { fila: ResultadoCampania }) {
  if (fila.casosInsuficientes || fila.tasaRenovacion === null) {
    return <span className="text-ink/70">{CASOS_INSUFICIENTES}</span>
  }
  return (
    <span>
      {porcentaje(fila.tasaRenovacion)}{' '}
      <span className="text-ink/70">{`(${fila.gestionesCerradas} casos)`}</span>
    </span>
  )
}

const COLUMNAS: DataTableColumn<ResultadoCampania>[] = [
  { key: 'nombre', header: 'Campaña' },
  { key: 'gestiones', header: 'Gestiones' },
  { key: 'contactados', header: 'Contactados' },
  { key: 'renovaciones', header: 'Renovaron' },
  { key: 'tasaRenovacion', header: 'Tasa de renovación', render: (fila) => <Tasa fila={fila} /> },
]

/**
 * Presentacional: resultados del mes por campaña (CU-11). La tasa se muestra con el numero de
 * gestiones cerradas con resultado; con menos de 10, "Casos insuficientes" (RN-11.1).
 */
export function TablaResultadosCampania({ filas }: TablaResultadosCampaniaProps) {
  return (
    <section className="flex flex-col gap-3 font-sans text-ink">
      <DataTable
        caption="Resultados por campaña"
        columns={COLUMNAS}
        rows={filas}
        getRowKey={(fila) => fila.campaniaId ?? 'sin-campania'}
        emptyMessage="No hay gestiones en este mes"
      />
      <p className="text-sm text-ink/70">
        La tasa de renovación se calcula sobre las gestiones cerradas con resultado y solo se
        muestra con 10 o más.
      </p>
      <p className="text-sm font-medium">{AVISO_RESULTADOS_OBSERVADOS}</p>
    </section>
  )
}
