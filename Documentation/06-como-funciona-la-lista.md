# ¿Cómo funciona la lista de socios por vencer?

Guía para el personal del gimnasio. Explica qué muestra la lista, cómo se ordena y qué hacer en los casos más comunes. No hace falta saber nada técnico para leerla.

## 1. Qué hace la lista

1. Eliges una **fecha**: hoy o un día posterior.
2. Eliges **cuántos días hacia adelante** quieres revisar (como máximo 31, es decir, un mes).
3. El sistema busca a los socios cuya membresía **vence entre esa fecha y los días que elegiste**.
4. Para cada uno calcula la **probabilidad de que no renueve** en los 30 días siguientes a su vencimiento. Ese cálculo se basa en lo que ha pasado con socios parecidos en el historial del gimnasio.
5. Los ordena **de mayor a menor riesgo**: arriba quedan los que tienen más probabilidad de no volver.

## 2. Socios prioritarios a contactar

Tú indicas **cuántos socios quieres contactar primero** (por ejemplo, 25).

- Esos son los **socios prioritarios a contactar**: salen arriba, en una tabla con ese mismo título.
- El resto de socios que vencen en esos días aparece debajo, en otra tabla llamada **otros socios por vencer** (si no queda ninguno, esa tabla no se muestra).
- El Excel que descargas tiene las mismas dos tablas, cada una en su hoja: **"Socios prioritarios a contactar"** y **"Otros socios por vencer"** (si no queda ninguno, esta hoja solo tiene los títulos de las columnas), más una hoja **"Resumen"** con el nombre de la lista, su fecha, hasta qué día vencen, cuántos socios hay en cada tabla y cuántos en cada nivel de riesgo.

**Nombre de la lista.** Antes de generarla puedes escribir un nombre (hasta 80 caracteres), por ejemplo "Campaña octubre". Si no lo cambias, el sistema propone uno con la fecha, por ejemplo **"Lista del 29 sep 2026"**, que se actualiza solo si cambias la fecha. El nombre es el título de la lista, aparece en **Listas anteriores** y en la hoja "Resumen" del Excel. Una vez generada, la lista no se puede renombrar.

## 3. Niveles de riesgo: alto, medio y bajo

Cada socio tiene un nivel: **alto**, **medio** o **bajo**.

- Los niveles **no dependen** de cuántos prioritarios pidas. Pedir 10 o 50 no cambia el nivel de nadie.
- Se fijaron una sola vez, al preparar el sistema con el historial del gimnasio:
  - aproximadamente el **20 %** de socios con más riesgo es **alto**;
  - el siguiente **30 %** es **medio**;
  - el **50 %** restante es **bajo**.
- Por eso lo normal es que los prioritarios salgan en nivel alto.

## 4. Motivos

Junto a cada socio se muestran los **motivos principales** por los que tiene más riesgo; por ejemplo, el plan que tiene o cuántas membresías ha tenido antes. Se muestran sin números, en pantalla y en el Excel: sirven para orientar la conversación con el socio. Si no hay motivos destacados, se indica "Sin factores de riesgo destacados".

> La ayuda **"¿Cómo funciona esta lista?"** de la aplicación muestra un resumen de las secciones 1 a 4 y, desde R-010, de las secciones 7 ("Gestionar a un socio") y 8 ("Campañas"). Las secciones 5 y 6 solo están en este documento.

## 5. Qué datos se muestran

| Se muestra | No se muestra |
|---|---|
| En pantalla y en el Excel, las mismas columnas: prioridad, nombre, cédula, plan, fecha de vencimiento ("Vence el"), días que faltan para el vencimiento, nivel de riesgo, motivos principales, **Gestión** y **Campaña** (ver sección 7). En pantalla hay además un botón para gestionar a cada socio. | Correo electrónico, celular y monto cobrado (ni en pantalla ni en el Excel). |

Encima de las tablas, el **nombre de la lista** como título y un resumen de dos líneas: **"Rango de fechas: 29 sep – 29 oct 2026"** (desde la fecha de la lista hasta los días que elegiste) y **"Socios priorizados para campañas: 25"**. En **Listas anteriores** cada lista aparece con su nombre, por ejemplo "Lista del 29 sep 2026 · 25 prioritarios" o "Campaña octubre · 25 prioritarios".

Los socios **sin cédula registrada no aparecen en la lista**. No se borran: siguen en el sistema y se siguen usando para aprender del historial.

## 6. Casos frecuentes

