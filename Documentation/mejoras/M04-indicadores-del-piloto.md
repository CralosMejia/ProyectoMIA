# M04 · Indicadores del piloto en el Dashboard

| | |
|---|---|
| **Requerimiento** | R-018 (harness), cerrado el 2026-10-16 |
| **App** | Backend: `Backend/app/domain/modelo/piloto.py` (verificación T+30 y los cinco indicadores), `Backend/app/application/dashboard/{consultar_dashboard,dtos,ports}.py`, `Backend/app/infrastructure/persistence/repositories/dashboard.py`, `Backend/app/api/routers/dashboard.py`. Frontend: `Frontend/src/features/dashboard/components/IndicadoresPiloto.tsx` (sección nueva), `AyudaDashboard.tsx` (apartado nuevo), `api/dashboard-api.ts`, `hooks/presentacion.ts`, `pages/DashboardPage.tsx` |
| **Contrato** | `GET /api/v1/dashboard`: bloque `piloto` **aditivo** ([API_CONTRACT §Alertas y dashboard](../docs/API_CONTRACT.md#alertas-y-dashboard-cu-09-cu-11-r-011)) |
| **Alcance** | Solo lectura. Sin migración, sin endpoint nuevo, sin tablas ni columnas nuevas. El modelo, la lista y la gestión no cambian. |
| **No implementado** | Grupo de control aleatorio y reporte comparativo A/B con intervalos de confianza (decisión del usuario, opción b): ver §9 |

Este documento reúne lo necesario para actualizar la tesis. Solo contiene cifras agregadas: ningún nombre, cédula, código de socio ni fecha de un socio concreto.

---

## 1. Objetivo y recomendación del tutor

El tutor recomendó **medir el piloto**: comprobar con datos reales si la lista acierta y si la gestión que se hace con ella llega a tiempo y retiene socios. Propuso además comparar el uso del sistema con el proceso habitual mediante un **grupo de control** aleatorio y un reporte con intervalos de confianza.

**Qué se implementó.** Una sección fija **"Indicadores del piloto"** en el Dashboard con cinco indicadores descriptivos por mes, calculados sobre los 25 primeros socios de la lista del mes: precisión del top 25, contactados antes del vencimiento, días de anticipación, renovación de los contactados y monto retenido. Cada uno con su número de casos (`n`) y su estado (completo, parcial, pendiente o sin datos). La sección se imprime con el PDF del dashboard y tiene su apartado en la ayuda.

**Qué no se implementó y por qué.** El grupo de control y el reporte A/B con IC. El planner devolvió el requerimiento bloqueado porque "pruebas A/B o inferencia causal" está fuera del proyecto ([DEVELOPMENT_GUIDELINES §Fuera del proyecto](../DEVELOPMENT_GUIDELINES.md)) y dejaba decisiones abiertas de diseño del experimento. El usuario eligió la **opción b**: reducir el alcance a los indicadores descriptivos y dejar el grupo de control como trabajo futuro, con su diseño documentado (§9). Así, las cifras de M04 son **observadas, no causales**.

## 2. Población: el top 25 de la lista del mes

- **Mes:** el elegido en el filtro del dashboard (por defecto, el mes actual en fecha de negocio de Ecuador).
- **Lista del mes:** la **última** lista con `listas_priorizadas.fecha_generacion` dentro del mes (orden `fecha_generacion DESC, creada_en DESC, id DESC`). Si en el mes no hay lista, todo el bloque queda en **Sin datos**.
- **Top 25:** las predicciones de esa lista con `predicciones.prioridad ≤ 25` (todas si hay menos), fijo en 25 aunque la lista se haya generado con otro `top_k`. `n_top` = cuántas filas hay.
- **T (vencimiento):** `membresias.fecha_vencimiento` de la membresía de cada predicción.
- **Sin dato:** casos cuya membresía falta, está borrada o no tiene vencimiento, y los que el dominio excluye por otra causa (duración imposible, plan `DIARIO`, fecha fuera de rango). Se cuentan aparte en `sin_dato` y **no entran en ningún `n`**. En pantalla: "N socios del top 25 sin datos de membresía: no cuentan en los casos."

## 3. Verificación a los 30 días (T+30) y corte de los datos

**Corte de verificación.** `corte = corte_de_datos(hoy, corte del modelo vigente, día de la última carga por plantilla) = min(hoy, max(corte vigente, última carga))`: el último día del que hay datos cargados. Es el mismo criterio que CU-02 usa para etiquetar ([backend/12 §Reentrenamiento](../docs/backend/12-modelo-y-listas.md)). Sin modelo vigente el corte es nulo y todo queda pendiente.

**Por qué no se usa "hoy".** Si el mes siguiente aún no se ha cargado, ninguna renovación de ese periodo existe en la base; verificar a "hoy" contaría como **"no renovó"** a socios que sí renovaron y subiría la precisión de forma artificial. Con el corte, esos casos quedan **pendientes** y no cuentan como no renovación.

**Estado de cada caso** (`verificar_renovacion` en el dominio, reutilizando `clasificar` y las constantes de la etiqueta del modelo):

| Estado | Condición |
|---|---|
| Pendiente | `T + 30 > corte` (incluye vencimiento posterior al corte) o corte nulo |
| Renovó | `T + 30 ≤ corte` y existe otra membresía **no `DIARIO`** del mismo socio con `fecha_actividad` en `[T, T+30]` |
| No renovó | `T + 30 ≤ corte` y no existe esa membresía |
| Sin dato | ver §2 |

La regla de "renovó" es **la misma etiqueta del modelo** (`etiquetar` / `etiquetar_ciclos`, ventana `[T − 0, T + 30]`); una prueba de coherencia comprueba que coincide caso a caso con `etiquetar_ciclos`. La **membresía de renovación** es la primera de la ventana por `(fecha_actividad, id)`.

## 4. Definición y fórmula de cada indicador

Proporciones como `Decimal` con 8 decimales (`ROUND_HALF_EVEN`), sin mínimo de casos y siempre con su `n`. En pantalla se muestran como porcentaje con un decimal ("41,2 %") junto a "X de N".

| # | Indicador (nombre en pantalla) | Fórmula | Origen de los datos | `n` |
|---|---|---|---|---|
| 1 | **Precisión del top 25** | no renovaron / verificados | §3 sobre `membresias` (`fecha_vencimiento`, `fecha_actividad`, `plan`, socio) | verificados + pendientes |
| 2 | **Contactados antes del vencimiento** | contactados con `fecha_contacto < T` / casos con dato | `gestiones.contactado` y `gestiones.fecha_contacto` de la gestión **no borrada** del mismo `membresia_id` (una por ciclo, RN-08.1), venga de la lista que venga | casos con dato |
| 3 | **Días de anticipación** | promedio de `T − fecha_contacto` (días) de los contactados con fecha | igual que 2 | contactados con `fecha_contacto` |
| 4 | **Renovación de los contactados** | renovaron / contactados verificados | 2 + §3 | todos los contactados (verificados + pendientes) |
| 5 | **Monto retenido** | Σ monto de la membresía de renovación de los contactados verificados que renovaron | `membresias.monto_cobrado`; si es nulo, `monto_facturado` (`NUMERIC(19,4)`) | solo contactados **ya verificados** |

Precisiones:

- Contactar **el mismo día** del vencimiento no cuenta como "antes" (`fecha_contacto < T` estricto). En días de anticipación, el promedio puede ser 0 o negativo si se contactó el día o después; se redondea a 1 decimal.
- El monto se suma en `Decimal` y se cuantiza a 2 decimales; viaja como texto y la pantalla lo formatea en dólares (`$1.234,56`) sin coma flotante. Las renovaciones sin ningún monto se cuentan aparte (`renovaciones_sin_monto`, "N sin monto registrado") y no se suman como cero en silencio.
- El **`n` del monto** es distinto del de la renovación: la renovación cuenta a todos los contactados (con sus pendientes), el monto solo a los contactados que ya cumplieron los 30 días. La pantalla lo aclara con "n = X contactados ya verificados" y la ayuda lo explica.

## 5. Estados

| Estado (API) | Texto en pantalla | Cuándo |
|---|---|---|
| `COMPLETO` | "Completo" | todos los casos verificados |
| `PARCIAL` | "Parcial: faltan N por verificar (X de N verificados)" | algunos pendientes |
| `PENDIENTE` | "Pendiente: aún no se puede verificar (se verifica 30 días después del vencimiento)" | ningún caso verificado |
| `SIN_DATOS` | "Sin datos" | `n = 0` (o mes sin lista) |

Los indicadores 2 y 3 no dependen de T+30: solo pueden estar en Completo o Sin datos. El indicador 5 toma el estado del 4. El estado general del bloque es el de la precisión (o Sin datos si el mes no tiene lista). Con `0 < n < 10` la tarjeta añade **"Pocos casos: léase con cuidado"**.

## 6. Sesgo, muestras pequeñas y causalidad

- **Sesgo de la precisión por la gestión.** El top 25 es justamente a quien se llama. Si la llamada funciona, algunos socios que iban a irse renuevan, y la precisión **observada** queda **por debajo de la real** (el modelo acertó, pero la gestión cambió el desenlace). Aviso fijo en pantalla e impresión: "Los socios del top 25 se contactan; por eso la precisión observada puede quedar por debajo de la real."
- **Muestras pequeñas.** Como mucho 25 casos por mes, y bastantes menos en renovación y monto (solo contactados). Una diferencia de 1–2 socios mueve el porcentaje varios puntos. Por eso cada cifra lleva su `n`, el aviso de pocos casos y no se calculan intervalos ni comparaciones entre meses.
- **No causales.** Las cifras describen lo que pasó. "El 60 % de los contactados renovó" **no** implica que la llamada causara esas renovaciones: no hay grupo de comparación (§9). Aviso fijo: "Cifras observadas, no causales."

## 7. Resultados reales: septiembre de 2026 (ejemplo)

Puesta en uso en el stack principal el 2026-10-16 (respaldo previo verificado; reconstrucción sin migración; modelo v2 `LISTO`; conteos de tablas idénticos antes y después; no se generaron listas, gestiones ni datos).

| Indicador | Septiembre 2026 |
|---|---|
| Estado del bloque | **Pendiente** |
| Top 25 | 25 casos; corte de verificación 2026-09-30 |
| Precisión del top 25 | Pendiente (ningún caso cumple aún T+30 con datos cargados) |
| Contactados antes del vencimiento | **2 de 25 (8,0 %)** |
| Días de anticipación | **9,5 días** (n = 2; "Pocos casos") |
| Renovación de los contactados | Pendiente |
| Monto retenido | Pendiente |

Octubre de 2026: **Sin datos** (no hay lista generada en el mes).

Lectura: la lista de septiembre ya permite ver la oportunidad del contacto (solo 2 de los 25 socios prioritarios se llamaron antes de vencer, con 9,5 días de margen), pero la precisión, la renovación y el monto se podrán leer cuando se cargue el mes siguiente y los vencimientos cumplan 30 días dentro del corte.

Comprobación manual en el stack de pruebas (datos sembrados, calculado a mano y coincidente con la pantalla): precisión 3/7, contactados antes 5/8, 7,5 días, renovación 3/5, monto $75,50 con 1 renovación sin monto.

## 8. Cómo leer la sección y cómo imprimirla

1. Elegir el mes en el filtro del Dashboard. La sección indica "Lista del mes: <nombre>, generada el <fecha>" y "Verificado con datos hasta el <fecha de corte>".
2. Cada tarjeta muestra el valor, "X de N" cuando es una proporción, el `n` y el estado. Leer primero el estado: una cifra **Parcial** puede cambiar al cargar más datos; una **Pendiente** aún no existe.
3. Si aparece "Pocos casos: léase con cuidado", no sacar conclusiones de esa cifra sola.
4. Leer la precisión con el aviso de sesgo en mente, y ninguna cifra como efecto del sistema.
5. **Imprimir:** botón "Imprimir / Guardar PDF" del Dashboard. La sección sale completa (no se corta entre páginas) junto con el resto del dashboard; no salen menú, botones ni filtro. Es la impresión normal del navegador.
6. **Ayuda:** "¿Cómo funciona el dashboard?" → apartado "Indicadores del piloto", en lenguaje sencillo.

## 9. Trabajo futuro: diseño del grupo de control

Para pasar de cifras observadas a una **estimación causal** del efecto del sistema haría falta un experimento controlado. Diseño propuesto:

1. **Unidad y asignación.** Aleatorización **por socio** (no por membresía), 50/50 entre "sistema" y "proceso habitual", **estratificada por nivel de riesgo** (alto/medio/bajo) con bloques dentro de cada estrato para que los dos grupos tengan la misma mezcla de riesgo. Un socio queda en su grupo durante todo el piloto (evita que pase de un grupo a otro entre meses). Semilla registrada y asignación guardada en una tabla propia (requiere migración), para que sea auditable y reproducible.
2. **Tratamiento.** Grupo "sistema": el personal ve probabilidad, nivel y motivos y gestiona con la lista. Grupo "proceso habitual": el socio aparece marcado como tal, **sin probabilidad ni motivos**, y se gestiona como antes de la app. No se le niega el contacto: solo se le retira la información del modelo.
3. **Medida.** Tasa de renovación verificada en T+30 con la misma etiqueta y el mismo corte de datos de §3, por grupo.
4. **Análisis.** Diferencia de proporciones `p_sistema − p_habitual` con **IC 95 % de Newcombe** (método híbrido de puntuación), construido con los intervalos de **Wilson** de cada grupo:
   - Wilson para `p` con `n` casos y `z = 1,96`: `(p + z²/2n ± z·√(p(1−p)/n + z²/4n²)) / (1 + z²/n)` → `[l, u]`.
   - Newcombe para `d = p₁ − p₂`: `L = d − √((p₁ − l₁)² + (u₂ − p₂)²)`, `U = d + √((u₁ − p₁)² + (p₂ − l₂)²)`.
   - Se elige porque se comporta bien con muestras pequeñas y proporciones cercanas a 0 o 1, a diferencia del intervalo de Wald. Reporte con `n` por grupo y por estrato.
5. **Tamaño de muestra.** Por grupo, `n = [z_{α/2}·√(2p̄q̄) + z_β·√(p₁q₁ + p₂q₂)]² / (p₁ − p₂)²` (α = 0,05, potencia 80 %). Ejemplos ilustrativos (las tasas base son supuestos, no medidas): detectar 35 % → 50 % exige unos **170 socios por grupo** (340 en total); 40 % → 50 %, unos **390 por grupo**. Con 25 socios al mes (12–13 por grupo) serían de **14 a 31 meses** de piloto: hay que ampliar el top, alargar el piloto o aceptar detectar solo efectos grandes.
6. **Riesgo de contaminación.** El mismo personal atiende a ambos grupos: puede tratar distinto al grupo habitual por saber que está en la lista, o llamar a todos por igual (diluye el efecto). Mitigaciones: no mostrar el riesgo del grupo habitual, registrar todo contacto en ambos grupos, analizar por intención de tratar (según la asignación, no según lo que se hizo) y vigilar la proporción contactada en cada grupo.
7. **Alcance.** Hoy está fuera del proyecto ([DEVELOPMENT_GUIDELINES §Fuera del proyecto](../DEVELOPMENT_GUIDELINES.md)); implementarlo exigiría un requerimiento nuevo, un ADR y una migración.

## 10. Limitaciones

- Muestra de como mucho 25 casos por mes; renovación y monto, menos aún.
- `fecha_contacto` y `contactado` se registran a mano en la gestión: un contacto no anotado cuenta como no contactado.
- La renovación depende de los datos **cargados**: hasta que se carga el mes siguiente, los casos quedan pendientes; una carga incompleta puede ocultar renovaciones.
- Se usa la última lista del mes; si se generaron varias, las anteriores no se miden.
- Sesgo de la precisión por la gestión y cifras no causales (§6).
- **Rendimiento (S1, low, diferido):** cada consulta del dashboard carga todas las membresías (`ciclos()`) y la verificación recorre los ciclos por cada uno de los 25 casos (25 × N). Con el volumen actual no es un problema; si crece, filtrar por los socios del top.
- **Supuesto de una gestión por membresía (S2, low, diferido):** el cruce con `gestiones` depende de RN-08.1 (una gestión no borrada por ciclo). Si esa regla se rompiera, el cruce duplicaría filas del top.

## 11. Cómo se verificó

- Backend: 2098 pruebas pytest (dominio con casos frontera de T+30, coherencia con `etiquetar_ciclos`, fórmulas exactas con `Decimal`; aplicación con reloj fijo; repositorio con PostgreSQL real; API y contrato aditivo, sin datos personales en la respuesta).
- Frontend: 917 pruebas Vitest (estados Completo/Parcial/Pendiente/Sin datos, pocos casos, avisos, impresión, ayuda).
- E2E: 11 pruebas Playwright contra el stack aislado (8081), más la comprobación manual de §7.
- Seguridad: limpia (solo lectura, SQL parametrizado, sin datos personales, sin dependencias nuevas); dos hallazgos low diferidos (§10).

## 12. Qué añadir/cambiar en el documento de la tesis

1. **Capítulo de evaluación / resultados:** añadir un apartado "Indicadores del piloto" con la tabla de §4 (definición, fórmula, `n`) y la verificación T+30 con corte de datos de §3.
2. **Resultados:** incluir la tabla de septiembre de 2026 (§7) como primer registro del piloto, dejando explícito que precisión, renovación y monto están pendientes; actualizarla cuando se carguen los meses siguientes.
3. **Discusión:** añadir el sesgo de la precisión por la gestión, el tamaño de muestra y la naturaleza descriptiva de las cifras (§6). Sustituir cualquier frase que hable de "efecto" o "impacto" del sistema por "resultado observado".
4. **Limitaciones:** añadir las de §10.
5. **Trabajo futuro:** describir el diseño del grupo de control (§9) con el cálculo de tamaño de muestra y el IC de Newcombe, y explicar por qué no se implementó en esta versión (fuera de alcance, decisión de reducir a indicadores descriptivos).
6. **Descripción de la aplicación (CU-11):** añadir la sección "Indicadores del piloto" al contenido del dashboard y a lo que se imprime.
