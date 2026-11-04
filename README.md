# Mtabolic · Estimación temprana del riesgo de no renovación de membresías

**Proyecto:** Sistema inteligente para la estimación temprana del riesgo de no renovación de membresías mediante aprendizaje automático.
**Caso de estudio:** Mtabolic, Puembo (Quito, Ecuador).
**Notebook oficial:** [`Notebookes/Prototipo_Final_Mtabolic.ipynb`](Notebookes/Prototipo_Final_Mtabolic.ipynb) (versión v3, 2026-11-03: Regresión Logística como modelo adoptado).

Este README tiene dos partes:

- **Parte A (§1 a §5), para cualquier persona.** Qué es el proyecto, qué hace y cómo probarlo en su computadora paso a paso, aunque nunca haya usado estas herramientas. No necesita ningún archivo confidencial.
- **Parte B (§6 en adelante), técnica.** Arquitectura, tecnologías, datos y cómo reproducir el análisis y las pruebas. Reproducir las cifras de la tesis **requiere los libros reales**, que no están en el repositorio.

---

# Parte A · Para cualquier persona

## 1. ¿Qué es y cuál es su objetivo?

Mtabolic es un gimnasio que guarda las membresías de sus socios en libros de Excel. Revisarlos a mano no permite saber a tiempo **qué socios podrían no renovar**, y la llamada para retenerlos suele llegar cuando la membresía ya venció.

**Objetivo:** avisar con anticipación. La aplicación estima el riesgo de cada socio **30 días antes de que venza su membresía** y entrega una **lista ordenada** de a quién llamar primero, con un nivel de riesgo (ALTO, MEDIO o BAJO) y los motivos de cada caso.

Se considera que un socio **no renovó** si no compra una nueva membresía en los 30 días siguientes al vencimiento. Si todavía no se puede saber, el caso queda **pendiente**; nunca se cuenta como baja.

> La estimación ayuda a decidir a quién llamar primero. No es una certeza, y no demuestra que una campaña cause la renovación.

## 2. ¿Qué hace la aplicación?

Es una página web que funciona en la propia computadora del gimnasio. No necesita internet ni usuario y contraseña: solo responde a esa computadora.

| Pantalla | Para qué sirve |
|---|---|
| **Inicio** | Indica si el sistema está listo para usarse |
| **Lista** | Genera la lista del mes con los socios a contactar, su nivel de riesgo y sus motivos; se descarga en Excel. Desde aquí se registra cada contacto con el socio y su resultado |
| **Campañas** | Guarda las ofertas que se usan al llamar (por ejemplo, una clase de regalo) |
| **Carga** | Sube el Excel con las membresías del mes; el sistema lo revisa antes de guardarlo |
| **Dashboard** | Muestra con gráficos cómo le fue a cada lista: cuántos socios se contactaron, cuántos renovaron y con cuánta anticipación se llamó |

Al arrancar por primera vez, la aplicación lee el histórico de Excel, lo guarda en su base de datos y **aprende** de él (entrena el modelo). Cada seis meses, o cuando se pida, vuelve a aprender con los datos nuevos y solo cambia de modelo si el nuevo es mejor.

## 3. Probarla en su computadora, paso a paso

Así se instala una **versión de demostración con datos inventados**. Funciona en cualquier computadora con Windows, macOS o Linux y no hace falta pedir ningún archivo.

> **Los datos son inventados.** Sirven para ver la aplicación funcionando. Las cifras que verá **no son las de la tesis** ni describen al gimnasio.

**Qué necesita:**

- Una computadora con Windows 10 u 11, macOS o Linux. Se recomiendan 8 GB de memoria RAM y unos 10 GB libres en disco.
- Internet **solo la primera vez**, para descargar los programas.
- Unos 20 minutos la primera vez. Las siguientes, menos de un minuto.

### Paso 1 · Instalar Docker Desktop

Docker es el programa que hace funcionar la aplicación sin instalar nada más. Es gratuito para uso personal y educativo.

1. Entre en <https://www.docker.com/products/docker-desktop/> y pulse el botón de descarga de su sistema (Windows, Mac con chip Apple, Mac con Intel o Linux).
2. Abra el archivo descargado y siga el instalador con las opciones que trae por defecto.
   - **En Windows**, si pregunta por **WSL 2**, deje esa opción marcada. Si al terminar pide reiniciar, reinicie.