| Situación | Qué pasa | Qué hacer |
|---|---|---|
| Eliges una fecha futura, pero los datos solo se cargaron hasta un mes antes | La lista sale **incompleta**. Solo aparecen las membresías que el sistema ya conoce (por ejemplo, planes largos comprados antes). Los planes mensuales vendidos después de la última carga no aparecen, porque el sistema todavía no sabe de ellos. | Cargar los datos **cada mes**. Si la última carga tiene más de 30 días, la lista muestra un **aviso de datos antiguos**. |
| Eliges una fecha anterior a hoy | No se permite. La lista siempre mira de hoy en adelante. | Elegir hoy o una fecha posterior. |
| Pides más de 31 días | No se permite. El máximo es un mes. | Elegir 31 días o menos. |
| Un socio no tiene cédula registrada | No aparece en la lista, pero sigue en el sistema. | Registrar su cédula en los datos del gimnasio. |
| Consultas una lista generada antes de estos ajustes | Se conserva tal como se generó. | Nada; si necesitas el formato nuevo, genera una lista nueva. |

## 7. Cómo gestionar a un socio desde la lista

"Gestionar" es anotar qué se va a hacer con un socio para que renueve y qué pasó después.

**Las dos columnas nuevas**

| Columna | Qué puede decir | Qué significa |
|---|---|---|
| **Gestión** | "Sin gestión" | Nadie ha empezado a trabajar con este socio. |
| | "Pendiente" | Ya hay un seguimiento abierto; falta saber si renovó. |
| | "Cerrada" | Ya se anotó si renovó o no, o se eligió "No asignar campaña". No se puede cambiar. |
| **Campaña** | el nombre de una campaña | La campaña que se le asignó. |
| | "Sin campaña" | Se eligió "No asignar campaña". La gestión está cerrada. |
| | "—" | Todavía no tiene gestión. |

**Paso 1 · Crear la gestión.** En la fila de cada socio está el botón **"Gestionar"**. Al pulsarlo se abre una ventana donde eliges una de las campañas sugeridas para ese socio o **"No asignar campaña"**.

Si eliges **una campaña**, completas además:

- **La fecha de seguimiento**: el día en que volverás a revisar a ese socio. El sistema propone una; puedes cambiarla, siempre entre hoy y 30 días después del vencimiento.
- **El responsable** (opcional): quién se encarga.

Pulsa **"Crear gestión"**. La ventana se cierra, la lista se actualiza y la fila pasa a "Pendiente", con la campaña y el botón **"Registrar resultado"**. El resultado no se anota en ese momento: se anota después, con ese botón (paso 2).

Si eliges **"No asignar campaña"**, la ventana ya no pide fecha de seguimiento ni responsable y avisa: "Sin campaña, la gestión queda cerrada y no tendrá seguimiento." Al pulsar **"Crear gestión"** la ventana se cierra y la fila pasa a "Cerrada" y "Sin campaña". La gestión queda cerrada desde el inicio: no hay resultado que anotar y solo se puede consultar con **"Ver gestión"**, donde se lee "No se le asignó campaña".

**Paso 2 · Registrar el resultado** (solo si asignaste una campaña). Cuando hayas hablado con el socio (o cuando llegue la fecha), pulsa **"Registrar resultado"** y anota cómo te fue:

| Pregunta | Qué significa |
|---|---|
| **¿Se contactó al socio?** | Si lograste hablar o escribirte con él. |
| **¿Se ofreció la campaña?** | Si le propusiste la campaña que tenía asignada. |
| **¿Aceptó la campaña?** | Si el socio aceptó lo que le propusiste. |
| **¿Renovó?** | **Sí** o **No** cierran la gestión y ya no se puede cambiar; **Pendiente** la deja abierta para seguir revisando al socio (puedes poner una nueva fecha de seguimiento). |

Puedes añadir observaciones. Al pulsar **guardar**, la ventana se cierra y la lista se actualiza: con **Sí** o **No** la fila pasa a "Cerrada" y muestra **"Ver gestión"**; con **Pendiente** sigue "Pendiente" y puedes volver a abrirla con **"Registrar resultado"**. Una gestión cerrada solo se puede consultar con **"Ver gestión"**.

Si algo sale mal al guardar (por ejemplo, una fecha que no vale), la ventana **no** se cierra: muestra el mensaje para que lo corrijas.

**La fecha del contacto.** Si contactaste al socio, anotas qué día fue. Esa fecha debe estar **entre el día en que se creó la gestión y hoy**: no puede ser anterior a ese día ni una fecha futura. Por ejemplo, si creaste la gestión el 30 de septiembre y hoy es 5 de octubre, vale cualquier día del 30 de septiembre al 5 de octubre.

El formulario no deja marcar respuestas que no tienen sentido juntas (por ejemplo, "aceptó la campaña" si no se contactó al socio): esas opciones aparecen desactivadas.

**Conviene saber**

- Cada socio tiene **una sola gestión por cada período de su membresía**. Si el mismo socio aparece en otra lista, verás ahí la misma gestión.
- Si después se cambia el nombre de una campaña o se inactiva, los socios que ya la tenían asignada **la conservan tal como estaba**.
- El Excel muestra las columnas Gestión y Campaña tal como están en el momento de descargarlo; una gestión sin campaña aparece como "Cerrada" y "Sin campaña".

