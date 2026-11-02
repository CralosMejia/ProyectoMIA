# Mtabolic · Estimación temprana del riesgo de no renovación de membresías

**Proyecto:** Sistema inteligente para la estimación temprana del riesgo de no renovación de membresías mediante aprendizaje automático.
**Caso de estudio:** Mtabolic, Puembo (Quito, Ecuador).
**Notebook oficial:** [`Notebookes/Prototipo_Final_Mtabolic.ipynb`](Notebookes/Prototipo_Final_Mtabolic.ipynb) (versión v2, 2026-11-02).

**¿Solo quiere probar la aplicación?** Siga la [Guía rápida](GUIA-RAPIDA.md): un comando, solo Docker Desktop y datos inventados, sin ningún archivo confidencial.

Este README explica cómo **reproducir** el proyecto completo: el análisis y las métricas (notebook), la aplicación web (Backend + Frontend + PostgreSQL en Docker), la comprobación de que ambos dan la misma lista y las pruebas automáticas. Las secciones §5 a §7 son para reproducir el análisis y **requieren los libros reales**, que no están en el repositorio.

---

## 1. Problema y solución

Mtabolic guarda sus membresías en libros de Excel. Revisarlos a mano no permite identificar a tiempo a los socios que podrían no renovar, y el seguimiento comercial suele empezar cuando la membresía ya está por vencer o venció.

El proyecto estima el riesgo **30 días antes del vencimiento (T−30)** y define la no renovación como la ausencia de una nueva membresía del socio en los **30 días posteriores al vencimiento (T+30)**. Los casos cuyo resultado todavía no se puede conocer quedan **pendientes**; nunca se cuentan como bajas. El resultado es una **lista priorizada** de socios a contactar, con nivel de riesgo y motivos.

**Uso previsto:** apoyar la priorización del contacto. La estimación no es una certeza ni demuestra que una campaña cause la renovación.

## 2. Contenido del repositorio

| Ruta | Qué contiene |
|---|---|
| `Notebookes/Prototipo_Final_Mtabolic.ipynb` | **Notebook oficial**: datos, variables, partición temporal, modelos, bootstrap por socio, SHAP, lista de septiembre, controles y cifras del informe |
| `requirements.txt` | Dependencias del notebook con versiones exactas (en la raíz) |
| `Notebookes/MVP.ipynb` | Notebook completo **histórico** (mejoras M01–M03, partición con márgenes de 30 días). Se conserva como registro; sus cifras ya no son las del informe |
| `Backend/` | API FastAPI en capas, modelo y listas ([Backend/README.md](Backend/README.md)) |
| `Frontend/` | SPA React + TypeScript ([Frontend/README.md](Frontend/README.md)) |
| `compose.yaml` | Stack Docker: `db` (PostgreSQL 16), `migrate`, `backend`, `frontend` (nginx) |
| `Documentation/` | Fuente de verdad del proyecto: casos de uso, ADR, mejoras ([Documentation/README.md](Documentation/README.md)) |
| `Documentation/mejoras/M05-correcciones-evaluacion-semana-10.md` | Correcciones de la evaluación de la semana 10 y cifras v2 |
| `scripts/` | Levantar el demo, respaldo, restauración, reinicio de la base y ensayo de la demostración |
| `datos-demo/` | Libros **inventados** con que se levanta el demo y su fecha de vigencia ([datos-demo/README.md](datos-demo/README.md)) |
| `plantillas/` | **Fuera de git.** Libros `Control Gym 2025*.xlsx` y `Control Gym 2026*.xlsx` (datos personales) y la plantilla de carga mensual |
| `salidas/` | **Fuera de git.** Resultados del notebook, modelos y clave de los códigos seudónimos |

## 3. Requisitos

| Para | Necesita |
|---|---|
| Notebook | Python **3.12** y las librerías de `requirements.txt` (raíz) |
| Aplicación | Docker con Compose v2 |
| Desarrollo y pruebas del Backend | Python 3.12, `pip install -e ".[dev]"` en `Backend/` y un PostgreSQL 16 (el de `compose.yaml`) |
| Desarrollo y pruebas del Frontend | Node 22 LTS |

Las versiones de datos y ML son las mismas en el notebook y en la app: pandas 3.0.6, numpy 2.5.3, **scikit-learn 1.8.0**, **shap 0.54.1**, openpyxl 3.1.5, joblib 1.6.0. Con otra versión de scikit-learn el Random Forest cambia y las cifras dejan de coincidir.

