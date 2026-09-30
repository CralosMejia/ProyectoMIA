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
- El Excel que descargas tiene una hoja solo con los prioritarios, otra con todos y una hoja de resumen.

## 3. Niveles de riesgo: alto, medio y bajo

Cada socio tiene un nivel: **alto**, **medio** o **bajo**.

- Los niveles **no dependen** de cuántos prioritarios pidas. Pedir 10 o 50 no cambia el nivel de nadie.
- Se fijaron una sola vez, al preparar el sistema con el historial del gimnasio:
  - aproximadamente el **20 %** de socios con más riesgo es **alto**;
  - el siguiente **30 %** es **medio**;
  - el **50 %** restante es **bajo**.
- Por eso lo normal es que los prioritarios salgan en nivel alto.

## 4. Factores

Junto a cada socio se muestran los **motivos principales** por los que tiene más riesgo; por ejemplo, el plan que tiene o cuántas membresías ha tenido antes. En pantalla se muestran sin números: sirven para orientar la conversación con el socio. Si no hay motivos destacados, se indica "Sin factores de riesgo destacados". El Excel sí incluye los números, para quien quiera revisarlos.

## 5. Qué datos se muestran

| Se muestra | No se muestra |
|---|---|
| En pantalla: prioridad, nombre, cédula, plan, fecha de vencimiento ("Vence el"), días que faltan para el vencimiento, nivel de riesgo y motivos principales. El Excel añade el celular y el monto cobrado. | Correo electrónico (ni en pantalla ni en el Excel). El celular no se muestra en pantalla, solo en el Excel. |

Encima de las tablas, un resumen de dos líneas: **"Rango de fechas: 29 sep – 29 oct 2026"** (desde la fecha de la lista hasta los días que elegiste) y **"Socios priorizados para campañas: 25"**. En **Listas anteriores** cada lista aparece con un nombre corto, por ejemplo "29 sep 2026 · 25 prioritarios".

Los socios **sin cédula registrada no aparecen en la lista**. No se borran: siguen en el sistema y se siguen usando para aprender del historial.

## 6. Casos frecuentes

| Situación | Qué pasa | Qué hacer |
|---|---|---|
| Eliges una fecha futura, pero los datos solo se cargaron hasta un mes antes | La lista sale **incompleta**. Solo aparecen las membresías que el sistema ya conoce (por ejemplo, planes largos comprados antes). Los planes mensuales vendidos después de la última carga no aparecen, porque el sistema todavía no sabe de ellos. | Cargar los datos **cada mes**. Si la última carga tiene más de 30 días, la lista muestra un **aviso de datos antiguos**. |
| Eliges una fecha anterior a hoy | No se permite. La lista siempre mira de hoy en adelante. | Elegir hoy o una fecha posterior. |
| Pides más de 31 días | No se permite. El máximo es un mes. | Elegir 31 días o menos. |
| Un socio no tiene cédula registrada | No aparece en la lista, pero sigue en el sistema. | Registrar su cédula en los datos del gimnasio. |
| Consultas una lista generada antes de estos ajustes | Se conserva tal como se generó. | Nada; si necesitas el formato nuevo, genera una lista nueva. |

## 7. Próximamente

Está planificada, todavía no disponible:

- una **alerta** cuando no se hayan cargado los datos del mes.

Ya disponible: en la pantalla de la lista, el botón **"¿Cómo funciona esta lista?"** abre un resumen de esta misma explicación.
