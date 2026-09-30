import { useState } from 'react'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { Modal } from '../../../shared/ui/Modal'
import { FormularioCampania } from '../components/FormularioCampania'
import { TablaCampanias } from '../components/TablaCampanias'
import { useCampanias } from '../hooks/useCampanias'
import type { Campania, CampaniaEntrada } from '../types'

const AVISO_INACTIVAR =
  'La campaña dejará de sugerirse; las gestiones que ya la usan la conservan.'

type Dialogo =
  | { tipo: 'nueva' }
  | { tipo: 'editar'; campania: Campania }
  | { tipo: 'inactivar'; campania: Campania }
  | null

/** Página de ruta de campañas (CU-06): conecta `useCampanias` con la tabla y el formulario. */
export default function CampaniasPage() {
  const vista = useCampanias()
  const [dialogo, setDialogo] = useState<Dialogo>(null)

  const abrir = (siguiente: Dialogo) => {
    vista.limpiarError()
    setDialogo(siguiente)
  }

  const cerrar = () => {
    if (vista.guardando) return
    vista.limpiarError()
    setDialogo(null)
  }

  const guardar = async (entrada: CampaniaEntrada) => {
    if (dialogo === null || dialogo.tipo === 'inactivar') return
    const ok =
      dialogo.tipo === 'editar'
        ? await vista.editar(dialogo.campania.id, entrada)
        : await vista.crear(entrada)
    if (ok) setDialogo(null)
  }

  const confirmarInactivar = async () => {
    if (dialogo?.tipo !== 'inactivar') return
    if (await vista.inactivar(dialogo.campania.id)) setDialogo(null)
  }

  return (
    <section aria-labelledby="campanias-title" className="flex flex-col gap-6 font-sans text-ink">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 id="campanias-title" className="text-2xl font-semibold">
          Campañas
        </h1>
        <button
          type="button"
          onClick={() => abrir({ tipo: 'nueva' })}
          className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface"
        >
          Nueva campaña
        </button>
      </div>

      {vista.cargando && <LoadingIndicator label="Cargando campañas..." />}
      {vista.errorCarga && <ErrorAlert message={vista.errorCarga} onRetry={vista.recargar} />}
      {vista.error && dialogo === null && <ErrorAlert message={vista.error} />}

      {!vista.cargando && !vista.errorCarga && (
        <TablaCampanias
          campanias={vista.campanias}
          deshabilitado={vista.guardando}
          onEditar={(campania) => abrir({ tipo: 'editar', campania })}
          onInactivar={(campania) => abrir({ tipo: 'inactivar', campania })}
          onActivar={(campania) => void vista.activar(campania.id)}
        />
      )}

      <Modal
        open={dialogo !== null && dialogo.tipo !== 'inactivar'}
        title={dialogo?.tipo === 'editar' ? 'Editar campaña' : 'Nueva campaña'}
        onClose={cerrar}
      >
        {dialogo !== null && dialogo.tipo !== 'inactivar' && (
          <FormularioCampania
            inicial={dialogo.tipo === 'editar' ? dialogo.campania : undefined}
            guardando={vista.guardando}
            error={vista.error}
            onGuardar={(entrada) => void guardar(entrada)}
            onCancelar={cerrar}
          />
        )}
      </Modal>

      <Modal open={dialogo?.tipo === 'inactivar'} title="Inactivar campaña" onClose={cerrar}>
        {dialogo?.tipo === 'inactivar' && (
          <div className="flex flex-col gap-4">
            <p>
              ¿Inactivar «{dialogo.campania.nombre}»? {AVISO_INACTIVAR}
            </p>
            {vista.error && <ErrorAlert message={vista.error} />}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={cerrar}
                disabled={vista.guardando}
                className="rounded-pill border border-ink/20 px-4 py-2 text-sm font-medium disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void confirmarInactivar()}
                disabled={vista.guardando}
                className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:opacity-50"
              >
                Inactivar
              </button>
            </div>
          </div>
        )}
      </Modal>
    </section>
  )
}