3. Abra **Docker Desktop** desde el menú de inicio (Windows) o desde Aplicaciones (Mac).
4. Acepte las condiciones de uso. No hace falta crear una cuenta: puede pulsar **Skip** (Omitir).
5. Espere a que abajo a la izquierda diga **Engine running** (en marcha), con un punto verde. Deje Docker Desktop abierto.

### Paso 2 · Descargar el proyecto

1. Entre en <https://github.com/CralosMejia/ProyectoMIA>.
2. Pulse el botón verde **Code** y después **Download ZIP**.
3. Busque el archivo en su carpeta **Descargas** y descomprímalo:
   - Windows: clic derecho sobre el archivo → **Extraer todo** → **Extraer**.
   - Mac: doble clic sobre el archivo.
4. Queda una carpeta llamada `ProyectoMIA-...`. Recuerde dónde está.

> Si ya usa git, puede usar en su lugar `git clone https://github.com/CralosMejia/ProyectoMIA.git`.

### Paso 3 · Abrir una terminal dentro de esa carpeta

La terminal es una ventana donde se escriben órdenes. Debe abrirse **dentro** de la carpeta del proyecto.

- **Windows:** abra la carpeta descomprimida (la que contiene `README.md` y la carpeta `scripts`). Haga clic derecho en un espacio vacío y elija **Abrir en Terminal**. Si no aparece, escriba `powershell` en la barra de direcciones de la carpeta y pulse Enter.
- **Mac:** abra la aplicación **Terminal**, escriba `cd ` (con un espacio al final), arrastre la carpeta a la ventana y pulse Enter.
- **Linux:** clic derecho dentro de la carpeta → **Abrir en una terminal**.

### Paso 4 · Ejecutar el comando de arranque

Copie la línea de su sistema, péguela en la terminal y pulse Enter:

| Sistema | Comando |
|---|---|
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\levantar-demo.ps1` |
| Mac o Linux | `bash scripts/levantar-demo.sh` |

No tiene que responder nada. Verá avanzar cuatro pasos (`[1/4]` a `[4/4]`). La primera vez tarda varios minutos, porque descarga y prepara todo. Espere hasta que aparezca:

```
Listo. Abra http://localhost:8083 en el navegador.
```

### Paso 5 · Usar la aplicación

1. Abra su navegador (Chrome, Edge, Firefox o Safari) y escriba en la barra de direcciones: **http://localhost:8083**
2. En **Inicio** debe decir que el sistema está listo.
3. Entre en **Lista**, deje la fecha y los días que propone la pantalla y pulse **Generar lista**. Después pulse **Descargar Excel** para guardarla.
4. Para probar la carga de datos, en **Carga** suba el archivo `Backend/tests/fixtures/plantillas/plantilla_valida.xlsx` de la carpeta del proyecto.

## 4. Parar, volver a abrir y borrar

Escriba estos comandos en una terminal abierta dentro de la carpeta del proyecto (Paso 3).

| Quiero | Comando |
|---|---|
| Parar, sin perder nada | `docker compose -p mtabolic-demo --env-file .env.demo stop` |
| Volver a abrirla | Abrir Docker Desktop y repetir el comando del Paso 4 |
| Borrar todo el demo | `docker compose -p mtabolic-demo --env-file .env.demo down -v` |

También puede pararla desde Docker Desktop: en **Containers**, botón de parar junto a `mtabolic-demo`. Si apaga la computadora no se pierde nada: al volver, abra Docker Desktop y repita el Paso 4.

> **Cuidado al borrar:** escriba siempre `-p mtabolic-demo`. Sin esa parte, `down -v` actúa sobre la instalación principal y borra su base de datos.

## 5. Si algo falla

| Qué ve | Qué hacer |
|---|---|
| `Docker no esta instalado` o `no esta en marcha` | Abra Docker Desktop, espere el punto verde de **Engine running** y repita el Paso 4 |
| Docker Desktop no arranca en Windows | Abra PowerShell como administrador, escriba `wsl --install`, reinicie y vuelva a abrir Docker Desktop. En algunas computadoras hay que activar la **virtualización** en la BIOS |
| La descarga se corta o tarda muchísimo | Revise la conexión a internet; un antivirus o una VPN pueden bloquear a Docker. Repita el Paso 4: continúa donde quedó |
| `el puerto 8083 ya esta ocupado` (o 8003, 5435) | Otro programa usa ese puerto. Ciérrelo, o reinicie la computadora, y repita el Paso 4 |
| Windows dice que no se puede ejecutar el script | Compruebe que copió el comando completo, incluido `-ExecutionPolicy Bypass` |
| `No such file or directory` o `no se encontro` | La terminal no está dentro de la carpeta del proyecto. Repita el Paso 3 |
| La página no abre | Espere al mensaje `Listo.` antes de abrirla y compruebe la dirección: `http://localhost:8083` |
| La lista sale vacía | Los datos inventados tienen fecha de vigencia (`datos-demo/vigencia.txt`). Si ya pasó, borre el demo (§4) y repita el Paso 4: se crean de nuevo con la fecha de hoy |
| `tiempo agotado` u otro error | Ejecute el comando de `logs` que muestra el mensaje y revise la última línea con error |

