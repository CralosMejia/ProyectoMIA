import type { EstadoSistema } from '../types'

export interface EstadoSistemaPanelProps {
  estado: EstadoSistema
}

const FECHA_HORA = new Intl.DateTimeFormat('es-EC', { dateStyle: 'long', timeStyle: 'short' })

function formatear(fecha: Date | null): string {
  return fecha ? FECHA_HORA.format(fecha) : 'Sin registro'
}

/** Presentacional: pinta el estado general del sistema a partir de props. */
export function EstadoSistemaPanel({ estado }: EstadoSistemaPanelProps) {
  if (estado.estado === 'INICIALIZANDO') {
    return (
      <p role="status" className="rounded-card border border-ink/20 p-4 font-sans text-ink">
        Inicializando datos históricos. Esto puede tardar unos minutos.
      </p>
    )
  }

  if (estado.estado === 'FALTAN_DATOS_HISTORICOS') {
    return (
      <div
        role="alert"
        className="rounded-card border border-degraded bg-degraded/10 p-4 font-sans text-ink"
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
    <div className="rounded-card border border-ink/20 p-4 font-sans text-ink">
      <h2 className="mb-4 text-lg font-semibold">Sistema listo</h2>
      {modelo ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
          <dt className="text-ink/70">Versión del modelo</dt>
          <dd>{modelo.version}</dd>
          <dt className="text-ink/70">Fecha de entrenamiento</dt>
          <dd>{formatear(modelo.fechaEntrenamiento)}</dd>
          <dt className="text-ink/70">Última carga</dt>
          <dd>{formatear(estado.ultimaCargaEn)}</dd>
        </dl>
      ) : (
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
          <dt className="text-ink/70">Modelo</dt>
          <dd>Sin modelo vigente</dd>
          <dt className="text-ink/70">Última carga</dt>
          <dd>{formatear(estado.ultimaCargaEn)}</dd>
        </dl>
      )}
    </div>
  )
}
