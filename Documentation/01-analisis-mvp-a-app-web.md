# 01 · Análisis: del notebook MVP a una aplicación web

**Fecha:** 28 de septiembre de 2026
**Fuente analizada:** `Notebookes/MVP.ipynb` (informe técnico del MVP de Mtabolic, 196 celdas)
**Estado:** análisis inicial. Su alcance fue **ampliado y reemplazado** por [03 · Casos de uso](03-casos-de-uso.md); se conserva como registro de cómo evolucionó la decisión.

> **Nota de alineación (28-09-2026).** Este documento describe una app de tres funciones (cargar, generar lista, exportar), sin base de datos. La versión vigente del alcance es la de `03`: sistema de apoyo a la retención con base de datos acumulativa, migración única del histórico (CU-03), carga paulatina por plantilla (CU-01), reentrenamiento semestral (CU-02), campañas, seguimiento y dashboard. Donde este documento y `03` difieren, manda `03`. Las decisiones que cierran las preguntas de la §8 están anotadas en la propia tabla; las que siguen abiertas se consolidan en [04 · Pendientes para iniciar el desarrollo](04-pendientes-para-iniciar-desarrollo.md).

---

## 1. Objetivo de la aplicación

Llevar el MVP a una aplicación web fácil de desplegar que haga únicamente tres cosas:

1. Cargar el archivo (o archivos) Excel con los datos históricos de membresías.
2. Generar la lista priorizada de socios con riesgo de no renovación.
3. Exportar esa lista a Excel.

Queda fuera la parte analítica del informe: gráficos, comparación de modelos, métricas, validación y reconciliación con el Informe S5.

## 2. Qué parte del notebook se reutiliza

La aplicación solo necesita la cadena que termina en la **lista operativa** (Sección 13.8 del notebook).

| Bloque | Secciones del notebook | Qué hace |
|---|---|---|
| Lectura | 2.4, 3.1 – 3.7 | Selecciona hojas mensuales, detecta el encabezado, unifica nombres de columna, convierte fechas y montos. |
| Estandarización | 4.1 – 4.6 | Normaliza nombre, cédula, `socio_id`, plan (6 categorías) y forma de pago (5 categorías). |
| Variable objetivo | 5.1, 5.3 – 5.5 | Fecha de corte, estado del ciclo (evaluable / pendiente / excluido) y etiqueta `no_renovo` (ventana T a T+30). |
| Variables del modelo | 7.2 – 7.4 | Historial previo en T−30, imputación de monto y duración. |
| Lista operativa | 13.2, 13.3, 13.8 | Cartera a vencer, exclusión de quienes ya renovaron, reentrenamiento del Random Forest, probabilidad, nivel de riesgo y factores principales. |
| Exportación | 14.1 (parcial) | Excel con las hojas `top_25`, `cartera_completa` y `resumen`. |

Se elimina alrededor del **80 % del código** del notebook.

## 3. Implicaciones técnicas

### 3.1 Reorganizar el código en funciones

El notebook depende de variables globales creadas celda a celda (`fecha_corte_datos`, `actividades_por_socio`, `historial_por_socio`, `mediana_por_plan`, `REFERENCIA`, entre otras). Hay que reescribirlo como funciones encadenadas y sin estado global:

```
cargar(archivos) → preparar(datos) → entrenar(ciclos_evaluables) → lista_operativa(...) → exportar_excel(...)
```

Estimación: unas 250 a 300 líneas en un módulo de procesamiento y unas 60 a 80 líneas de interfaz.

### 3.2 Entrenar el modelo en cada carga o usar uno ya entrenado

El notebook ya reentrena el modelo operativo con todos los ciclos evaluables. La opción recomendada es **reentrenar en cada carga**:

- Con unos 1.500 ciclos, el entrenamiento tarda segundos.
- Las variables (ciclos previos, antigüedad, monto histórico) dependen del historial completo, así que los datos hay que procesarlos de todas formas.
- Evita que la versión del `.joblib` no coincida con la de scikit-learn del servidor.

**Consecuencia:** el algoritmo y sus parámetros quedan fijos (Random Forest, 300 árboles, profundidad 6, `min_samples_leaf=20`). La aplicación no vuelve a comparar modelos ni a validar su desempeño, así que un cambio fuerte en los datos no genera ninguna alerta.

### 3.3 Formato del archivo de entrada

El notebook espera **dos libros** (`Control Gym 2025` y `Control Gym 2026`):

- el **año** se obtiene del **nombre del archivo**;
- el **mes** se obtiene del **nombre de cada hoja** (ENERO, FEBRERO…);
- el resto de hojas (diarias, novedades, ventas) se ignora.

Si la aplicación recibe "un archivo", hay que redefinir este contrato (ver P-01). Además, los errores que hoy detienen el notebook (`raise`) tienen que convertirse en mensajes comprensibles en pantalla.

