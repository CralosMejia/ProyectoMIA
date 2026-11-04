# M05 · Correcciones de la evaluación de la semana 10

| Campo | Valor |
|---|---|
| **Fecha** | 2026-11-02 |
| **Origen** | Evaluación docente de la semana 10 (31-10-2026): 52/80 y seis no conformidades (NC1–NC6) |
| **Alcance** | Notebook oficial, `requirements.txt` (raíz), README de la raíz, reentrenamiento de la app (margen del candidato), periodo de referencia de los factores, `verificar_lista.py`, pruebas unitarias y documentación |
| **Notebook** | [`Notebookes/Prototipo_Final_Mtabolic.ipynb`](../../Notebookes/Prototipo_Final_Mtabolic.ipynb), versión v2 (antes `MVP_simple.ipynb`) |
| **Modelo adoptado** | **Random Forest** (el de la app), como desviación explícita de la regla de selección (§5). **Sustituido por [M06](M06-regresion-logistica-modelo-adoptado.md) (2026-11-03): se adopta la Regresión Logística** |
| **Datos fuente (fuera de git)** | `salidas/prototipo_final/` (tablas CSV, modelos `.joblib`, `parametros_modelo_operativo.json`, `lista_operativa_2026-09.xlsx`, `ejecucion.json`) |
| **Correcciones del informe** | [M05-correcciones-del-informe.pdf](M05-correcciones-del-informe.pdf), página por página y con las cifras de esta versión |

Solo contiene cifras agregadas: ningún nombre, cédula ni código de socio.

## 1. Qué pidió el docente y qué se hizo en el proyecto

| NC | Observación | Qué se hizo |
|---|---|---|
| NC1 · Mayor | La partición con márgenes de 30 días no garantiza que las etiquetas (T+30) se conozcan antes de las primeras predicciones (T−30) del período siguiente | Notebook: partición con márgenes de más de 60 días, tabla de cronología y `assert`; métricas recalculadas (§3 y §4). App: el candidato del reentrenamiento usa la misma regla (§6) |
| NC2 · Mayor | El notebook entregado remuestreaba filas, explicaba por sustitución de variables y usaba SHA-256 sin clave | El notebook oficial ya implementa bootstrap **por socio**, SHAP con `TreeExplainer` (aditividad comprobada) y HMAC-SHA256 con clave secreta; la causa fue que se entregó otro notebook (§2). Se aclaran los términos: seudonimización, clave |
| NC3 · Mayor | Faltaban insumos, dependencias y evidencia reproducible | `requirements.txt` en la raíz, versiones y huellas de los libros impresas, tablas, modelos y lista de referencia exportados, README de reproducción. Tag y reportes de pruebas con base de datos: pendientes del equipo (§8) |
| NC4 · Mayor | Cantidades y métricas de distintas ejecuciones; Tabla 10 mal rotulada; Tabla 12 con valores intercambiados | Una sola ejecución congelada (v2) con 17 controles; la Parte 12 reúne todas las cifras del informe y la Tabla 10 incluye RF − RL. La app se verifica contra esa misma ejecución (0 diferencias) |
| NC5 · Mayor | Registro del piloto sin trazabilidad real/simulado | Se corrige en el informe (no depende del código) |
| NC6 · Menor | Índice, figuras, glosario, nombre del notebook en el README | README reescrito con el nombre correcto; el resto se corrige en el informe |

El informe (documento de la tesis) **no se modificó** en este requerimiento.

## 2. Por qué el notebook entregado no coincidía

El notebook que recibió el docente (`Prototipo_Final_Mtabolic.ipynb` de la entrega, versión para Google Colab con Python 3.11) no era el del proyecto: no tenía SHAP, ni bootstrap por socio, ni HMAC, y su ejecución daba 846 casos de entrenamiento, 1.565 evaluables y PR-AUC 0,796, frente a 845, 1.564 y 0,7934 del informe. Las cifras del informe provenían de `MVP.ipynb` (mejoras M01–M03), que el notebook simplificado `MVP_simple.ipynb` reproducía exactamente.

Por eso se adoptó `MVP_simple.ipynb` como notebook oficial y se renombró `Prototipo_Final_Mtabolic.ipynb`. `MVP.ipynb` se conserva como registro histórico (partición de 30 días; sus cifras ya no son las del informe). Antes de cambiarlo se ejecutó tal como estaba con las versiones de la app (Python 3.12, scikit-learn 1.8.0, shap 0.54.1): todos sus controles dieron OK.

## 3. NC1 · Partición con disponibilidad temporal de las etiquetas

**Regla.** La última etiqueta de un conjunto (su vencimiento más tardío + 30 días) debe conocerse **antes** de la primera predicción del conjunto siguiente (su vencimiento más temprano − 30 días). Exige más de 60 días entre vencimientos. Es el «criterio estricto» que M01 dejó pendiente en sus limitaciones.