## 4. Datos

- Los libros reales tienen datos personales: **no están en el repositorio** y se entregan por un canal autorizado. Se colocan en `plantillas/` (o en la carpeta indicada por la variable `MTABOLIC_DATOS`) con nombres que contengan `Control Gym 2025` y `Control Gym 2026`. Se usa **un** libro de cada año.
- El notebook imprime la **huella SHA-256** de los libros que leyó. Con los libros de la entrega las huellas son `7ad9e21de2dd5f15` (2025) y `516600703c316ca1` (2026): si no coinciden, las cifras tampoco coincidirán.
- **Datos sintéticos** para probar sin datos reales: `datos-demo/` (libros inventados para levantar la app con la [Guía rápida](GUIA-RAPIDA.md)) y `Backend/tests/fixtures/historico/` (dos libros ficticios mínimos para las pruebas). Ver §9.
- **Clave de los códigos seudónimos:** los socios se muestran como `MTB-XXXXXXXX`, un HMAC-SHA256 de su identidad con una clave secreta (variable `MTABOLIC_SAL_CODIGOS` o archivo `salidas/.sal_codigos`, fuera de git). Si no existe, el notebook crea una nueva; con otra clave cambian los códigos, pero no las métricas. Es seudonimización, no anonimato.

## 5. Reproducir el análisis (notebook)

### 5.1 Entorno

Desde la raíz del proyecto:

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1     ·   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 5.2 Ejecución

- **Jupyter o VS Code:** abrir `Notebookes/Prototipo_Final_Mtabolic.ipynb` con el entorno anterior, **desde la carpeta `Notebookes/`** (las rutas a `plantillas/` y `salidas/` son relativas), y ejecutar *Run All*. Tarda alrededor de un minuto.
- **Terminal (sin abrir Jupyter):**

  ```bash
  cd Notebookes
  jupyter nbconvert --to notebook --execute --inplace Prototipo_Final_Mtabolic.ipynb
  ```

### 5.3 Qué se debe obtener

La **Parte 11 · Controles** termina con `TODOS LOS CONTROLES OK`. Valores de la versión congelada v2:

| Control | Valor esperado |
|---|---|
| Registros con identidad / socios distintos | 2.748 / 1.410 |
| Membresías evaluables / no renovaron | 1.564 / 1.098 (70,2 %) |
| Entrenamiento / validación / prueba | 721 / 180 / 277 |
| Cronología: cada etiqueta se conoce antes de la siguiente predicción | Sí (2 días de holgura en ambas transiciones) |
| Prueba anti-fuga (variables que cambian al borrar el futuro) | 0 |
| Modelo adoptado / umbral | **Random Forest** / 0,32 |
| Modelo que elige la regla (desviación informada, §10) | Regresión Logística (umbral 0,21) |
| PR-AUC en prueba: Random Forest / Regresión Logística / sin modelo | 0,787 / 0,820 / 0,668 |
| Precisión@25 en prueba: Random Forest / Regresión Logística | 0,76 (19 de 25) / 1,00 (25 de 25) |
| Matriz de confusión del Random Forest en prueba (VN, FP, FN, VP) | 5, 87, 3, 182 |
| Lista de septiembre | 57 socios: ALTO 2, MEDIO 39, BAJO 16, igual a la app |

Si un control falla, **no** se cambian los valores esperados para que coincidan: se revisan los datos (huellas), las versiones de las librerías y el código, y se documenta el motivo.

### 5.4 Salidas

La **Parte 13** guarda en `salidas/prototipo_final/` (solo cifras agregadas y modelos, sin datos personales):

| Archivo | Contenido |
|---|---|
| `particiones.csv`, `cronologia.csv` | Tamaño de cada conjunto y control de cronología |
| `comparacion_validacion.csv`, `comparacion_prueba.csv` | Métricas de la referencia, la Regresión Logística y el Random Forest |
| `bootstrap_validacion.csv`, `bootstrap_prueba.csv` | Diferencias con intervalo bootstrap por socio (1.000 réplicas, semilla 42) |
| `importancias_validacion.csv`, `coeficientes_regresion_logistica.csv`, `shap_medio.csv` | Permutación, coeficientes y SHAP |
| `tabla_11_top25_por_mes.csv`, `uso_operativo_prueba.csv`, `matriz_confusion_prueba.csv` | Aciertos y errores con el top 25 por mes y con el umbral |
| `medianas_por_plan.csv` | Medianas de monto (entrenamiento y modelo operativo) |
| `modelo_evaluado.joblib`, `modelo_regla_evaluado.joblib`, `modelo_operativo.joblib` | Random Forest adoptado y Regresión Logística (entrenados hasta el 31-10-2025) y Random Forest operativo (el de la app) |
| `parametros_modelo_operativo.json`, `lista_operativa_2026-09.xlsx` | Referencia con que `verificar_lista.py` compara la app (§7); la lista lleva códigos seudónimos |
| `controles.csv`, `ejecucion.json` | Resultado de los controles, versiones, huellas de los libros y de los modelos y cifras para el informe |

