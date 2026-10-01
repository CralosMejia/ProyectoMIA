import { BotonAyuda, SeccionAyuda } from '../../../shared/ui/Ayuda'

/**
 * Resumen estatico de `Documentation/06-como-funciona-la-lista.md` §1–§4 (decision (m) de R-007;
 * R-008 retira "Qué datos se muestran" y "Casos frecuentes") y, desde R-010, de su §7: campañas y
 * gestion de un socio (decision (i)).
 * El texto vive en el componente: no se carga el `.md` en tiempo de ejecucion.
 * Lenguaje para el personal del gimnasio, sin terminos tecnicos. Desde R-012 usa la ayuda
 * compartida de `shared/ui/Ayuda` (boton, `Modal` y devolucion de foco).
 */

function Contenido() {
  return (
    <>
      <SeccionAyuda titulo="Qué hace la lista">
        <p>
          Eliges una fecha (hoy o un día posterior) y cuántos días hacia adelante quieres revisar,
          como máximo 31. El sistema busca a los socios cuya membresía vence en esos días, calcula
          la probabilidad de que cada uno no renueve y los ordena de mayor a menor riesgo.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Socios prioritarios a contactar">
        <p>
          Tú indicas cuántos socios quieres contactar primero (por ejemplo, 25). Esos salen arriba,
          en la tabla «Socios prioritarios a contactar». El resto aparece debajo, en «Otros socios
          por vencer».
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Niveles de riesgo: alto, medio y bajo">
        <p>
          Cada socio tiene un nivel alto, medio o bajo. Los niveles se fijaron una sola vez con el
          historial del gimnasio (más o menos, el 20 % con más riesgo es alto, el siguiente 30 % es
          medio y el resto es bajo) y no cambian según cuántos prioritarios pidas.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Motivos">
        <p>
          Junto a cada socio se muestran los motivos principales de su riesgo, por ejemplo el plan
          que tiene o cuántas membresías ha tenido antes. Sirven para orientar la conversación. Si
          no hay motivos destacados, se indica «Sin factores de riesgo destacados».
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Campañas">
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
      </SeccionAyuda>

      <SeccionAyuda titulo="Gestionar a un socio">
        <p>
          En la fila de cada socio está el botón «Gestionar». Al pulsarlo eliges una de las campañas
          sugeridas para ese socio o «No asignar campaña». La fecha de seguimiento es el día en que
          volverás a revisar a ese socio.
        </p>
        <p>
          Al pulsar «Crear gestión», la ventana se cierra y la lista se actualiza. El resultado se
          anota después con «Registrar resultado» en la fila del socio, donde respondes cómo te fue:
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>«¿Se contactó al socio?»: si lograste hablar o escribirte con él.</li>
          <li>«¿Se ofreció la campaña?»: si le propusiste la campaña que tenía asignada.</li>
          <li>«¿Aceptó la campaña?»: si el socio aceptó lo que le propusiste.</li>
          <li>
            «¿Renovó?»: «Sí» o «No» cierran la gestión y ya no se puede cambiar; «Pendiente» la deja
            abierta para seguir revisando al socio.
          </li>
        </ul>
        <p>Al guardar el resultado, la ventana también se cierra y la lista se actualiza.</p>
        <p>
          La fecha del contacto debe estar entre el día en que se creó la gestión y hoy: no puede
          ser anterior a ese día ni una fecha futura.
        </p>
        <p>
          Si eliges «No asignar campaña», la gestión queda cerrada desde el inicio: no hay resultado
          que anotar y solo se puede consultar con «Ver gestión».
        </p>
      </SeccionAyuda>
    </>
  )
}

/** Boton "¿Como funciona esta lista?" que abre la ayuda y devuelve el foco al cerrar. */
export function AyudaLista() {
  return (
    <BotonAyuda titulo="¿Cómo funciona esta lista?">
      <Contenido />
    </BotonAyuda>
  )
}