**Opción elegida.** Se conserva intacto el conjunto de prueba (mayo–agosto 2026, 277 membresías) y se recortan los bordes de entrenamiento y validación.

| Conjunto | v1 (M01, 30 días) | v2 (M05) | Membresías v1 → v2 | Socios v2 | No renovó v2 |
|---|---|---|---|---|---|
| Entrenamiento | hasta 01-12-2025 | hasta 31-10-2025 | 845 → **721** | 543 | 75,5 % |
| Margen 1 (descartado) | 02-12 a 30-12-2025 | 01-11 a 31-12-2025 | 87 → 211 | 182 | 71,1 % |
| Validación | 01-01 a 29-03-2026 | 01-01 a 01-03-2026 | 247 → **180** | 158 | 63,3 % |
| Margen 2 (descartado) | 02-04 a 30-04-2026 | 02-03 a 30-04-2026 | 108 → 175 | 151 | 60,0 % |
| Prueba | 02-05 a 01-08-2026 | sin cambios | 277 → **277** | 215 | 66,8 % |

| Transición | Cierre de la última etiqueta | Primera predicción siguiente | Holgura | v1 |
|---|---|---|---|---|
| Entrenamiento → Validación | 30-11-2025 | 02-12-2025 | 2 días | se solapaban 29 días |
| Validación → Prueba | 31-03-2026 | 02-04-2026 | 2 días | se solapaban 26 días |

El modelo operativo no cambia: sigue aprendiendo con las 1.564 membresías evaluables (incluidos los márgenes). Las medianas de monto de entrenamiento tampoco cambian.

## 4. Resultados v2

### 4.1 Validación (aplica la regla)

| Modelo | Umbral | PR-AUC | Precisión@25 | ROC-AUC | F1 | Brier | Especificidad |
|---|---|---|---|---|---|---|---|
| Sin modelo | 0,50 | 0,633 | 0,633 | 0,500 | 0,776 | 0,247 | 0,000 |
| Regresión Logística | 0,21 | 0,724 | 0,640 | 0,621 | 0,783 | 0,240 | 0,136 |
| **Random Forest (adoptado)** | 0,32 | 0,707 | 0,760 | 0,624 | 0,780 | 0,243 | 0,076 |

Los dos modelos superan a la referencia en F1, PR-AUC y Brier. La regla (gana el de mayor PR-AUC) elige la Regresión Logística por 0,017. En v1 la Regresión Logística no cumplía el criterio de Brier y la regla elegía el Random Forest.

### 4.2 Prueba (comprobación final, una sola vez)

| Modelo | PR-AUC | Precisión@25 | Lift@25 | ROC-AUC | F1 | Brier | Especificidad | Recall | Accuracy |
|---|---|---|---|---|---|---|---|---|---|
| Sin modelo | 0,668 | 0,668 | 1,00 | 0,500 | 0,801 | 0,229 | 0,000 | 1,000 | 0,668 |
| **Random Forest (adoptado, umbral 0,32)** | **0,787** | **0,760** | 1,14 | 0,700 | 0,802 | 0,236 | 0,054 | 0,984 | 0,675 |
| Regresión Logística (regla, umbral 0,21) | 0,820 | 1,000 | 1,50 | 0,680 | 0,800 | 0,236 | 0,239 | 0,919 | 0,693 |

Uso operativo en prueba (277 membresías, 215 socios):

| | Random Forest (adoptado) | Regresión Logística |
|---|---|---|
| Marcados en riesgo con el umbral | 269 | 240 |
| No renovaron y no fueron marcados (FN) | 3 | 15 |
| Renovaron y fueron marcados (FP) | 87 | 70 |
| Aciertos en el top 25 (azar ≈ 16,7) | 19 | 25 |

Matriz de confusión del Random Forest en prueba (VN, FP, FN, VP): 5, 87, 3, 182. Ninguno de los dos mejora el Brier de la referencia en prueba (0,236 frente a 0,229): las probabilidades sirven para ordenar, no como porcentajes. Respecto del informe anterior, el Random Forest baja un poco porque aprende con menos casos (PR-AUC 0,793 → 0,787; aciertos en el top 25: 20 → 19; marcados: 254 → 269).

### 4.3 Bootstrap por socio (1.000 réplicas, semilla 42; percentiles 2,5–97,5)

| Comparación de PR-AUC | Prueba | % réplicas > 0 | Validación |
|---|---|---|---|
| Random Forest − sin modelo | +0,121 (+0,061 a +0,182) | 100,0 % | +0,079 (+0,011 a +0,152) |
| Regresión Logística − sin modelo | +0,150 (+0,103 a +0,201) | 100,0 % | +0,093 (+0,026 a +0,164) |
| Random Forest − Regresión Logística | −0,029 (−0,069 a +0,010) | 6,7 % | −0,014 (−0,060 a +0,031) |