### 3.4 Fechas y valores escritos a mano

| Valor en el notebook | Situación en la aplicación |
|---|---|
| `FECHA_MINIMA_RAZONABLE = 2024-12-01` | Debe calcularse a partir de los datos o volverse un parámetro. |
| Fechas de partición `2026-01-01` y `2026-05-01` | Desaparecen: la aplicación no evalúa el modelo. |
| Fecha de generación = último día del último mes cargado | Hay que decidir si se mantiene o si se usa la fecha real del día (ver P-04). |
| `TOP_K = 25`, horizonte de 30 días | Hay que decidir si quedan fijos o configurables (ver P-05). |

### 3.5 Limitación conocida de la variable `mes_vencimiento`

Es categórica. En la lista operativa el mes a predecir (por ejemplo `2026-09`) nunca apareció en el entrenamiento y el codificador lo ignora (`handle_unknown="ignore"`). No da error, pero **no aporta nada** al predecir el futuro. Pasar a la aplicación no lo empeora; queda registrado como posible mejora (ver P-10).

### 3.6 Dependencias del entorno de notebook

Se eliminan `google.colab.files`, `IPython.display`, `matplotlib` y los `print`. El Excel se genera **en memoria** y se entrega con un botón de descarga; no se escribe nada en disco del servidor.

## 4. Datos personales y privacidad

Es la implicación más seria.

- Para que la asesora pueda contactar a los socios, la lista útil necesita **nombre, celular y correo**. En el notebook eso corresponde a `mostrar_datos_personales=True`.
- Los archivos que se suben contienen **cédulas, nombres, teléfonos y correos**.
- En Ecuador aplica la **Ley Orgánica de Protección de Datos Personales (LOPDP, 2021)**. Mtabolic debe autorizar el tratamiento y el lugar donde se aloja la aplicación.

Requisitos mínimos si la aplicación se publica en internet:

1. Acceso restringido (contraseña o invitación); **nunca pública**.
2. Procesamiento solo en memoria, sin guardar los archivos subidos.
3. Ningún dato personal en los registros (logs) del servidor.

La alternativa que evita el problema es ejecutar la aplicación **en local**, en un equipo de Mtabolic.

## 5. Opciones de despliegue

| Opción | Esfuerzo | Comentario |
|---|---|---|
| **Streamlit** (recomendada) | Bajo | Todo en Python; trae carga de archivos, tablas y botón de descarga. Se despliega en Streamlit Community Cloud con acceso restringido o se ejecuta en local con `streamlit run`. |
| Gradio / Hugging Face Spaces | Bajo | Parecido a Streamlit. Los Spaces privados requieren cuenta. |
| FastAPI con frontend (HTML o React) | Medio – alto | Más control y bastante más código. No compensa para este alcance. |
| Ejecutable local (PyInstaller) | Medio | Sin servidor y sin exposición de datos, pero el ejecutable pesa mucho por scikit-learn. |

> **Nota (2026-09-28):** la recomendación de esta tabla no se adoptó. Se eligió FastAPI + React + PostgreSQL (P-07 cerrada, [ADR-001](adr/ADR-001-fastapi-react-postgresql.md)). El flujo de pantalla siguiente sigue siendo válido como flujo funcional, independiente de la tecnología.

Flujo de pantalla propuesto (Streamlit):

1. Subir el o los Excel.
2. Procesar y mostrar el resumen de la cartera (ciclos que vencen, ya renovados, socios a priorizar).
3. Mostrar la tabla de la lista ordenada por prioridad.
4. Descargar el Excel (`top_25`, `cartera_completa`, `resumen`).

## 6. Riesgos que se mantienen

| Riesgo | Mitigación |
|---|---|
| Diferencias de uno o dos casos entre versiones de pandas o scikit-learn | Fijar versiones en `requirements.txt`. |
| Probabilidades desplazadas hacia abajo: casi nadie aparece como "ALTO" | Presentar la lista por orden de prioridad y no destacar el nivel, o recalibrar los niveles. |
| Los servicios gratuitos se suspenden cuando no se usan | La primera carga puede tardar unos 30 segundos; aceptable para un uso mensual. |
| Sin monitoreo del desempeño del modelo | Opcional: mostrar una métrica de control (ver P-09). |

## 7. Conclusión

> **Nota:** esta estimación corresponde al alcance original. Con FastAPI + React + PostgreSQL ([ADR-001](adr/ADR-001-fastapi-react-postgresql.md)) y los casos de uso de `03`, el esfuerzo pasa a **medio – alto**.

La migración es **viable y de esfuerzo bajo a medio**. El trabajo real está en:

1. convertir el notebook en funciones reutilizables;
2. definir el formato del archivo de entrada;
3. resolver el acceso y la privacidad de los datos.

Antes de empezar a programar hay que responder los puntos abiertos de la sección 8.

---

## 8. Puntos por aclarar antes del desarrollo

