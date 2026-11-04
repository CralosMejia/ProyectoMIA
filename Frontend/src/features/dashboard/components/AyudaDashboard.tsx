import { BotonAyuda, SeccionAyuda } from '../../../shared/ui/Ayuda'

/**
 * Ayuda "¿Cómo funciona el dashboard?" (R-012, T7): resumen de
 * `Documentation/03-casos-de-uso.md` §14 (CU-11, RN-11.1) y de
 * `Documentation/06-como-funciona-la-lista.md` §9 para el personal del gimnasio, sin terminos
 * tecnicos. El texto vive en el componente. R-018 (T7) añadio los indicadores del piloto y
 * R-021 (T3) los explica con las palabras de sus graficos, sin dinero.
 */
export function AyudaDashboard() {
  return (
    <BotonAyuda titulo="¿Cómo funciona el dashboard?">
      <SeccionAyuda titulo="El filtro por mes">
        <p>
          Eliges un mes y el dashboard muestra las gestiones que se crearon en ese mes. Al abrir la
          página aparece el mes actual. Si cambias de mes, todas las cifras se actualizan.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="El embudo">
        <p>
          El embudo muestra cuántas gestiones avanzaron en cada paso. Solo cuenta las gestiones que
          tienen campaña:
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>«Gestiones asignadas»: socios a los que se les asignó una campaña en el mes.</li>
          <li>«Socios contactados»: con cuántos de ellos se logró hablar o escribirse.</li>
          <li>«Campaña ofrecida»: a cuántos se les propuso la campaña.</li>
          <li>«Campaña aceptada»: cuántos aceptaron lo que se les propuso.</li>
          <li>«Renovaron»: cuántos renovaron su membresía.</li>
        </ul>
        <p>Cada paso muestra el número y su porcentaje sobre las gestiones asignadas.</p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Resultado de las gestiones">
        <p>El gráfico redondo reparte todas las gestiones del mes en tres grupos:</p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>«Renovaron»: gestiones cerradas en las que el socio renovó.</li>
          <li>«No renovaron»: gestiones cerradas en las que el socio no renovó.</li>
          <li>
            «Sin resultado»: gestiones que siguen abiertas o que se crearon sin campaña, y que por
            eso todavía no tienen un resultado.
          </li>
        </ul>
        <p>En el centro aparece el total de gestiones del mes.</p>
      </SeccionAyuda>

      <SeccionAyuda titulo="La tabla por campaña">
        <p>
          Cada fila es una campaña. Muestra cuántas gestiones tuvo en el mes, a cuántos socios se
          contactó, cuántos renovaron y su tasa de renovación.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Tasa de renovación y de no renovación">
        <p>
          Las tasas se calculan solo con las gestiones cerradas con respuesta «Sí» o «No» en
          «¿Renovó?». Las que siguen abiertas no cuentan.
        </p>
        <p>
          La tasa de renovación es cuántas respondieron «Sí» sobre ese total, y la de no renovación
          es cuántas respondieron «No». Por ejemplo, si de 10 gestiones cerradas 4 son «Sí», la
          tasa de renovación es 40 % y la de no renovación es 60 %.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="Casos insuficientes">
        <p>
          Si una campaña tiene menos de 10 gestiones cerradas con respuesta, no se muestra su tasa
          y aparece «Casos insuficientes»: con tan pocos casos el porcentaje podría engañar.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="La fila «Sin campaña»">
        <p>
          Reúne a los socios que se gestionaron sin asignarles una campaña. Esas gestiones quedan
          cerradas desde el inicio sin resultado, así que esta fila nunca tiene tasa.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="La tarjeta del modelo">
        <p>
          Muestra el modelo que calcula el riesgo de los socios: su versión, la fecha en que se
          entrenó, cuántos ciclos de membresía se usaron para entrenarlo, la fecha de la próxima
          revisión y cuántos ciclos nuevos hay desde entonces para volver a entrenarlo.
        </p>
      </SeccionAyuda>

      <SeccionAyuda titulo="¿Cómo le fue a la lista del mes?">
        <p>
          Esta parte cuenta cómo le fue a la última lista del mes y a las llamadas que se hicieron
          con ella. Se fija en los 25 primeros socios de esa lista y lo muestra en dos gráficos:
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>
            «¿Cuántos contactamos y cuántos renovaron?»: tres barras. «Lista del mes» son los 25
            socios; «Los contactamos», a cuántos de ellos se llamó o se escribió, y cuántos fueron
            antes del vencimiento; «Renovaron», cuántos de los contactados renovaron. La parte
            rayada son los contactados que aún están «Por confirmar».
          </li>
          <li>
            «¿Con cuánta anticipación?»: una línea en días que dice, en promedio, cuántos días
            antes del vencimiento se llamó a los socios. Las marcas «30 días», «15 días» y «7 días»
            cuentan los días que faltaban para el vencimiento, y la marca alta «Vence» es el día en
            que vence la membresía. El punto «Promedio» señala el promedio. Debajo se lee cuántos
            socios se llamaron antes del vencimiento y cuántos el mismo día o después, cuándo fue
            la llamada más temprana y cuándo la más tardía, y cuántas llamadas hubo en cada tramo:
            «15 días o más antes», «Entre 8 y 14 días antes», «Entre 1 y 7 días antes» y «El mismo
            día o después» (con rayas). Solo cuentan como antes del vencimiento las llamadas hechas
            antes del día en que vence la membresía.
          </li>
        </ul>
        <p>
          De cada socio solo se sabe si renovó 30 días después de su vencimiento; hasta entonces
          aparece «Por confirmar». Si son pocos socios todavía, la pantalla lo avisa: tómalo con
          cuidado.
        </p>
        <DefinicionesPiloto />
      </SeccionAyuda>

      <SeccionAyuda titulo="Qué significan las cifras">
        <p>
          Las cifras son resultados observados: cuentan lo que pasó, pero no demuestran que la
          campaña causó la renovación. Un socio pudo renovar por otros motivos.
        </p>
      </SeccionAyuda>
    </BotonAyuda>
  )
}

