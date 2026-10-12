import { type FormEvent, type Ref, useId, useState } from 'react'
import { CLASE_CAMPO } from '../../../shared/ui/clases'
import { Boton } from '../../../shared/ui/Diseno'
import {
  type BorradorResultado,
  type CampoResultado,
  type ErroresResultado,
  type RespuestasContacto,
  ajustarRespuestas,
  fechaDdMmAaaa,
  fechaLocalIso,
  MENSAJE_PLAZO_TERMINADO,
  opcionesPermitidas,
  rangoSeguimiento,
  validarResultado,
} from '../hooks/reglasGestion'
import type {
  Gestion,
  RespuestaAceptacion,
  RespuestaOfrecimiento,
  RespuestaRenovacion,
  ResultadoGestionParams,
} from '../types'

/*
 * Parte 2 del formulario de gestion (CU-10). Presentacional: el estado es solo el del formulario
 * y el resultado se emite con `onRegistrar`. Las reglas de coherencia son las funciones puras de
 * `reglasGestion` (sin estado de React ni llamadas a la API).
 */

export const TEXTO_GESTION_CERRADA = 'Gestión cerrada: no se puede modificar.'

/** Opcion de radio como fila seleccionable: resalta con `brand` la marcada. */
const CLASE_OPCION =
  'flex flex-col rounded-card border border-line bg-surface transition-colors hover:bg-canvas has-[:checked]:border-brand has-[:checked]:bg-brand/5 has-[:disabled]:opacity-60 has-[:disabled]:hover:bg-surface'

export interface OpcionRadio<T extends string> {
  valor: T
  etiqueta: string
  descripcion?: string | null
}

export interface GrupoRadiosProps<T extends string> {
  id: string
  legend: string
  opciones: OpcionRadio<T>[]
  valor: T | null
  /** Opciones elegibles; el resto se deshabilitan. Sin valor, todas se pueden elegir. */
  permitidas?: T[]
  error?: string
  primerCampoRef?: Ref<HTMLInputElement>
  onCambiar: (valor: T) => void
}

/** Grupo de radios accesible: `fieldset` con `legend` y error enlazado con `aria-describedby`. */
export function GrupoRadios<T extends string>({
  id,
  legend,
  opciones,
  valor,
  permitidas,
  error,
  primerCampoRef,
  onCambiar,
}: GrupoRadiosProps<T>) {
  const errorId = `${id}-error`
  return (
    <fieldset
      className="flex flex-col gap-2"
      aria-describedby={error ? errorId : undefined}
      aria-invalid={error ? true : undefined}
    >
      <legend className="mb-2 text-sm font-semibold text-ink">{legend}</legend>
      {opciones.map((opcion, i) => {
        const inputId = `${id}-${opcion.valor}`
        const descripcionId = opcion.descripcion ? `${inputId}-descripcion` : undefined
        return (
          <div key={opcion.valor} className={CLASE_OPCION}>
            <label
              htmlFor={inputId}
              className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm has-[:disabled]:cursor-not-allowed"
            >
              <input
                ref={i === 0 ? primerCampoRef : undefined}
                id={inputId}
                type="radio"
                name={id}
                value={opcion.valor}
                checked={valor === opcion.valor}
                disabled={permitidas !== undefined && !permitidas.includes(opcion.valor)}
                aria-describedby={descripcionId}
                className="size-4 accent-brand"
                onChange={() => onCambiar(opcion.valor)}
              />
              {opcion.etiqueta}
            </label>
            {opcion.descripcion && (
              <p id={descripcionId} className="px-3 pb-2 pl-10 text-xs text-muted">
                {opcion.descripcion}
              </p>
            )}
          </div>
        )
      })}
      {error && (
        <p id={errorId} className="text-sm font-medium text-danger">
          {error}
        </p>
      )}
    </fieldset>
  )
}

export interface CampoFormularioProps {
  id: string
  etiqueta: string
  tipo: 'text' | 'date' | 'textarea'
  valor: string
  ayuda?: string
  error?: string
  min?: string
  max?: string
  maxLength?: number
  deshabilitado?: boolean
  onCambiar: (valor: string) => void
}

