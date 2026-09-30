import { useRef, useState, type ReactNode } from 'react'
import { Modal } from '../../../shared/ui/Modal'

/**
 * Resumen estatico de `Documentation/06-como-funciona-la-lista.md` §1–§4 (decision (m) de R-007;
 * R-008 retira "Qué datos se muestran" y "Casos frecuentes") y, desde R-010, de su §7: campañas y
 * gestion de un socio (decision (i)).
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

      <Seccion titulo="Campañas">
        <p>
          Una campaña es lo que el gimnasio le propone a un socio para que renueve, por ejemplo una
          llamada o un beneficio. Se crean y administran en la página «Campañas». Allí puedes crear
          una campaña, editarla, inactivarla y volver a activarla. Las campañas no se borran.
        </p>
        <p>
          Los niveles de riesgo y los planes que marcas en una campaña deciden a qué socios se les
          sugiere. La prioridad ordena las sugerencias: la campaña con prioridad 1 sale primero.
        </p>
        <p>
          Una campaña inactiva deja de sugerirse hasta que la actives de nuevo. Los socios que ya la
          tenían asignada la conservan.
        </p>
      </Seccion>

      <Seccion titulo="Gestionar a un socio">
        <p>
          En la fila de cada socio está el botón «Gestionar». Al pulsarlo eliges una de las campañas
          sugeridas para ese socio o «No asignar campaña». La fecha de seguimiento es el día en que
          volverás a revisar a ese socio.
        </p>
        <p>Después, con «Registrar resultado», anotas cómo te fue:</p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>«¿Se contactó al socio?»: si lograste hablar o escribirte con él.</li>
          <li>«¿Se ofreció la campaña?»: si le propusiste la campaña que tenía asignada.</li>
          <li>«¿Aceptó la campaña?»: si el socio aceptó lo que le propusiste.</li>
          <li>
            «¿Renovó?»: «Sí» o «No» cierran la gestión y ya no se puede cambiar; «Pendiente» la deja
            abierta para seguir revisando al socio.
          </li>
        </ul>
        <p>
          La fecha del contacto debe estar entre el día en que se creó la gestión y hoy: no puede
          ser anterior a ese día ni una fecha futura.
        </p>
        <p>
          Si eliges «No asignar campaña», la gestión queda cerrada desde el inicio: no hay resultado
          que anotar y solo se puede consultar con «Ver gestión».
        </p>
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
