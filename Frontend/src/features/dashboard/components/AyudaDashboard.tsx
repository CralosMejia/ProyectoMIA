import { BotonAyuda, SeccionAyuda } from '../../../shared/ui/Ayuda'

/**
 * Ayuda "¿Cómo funciona el dashboard?" (R-012, T7): resumen de
 * `Documentation/03-casos-de-uso.md` §14 (CU-11, RN-11.1) y de
 * `Documentation/06-como-funciona-la-lista.md` §9 para el personal del gimnasio, sin terminos
 * tecnicos. El texto vive en el componente. R-018 (T7) añade "Indicadores del piloto"
 * (definiciones (a)-(f) del plan de R-018).
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

      <SeccionAyuda titulo="Indicadores del piloto">
        <p>
          Miden cómo le fue a la lista del mes y a las llamadas que se hicieron con ella. Se fijan en
          los 25 primeros socios de la última lista del mes:
        </p>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          <li>
            «Precisión del top 25»: de los 25 primeros socios de la lista del mes, cuántos no
            renovaron. De cada socio solo se sabe si renovó 30 días después de que vence su
            membresía; hasta entonces aparece «pendiente».
          </li>
          <li>
            «Contactados antes del vencimiento»: qué porcentaje de esos 25 socios se contactó antes
            de que venciera su membresía. Contactarlo el mismo día del vencimiento ya no cuenta.
          </li>
          <li>
            «Días de anticipación»: en promedio, cuántos días antes del vencimiento se contactó a
            los socios.
          </li>
          <li>
            «Renovación de los contactados»: de los socios contactados, qué porcentaje renovó. Como
            en la precisión, solo cuentan los socios que ya cumplieron los 30 días.
          </li>
          <li>
            «Monto retenido»: la suma de lo que se cobró en las renovaciones de los socios
            contactados. Si una renovación no tiene cobro registrado, se usa lo facturado; las
            renovaciones que no tienen ningún monto se cuentan aparte.
          </li>
        </ul>
        <p>
          Cada cifra muestra cuántos casos tiene, para saber con cuántos socios se calculó. En
          «Renovación de los contactados» el número de casos cuenta a todos los contactados; en
          «Monto retenido» cuenta solo a los contactados ya verificados, los que cumplieron los 30
          días. Por eso pueden ser distintos.
        </p>
        <p>
          Un aviso: la precisión puede salir más baja que la real, porque contactar a los socios
          hace que algunos que se iban a ir terminen renovando.
        </p>
        <p>
          Estas cifras describen lo que ocurrió y no prueban que el sistema cause la renovación.
        </p>
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