Con estos datos hay evidencia de que los dos modelos ordenan mejor que no usar modelo; la diferencia de PR-AUC entre ellos incluye el cero en los dos conjuntos. En Precisión@25 de prueba, RF − RL = −0,22 (−0,40 a −0,08): con 25 casos el intervalo es ancho, pero excluye el cero.

### 4.4 Top 25 por mes (Tabla 11)

| Modelo · conjunto | VP | FP | FN | VN | FN inevitables por capacidad |
|---|---|---|---|---|---|
| Random Forest · validación (180) | 39 | 13 | 75 | 53 | 63 |
| Random Forest · prueba (277) | 63 | 16 | 122 | 76 | 109 |
| Regresión Logística · validación (180) | 35 | 17 | 79 | 49 | 63 |
| Regresión Logística · prueba (277) | 63 | 16 | 122 | 76 | 109 |

En prueba los dos coinciden en los totales por coincidencia (Random Forest 19 + 21 + 22 + 1 VP por mes; Regresión Logística 18 + 22 + 22 + 1). En el Random Forest hay empates de probabilidad en el corte del top 25 (orden estable).

### 4.5 Interpretabilidad

- **SHAP del Random Forest:** valor base 0,499 (modelo evaluado) y 0,500 (operativo); error de aditividad 2,3e-15. Aporte medio absoluto en validación: total pagado antes 0,043, membresías anteriores 0,027, plan 0,023, monto actual 0,016. Mismo orden en validación y prueba (correlación de rangos 1,00). Total pagado y membresías previas tienen correlación 0,93.
- **Permutación en validación:** en el Random Forest las importancias son pequeñas (la mayor, duración del plan, 0,010); en la Regresión Logística, duración del plan 0,081, membresías anteriores 0,059 y plan 0,032.
- **Regresión Logística:** los coeficientes de mayor magnitud son categorías de `mes_vencimiento` de 2025 (mayo de 2025: +1,85) y el plan (MENSUAL −0,79; SEMESTRAL +0,63). Como `mes_vencimiento` está codificada como año-mes, los meses de 2026 no existen en entrenamiento y no aportan en validación ni en prueba (permutación 0,000).

### 4.6 Lista de septiembre (producto)

Sin cambios: 57 socios (ALTO 2, MEDIO 39, BAJO 16), mismas probabilidades, niveles y motivos SHAP en el notebook, en `MVP.ipynb` y en la app. Con la Regresión Logística operativa, 23 de los 25 primeros socios serían los mismos.

## 5. Decisión sobre el modelo (2026-11-02)

> **Sustituida por [M06](M06-regresion-logistica-modelo-adoptado.md) y [ADR-016](../adr/ADR-016-regresion-logistica-como-modelo-adoptado.md) (2026-11-03):** se adopta la Regresión Logística, la que elige la regla. Lo que sigue se conserva como registro histórico.

Con la partición corregida, la regla fijada de antemano elige la Regresión Logística. **Decisión del equipo: adoptar el Random Forest como desviación explícita de la regla**, por estas razones:

1. La diferencia de PR-AUC (0,017 en validación) no es distinguible con el bootstrap por socio: el intervalo de RF − RL incluye el cero en validación y en prueba.
2. El Random Forest es el modelo integrado y verificado en la aplicación: lista, niveles, motivos SHAP, pruebas automáticas y paridad exacta con el notebook. Cambiarlo al cierre implica riesgo técnico sin una ganancia demostrada en el orden.
3. Supera con claridad a no usar modelo y, en validación, acierta más en el top 25 (19 frente a 16), que es la capacidad real de contacto.

Se informa igual que en la comprobación final la Regresión Logística acertó 25 de 25 en el top 25 frente a 19 del Random Forest (diferencia cuyo intervalo excluye el cero). Como la comprobación final no se usa para elegir, no cambia la decisión, pero deja a la Regresión Logística como alternativa a evaluar en la siguiente versión. El notebook separa `modelo_seleccionado` (la regla) de `modelo_adoptado` y lo muestra en la Parte 7; el informe no debe decir que la regla eligió el Random Forest.

## 6. Alineación de la app con el notebook oficial

| Pieza | Antes | Ahora |
|---|---|---|
| Margen del candidato en el reentrenamiento (`ciclos_para_candidato`, `DIAS_MARGEN_CANDIDATO`) | `vencimiento + 30 < primer vencimiento de la comparación` | `vencimiento + 60 < primer vencimiento de la comparación` (30 de observación + 30 de anticipación): la misma regla de la partición del notebook |
| Periodo de referencia de los factores (`PERIODO_REFERENCIA_FACTORES`, informativo) | vencimientos hasta el 2025-12-01 (`X_train` de M01) | vencimientos hasta el 2025-10-31 (`X_train` de M05) |
| Referencia de `scripts/verificar_lista.py` | `salidas/m01/despues/` y `salidas/mvp/` de `MVP.ipynb` | `salidas/prototipo_final/` del notebook oficial (Parte 13; mismo formato) |
| Modelo, umbrales, lista y motivos | Random Forest, 0,70 / 0,50, SHAP | Sin cambios |

