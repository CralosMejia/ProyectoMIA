import { type FormEvent, type Ref, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import { LoadingIndicator } from '../../../shared/ui/LoadingIndicator'
import { Modal } from '../../../shared/ui/Modal'
import { RiskBadge } from '../../../shared/ui/RiskBadge'
import {
  fechaDdMmAaaa,
  fechaSugerida,
  MENSAJE_PLAZO_TERMINADO,
  rangoSeguimiento,
  validarFechaSeguimiento,
} from '../hooks/reglasGestion'
import type {
  CampaniaSugerida,
  DatosNuevaGestion,
  Gestion,
  Prediccion,
  ResultadoGestionParams,
} from '../types'
import { fechaCorta } from './formatoFechas'
import { CampoFormulario, GrupoRadios, type OpcionRadio, ResultadoGestion } from './ResultadoGestion'

/*
 * Ventana de gestion de un socio de la lista (CU-07, CU-08, CU-10). Presentacional: recibe el
 * estado del hook `useGestion` por props y emite `onCrear`, `onRegistrar` y `onCerrar`.
 * Parte 1 (sin gestion): campaña sugerida, fecha de seguimiento y responsable; o "No asignar
 * campaña", que oculta esos dos campos porque la gestion nace cerrada. Parte 2 (con gestion):
 * `ResultadoGestion`; una gestion cerrada sin campaña solo muestra "No se le asignó campaña".
 */

export const MENSAJE_ELEGIR_CAMPANIA = 'Elija una campaña o «No asignar campaña».'
export const AVISO_SIN_CAMPANIA = 'Sin campaña, la gestión queda cerrada y no tendrá seguimiento.'
export const TEXTO_SIN_CAMPANIA = 'No se le asignó campaña'

const SIN_CAMPANIA = 'ninguna'
const CLASE_BOTON =
  'rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:opacity-50'

type EleccionCampania = typeof SIN_CAMPANIA | `${number}`

interface NuevaGestionProps {
  prediccion: Prediccion
  hoy: string
  sugeridas: CampaniaSugerida[]
  enviando: boolean
  primerCampoRef: Ref<HTMLInputElement>
  onCrear: (datos: DatosNuevaGestion) => void
}

interface ErroresNueva {
  campania?: string
  fechaSeguimiento?: string
}

/** Parte 1: crear la gestion. */
function NuevaGestion({
  prediccion,
  hoy,
  sugeridas,
  enviando,
  primerCampoRef,
  onCrear,
}: NuevaGestionProps) {
  const id = useId()
  const rango = rangoSeguimiento(hoy, prediccion.fechaVencimiento)
  // Sin sugerencias, "No asignar campaña" viene marcada; con sugerencias, hay que elegir.
  const [campania, setCampania] = useState<EleccionCampania | null>(
    sugeridas.length === 0 ? SIN_CAMPANIA : null,
  )
  const [fecha, setFecha] = useState(() => fechaSugerida(hoy, prediccion.fechaVencimiento) ?? '')
  const [responsable, setResponsable] = useState('')
  const [errores, setErrores] = useState<ErroresNueva>({})

  const opciones: OpcionRadio<EleccionCampania>[] = [
    ...sugeridas.map((c) => ({
      valor: `${c.id}` as const,
      etiqueta: c.nombre,
      descripcion: c.descripcion,
    })),
    { valor: SIN_CAMPANIA, etiqueta: 'No asignar campaña' },
  ]

  // Sin campaña la gestion nace cerrada: no hay seguimiento ni responsable que indicar.
  const sinCampania = campania === SIN_CAMPANIA
  const bloqueado = enviando || (rango === null && !sinCampania)

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (bloqueado) return
    if (sinCampania) {
      setErrores({})
      onCrear({ campaniaId: null, fechaSeguimiento: null, responsable: null })
      return
    }
    const siguientes: ErroresNueva = {}
    if (campania === null) siguientes.campania = MENSAJE_ELEGIR_CAMPANIA
    const errorFecha = validarFechaSeguimiento(fecha, hoy, prediccion.fechaVencimiento)
    if (errorFecha !== null) siguientes.fechaSeguimiento = errorFecha
    setErrores(siguientes)
    if (campania === null || errorFecha !== null) return
    const elegida = sugeridas.find((c) => `${c.id}` === campania)
    const recortado = responsable.trim()
    onCrear({
      campaniaId: elegida ? elegida.id : null,
      fechaSeguimiento: fecha.trim(),
      responsable: recortado === '' ? null : recortado,
    })
  }

  return (
    <form aria-label="Nueva gestión" noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      <GrupoRadios
        id={`${id}-campania`}
        legend="Campaña"
        opciones={opciones}
        valor={campania}
        error={errores.campania}
        primerCampoRef={primerCampoRef}
        onCambiar={(valor) => {
          setCampania(valor)
          setErrores((actual) =>
            valor === SIN_CAMPANIA ? {} : { ...actual, campania: undefined },
          )
        }}
      />
      {sinCampania ? (
        <p>{AVISO_SIN_CAMPANIA}</p>
      ) : (
        <>
          <CampoFormulario
            id={`${id}-fecha`}
            etiqueta="Fecha de seguimiento"
            tipo="date"
            valor={fecha}
            min={rango?.desde}
            max={rango?.hasta}
            ayuda={
              rango === null
                ? undefined
                : `Entre el ${fechaDdMmAaaa(rango.desde)} y el ${fechaDdMmAaaa(rango.hasta)}.`
            }
            error={rango === null ? MENSAJE_PLAZO_TERMINADO : errores.fechaSeguimiento}
            deshabilitado={rango === null}
            onCambiar={(valor) => {
              setFecha(valor)
              setErrores((actual) => ({ ...actual, fechaSeguimiento: undefined }))
            }}
          />
          <CampoFormulario
            id={`${id}-responsable`}
            etiqueta="Responsable (opcional)"
            tipo="text"
            valor={responsable}
            maxLength={120}
            onCambiar={setResponsable}
          />
        </>
      )}
      <div>
        <button type="submit" disabled={bloqueado} className={CLASE_BOTON}>
          Crear gestión
        </button>
      </div>
    </form>
  )
}