/** Campo con `label`, ayuda y error enlazados con `aria-describedby`. */
export function CampoFormulario({
  id,
  etiqueta,
  tipo,
  valor,
  ayuda,
  error,
  min,
  max,
  maxLength,
  deshabilitado,
  onCambiar,
}: CampoFormularioProps) {
  const describedBy = [ayuda ? `${id}-ayuda` : null, error ? `${id}-error` : null]
    .filter((v) => v !== null)
    .join(' ')
  const comunes = {
    id,
    value: valor,
    maxLength,
    disabled: deshabilitado,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy === '' ? undefined : describedBy,
    className: CLASE_CAMPO,
  }
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {etiqueta}
      </label>
      {tipo === 'textarea' ? (
        <textarea {...comunes} rows={3} onChange={(event) => onCambiar(event.target.value)} />
      ) : (
        <input
          {...comunes}
          type={tipo}
          min={min}
          max={max}
          onChange={(event) => onCambiar(event.target.value)}
        />
      )}
      {ayuda && (
        <p id={`${id}-ayuda`} className="text-xs text-muted">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

type SiNo = 'SI' | 'NO'

const OPCIONES_CONTACTADO: OpcionRadio<SiNo>[] = [
  { valor: 'SI', etiqueta: 'Sí' },
  { valor: 'NO', etiqueta: 'No' },
]
const OPCIONES_OFRECIDA: OpcionRadio<RespuestaOfrecimiento>[] = [
  { valor: 'SI', etiqueta: 'Sí' },
  { valor: 'NO', etiqueta: 'No' },
  { valor: 'NO_APLICA', etiqueta: 'No aplica' },
]
const OPCIONES_ACEPTADA: OpcionRadio<RespuestaAceptacion>[] = [
  { valor: 'SI', etiqueta: 'Sí' },
  { valor: 'NO', etiqueta: 'No' },
  { valor: 'PENDIENTE', etiqueta: 'Pendiente' },
  { valor: 'NO_APLICA', etiqueta: 'No aplica' },
]
const OPCIONES_RENOVO: OpcionRadio<RespuestaRenovacion>[] = [
  { valor: 'SI', etiqueta: 'Sí' },
  { valor: 'NO', etiqueta: 'No' },
  { valor: 'PENDIENTE', etiqueta: 'Pendiente' },
]

function borradorInicial(gestion: Gestion): BorradorResultado {
  const guardadas: RespuestasContacto = {
    contactado: gestion.contactado,
    ofrecida: gestion.campaniaOfrecida,
    aceptada: gestion.campaniaAceptada,
  }
  // Una gestion cerrada se muestra tal como se guardo; una pendiente se deja coherente.
  const respuestas =
    gestion.estado === 'CERRADA'
      ? guardadas
      : ajustarRespuestas(gestion.campaniaId !== null, guardadas)
  return {
    contactado: respuestas.contactado,
    campaniaOfrecida: respuestas.ofrecida,
    campaniaAceptada: respuestas.aceptada,
    renovoDeclarado: gestion.renovoDeclarado,
    fechaContacto: gestion.fechaContacto ?? '',
    observaciones: gestion.observaciones ?? '',
    responsable: gestion.responsable ?? '',
    fechaSeguimiento: gestion.fechaSeguimiento,
  }
}

export interface ResultadoGestionProps {
  gestion: Gestion
  /** Fecha local `YYYY-MM-DD`. */
  hoy: string
  enviando: boolean
  primerCampoRef?: Ref<HTMLInputElement>
  onRegistrar: (datos: ResultadoGestionParams) => void
}

/**
 * Parte 2 (gestion pendiente o cerrada): resultado del seguimiento. Las opciones incoherentes se
 * deshabilitan y se valida al guardar; una gestion cerrada es de solo lectura y sin "Guardar".
 */
export function ResultadoGestion({
  gestion,
  hoy,
  enviando,
  primerCampoRef,
  onRegistrar,
}: ResultadoGestionProps) {
  const id = useId()
  const [borrador, setBorrador] = useState<BorradorResultado>(() => borradorInicial(gestion))
  const [errores, setErrores] = useState<ErroresResultado>({})
  const cerrada = gestion.estado === 'CERRADA'
  const conCampania = gestion.campaniaId !== null
  const fechaAsignacion = fechaLocalIso(gestion.fechaAsignacion)
  const rango = rangoSeguimiento(hoy, gestion.fechaVencimiento)
  const opciones = opcionesPermitidas({
    conCampania,
    contactado: borrador.contactado,
    ofrecida: borrador.campaniaOfrecida,
  })

  const limpiarErrores = (...campos: CampoResultado[]) => {
    setErrores((actual) => {
      if (!campos.some((campo) => campo in actual)) return actual
      const siguiente = { ...actual }
      for (const campo of campos) delete siguiente[campo]
      return siguiente
    })
  }

  const cambiarRespuestas = (cambio: Partial<RespuestasContacto>) => {
    setBorrador((actual) => {
      const respuestas = ajustarRespuestas(conCampania, {
        contactado: actual.contactado,
        ofrecida: actual.campaniaOfrecida,
        aceptada: actual.campaniaAceptada,
        ...cambio,
      })
      return {
        ...actual,
        contactado: respuestas.contactado,
        campaniaOfrecida: respuestas.ofrecida,
        campaniaAceptada: respuestas.aceptada,
        fechaContacto: respuestas.contactado === true ? actual.fechaContacto : '',
      }
    })
    limpiarErrores('contactado', 'campaniaOfrecida', 'campaniaAceptada', 'fechaContacto')
  }

  const cambiar = (campo: keyof BorradorResultado, valor: string) => {
    setBorrador((actual) => ({ ...actual, [campo]: valor }))
    if (campo === 'fechaContacto' || campo === 'fechaSeguimiento') limpiarErrores(campo)
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (cerrada || enviando) return
    const validacion = validarResultado(borrador, {
      conCampania,
      fechaAsignacion,
      hoy,
      vencimiento: gestion.fechaVencimiento,
      fechaSeguimientoActual: gestion.fechaSeguimiento,
    })
    if (validacion.params === null) {
      setErrores(validacion.errores)
      return
    }
    setErrores({})
    onRegistrar(validacion.params)
  }

  const contactado = borrador.contactado === null ? null : borrador.contactado ? 'SI' : 'NO'

  return (
    <form aria-label="Resultado del seguimiento" noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-card border border-line bg-canvas px-4 py-3 text-sm">
        <dt className="text-muted">Campaña asignada</dt>
        <dd className="font-medium">{gestion.campaniaNombre ?? 'Sin campaña'}</dd>
        <dt className="text-muted">Seguimiento previsto</dt>
        <dd className="font-medium">{fechaDdMmAaaa(gestion.fechaSeguimiento)}</dd>
      </dl>
      {cerrada && (
        <p className="rounded-card bg-ok/10 px-3 py-2 text-sm font-medium">{TEXTO_GESTION_CERRADA}</p>
      )}
      <fieldset disabled={cerrada} className="flex flex-col gap-5">
        <GrupoRadios
          id={`${id}-contactado`}
          legend="¿Se contactó al socio?"
          opciones={OPCIONES_CONTACTADO}
          valor={contactado}
          error={errores.contactado}
          primerCampoRef={primerCampoRef}
          onCambiar={(valor) => cambiarRespuestas({ contactado: valor === 'SI' })}
        />
        <GrupoRadios
          id={`${id}-ofrecida`}
          legend="¿Se ofreció la campaña?"
          opciones={OPCIONES_OFRECIDA}
          valor={borrador.campaniaOfrecida}
          permitidas={opciones.ofrecida}
          error={errores.campaniaOfrecida}
          onCambiar={(valor) => cambiarRespuestas({ ofrecida: valor })}
        />
        <GrupoRadios
          id={`${id}-aceptada`}
          legend="¿Aceptó la campaña?"
          opciones={OPCIONES_ACEPTADA}
          valor={borrador.campaniaAceptada}
          permitidas={opciones.aceptada}
          error={errores.campaniaAceptada}
          onCambiar={(valor) => cambiarRespuestas({ aceptada: valor })}
        />
        <CampoFormulario
          id={`${id}-fecha-contacto`}
          etiqueta="Fecha del contacto"
          tipo="date"
          valor={borrador.fechaContacto}
          min={fechaAsignacion}
          max={hoy}
          deshabilitado={borrador.contactado !== true}
          error={errores.fechaContacto}
          onCambiar={(valor) => cambiar('fechaContacto', valor)}
        />
        <GrupoRadios
          id={`${id}-renovo`}
          legend="¿Renovó?"
          opciones={OPCIONES_RENOVO}
          valor={borrador.renovoDeclarado}
          error={errores.renovoDeclarado}
          onCambiar={(valor) => {
            setBorrador((actual) => ({ ...actual, renovoDeclarado: valor }))
            limpiarErrores('renovoDeclarado', 'fechaSeguimiento')
          }}
        />
        {borrador.renovoDeclarado === 'PENDIENTE' && (
          <CampoFormulario
            id={`${id}-fecha-seguimiento`}
            etiqueta="Fecha de seguimiento"
            tipo="date"
            valor={borrador.fechaSeguimiento}
            min={rango?.desde}
            max={rango?.hasta}
            ayuda={
              rango === null
                ? MENSAJE_PLAZO_TERMINADO
                : `Entre el ${fechaDdMmAaaa(rango.desde)} y el ${fechaDdMmAaaa(rango.hasta)}.`
            }
            error={errores.fechaSeguimiento}
            onCambiar={(valor) => cambiar('fechaSeguimiento', valor)}
          />
        )}
        <CampoFormulario
          id={`${id}-observaciones`}
          etiqueta="Observaciones"
          tipo="textarea"
          valor={borrador.observaciones}
          maxLength={500}
          onCambiar={(valor) => cambiar('observaciones', valor)}
        />
        <CampoFormulario
          id={`${id}-responsable`}
          etiqueta="Responsable"
          tipo="text"
          valor={borrador.responsable}
          maxLength={120}
          onCambiar={(valor) => cambiar('responsable', valor)}
        />
      </fieldset>
      {!cerrada && (
        <div className="flex justify-end border-t border-line pt-4">
          <Boton type="submit" variante="primario" disabled={enviando}>
            Guardar resultado
          </Boton>
        </div>
      )}
    </form>
  )
}
