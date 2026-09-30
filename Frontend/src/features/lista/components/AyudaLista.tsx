import { useRef, useState, type ReactNode } from 'react'
import { Modal } from '../../../shared/ui/Modal'

/**
 * Resumen estatico de `Documentation/06-como-funciona-la-lista.md` §1–§6 (decision (m) de R-007).
 * El texto vive en el componente: no se carga el `.md` en tiempo de ejecucion.
 * Lenguaje para el personal del gimnasio, sin terminos tecnicos.
 */

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="font-semibold">{titulo}</h3>
      {children}
    </section>
  )
}

function Contenido() {
  return (
    <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto pr-2 text-sm">
      <Seccion titulo="Qué hace la lista">
        <p>
          Eliges una fecha (hoy o un día posterior) y cuántos días hacia adelante quieres revisar,
          como máximo 31. El sistema busca a los socios cuya membresía vence en esos días, calcula
          la probabilidad de que cada uno no renueve y los ordena de mayor a menor riesgo.
        </p>
      </Seccion>

      <Seccion titulo="Socios prioritarios a contactar">
        <p>
          Tú indicas cuántos socios quieres contactar primero (por ejemplo, 25). Esos salen arriba,
          en la tabla «Socios prioritarios a contactar». El resto aparece debajo, en «Otros socios
          por vencer».
        </p>
      </Seccion>

      <Seccion titulo="Niveles de riesgo: alto, medio y bajo">
        <p>
          Cada socio tiene un nivel alto, medio o bajo. Los niveles se fijaron una sola vez con el
          historial del gimnasio (más o menos, el 20 % con más riesgo es alto, el siguiente 30 % es
          medio y el resto es bajo) y no cambian según cuántos prioritarios pidas.
        </p>
      </Seccion>

      <Seccion titulo="Motivos">
        <p>
          Junto a cada socio se muestran los motivos principales de su riesgo, por ejemplo el plan
          que tiene o cuántas membresías ha tenido antes. Sirven para orientar la conversación. Si
          no hay motivos destacados, se indica «Sin factores de riesgo destacados».
        </p>
      </Seccion>

      <Seccion titulo="Qué datos se muestran">
        <p>
          En pantalla: prioridad, nombre, cédula, plan, fecha de vencimiento, días que faltan, nivel
          de riesgo y motivos. El celular no se muestra en pantalla: solo en el Excel, que también
          incluye el monto cobrado. El correo no se muestra en ningún lado.
        </p>
      </Seccion>

      <Seccion titulo="Casos frecuentes">
        <ul className="list-disc pl-5">
          <li>
            Cargar los datos cada mes: si la última carga tiene más de 30 días, la lista puede salir
            incompleta y muestra un aviso de datos antiguos.
          </li>
          <li>
            Socios sin cédula: no aparecen en la lista, pero siguen en el sistema. Registre su
            cédula en los datos del gimnasio.
          </li>
          <li>
            Fecha pasada: no se permite; la lista siempre mira de hoy en adelante. Elija hoy o una
            fecha posterior.
          </li>
        </ul>
      </Seccion>
    </div>
  )
}

/** Boton "¿Como funciona esta lista?" que abre el Modal de ayuda y devuelve el foco al cerrar. */
export function AyudaLista() {
  const [abierta, setAbierta] = useState(false)
  const botonRef = useRef<HTMLButtonElement>(null)

  const cerrar = () => {
    setAbierta(false)
    botonRef.current?.focus()
  }

  return (
    <>
      <button
        ref={botonRef}
        type="button"
        onClick={() => setAbierta(true)}
        className="self-start rounded-pill border border-ink/20 px-4 py-2 text-sm font-medium"
      >
        ¿Cómo funciona esta lista?
      </button>
      <Modal open={abierta} title="¿Cómo funciona esta lista?" onClose={cerrar}>
        <Contenido />
      </Modal>
    </>
  )
}