| ID | Pregunta | Opciones | Recomendación | Estado |
|---|---|---|---|---|
| P-01 | ¿Qué formato tendrá el archivo de entrada? | (a) Varios libros por año, con el año en el nombre del archivo, como hoy. (b) Un solo libro con hojas `ENERO 2025`, `ENERO 2026`… (c) Un solo libro y el usuario indica el año. | (a): no obliga a cambiar la forma en que Mtabolic lleva sus Excel. | **Cerrada** (28-09-2026): dos formatos. El histórico 2025–2026 (libros mensuales de `plantillas/`) se migra **una sola vez** al generar la base (CU-03). Desde entonces, la carga paulatina usa solo la plantilla `Plantilla_Carga_Datos_Mtabolic.xlsx` (CU-01). |
| P-02 | ¿La lista exportada incluye datos de contacto (nombre, celular, correo)? | Sí / solo código anónimo `MTB-XXXXXXXX` | Sí: sin contacto la lista no sirve para operar, pero obliga a resolver P-03. | **Cerrada** (28-09-2026): sí; nombre, celular y correo (CU-04 y CU-12 de `03`). |
| P-03 | ¿Dónde se ejecutará la aplicación? | Nube con acceso restringido / equipo local de Mtabolic / servidor propio | Depende de P-02 y de la autorización de Mtabolic sobre los datos. | **Cerrada** (28-09-2026): en un solo PC de Mtabolic, con Docker Compose. Ver `04` §3. |
| P-04 | ¿Qué fecha se usa para generar la lista? | Último día del último mes cargado (como hoy) / fecha real del día / elegida por el usuario | Elegida por el usuario, con el último día cargado como valor por defecto. | **Abierta.** `03` (CU-04) propone la fecha de corte de los últimos datos; falta confirmar frente al uso del reloj del sistema. Ver `04`. |
| P-05 | ¿`TOP_K` y el horizonte de días son fijos o configurables? | Fijos (25 socios, 30 días) / configurables en pantalla | Configurables, con esos valores por defecto. | **Cerrada** (28-09-2026): configurables; 25 socios y 30 días por defecto (CU-04). |
| P-06 | ¿Se reentrena el modelo en cada carga o se usa uno ya entrenado? | Reentrenar / modelo fijo `.joblib` | Reentrenar (sección 3.2). | **Cerrada** (28-09-2026), con otra solución: la carga no reentrena. El primer modelo se entrena en la migración del histórico (CU-03) y después una tarea semestral reentrena solo si hay datos suficientes (CU-02). |
| P-07 | ¿Qué tecnología se usa? | Streamlit / Gradio / FastAPI + React (plantilla actual del repositorio) | Streamlit. La plantilla en `.claude/` asume FastAPI + React + PostgreSQL, un tamaño desproporcionado para este alcance; hay que decidir si se adapta o se ignora. | **Cerrada** (2026-09-28): FastAPI + React + PostgreSQL, decisión del usuario en R-001. Ver [ADR-001](adr/ADR-001-fastapi-react-postgresql.md). |
| P-08 | ¿Quién usará la aplicación y cuántas personas? | Solo la asesora / varias personas de Mtabolic / el equipo académico | Define si basta una contraseña compartida o hacen falta usuarios. | **Cerrada** (28-09-2026): personal interno de Mtabolic, sin cuentas de usuario; acceso restringido por IP (CU-00). |
| P-09 | ¿La aplicación muestra algún indicador de calidad del modelo? | Ninguno / métrica simple (p. ej. PR-AUC del último período conocido) / advertencias de datos (porcentaje de filas sin fecha de fin, hojas no leídas) | Advertencias de calidad de datos; son baratas y útiles. | **Parcial.** `03` define advertencias de datos en CU-01/CU-03 y el bloque "Estado del modelo" del dashboard (CU-11). Falta decidir la métrica de control del reentrenamiento. Ver `04`. |
| P-10 | ¿Se corrige `mes_vencimiento` antes de pasar a producción? | Mantener igual que el notebook / reemplazar por mes del año (1-12) / eliminar | Mantener igual para no desalinearse del informe académico; registrar como mejora futura. | **Abierta.** Se suma a la de `inicio_aproximado` (ver `04`). |
| P-11 | ¿Qué columnas lleva el Excel exportado y en qué orden? | Las de `lista_operativa()` del notebook / formato acordado con la asesora | Validar con la asesora antes de programar la exportación. | **Cerrada** (28-09-2026): columnas propuestas en CU-12 de `03`; pendiente la validación final con la asesora. |
| P-12 | ¿Se conserva algún historial de listas generadas? | No (todo en memoria) / sí (requiere almacenamiento) | No: simplifica el despliegue y reduce el riesgo sobre los datos. | **Cerrada** (28-09-2026): sí. Las listas se guardan con la versión del modelo (CU-04); el Excel de descarga se genera en memoria (CU-12). |