Archivos de código: `Backend/app/domain/modelo/reentrenamiento.py`, `Backend/app/domain/modelo/variables.py`, `Backend/app/application/modelo/reentrenar_modelo.py` (docstring), `Backend/scripts/verificar_lista.py`. Pruebas: `tests/unit/domain/modelo/test_reentrenamiento.py` (margen de 60 días, con casos a 61, 60 y 31 días), `tests/unit/application/modelo/test_reentrenar_modelo.py` (escenario con un mes de comparación cuando los datos sintéticos no alcanzan para tres más el margen), `tests/unit/domain/modelo/test_variables.py`, `tests/unit/application/modelo/test_entrenar_modelo.py`, `tests/unit/scripts/test_verificar_lista.py`.

Consecuencia operativa: con 3 meses de comparación y el margen de 60 días, el candidato necesita ciclos que venzan al menos cinco meses antes del corte de los datos; con el histórico real (desde febrero de 2025) se cumple.

## 7. Cómo se verificó

| Verificación | Resultado |
|---|---|
| Notebook v1 sin cambios, con las versiones de la app | Todos los controles OK (reproduce el informe anterior) |
| Notebook v2, ejecución completa (Python 3.12.16, pandas 3.0.6, numpy 2.5.3, scikit-learn 1.8.0, shap 0.54.1) | 17/17 controles OK, sin errores, ~1 minuto |
| Prueba anti-fuga con corte T−30 | 0 membresías cambian |
| Control de cronología NC1 | Cumple en las dos transiciones |
| `verificar_lista.py` (app con los cambios de §6) frente a `salidas/prototipo_final/` | Código 0: 0 diferencias de conteos, variables, medianas, probabilidades, niveles, motivos y orden en 57 filas; referencia de los factores igual |
| Pruebas unitarias del Backend (`pytest -m unit`) | 1.435 aprobadas |
| `ruff check`, `ruff format --check`, `lint-imports`, `mypy app` | Sin errores (7 contratos de capas respetados) |
| `requirements.txt` instalado en un entorno limpio | Correcto |
| Salidas del notebook revisadas | Sin nombres, cédulas ni identificadores en claro; solo códigos seudónimos |
| Notebook con los libros sintéticos (`Backend/tests/fixtures/historico`) | Se ejecuta completo; los controles fallan, como se espera, porque comparan con las cifras reales |
| Huellas SHA-256 (16 caracteres) de los libros | 2025 `7ad9e21de2dd5f15`, 2026 `516600703c316ca1` (las de los modelos, en `ejecucion.json`) |

## 8. Pendientes y limitaciones

| Pendiente | Responsable / siguiente paso |
|---|---|
| Pruebas de integración del Backend (PostgreSQL), Frontend y E2E con los cambios de §6 | Equipo, con Docker; comandos en el README §8. Ninguna prueba de integración cita el margen ni el periodo de referencia, pero no se ejecutaron aquí |
| Evaluar la Regresión Logística como modelo de la siguiente versión | Con más datos; recodificar antes `mes_vencimiento` |
| Recodificar `mes_vencimiento` como mes del año (1–12) o retirarla | Trabajo futuro; hoy aporta solo en 2025 |
| Commit, tag de la versión entregada y acceso del evaluador | Equipo (`git add -A` registra el renombre `MVP_simple.ipynb` → `Prototipo_Final_Mtabolic.ipynb`) |
| Correcciones del informe | Equipo, con [M05-correcciones-del-informe.pdf](M05-correcciones-del-informe.pdf) |

## 9. Requerimiento

Cambios hechos fuera del harness `req` (no estaba disponible en la sesión), siguiendo su flujo: prueba primero (roja), cambio mínimo, suite unitaria y controles de calidad. Archivos: `Notebookes/Prototipo_Final_Mtabolic.ipynb` (renombrado desde `MVP_simple.ipynb` y corregido), `requirements.txt` (raíz), `README.md`, los archivos de código y pruebas de §6, `Backend/README.md`, `Documentation/docs/backend/12-modelo-y-listas.md`, `Documentation/adr/ADR-011-reglas-del-reentrenamiento.md`, `Documentation/03-casos-de-uso.md`, `Documentation/README.md`, `Documentation/07-cierre.md`, `Documentation/mejoras/README.md`, este documento y `M05-correcciones-del-informe.pdf`. Commits: pendientes del usuario.