export type EstadoFormularioGestion = 'inactivo' | 'cargando' | 'listo' | 'enviando' | 'error'

export interface FormularioGestionProps {
  prediccion: Prediccion
  /** Fecha local `YYYY-MM-DD`. */
  hoy: string
  estado: EstadoFormularioGestion
  sugeridas: CampaniaSugerida[]
  gestion: Gestion | null
  /** Error de la carga o del ultimo envio (mensaje del servidor). */
  error: string | null
  onCrear: (datos: DatosNuevaGestion) => void
  onRegistrar: (datos: ResultadoGestionParams) => void
  /** Debe ser estable: el `Modal` vuelve a enfocar el dialogo cuando cambia. */
  onCerrar: () => void
  onReintentar?: () => void
}

/**
 * Ventana modal de la gestion de un socio. Al abrir enfoca el primer campo y al cerrar devuelve
 * el foco al elemento que la abrio (el boton de la fila).
 */
export function FormularioGestion({
  prediccion,
  hoy,
  estado,
  sugeridas,
  gestion,
  error,
  onCrear,
  onRegistrar,
  onCerrar,
  onReintentar,
}: FormularioGestionProps) {
  const primerCampoRef = useRef<HTMLInputElement>(null)
  const cargando = estado === 'cargando' || estado === 'inactivo'
  const enviando = estado === 'enviando'
  const vista =
    cargando || estado === 'error'
      ? 'espera'
      : gestion === null
        ? 'nueva'
        : gestion.estado !== 'CERRADA'
          ? 'resultado'
          : gestion.campaniaId === null
            ? 'sinCampania'
            : 'cerrada'

  // Antes que los efectos (el `Modal` enfoca el dialogo en el suyo): guarda quien tenia el foco.
  useLayoutEffect(() => {
    const anterior = document.activeElement
    return () => {
      if (anterior instanceof HTMLElement && anterior.isConnected) anterior.focus()
    }
  }, [])

  // Los efectos del padre corren despues de los del `Modal`: el primer campo gana el foco.
  useEffect(() => {
    if (vista === 'nueva' || vista === 'resultado') primerCampoRef.current?.focus()
  }, [vista])

  return (
    <Modal open title={`Gestión de la prioridad ${prediccion.prioridad}`} onClose={onCerrar}>
      <div className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto pr-2">
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <span>{`Plan: ${prediccion.plan}`}</span>
          <span aria-hidden="true">·</span>
          <span>{`Vence el ${fechaCorta(prediccion.fechaVencimiento)}`}</span>
          <span aria-hidden="true">·</span>
          <span>Nivel de riesgo:</span>
          <RiskBadge nivel={prediccion.nivelRiesgo} />
        </p>
        {cargando && <LoadingIndicator label="Cargando la gestión..." />}
        {error && <ErrorAlert message={error} onRetry={estado === 'error' ? onReintentar : undefined} />}
        {vista === 'nueva' && (
          <NuevaGestion
            prediccion={prediccion}
            hoy={hoy}
            sugeridas={sugeridas}
            enviando={enviando}
            primerCampoRef={primerCampoRef}
            onCrear={onCrear}
          />
        )}
        {vista === 'sinCampania' && <p>{TEXTO_SIN_CAMPANIA}</p>}
        {gestion !== null && (vista === 'resultado' || vista === 'cerrada') && (
          <ResultadoGestion
            key={`${gestion.id}-${gestion.estado}`}
            gestion={gestion}
            hoy={hoy}
            enviando={enviando}
            primerCampoRef={primerCampoRef}
            onRegistrar={onRegistrar}
          />
        )}
      </div>
    </Modal>
  )
}