La [Guía rápida](GUIA-RAPIDA.md) resume esta parte en una página.

---

# Parte B · Técnica

## 6. Arquitectura

La aplicación son cuatro servicios Docker definidos en `compose.yaml`:

```
 Navegador
     │  http://localhost:8080  (solo desde el propio equipo)
     ▼
┌────────────────────┐   /api/v1/...   ┌──────────────────────┐   SQL    ┌─────────────────┐
│ frontend           │ ──────────────▶ │ backend              │ ───────▶ │ db              │
│ nginx + SPA React  │                 │ FastAPI + modelo ML  │          │ PostgreSQL 16   │
└────────────────────┘                 └──────────┬───────────┘          └────────▲────────┘
                                                  │ lee al arrancar               │ esquema
                                       libros Excel del histórico        ┌────────┴────────┐
                                       (carpeta HISTORICO_DIR, solo      │ migrate         │
                                        lectura)                         │ Alembic, 1 vez  │
                                                                         └─────────────────┘
```

- **`migrate`** crea o actualiza el esquema de la base con Alembic y termina. Es el único que cambia el esquema.
- **`backend`** arranca cuando la base está lista y `migrate` terminó. Con la base vacía migra el histórico de Excel (CU-03) y entrena el modelo; después atiende la API.
- **`frontend`** sirve la página y reenvía `/api` al backend por una red interna.
- **Acceso:** sin login. Los puertos se publican solo en `127.0.0.1` y el backend atiende solo a las IP autorizadas (CU-00): desde otro equipo responde `403`, por diseño.

**Arquitectura del código.** Ambos lados están en capas, y cada capa depende solo de las de adentro:

| Lado | Capas |
|---|---|
| Backend (`Backend/app/`) | `api` (HTTP) → `application` (casos de uso) → `domain` (reglas de negocio, sin librerías externas). `infrastructure` (base de datos, Excel, modelo, reloj) implementa los puertos de `application`. `import-linter` verifica las dependencias en cada prueba. Módulos: `historico`, `cargas`, `modelo`, `listas`, `campanias`, `gestiones`, `health` |
| Frontend (`Frontend/src/`) | Por funcionalidad: `features/{inicio,lista,campanias,carga,dashboard,health}`, cada una con `api/`, `hooks/`, `components/` y `pages/`; `core/` para lo transversal y `shared/ui/` para los componentes reutilizables |

Detalle: [Documentation/docs/backend/01-arquitectura.md](Documentation/docs/backend/01-arquitectura.md), [Documentation/docs/frontend/01-arquitectura.md](Documentation/docs/frontend/01-arquitectura.md) y las decisiones en [Documentation/adr/](Documentation/adr/).

## 7. Tecnologías y dependencias