## 6. Levantar la aplicación

```bash
cp .env.example .env        # sustituir los valores marcador; contraseña URL-safe (p. ej. hex)
                            # HISTORICO_DIR = carpeta con los libros Control Gym (p. ej. ./plantillas)
docker compose up -d --build
docker compose ps           # db, backend y frontend en estado healthy
```

| URL | Qué |
|---|---|
| http://localhost:8080 | Aplicación (frontend) |
| http://localhost:8080/api/v1/... | API del backend a través de nginx |
| http://localhost:8000/api/v1/health | Salud del backend (único endpoint abierto en el puerto 8000) |

Con la base vacía, el backend migra el histórico y entrena el modelo al arrancar; Inicio pasa a «Sistema listo» en unos segundos. El backend solo atiende a las IP autorizadas (CU-00): desde otro equipo o contenedor responde `403`, por diseño. Para parar: `docker compose down` (con `-v` se borra también la base). Operación en el PC del gimnasio, respaldo y restauración: [Backend/README.md §Operación](Backend/README.md).

## 7. Comprobar que la app y el notebook dan la misma lista

`Backend/scripts/verificar_lista.py` recompone en memoria (sin base de datos ni Docker) la lógica de la app y compara la lista de septiembre con la del notebook oficial, que lee de `salidas/prototipo_final/` (por eso hay que ejecutar antes el notebook): conteos, variables, medianas, probabilidades a 8 decimales, niveles, motivos SHAP y orden.

```bash
cd Backend
pip install -e .              # o usar el entorno del Backend
python scripts/verificar_lista.py ../plantillas
```

Resultado esperado: `diferencias: ... | total 0` y código de salida `0`. Resultado registrado el 2026-11-02: 57 filas, 0 diferencias de conteos, variables, medianas, probabilidad, nivel, motivo u orden, y referencia de los factores igual.

## 8. Pruebas automáticas

| Parte | Comando | Requiere |
|---|---|---|
| Backend, unitarias | `cd Backend && pytest -m unit` | Python 3.12 |
| Backend, completas | `cd Backend && pytest` | `TEST_DATABASE_URL` hacia una base cuyo nombre termine en `_test` (`docker compose up -d db`) |
| Backend, calidad | `ruff check . && ruff format --check . && mypy app && lint-imports` | — |
| Frontend | `cd Frontend && npm install && npm run lint && npm test && npm run build` | Node 22 |
| Extremo a extremo | Ver [Frontend/README.md §E2E](Frontend/README.md) (stack aislado `mtabolic-e2e`, puerto 8081, datos sintéticos) | Docker |

Para dejar evidencia de una ejecución limpia, guardar los reportes con fecha, por ejemplo `pytest --junitxml=reportes/backend.xml`, `npx vitest run --reporter=junit --outputFile=reportes/frontend.xml` y `npx playwright test --reporter=html`.

## 9. Demostración con datos sintéticos

- **Notebook:** `MTABOLIC_DATOS=../Backend/tests/fixtures/historico` antes de ejecutar (PowerShell: `$env:MTABOLIC_DATOS="..\Backend\tests\fixtures\historico"`). Recorre todo el proceso con 23 registros ficticios; la Parte 11 informa controles fallidos porque compara con las cifras de los libros reales, lo que es esperado. **Atención:** la Parte 13 escribe en `salidas/prototipo_final/`; ejecutar la demo sobre una copia del notebook en otra carpeta para no sobrescribir los resultados reales.
- **Aplicación, para probarla:** `bash scripts/levantar-demo.sh` o `powershell -ExecutionPolicy Bypass -File scripts\levantar-demo.ps1` (stack aislado `mtabolic-demo`, puerto 8083, datos de `datos-demo/`, sin configurar nada). Ver la [Guía rápida](GUIA-RAPIDA.md). Sus cifras no son las de la tesis.
- **Aplicación, para el E2E:** stack aislado con libros sintéticos: `docker compose -p mtabolic-e2e --env-file .env.e2e up -d --build` y abrir http://localhost:8081 ([detalle](Documentation/comandos/ensayo-demo-e2e.md)).

