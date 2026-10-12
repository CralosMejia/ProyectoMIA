import { useState, type FormEvent } from 'react'
import { CLASE_CAMPO } from '../../../shared/ui/clases'
import { Boton } from '../../../shared/ui/Diseno'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import type { CampaniaEntrada, NivelRiesgo, PlanCampania } from '../types'
import { NIVELES, PLANES } from './etiquetas'

const NOMBRE_MAXIMO = 120
const DESCRIPCION_MAXIMA = 500
const PRIORIDAD_MAXIMA = 999
const ENTERO = /^\d+$/

const CLASE_ETIQUETA = 'text-sm font-semibold text-ink'
const CLASE_ERROR = 'text-sm font-medium text-danger'
/** Casilla como insignia seleccionable: resalta con `brand` la marcada. */
const CLASE_CASILLA =
  'flex cursor-pointer items-center gap-2 rounded-pill border border-line bg-surface px-3 py-1.5 text-sm transition-colors hover:bg-canvas has-[:checked]:border-brand has-[:checked]:bg-brand/5 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50'

const MENSAJE_NOMBRE = 'Escriba un nombre para la campaña.'
const MENSAJE_NIVELES = 'Elija al menos un nivel de riesgo.'
const MENSAJE_PLANES = 'Elija al menos un plan.'
const MENSAJE_PRIORIDAD = `La prioridad debe ser un número entre 1 y ${PRIORIDAD_MAXIMA}.`

type Campo = 'nombre' | 'niveles' | 'planes' | 'prioridad'
type Errores = Partial<Record<Campo, string>>

export interface FormularioCampaniaProps {
  /** Datos para precargar al editar; sin valor, el formulario empieza vacío. */
  inicial?: CampaniaEntrada
  guardando: boolean
  /** Mensaje del servidor si falló el guardado. */
  error: string | null
  onGuardar: (entrada: CampaniaEntrada) => void
  onCancelar: () => void
}

function alternar<T>(valores: T[], valor: T): T[] {
  return valores.includes(valor) ? valores.filter((v) => v !== valor) : [...valores, valor]
}

function prioridadValida(texto: string): boolean {
  if (!ENTERO.test(texto.trim())) return false
  const numero = Number(texto.trim())
  return numero >= 1 && numero <= PRIORIDAD_MAXIMA
}

