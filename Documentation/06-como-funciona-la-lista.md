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

> Las secciones 5 a 7 amplían la explicación en este documento; la ayuda **"¿Cómo funciona esta lista?"** de la aplicación solo muestra las secciones 1 a 4 (desde R-008).

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
| | "Cerrada" | Ya se anotó si renovó o no. No se puede cambiar. |
| **Campaña** | el nombre de una campaña | La campaña que se le asignó. |
| | "Sin campaña" | Se decidió hacer seguimiento sin campaña. |
| | "—" | Todavía no tiene gestión. |

**Paso 1 · Crear la gestión.** Pulsa **"Gestionar"** en la fila del socio. Se abre una ventana donde eliges:

- **La campaña.** El sistema sugiere solo las campañas que aplican a ese socio (según su nivel de riesgo y su plan), en orden de prioridad. También puedes elegir **"No asignar campaña"**.
- **La fecha de seguimiento**: el día en que vas a revisar si renovó. El sistema propone una; puedes cambiarla, siempre entre hoy y 30 días después del vencimiento.
- **El responsable** (opcional): quién se encarga.

Pulsa **"Crear gestión"**. La fila pasa a "Pendiente".

**Paso 2 · Registrar el resultado.** Cuando hayas hablado con el socio (o cuando llegue la fecha), pulsa **"Registrar resultado"** y responde: si se le contactó y cuándo, si se le ofreció la campaña, si la aceptó, y **si renovó**. Puedes añadir observaciones.

- Si en "¿Renovó?" eliges **Pendiente**, la gestión sigue abierta y puedes poner una nueva fecha de seguimiento.
- Si eliges **Sí** o **No**, la gestión se **cierra**. Desde ese momento solo se puede consultar con **"Ver gestión"**.

El formulario no deja marcar respuestas que no tienen sentido juntas (por ejemplo, "aceptó la campaña" si no se contactó al socio): esas opciones aparecen desactivadas.

**Conviene saber**

- Cada socio tiene **una sola gestión por cada período de su membresía**. Si el mismo socio aparece en otra lista, verás ahí la misma gestión.
- Si después se cambia el nombre de una campaña o se inactiva, las gestiones que ya la tenían **la conservan tal como estaba**.
- Las campañas se crean, se editan y se inactivan en la pantalla **Campañas**. Vienen tres de ejemplo (su nombre empieza por "Ejemplo:"). Una campaña inactiva deja de sugerirse; no se borra.
- El Excel muestra las columnas Gestión y Campaña tal como están en el momento de descargarlo.

## 8. Próximamente

Está planificado, todavía no disponible:

- una **alerta** cuando no se hayan cargado los datos del mes;
- **avisos en Inicio** de los seguimientos vencidos, de hoy y de los próximos días.

Ya disponible: en la pantalla de la lista, el botón **"¿Cómo funciona esta lista?"** abre un resumen de esta misma explicación.
