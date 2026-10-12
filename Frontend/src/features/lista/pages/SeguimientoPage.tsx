import { Link, useSearchParams } from 'react-router-dom'
import { claseBoton } from '../../../shared/ui/clases'
import { DataTable, type DataTableColumn } from '../../../shared/ui/DataTable'
import { Boton, EncabezadoPagina, Tarjeta } from '../../../shared/ui/Diseno'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { FormularioGestion } from '../components/FormularioGestion'
import { fechaCorta } from '../components/formatoFechas'
import { useSeguimiento } from '../hooks/useSeguimiento'
import type { FiltroAlerta, GestionResumen } from '../types'

const TITULOS: Record<FiltroAlerta, string> = {
  vencidas: 'Seguimientos vencidos',
  hoy: 'Seguimientos para hoy',
  proximas: 'Seguimientos de los próximos 7 días',
}

/** Enlace con aspecto de boton secundario (la guia de `Boton`), para la navegacion de vuelta. */
const CLASE_ENLACE = claseBoton('secundario')

/**
 * Pagina de ruta `/seguimiento?filtro=vencidas|hoy|proximas` (CU-09): gestiones pendientes del
 * grupo y, en cada fila, "Abrir gestión" para registrar el resultado (CU-10).
 */
export default function SeguimientoPage() {
  const [parametros] = useSearchParams()
  const seguimiento = useSeguimiento(parametros.get('filtro'))
  const { filtro, gestiones, ventana, abierta } = seguimiento

  if (filtro === null) {
    return (
      <section
        aria-label="Grupo de seguimiento no válido"
        className="flex flex-col gap-6 font-sans text-ink"
      >
        <EncabezadoPagina titulo="Grupo de seguimiento no válido" />
        <Tarjeta className="items-start">
          <p className="text-sm text-muted">
            Elija uno de los grupos de seguimiento desde la página de Inicio.
          </p>
          <Link to="/" className={CLASE_ENLACE}>
            Volver a Inicio
          </Link>
        </Tarjeta>
      </section>
    )
  }

  const columnas: DataTableColumn<GestionResumen>[] = [
    { key: 'socioNombre', header: 'Socio' },
    { key: 'plan', header: 'Plan' },
    { key: 'fechaVencimiento', header: 'Vence', render: (g) => fechaCorta(g.fechaVencimiento) },
    {
      key: 'fechaSeguimiento',
      header: 'Fecha de seguimiento',
      render: (g) => fechaCorta(g.fechaSeguimiento),
    },
    { key: 'campaniaNombre', header: 'Campaña', render: (g) => g.campaniaNombre ?? '—' },
    { key: 'responsable', header: 'Responsable', render: (g) => g.responsable ?? '—' },
    {
      key: 'id',
      header: 'Acción',
      render: (g) => (
        <Boton
          aria-label={`Abrir gestión ${g.socioNombre}`}
          onClick={() => seguimiento.abrir(g)}
          className="whitespace-nowrap px-3 py-1"
        >
          Abrir gestión
        </Boton>
      ),
    },
  ]

  return (
    <section aria-label={TITULOS[filtro]} className="flex flex-col gap-6 font-sans text-ink">
      <EncabezadoPagina
        titulo={TITULOS[filtro]}
        acciones={
          <Link to="/" className={CLASE_ENLACE}>
            Volver a Inicio
          </Link>
        }
      />

      {seguimiento.cargando && <LoadingIndicator label="Cargando seguimientos..." />}
      {seguimiento.error && (
        <ErrorAlert message={seguimiento.error} onRetry={seguimiento.reintentar} />
      )}
      {gestiones && (
        <DataTable
          caption="Gestiones pendientes"
          columns={columnas}
          rows={gestiones}
          getRowKey={(g) => g.id}
          emptyMessage="No hay gestiones en este grupo"
        />
      )}

      {ventana.prediccion && (
        <FormularioGestion
          titulo={abierta ? `Gestión de ${abierta.socioNombre}` : undefined}
          prediccion={ventana.prediccion}
          hoy={ventana.hoy}
          estado={ventana.estado}
          sugeridas={ventana.sugeridas}
          gestion={ventana.gestion}
          error={ventana.error}
          onCrear={ventana.crear}
          onRegistrar={ventana.registrar}
          onCerrar={ventana.cerrar}
          onReintentar={ventana.reintentar}
        />
      )}
    </section>
  )
}
