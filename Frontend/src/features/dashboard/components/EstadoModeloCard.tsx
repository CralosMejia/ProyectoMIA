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

/** Presentacional: estado del modelo de prediccion vigente (CU-11). */
export function EstadoModeloCard({ estadoModelo }: EstadoModeloCardProps) {
  return (
    <section
      aria-labelledby="modelo-title"
      className="flex flex-col gap-3 rounded-card border border-ink/20 p-4 font-sans text-ink"
    >
      <h2 id="modelo-title" className="text-lg font-semibold">
        Modelo de predicción
      </h2>
      {estadoModelo === null ? (
        <p>{SIN_MODELO_VIGENTE}</p>
      ) : (
        <>
          <p className="font-semibold">{`Versión ${estadoModelo.version}`}</p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
            <dt className="text-ink/70">Fecha de entrenamiento</dt>
            <dd>{FECHA.format(estadoModelo.fechaEntrenamiento)}</dd>
            <dt className="text-ink/70">Ciclos usados para entrenar</dt>
            <dd>{estadoModelo.ciclosEntrenamiento}</dd>
            <dt className="text-ink/70">Próxima revisión</dt>
            <dd>{fechaSinHora(estadoModelo.proximaFechaReentrenamiento)}</dd>
            <dt className="text-ink/70">Ciclos nuevos evaluables</dt>
            <dd>{estadoModelo.ciclosNuevosEvaluables}</dd>
          </dl>
        </>
      )}
    </section>
  )
}
