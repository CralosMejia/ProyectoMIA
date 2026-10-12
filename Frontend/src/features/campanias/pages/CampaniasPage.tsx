import { useState } from 'react'
import { Boton, EncabezadoPagina } from '../../../shared/ui/Diseno'
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
    <section aria-label="Campañas" className="flex flex-col gap-6 font-sans text-ink">
      <EncabezadoPagina
        titulo="Campañas"
        acciones={
          <Boton variante="primario" onClick={() => abrir({ tipo: 'nueva' })}>
            Nueva campaña
          </Boton>
        }
      />

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
          <div className="flex flex-col gap-5">
            <p className="text-sm leading-relaxed">
              ¿Inactivar «{dialogo.campania.nombre}»? {AVISO_INACTIVAR}
            </p>
            {vista.error && <ErrorAlert message={vista.error} />}
            <div className="flex justify-end gap-2 border-t border-line pt-4">
              <Boton onClick={cerrar} disabled={vista.guardando}>
                Cancelar
              </Boton>
              <Boton
                variante="peligro"
                onClick={() => void confirmarInactivar()}
                disabled={vista.guardando}
              >
                Inactivar
              </Boton>
            </div>
          </div>
        )}
      </Modal>
    </section>
  )
}
