import { Tarjeta } from '../../../shared/ui/Diseno'
import type { EstadoModelo } from '../types'

export interface EstadoModeloCardProps {
  estadoModelo: EstadoModelo | null
}

export const SIN_MODELO_VIGENTE = 'Aún no hay un modelo vigente'

const FECHA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long' })
// Fechas sin hora (`YYYY-MM-DD`): en UTC para no correr el dia por la zona horaria.
const FECHA_SIN_HORA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeZone: 'UTC' })

function fechaSinHora(iso: string | null): string {
  return iso === null ? 'Sin fecha programada' : FECHA_SIN_HORA.format(new Date(`${iso}T00:00:00Z`))
}

/** Una cifra del modelo: `dt` y su `dd` hermano inmediato dentro de un recuadro. */
function Dato({ titulo, valor }: { titulo: string; valor: string | number }) {
  return (
    <div className="flex flex-col gap-1 rounded-card border border-line bg-canvas px-4 py-3">
      <dt className="text-xs font-medium text-muted">{titulo}</dt>
      <dd className="text-base font-semibold tabular-nums">{valor}</dd>
    </div>
  )
}

/** Presentacional: estado del modelo de prediccion vigente (CU-11). */
export function EstadoModeloCard({ estadoModelo }: EstadoModeloCardProps) {
  return (
    <Tarjeta aria-labelledby="modelo-title">
      <h2 id="modelo-title" className="text-lg font-semibold">
        Modelo de predicción
      </h2>
      {estadoModelo === null ? (
        <p className="text-sm text-muted">{SIN_MODELO_VIGENTE}</p>
      ) : (
        <>
          <p className="w-fit rounded-pill bg-brand/10 px-3 py-1 text-sm font-semibold text-brand-strong">{`Versión ${estadoModelo.version}`}</p>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Dato
              titulo="Fecha de entrenamiento"
              valor={FECHA.format(estadoModelo.fechaEntrenamiento)}
            />
            <Dato titulo="Ciclos usados para entrenar" valor={estadoModelo.ciclosEntrenamiento} />
            <Dato
              titulo="Próxima revisión"
              valor={fechaSinHora(estadoModelo.proximaFechaReentrenamiento)}
            />
            <Dato titulo="Ciclos nuevos evaluables" valor={estadoModelo.ciclosNuevosEvaluables} />
          </dl>
        </>
      )}
    </Tarjeta>
  )
}