## 8. Campañas

Una campaña es lo que el gimnasio le propone a un socio para que renueve, por ejemplo una llamada o un beneficio.

- Se crean y administran en la página **"Campañas"**. Allí puedes **crear** una campaña, **editarla**, **inactivarla** y **volver a activarla**. Las campañas **no se borran**. Vienen tres de ejemplo (su nombre empieza por "Ejemplo:").
- Los **niveles de riesgo** y los **planes** que marcas en una campaña deciden a qué socios se les sugiere. Por ejemplo, una campaña marcada para nivel alto y plan mensual solo se sugiere a socios de riesgo alto con plan mensual.
- La **prioridad** ordena las sugerencias: la campaña con prioridad 1 sale primero.
- Una campaña **inactiva** deja de sugerirse hasta que la actives de nuevo con el botón **"Activar"** de su fila (no pide confirmación; si te equivocas, la vuelves a inactivar). Los socios que ya la tenían asignada la conservan.

## 9. Seguimientos pendientes y aviso de datos del mes (en Inicio)

- **Seguimientos pendientes.** Inicio muestra tres números: **Vencidos** (la fecha de seguimiento ya pasó), **Para hoy** y **Próximos 7 días**. Solo cuentan las gestiones que siguen abiertas ("Pendiente"); las cerradas, incluidas las que se crearon sin campaña, no aparecen.
- Al pulsar uno de los números se abre la página **Seguimiento** con esos socios. El botón **"Abrir gestión"** abre la misma ventana que en la lista para anotar el resultado. Al guardar, la ventana se cierra y la página se actualiza. Si respondes "¿Renovó?" **Sí** o **No**, la gestión se cierra, el socio sale de la página y el número baja; con **Pendiente** y una nueva fecha, el socio pasa al grupo que le toque.
- **Aviso de datos del mes.** Si en el mes actual todavía no se subió la plantilla en **Carga**, Inicio avisa "Aún no se han cargado los datos de este mes." con el enlace **"Ir a Carga"**. Los datos históricos del arranque no cuentan: el aviso desaparece al confirmar la primera carga del mes.
- **Ayuda.** El botón **"¿Cómo funciona el inicio?"**, junto al título, explica estas tres cosas: los seguimientos pendientes, qué hacer al pulsar un número y el aviso de datos del mes.

En la pantalla de la lista, el botón **"¿Cómo funciona esta lista?"** abre un resumen de esta misma explicación.

## 10. Cómo leer el dashboard

El **Dashboard** resume las gestiones del mes que elijas. Debajo del título se lee, por ejemplo, **"Resultados de septiembre de 2026"**. El botón **"¿Cómo funciona el dashboard?"** abre esta misma explicación.

- **El filtro por mes.** Se cuentan las gestiones **creadas** en ese mes. Por defecto es el mes actual.
- **El embudo.** Cinco barras: gestiones asignadas, socios contactados, campaña ofrecida, campaña aceptada y renovaron. Cada barra muestra el número y el porcentaje sobre las asignadas (por ejemplo "4 · 40,0 %"). Solo cuenta gestiones **con campaña**.
- **Resultado de las gestiones.** Un gráfico redondo con tres partes: **Renovaron**, **No renovaron** y **Sin resultado** (gestiones que siguen abiertas o que se crearon sin campaña). En el centro está el total de gestiones del mes.
- **La tabla por campaña.** Para cada campaña: gestiones, socios contactados y renovaciones.
- **Tasa de renovación y de no renovación.** Se calculan solo con las gestiones cerradas en las que "¿Renovó?" es **Sí** o **No**. Ejemplo: 4 "Sí" de 10 → renovación 40 % y no renovación 60 %.
- **Casos insuficientes.** Si una campaña tiene menos de 10 gestiones cerradas con respuesta, no se muestra la tasa: dice "Casos insuficientes".
- **La fila "Sin campaña".** Son los socios gestionados sin campaña. Nunca tienen tasa.
- **La tarjeta del modelo.** Versión del modelo, fecha en que se entrenó, ciclos usados, próxima revisión y ciclos nuevos acumulados.
- **Qué significan las cifras.** Son resultados observados: no demuestran que la campaña causó la renovación.

Cada gráfico tiene debajo una tabla con los mismos números, para quien prefiera leerlos.

**Imprimir o guardar en PDF.** El botón **"Imprimir / Guardar PDF"** abre la ventana de impresión del navegador; ahí puedes imprimir o elegir "Guardar como PDF". Se imprimen el título, el mes, los gráficos con sus tablas, la tabla por campaña, la tarjeta del modelo y el aviso; no salen el menú, los botones ni el filtro. El botón está desactivado mientras no hay datos. La aplicación no genera archivos por sí misma: es la impresión normal del navegador.