| Parte | Tecnología |
|---|---|
| Base de datos | PostgreSQL 16 (`postgres:16.15-alpine`) |
| Backend | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, psycopg 3, Alembic 1.20, Uvicorn |
| Modelo y datos | **scikit-learn 1.8.0** (Regresión Logística), **shap 0.54.1** (motivos), pandas 3.0.6, numpy 2.5.3, openpyxl 3.1.5, joblib 1.6.0 |
| Frontend | React 19, TypeScript, Vite, React Router 7, Tailwind CSS 4, exceljs (descarga en Excel) |
| Servidor web | nginx (`nginxinc/nginx-unprivileged`), imagen construida con Node 22 |
| Pruebas | pytest, ruff, mypy e import-linter (Backend); Vitest, Testing Library, MSW y Playwright (Frontend) |
| Análisis | Jupyter, con las librerías de `requirements.txt` (raíz) |
| Ejecución | Docker con Compose v2 |

Las librerías de datos y ML tienen la **misma versión exacta** en el notebook (`requirements.txt`) y en la app (`Backend/pyproject.toml`). Con otra versión de scikit-learn los modelos cambian y las cifras dejan de coincidir.

**Requisitos según lo que quiera hacer:**

| Para | Necesita |
|---|---|
| Probar la aplicación (Parte A) | Solo Docker Desktop |
| Usar la aplicación con los datos reales | Docker y los libros reales (§11) |
| Ejecutar el notebook | Python **3.12** y `pip install -r requirements.txt` |
| Desarrollo y pruebas del Backend | Python 3.12, `pip install -e ".[dev]"` en `Backend/` y un PostgreSQL 16 (el de `compose.yaml`) |
| Desarrollo y pruebas del Frontend | Node 22 LTS |

## 8. Contenido del repositorio

| Ruta | Qué contiene |
|---|---|
| `Notebookes/Prototipo_Final_Mtabolic.ipynb` | **Notebook oficial**: datos, variables, partición temporal, modelos, bootstrap por socio, SHAP, lista de septiembre, controles y cifras del informe |
| `requirements.txt` | Dependencias del notebook con versiones exactas |
| `Notebookes/MVP.ipynb` | Notebook **histórico** (mejoras M01–M03). Se conserva como registro; sus cifras ya no son las del informe |
| `Backend/` | API FastAPI en capas, modelo y listas ([Backend/README.md](Backend/README.md)) |
| `Frontend/` | Página React + TypeScript ([Frontend/README.md](Frontend/README.md)) |
| `compose.yaml` | Servicios Docker: `db`, `migrate`, `backend`, `frontend` |
| `Documentation/` | Fuente de verdad del proyecto: casos de uso, ADR, mejoras ([Documentation/README.md](Documentation/README.md)) |
| `Documentation/mejoras/` | Cambios posteriores a la entrega; el más reciente es [M06](Documentation/mejoras/M06-regresion-logistica-modelo-adoptado.md) (Regresión Logística) |
| `scripts/` | Levantar el demo, preparar el entorno de prueba (8081), respaldo, restauración y reinicio de la base |
| `datos-demo/` | Libros **inventados** con que se levanta el demo y su fecha de vigencia ([datos-demo/README.md](datos-demo/README.md)) |
| `plantillas/` | **Fuera de git.** Libros reales `Control Gym 2025*.xlsx` y `Control Gym 2026*.xlsx` (datos personales) |
| `salidas/` | **Fuera de git.** Resultados del notebook, modelos y clave de los códigos seudónimos |

**Instalaciones que conviven en un equipo** (proyectos de Compose distintos, cada uno con su base):

| Proyecto | Puerto | Datos | Cómo se levanta |
|---|---|---|---|
| `proyectofinal` | 8080 | Reales | §11 |
| `mtabolic-e2e` | 8081 | Inventados, para pruebas E2E y grabar demos | [Documentation/comandos/preparar-8081.md](Documentation/comandos/preparar-8081.md) |
| `mtabolic-demo` | 8083 | Inventados (`datos-demo/`) | Parte A |

## 9. Datos

