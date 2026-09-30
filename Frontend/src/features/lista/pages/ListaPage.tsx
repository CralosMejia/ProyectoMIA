import type { FormEvent } from 'react'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { AyudaLista } from '../components/AyudaLista'
import { DescargarExcelButton } from '../components/DescargarExcelButton'
import { FormularioGestion } from '../components/FormularioGestion'
import { HistorialListas } from '../components/HistorialListas'
import { TablaLista } from '../components/TablaLista'
import { useDescargarExcel } from '../hooks/useDescargarExcel'
import { useGestion } from '../hooks/useGestion'
import { useHistorialListas } from '../hooks/useHistorialListas'
import { type CampoParametro, useLista } from '../hooks/useLista'

const AVISO_DATOS_ANTIGUOS =
  'Los datos pueden estar desactualizados: la última carga de datos tiene más de 30 días y faltan los datos del mes, así que algunos socios pueden no aparecer en esta lista.'

interface CampoProps {
  id: string
  campo: CampoParametro
  etiqueta: string
  ayuda?: string
  type: 'text' | 'date' | 'number'
  min?: number | string
  max?: number
  maxLength?: number
  valor: string
  error?: string
  deshabilitado: boolean
  onCambiar: (campo: CampoParametro, valor: string) => void
}

function Campo({
  id,
  campo,
  etiqueta,
  ayuda,
  type,
  min,
  max,
  maxLength,
  valor,
  error,
  deshabilitado,
  onCambiar,
}: CampoProps) {
  const describedBy = [ayuda ? `${id}-ayuda` : null, error ? `${id}-error` : null]
    .filter((v) => v !== null)
    .join(' ')
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="font-medium">
        {etiqueta}
      </label>
      <input
        id={id}
        type={type}
        min={min}
        max={max}
        maxLength={maxLength}
        step={type === 'number' ? 1 : undefined}
        value={valor}
        onChange={(event) => onCambiar(campo, event.target.value)}
        disabled={deshabilitado}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy === '' ? undefined : describedBy}
        className="rounded-card border border-ink/30 px-3 py-2"
      />
      {ayuda && (
        <p id={`${id}-ayuda`} className="text-sm text-ink/60">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-degraded">
          {error}
        </p>
      )}
    </div>
  )
}

/**
 * Pagina de ruta: conecta los hooks de lista, historial, Excel y gestion con los componentes
 * (CU-04/05/12 y CU-07/08/10 desde la fila de cada socio).
 */
export default function ListaPage() {
  const historial = useHistorialListas()
  const vista = useLista({ onGenerada: historial.refrescar })
  const excel = useDescargarExcel()
  // Tras crear la gestion o registrar su resultado se recarga la lista para ver las columnas.
  const gestion = useGestion({ onGuardada: vista.recargar })
  const { parametros, errores, lista } = vista

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    vista.generar()
  }

  return (
    <section aria-labelledby="lista-title" className="flex flex-col gap-6 font-sans text-ink">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 id="lista-title" className="text-2xl font-semibold">
          Lista priorizada
        </h1>
        <AyudaLista />
      </div>

      <form
        aria-label="Parámetros de la lista"
        noValidate
        onSubmit={onSubmit}
        className="flex flex-wrap items-start gap-4"
      >
        <Campo
          id="lista-nombre"
          campo="nombre"
          etiqueta="Nombre de la lista"
          ayuda="Hasta 80 caracteres."
          type="text"
          maxLength={80}
          valor={parametros.nombre}
          error={errores.nombre}
          deshabilitado={vista.generando}
          onCambiar={vista.cambiarParametro}
        />
        <Campo
          id="lista-fecha"
          campo="fechaReferencia"
          etiqueta="Fecha de la lista"
          ayuda="Hoy o una fecha posterior."
          type="date"
          min={vista.fechaMinima}
          valor={parametros.fechaReferencia}
          error={errores.fechaReferencia}
          deshabilitado={vista.generando}
          onCambiar={vista.cambiarParametro}
        />
        <Campo
          id="lista-horizonte"
          campo="horizonteDias"
          etiqueta="Buscar socios que vencen en los próximos (días)"
          ayuda="Máximo 31 días."
          type="number"
          min={1}
          max={31}
          valor={parametros.horizonteDias}
          error={errores.horizonteDias}
          deshabilitado={vista.generando}
          onCambiar={vista.cambiarParametro}
        />
        <Campo
          id="lista-top-k"
          campo="topK"
          etiqueta="Socios prioritarios a contactar"
          ayuda="Cuántos socios contactar primero (1 o más)."
          type="number"
          min={1}
          valor={parametros.topK}
          error={errores.topK}
          deshabilitado={vista.generando}
          onCambiar={vista.cambiarParametro}
        />
        <div className="self-center">
          <button
            type="submit"
            disabled={vista.generando}
            className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:opacity-50"
          >
            Generar lista
          </button>
        </div>
      </form>

      {vista.generando && <LoadingIndicator label="Generando lista..." />}
      {vista.error && <ErrorAlert message={vista.error} />}

      <HistorialListas
        listas={historial.listas}
        seleccionadaId={lista?.id ?? null}
        deshabilitado={vista.generando}
        onSeleccionar={vista.seleccionar}
      />
      {historial.error && <ErrorAlert message={historial.error} onRetry={historial.refrescar} />}

      {vista.cargandoInicial && <LoadingIndicator label="Cargando la última lista..." />}
      {vista.errorInicial && <ErrorAlert message={vista.errorInicial} onRetry={vista.reintentar} />}
      {vista.sinListas && (
        <p className="rounded-card border border-ink/20 p-4">
          Aún no se ha generado ninguna lista. Elija la fecha y los días y pulse «Generar lista».
        </p>
      )}
      {vista.cargandoLista && <LoadingIndicator label="Cargando lista..." />}

      {lista && (
        <>
          {lista.advertenciaDatosAntiguos && <ErrorAlert message={AVISO_DATOS_ANTIGUOS} />}
          <DescargarExcelButton
            listaId={lista.id}
            descargando={excel.descargando}
            error={excel.error}
            onDescargar={(id) => excel.descargar(id, lista.fechaGeneracion)}
          />
          <TablaLista lista={lista} onGestionar={gestion.abrir} />
        </>
      )}

      {gestion.prediccion && (
        <FormularioGestion
          prediccion={gestion.prediccion}
          hoy={gestion.hoy}
          estado={gestion.estado}
          sugeridas={gestion.sugeridas}
          gestion={gestion.gestion}
          error={gestion.error}
          onCrear={gestion.crear}
          onRegistrar={gestion.registrar}
          onCerrar={gestion.cerrar}
          onReintentar={gestion.reintentar}
        />
      )}
    </section>
  )
}