/** Formulario de alta y edición de una campaña (CU-06); valida antes de emitir `onGuardar`. */
export function FormularioCampania({
  inicial,
  guardando,
  error,
  onGuardar,
  onCancelar,
}: FormularioCampaniaProps) {
  const [nombre, setNombre] = useState(inicial?.nombre ?? '')
  const [descripcion, setDescripcion] = useState(inicial?.descripcion ?? '')
  const [niveles, setNiveles] = useState<NivelRiesgo[]>(inicial?.nivelesRiesgo ?? [])
  const [planes, setPlanes] = useState<PlanCampania[]>(inicial?.planes ?? [])
  const [prioridad, setPrioridad] = useState(inicial ? String(inicial.prioridad) : '')
  const [errores, setErrores] = useState<Errores>({})

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nuevos: Errores = {}
    if (nombre.trim() === '') nuevos.nombre = MENSAJE_NOMBRE
    if (niveles.length === 0) nuevos.niveles = MENSAJE_NIVELES
    if (planes.length === 0) nuevos.planes = MENSAJE_PLANES
    if (!prioridadValida(prioridad)) nuevos.prioridad = MENSAJE_PRIORIDAD
    setErrores(nuevos)
    if (Object.keys(nuevos).length > 0) return
    const texto = descripcion.trim()
    onGuardar({
      nombre: nombre.trim(),
      descripcion: texto === '' ? null : texto,
      nivelesRiesgo: NIVELES.map((n) => n.valor).filter((v) => niveles.includes(v)),
      planes: PLANES.map((p) => p.valor).filter((v) => planes.includes(v)),
      prioridad: Number(prioridad.trim()),
    })
  }

  return (
    <form
      aria-label="Datos de la campaña"
      noValidate
      onSubmit={onSubmit}
      className="flex flex-col gap-5 font-sans text-ink"
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor="campania-nombre" className={CLASE_ETIQUETA}>
          Nombre
        </label>
        <input
          id="campania-nombre"
          type="text"
          maxLength={NOMBRE_MAXIMO}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          disabled={guardando}
          aria-invalid={errores.nombre ? true : undefined}
          aria-describedby={errores.nombre ? 'campania-nombre-error' : undefined}
          className={CLASE_CAMPO}
        />
        {errores.nombre && (
          <p id="campania-nombre-error" className={CLASE_ERROR}>
            {errores.nombre}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="campania-descripcion" className={CLASE_ETIQUETA}>
          Descripción
        </label>
        <textarea
          id="campania-descripcion"
          maxLength={DESCRIPCION_MAXIMA}
          rows={3}
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          disabled={guardando}
          className={CLASE_CAMPO}
        />
      </div>

      <fieldset
        aria-describedby={errores.niveles ? 'campania-niveles-error' : undefined}
        className="flex flex-col gap-2"
      >
        <legend className={`mb-2 ${CLASE_ETIQUETA}`}>Niveles de riesgo</legend>
        <div className="flex flex-wrap gap-2">
          {NIVELES.map((n) => (
            <label key={n.valor} className={CLASE_CASILLA}>
              <input
                type="checkbox"
                className="size-4 accent-brand"
                checked={niveles.includes(n.valor)}
                onChange={() => setNiveles((actuales) => alternar(actuales, n.valor))}
                disabled={guardando}
              />
              {n.etiqueta}
            </label>
          ))}
        </div>
        {errores.niveles && (
          <p id="campania-niveles-error" className={CLASE_ERROR}>
            {errores.niveles}
          </p>
        )}
      </fieldset>

      <fieldset
        aria-describedby={errores.planes ? 'campania-planes-error' : undefined}
        className="flex flex-col gap-2"
      >
        <legend className={`mb-2 ${CLASE_ETIQUETA}`}>Planes</legend>
        <div className="flex flex-wrap gap-2">
          {PLANES.map((p) => (
            <label key={p.valor} className={CLASE_CASILLA}>
              <input
                type="checkbox"
                className="size-4 accent-brand"
                checked={planes.includes(p.valor)}
                onChange={() => setPlanes((actuales) => alternar(actuales, p.valor))}
                disabled={guardando}
              />
              {p.etiqueta}
            </label>
          ))}
        </div>
        {errores.planes && (
          <p id="campania-planes-error" className={CLASE_ERROR}>
            {errores.planes}
          </p>
        )}
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="campania-prioridad" className={CLASE_ETIQUETA}>
          Prioridad
        </label>
        <input
          id="campania-prioridad"
          type="number"
          min={1}
          max={PRIORIDAD_MAXIMA}
          step={1}
          value={prioridad}
          onChange={(e) => setPrioridad(e.target.value)}
          disabled={guardando}
          aria-invalid={errores.prioridad ? true : undefined}
          aria-describedby={
            errores.prioridad ? 'campania-prioridad-ayuda campania-prioridad-error' : 'campania-prioridad-ayuda'
          }
          className={CLASE_CAMPO}
        />
        <p id="campania-prioridad-ayuda" className="text-xs text-muted">
          1 es la que se sugiere primero.
        </p>
        {errores.prioridad && (
          <p id="campania-prioridad-error" className={CLASE_ERROR}>
            {errores.prioridad}
          </p>
        )}
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="flex justify-end gap-2 border-t border-line pt-4">
        <Boton onClick={onCancelar} disabled={guardando}>
          Cancelar
        </Boton>
        <Boton type="submit" variante="primario" disabled={guardando}>
          Guardar
        </Boton>
      </div>
    </form>
  )
}