- Los libros reales tienen datos personales: **no están en el repositorio** y se entregan por un canal autorizado. Se colocan en `plantillas/` (o en la carpeta indicada por la variable `MTABOLIC_DATOS`) con nombres que contengan `Control Gym 2025` y `Control Gym 2026`. Se usa **un** libro de cada año.
- El notebook imprime la **huella SHA-256** de los libros que leyó. Con los libros de la entrega las huellas son `7ad9e21de2dd5f15` (2025) y `516600703c316ca1` (2026): si no coinciden, las cifras tampoco coincidirán.
- **Datos sintéticos** para probar sin datos reales: `datos-demo/` (los genera `Backend/scripts/generar_dataset_demo.py`) y `Backend/tests/fixtures/historico/` (dos libros mínimos para las pruebas). Ver §14.
- **Clave de los códigos seudónimos:** los socios se muestran como `MTB-XXXXXXXX`, un HMAC-SHA256 de su identidad con una clave secreta (variable `MTABOLIC_SAL_CODIGOS` o archivo `salidas/.sal_codigos`, fuera de git). Si no existe, el notebook crea una nueva; con otra clave cambian los códigos, pero no las métricas. Es seudonimización, no anonimato.

## 10. Reproducir el análisis (notebook)

### 10.1 Entorno

Desde la raíz del proyecto:

