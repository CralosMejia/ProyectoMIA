import { useState, type FormEvent } from 'react'
import { ErrorAlert } from '../../../shared/ui/ErrorAlert'
import type { CampaniaEntrada, NivelRiesgo, PlanCampania } from '../types'
import { NIVELES, PLANES } from './etiquetas'

const NOMBRE_MAXIMO = 120
const DESCRIPCION_MAXIMA = 500
const PRIORIDAD_MAXIMA = 999
const ENTERO = /^\d+$/

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
      className="flex flex-col gap-4 font-sans text-ink"
    >
      <div className="flex flex-col gap-1">
        <label htmlFor="campania-nombre" className="font-medium">
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
          className="rounded-card border border-ink/30 px-3 py-2"
        />
        {errores.nombre && (
          <p id="campania-nombre-error" className="text-sm text-degraded">
            {errores.nombre}
          </p>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="campania-descripcion" className="font-medium">
          Descripción
        </label>
        <textarea
          id="campania-descripcion"
          maxLength={DESCRIPCION_MAXIMA}
          rows={3}
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          disabled={guardando}
          className="rounded-card border border-ink/30 px-3 py-2"
        />
      </div>

      <fieldset
        aria-describedby={errores.niveles ? 'campania-niveles-error' : undefined}
        className="flex flex-col gap-1"
      >
        <legend className="font-medium">Niveles de riesgo</legend>
        <div className="flex flex-wrap gap-4">
          {NIVELES.map((n) => (
            <label key={n.valor} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={niveles.includes(n.valor)}
                onChange={() => setNiveles((actuales) => alternar(actuales, n.valor))}
                disabled={guardando}
              />
              {n.etiqueta}
            </label>
          ))}
        </div>
        {errores.niveles && (
          <p id="campania-niveles-error" className="text-sm text-degraded">
            {errores.niveles}
          </p>
        )}
      </fieldset>

      <fieldset
        aria-describedby={errores.planes ? 'campania-planes-error' : undefined}
        className="flex flex-col gap-1"
      >
        <legend className="font-medium">Planes</legend>
        <div className="flex flex-wrap gap-4">
          {PLANES.map((p) => (
            <label key={p.valor} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={planes.includes(p.valor)}
                onChange={() => setPlanes((actuales) => alternar(actuales, p.valor))}
                disabled={guardando}
              />
              {p.etiqueta}
            </label>
          ))}
        </div>
        {errores.planes && (
          <p id="campania-planes-error" className="text-sm text-degraded">
            {errores.planes}
          </p>
        )}
      </fieldset>

      <div className="flex flex-col gap-1">
        <label htmlFor="campania-prioridad" className="font-medium">
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
          className="rounded-card border border-ink/30 px-3 py-2"
        />
        <p id="campania-prioridad-ayuda" className="text-sm text-ink/60">
          1 es la que se sugiere primero.
        </p>
        {errores.prioridad && (
          <p id="campania-prioridad-error" className="text-sm text-degraded">
            {errores.prioridad}
          </p>
        )}
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancelar}
          disabled={guardando}
          className="rounded-pill border border-ink/20 px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={guardando}
          className="rounded-pill bg-ink px-4 py-2 text-sm font-medium text-surface disabled:opacity-50"
        >
          Guardar
        </button>
      </div>
    </form>
  )
}