/**
 * Definiciones exactas de los indicadores del piloto (R-021, definicion (d)); un solo contenido
 * para la ventana "¿Cómo se calcula?" de la tarjeta y para la ayuda del dashboard. Sin dinero.
 */
export function DefinicionesPiloto() {
  return (
    <div className="flex flex-col gap-2">
      <p className="font-medium">Cómo se calcula cada cifra</p>
      <p>Solo cuentan los 25 primeros socios de la última lista del mes (el top 25).</p>
      <ul className="flex list-disc flex-col gap-1 pl-5">
        <li>
          Contactados antes del vencimiento: socios contactados antes de su fecha de vencimiento ÷
          socios con datos de membresía. Contactarlo el mismo día del vencimiento ya no cuenta.
        </li>
        <li>
          Días de anticipación: promedio de (fecha de vencimiento − fecha del contacto), con un
          decimal. Puede ser cero o negativo si se llamó el mismo día o después del vencimiento.
        </li>
        <li>
          La llamada más temprana es la de mayor (fecha de vencimiento − fecha del contacto) y la
          más tardía, la de menor. Los tramos reparten esas llamadas en días enteros antes del
          vencimiento: 15 días o más (≥ 15), entre 8 y 14 días (8–14), entre 1 y 7 días (1–7) y
          el mismo día o después (≤ 0). Cuentan los mismos socios que el promedio: los
          contactados con fecha de contacto.
        </li>
        <li>
          Renovación de los contactados: contactados que renovaron ÷ contactados ya verificados.
        </li>
      </ul>
      <p>
        «n» es el número de socios con el que se calcula cada cifra. Los socios sin datos de
        membresía o sin fecha de vencimiento no entran en ese número.
      </p>
      <p>
        Verificación a los 30 días: de cada socio solo se sabe si renovó 30 días después del
        vencimiento de su membresía. Hasta entonces queda «Por confirmar».
      </p>
      <p>
        Estas cifras describen lo que ocurrió y no prueban que la llamada cause la renovación.
      </p>
    </div>
  )
}
