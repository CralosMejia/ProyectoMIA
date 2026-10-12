import { Tarjeta } from '../../../shared/ui/Diseno'
import type { EstadoSistema } from '../types'

export interface EstadoSistemaPanelProps {
  estado: EstadoSistema
}

const FECHA_HORA = new Intl.DateTimeFormat('es-EC', {
  dateStyle: 'long',
  timeStyle: 'short',
})
const FECHA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long' })

export const SIN_MODELO = 'El modelo de predicción aún no está disponible'

function formatear(fecha: Date | null): string {
  return fecha ? FECHA_HORA.format(fecha) : 'Sin registro'
}

/** Presentacional: pinta el estado general del sistema a partir de props. */
export function EstadoSistemaPanel({ estado }: EstadoSistemaPanelProps) {
  if (estado.estado === 'INICIALIZANDO') {
    return (
      <p
        role="status"
        className="flex items-center gap-3 rounded-card border border-line bg-surface p-5 font-sans text-ink shadow-sm"
      >
        <span
          aria-hidden="true"
          className="size-2.5 shrink-0 animate-pulse rounded-pill bg-brand"
        />
        Inicializando datos históricos. Esto puede tardar unos minutos.
      </p>
    )
  }

  if (estado.estado === 'FALTAN_DATOS_HISTORICOS') {
    return (
      <div
        role="alert"
        className="flex flex-col gap-1 rounded-card border border-degraded/40 border-l-4 border-l-degraded bg-degraded/10 p-4 font-sans text-sm text-ink"
      >
        <p className="font-semibold">Faltan los datos históricos.</p>
        <p>
          Revise que los libros históricos estén en la carpeta configurada para la instalación y
          reinicie el sistema.
        </p>
      </div>
    )
  }

  const modelo = estado.modeloVigente

  return (
    <Tarjeta
      titulo={
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="size-2.5 rounded-pill bg-ok" />
          Sistema listo
        </span>
      }
    >
      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1 rounded-card bg-canvas p-4">
          <dt className="text-sm text-muted">Modelo de predicción</dt>
          <dd className="font-medium">
            {modelo ? `Activo desde ${FECHA.format(modelo.fechaEntrenamiento)}` : SIN_MODELO}
          </dd>
        </div>
        <div className="flex flex-col gap-1 rounded-card bg-canvas p-4">
          <dt className="text-sm text-muted">Última carga</dt>
          <dd className="font-medium">{formatear(estado.ultimaCargaEn)}</dd>
        </div>
      </dl>
    </Tarjeta>
  )
}