## 10. Pipeline y modelo

1. **Carga:** se leen las 20 hojas mensuales (enero 2025 a agosto 2026) y se identifica cada columna aunque cambie de nombre.
2. **Limpieza:** identidad del socio (cédula o nombre normalizado), fechas, montos y plan (281 escrituras → 6 categorías).
3. **Etiqueta:** cada membresía queda evaluable, pendiente o excluida (con motivo). `no_renovo = 1` si no hay otra membresía del socio entre T y T+30.
4. **Variables en T−30:** solo con información registrada hasta T−30; una prueba anti-fuga lo comprueba. Ocho variables: `ciclos_previos`, `antiguedad_dias`, `duracion_modelo`, `monto_actual`, `monto_historico`, `dias_desde_ultima_membresia`, `plan`, `mes_vencimiento`. Los identificadores nunca entran al modelo.
5. **Partición temporal:** entrenamiento (vencimientos hasta el 31-10-2025), validación (01-01 a 01-03-2026) y prueba (desde el 01-05-2026), con márgenes descartados para que la última etiqueta de un conjunto (T+30) se conozca antes de la primera predicción del siguiente (T−30).
6. **Preparación:** imputación por mediana o moda, estandarización y one-hot, ajustados solo con entrenamiento; medianas de monto por plan solo de entrenamiento.
7. **Selección (regla fijada de antemano):** el modelo debe superar a la referencia sin modelo en F1, PR-AUC y Brier en validación; si varios cumplen, gana el de mayor PR-AUC. Con la partición v2 cumplen los dos y la regla elige la Regresión Logística por 0,017 de PR-AUC. **Se adopta el Random Forest** como desviación explícita: la diferencia no es distinguible con el bootstrap por socio y el Random Forest es el modelo integrado y verificado en la app. Se reportan siempre los dos ([M05](Documentation/mejoras/M05-correcciones-evaluacion-semana-10.md)).
8. **Comprobación final:** en prueba, una sola vez, con bootstrap por socio para la incertidumbre.
9. **Producto:** el Random Forest operativo se reentrena con las 1.564 membresías evaluables y genera la lista con niveles (ALTO ≥ 0,70, MEDIO ≥ 0,50) y hasta tres motivos SHAP, igual en el notebook y en la app.
10. **Reentrenamiento en la app (CU-02):** cada seis meses o a pedido; el candidato se entrena sin los ciclos de comparación ni los que vencen en los 60 días previos a ella, la misma regla de cronología del notebook.

## 11. Limitaciones

- La calidad depende de los libros de origen: 31 % de los registros no tiene fecha de vencimiento y no hay datos de asistencia.
- Las probabilidades no están calibradas (el Brier no mejora a la referencia en prueba): sirven para **ordenar**, no como porcentajes.
- Los conjuntos de evaluación son pequeños (180 y 277 membresías); los intervalos bootstrap describen la incertidumbre con estos datos, no garantizan el resultado en otros períodos.
- `mes_vencimiento` se codifica como año-mes: los meses futuros no se vieron en entrenamiento y la variable no aporta en ellos. Recodificarla como mes del año (1–12) es trabajo futuro.
- El modelo adoptado (Random Forest) no es el que elige la regla de selección (Regresión Logística); la desviación está justificada y documentada, y en prueba la Regresión Logística acertó más en el top 25 (25 frente a 19): queda como alternativa para la siguiente versión.
- El sistema prioriza; no mide el efecto causal de una campaña.

## 12. Lista de verificación antes de entregar

- [ ] Un libro de 2025 y uno de 2026, con las huellas de §4.
- [ ] Notebook ejecutado completo, sin errores, con `TODOS LOS CONTROLES OK` y las salidas guardadas.
- [ ] `verificar_lista.py` con 0 diferencias.
- [ ] Pruebas del Backend y del Frontend en verde, con reportes guardados.
- [ ] Commit y tag de la versión entregada (por ejemplo `v2.0-entrega-final`) y acceso del evaluador al repositorio.
- [ ] Cifras del informe tomadas de `salidas/prototipo_final/` (sin edición manual).