```bash
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1     ·   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 10.2 Ejecución

- **Jupyter o VS Code:** abrir `Notebookes/Prototipo_Final_Mtabolic.ipynb` con el entorno anterior, **desde la carpeta `Notebookes/`** (las rutas a `plantillas/` y `salidas/` son relativas), y ejecutar *Run All*. Tarda alrededor de un minuto.
- **Terminal (sin abrir Jupyter):**

  ```bash
  cd Notebookes
  jupyter nbconvert --to notebook --execute --inplace Prototipo_Final_Mtabolic.ipynb
  ```

### 10.3 Qué se debe obtener

La **Parte 11 · Controles** termina con `TODOS LOS CONTROLES OK`. Valores de la versión congelada v3 ([M06](Documentation/mejoras/M06-regresion-logistica-modelo-adoptado.md)):

| Control | Valor esperado |
|---|---|
| Registros con identidad / socios distintos | 2.748 / 1.410 |
| Membresías evaluables / no renovaron | 1.564 / 1.098 (70,2 %) |
| Entrenamiento / validación / prueba | 721 / 180 / 277 |
| Cronología: cada etiqueta se conoce antes de la siguiente predicción | Sí (2 días de holgura en ambas transiciones) |
| Prueba anti-fuga (variables que cambian al borrar el futuro) | 0 |
| Modelo adoptado / umbral (= el que elige la regla, §15) | **Regresión Logística** / 0,21 |
| PR-AUC en prueba: Regresión Logística / Random Forest (comparación) / sin modelo | 0,820 / 0,787 / 0,668 |
| Precisión@25 en prueba: Regresión Logística / Random Forest | 1,00 (25 de 25) / 0,76 (19 de 25) |
| Matriz de confusión de la Regresión Logística en prueba (VN, FP, FN, VP) | 22, 70, 15, 170 |
| SHAP lineal: aditividad y coincidencia con `shap.LinearExplainer` | < 1e-9 |
| Lista de septiembre | 57 socios: ALTO 9, MEDIO 33, BAJO 15, igual a la app |
| Top 25 del Random Forest igual a `MVP.ipynb` (continuidad) | Sí |

Si un control falla, **no** se cambian los valores esperados para que coincidan: se revisan los datos (huellas), las versiones de las librerías y el código, y se documenta el motivo.

### 10.4 Salidas

La **Parte 13** guarda en `salidas/prototipo_final/` (solo cifras agregadas y modelos, sin datos personales):

| Archivo | Contenido |
|---|---|
| `particiones.csv`, `cronologia.csv` | Tamaño de cada conjunto y control de cronología |
| `comparacion_validacion.csv`, `comparacion_prueba.csv` | Métricas de la referencia, la Regresión Logística y el Random Forest |
| `bootstrap_validacion.csv`, `bootstrap_prueba.csv` | Diferencias con intervalo bootstrap por socio (1.000 réplicas, semilla 42) |
| `importancias_validacion.csv`, `coeficientes_regresion_logistica.csv`, `shap_medio.csv` | Permutación, coeficientes y SHAP (lineal de la RL, en log-odds; TreeExplainer del RF como comparación) |
| `tabla_11_top25_por_mes.csv`, `uso_operativo_prueba.csv`, `matriz_confusion_prueba.csv`, `matriz_confusion_prueba_rf.csv` | Aciertos y errores con el top 25 por mes y con el umbral |
| `bandas_riesgo.csv` | Membresías y precisión por nivel (0,70/0,50) en validación y prueba, solo descriptivo |
| `medianas_por_plan.csv` | Medianas de monto (entrenamiento y modelo operativo) |
| `modelo_evaluado.joblib`, `modelo_rf_evaluado.joblib`, `modelo_operativo.joblib` | Regresión Logística adoptada y Random Forest de comparación (entrenados hasta el 31-10-2025) y Regresión Logística operativa (la de la app) |
| `parametros_modelo_operativo.json`, `lista_operativa_2026-09.xlsx` | Referencia con que `verificar_lista.py` compara la app (§12); la lista lleva códigos seudónimos |
| `controles.csv`, `ejecucion.json` | Resultado de los controles, versiones, huellas de los libros y de los modelos y cifras para el informe |

## 11. Levantar la aplicación con los datos reales

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

Con la base vacía, el backend migra el histórico y entrena el modelo al arrancar; Inicio pasa a «Sistema listo» en unos segundos. Para parar: `docker compose down` (con `-v` se borra también la base). Operación en el PC del gimnasio, respaldo y restauración: [Backend/README.md §Operación](Backend/README.md).

## 12. Comprobar que la app y el notebook dan la misma lista

`Backend/scripts/verificar_lista.py` recompone en memoria (sin base de datos ni Docker) la lógica de la app y compara la lista de septiembre con la del notebook oficial, que lee de `salidas/prototipo_final/` (por eso hay que ejecutar antes el notebook): conteos, variables, medianas, probabilidades a 8 decimales, niveles, motivos (SHAP lineal), algoritmo, hiperparámetros, cortes y orden.

```bash
cd Backend
pip install -e .              # o usar el entorno del Backend
python scripts/verificar_lista.py ../plantillas
```

Resultado esperado: `diferencias: ... | total 0` y código de salida `0`. Resultado registrado el 2026-11-03 (v3, Regresión Logística): 57 filas, 0 diferencias en los 12 apartados.

## 13. Pruebas automáticas

| Parte | Comando | Requiere |
|---|---|---|
| Backend, unitarias | `cd Backend && pytest -m unit` | Python 3.12 |
| Backend, completas | `cd Backend && pytest` | `TEST_DATABASE_URL` hacia una base cuyo nombre termine en `_test` (`docker compose up -d db`) |
| Backend, calidad | `ruff check . && ruff format --check . && mypy app && lint-imports` | — |
| Frontend | `cd Frontend && npm install && npm run lint && npm test && npm run build` | Node 22 |
| Extremo a extremo | Ver [Frontend/README.md §E2E](Frontend/README.md) (stack aislado `mtabolic-e2e`, puerto 8081, datos sintéticos) | Docker |

Para dejar evidencia de una ejecución limpia, guardar los reportes con fecha, por ejemplo `pytest --junitxml=reportes/backend.xml`, `npx vitest run --reporter=junit --outputFile=reportes/frontend.xml` y `npx playwright test --reporter=html`.

## 14. Demostración con datos sintéticos

- **Aplicación, para probarla:** Parte A de este README (stack `mtabolic-demo`, puerto 8083, datos de `datos-demo/`). Sus cifras no son las de la tesis.
- **Aplicación, para grabar un demo o para el E2E:** stack `mtabolic-e2e`, puerto 8081. `scripts\preparar-8081.ps1 grabacion` lo deja con varios meses de listas, contactos y resultados inventados; `scripts\preparar-8081.ps1 e2e` lo devuelve a los datos de las pruebas automáticas ([detalle](Documentation/comandos/preparar-8081.md)).
- **Notebook:** `MTABOLIC_DATOS=../Backend/tests/fixtures/historico` antes de ejecutar (PowerShell: `$env:MTABOLIC_DATOS="..\Backend\tests\fixtures\historico"`). Recorre todo el proceso con 23 registros ficticios; la Parte 11 informa controles fallidos porque compara con las cifras de los libros reales, lo que es esperado. **Atención:** la Parte 13 escribe en `salidas/prototipo_final/`; ejecutar la demo sobre una copia del notebook en otra carpeta para no sobrescribir los resultados reales.

## 15. Pipeline y modelo

1. **Carga:** se leen las 20 hojas mensuales (enero 2025 a agosto 2026) y se identifica cada columna aunque cambie de nombre.
2. **Limpieza:** identidad del socio (cédula o nombre normalizado), fechas, montos y plan (281 escrituras → 6 categorías).
3. **Etiqueta:** cada membresía queda evaluable, pendiente o excluida (con motivo). `no_renovo = 1` si no hay otra membresía del socio entre T y T+30.
4. **Variables en T−30:** solo con información registrada hasta T−30; una prueba anti-fuga lo comprueba. Ocho variables: `ciclos_previos`, `antiguedad_dias`, `duracion_modelo`, `monto_actual`, `monto_historico`, `dias_desde_ultima_membresia`, `plan`, `mes_vencimiento`. Los identificadores nunca entran al modelo.
5. **Partición temporal:** entrenamiento (vencimientos hasta el 31-10-2025), validación (01-01 a 01-03-2026) y prueba (desde el 01-05-2026), con márgenes descartados para que la última etiqueta de un conjunto (T+30) se conozca antes de la primera predicción del siguiente (T−30).
6. **Preparación:** imputación por mediana o moda, estandarización y one-hot, ajustados solo con entrenamiento; medianas de monto por plan solo de entrenamiento.
7. **Selección (regla fijada de antemano):** el modelo debe superar a la referencia sin modelo en F1, PR-AUC y Brier en validación; si varios cumplen, gana el de mayor PR-AUC. Cumplen los dos y la regla elige la **Regresión Logística** (PR-AUC 0,724 frente a 0,707), que es el modelo adoptado; el Random Forest se reporta como comparación ([M06](Documentation/mejoras/M06-regresion-logistica-modelo-adoptado.md), [ADR-016](Documentation/adr/ADR-016-regresion-logistica-como-modelo-adoptado.md)).
8. **Comprobación final:** en prueba, una sola vez, con bootstrap por socio para la incertidumbre.
9. **Producto:** la Regresión Logística operativa se reentrena con las 1.564 membresías evaluables y genera la lista con niveles (ALTO ≥ 0,70, MEDIO ≥ 0,50) y hasta tres motivos SHAP lineal (en log-odds), igual en el notebook y en la app.
10. **Reentrenamiento en la app (CU-02):** cada seis meses o a pedido; el candidato se entrena sin los ciclos de comparación ni los que vencen en los 60 días previos a ella, la misma regla de cronología del notebook. Solo reemplaza al modelo vigente si su PR-AUC es mayor.

## 16. Limitaciones

- La calidad depende de los libros de origen: 31 % de los registros no tiene fecha de vencimiento y no hay datos de asistencia.
- Las probabilidades no están calibradas (el Brier no mejora a la referencia en prueba): sirven para **ordenar**, no como porcentajes.
- Los conjuntos de evaluación son pequeños (180 y 277 membresías); los intervalos bootstrap describen la incertidumbre con estos datos, no garantizan el resultado en otros períodos.
- `mes_vencimiento` se codifica como año-mes: los meses futuros no se vieron en entrenamiento y la variable no aporta en ellos. Recodificarla como mes del año (1–12) es trabajo futuro.
- Con los cortes fijos 0,70/0,50, en validación el nivel ALTO no ordena mejor que el MEDIO (precisión 0,656 frente a 0,712; en prueba 0,889 frente a 0,707): los niveles son orientativos.
- El sistema prioriza; no mide el efecto causal de una campaña.

## 17. Lista de verificación antes de entregar

- [ ] Un libro de 2025 y uno de 2026, con las huellas de §9.
- [ ] Notebook ejecutado completo, sin errores, con `TODOS LOS CONTROLES OK` y las salidas guardadas.
- [ ] `verificar_lista.py` con 0 diferencias.
- [ ] Pruebas del Backend y del Frontend en verde, con reportes guardados.
- [ ] Commit y tag de la versión entregada (por ejemplo `v2.0-entrega-final`) y acceso del evaluador al repositorio.
- [ ] Cifras del informe tomadas de `salidas/prototipo_final/` (sin edición manual).
