import { BotonAyuda, SeccionAyuda } from '../../../shared/ui/Ayuda'

/**
 * Ayuda "¿Cómo funciona el inicio?" (R-012, T10): resumen de
 * `Documentation/06-como-funciona-la-lista.md` §9 para el personal del gimnasio, sin terminos
 * tecnicos. El texto vive en el componente.
 */
export function AyudaInicio() {
  return (
    <BotonAyuda titulo="¿Cómo funciona el inicio?">
      <SeccionAyuda titulo="Seguimientos pendientes">
        <p>
          Inicio muestra tres números con los socios que tienes que volver a revisar, según la
          fecha de seguimiento que se puso en su gestión:
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>«Vencidos»: la fecha de seguimiento ya pasó.</li>
          <li>«Para hoy»: la fecha de seguimiento es hoy.</li>
          <li>«Próximos 7 días»: la fecha de seguimiento es de mañana a 7 días.</li>
        </ul>
        <p>
          Solo cuentan las gestiones abiertas que tienen campaña. Las gestiones cerradas y las que
          se crearon sin campaña no cuentan.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Qué hacer al pulsar un número">
        <p>
          Al pulsar un número se abre la página «Seguimiento» con esos socios. En cada fila, el
          botón «Abrir gestión» abre la ventana para anotar el resultado del contacto.
        </p>
        <p>
          Al guardar, la ventana se cierra y la lista se actualiza. Si en «¿Renovó?» respondes «Sí»
          o «No», la gestión se cierra, el socio sale de la página y el número baja. Si respondes
          «Pendiente», el socio sigue en seguimiento con la fecha que elijas.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Aviso de datos del mes">
        <p>
          Si este mes todavía no se subió la plantilla en la página «Carga», Inicio muestra el aviso
          «Aún no se han cargado los datos de este mes.» con el enlace «Ir a Carga».
        </p>
        <p>
          El aviso desaparece cuando se confirma la primera carga del mes. Los datos históricos que
          se cargaron al instalar el sistema no cuentan para este aviso.
        </p>
      </SeccionAyuda>
    </BotonAyuda>
  )
}
