# Frontend · 01 · Arquitectura

React 19 · TypeScript estricto · Vite 8 · Tailwind CSS 4 · React Router 7 · Vitest + Testing Library + MSW · Playwright. Creado en R-001 (ver [ADR-001](../../adr/ADR-001-fastapi-react-postgresql.md)).

## Estructura

```
Frontend/src/
  main.tsx               arranque (MSW en navegador solo con DEV y VITE_API_MOCKS=true)
  index.css              Tailwind + tokens de diseño (@theme): único archivo de estilos
  app/router.tsx         createBrowserRouter; ruta raíz con AppLayout y rutas hijas de cada feature
  core/config.ts         VITE_API_BASE_URL (fallback "": mismo origen), apiMocks
  core/http/             cliente HTTP único: http-client.ts, api-error.ts (ApiError)
  core/layout/AppLayout  header + nav (5 enlaces) + <main> con Suspense y <Outlet/>
  shared/ui/             componentes base sin lógica de negocio (no importan features/)
  mocks/                 MSW: handlers.ts (autodescubrimiento), server.ts (pruebas), browser.ts (dev)
  features/{feature}/
    routes.tsx           rutas lazy (React.lazy + Suspense)
    pages/               componen y conectan con hooks
    hooks/               estado de servidor: carga, error, cancelación
    api/                 contrato con el backend y mapeo snake_case → camelCase
    components/          presentacionales, solo props
    types.ts
Frontend/e2e/            Playwright
```

Flujo en una sola dirección: `pages → hooks → api → core/http`. `components/` no importa hooks ni `api/`; `pages/` no importa `api/` ni `core/http`; ningún feature llama a `fetch` directamente (lo verifica `features/health/architecture.test.ts`).

## `core/http`

- `httpGet<T>(path, { signal })` antepone la base URL y parsea JSON.
- `httpPost<T>` y `httpPut<T>` envían JSON (`Content-Type: application/json`); `httpPostForm<T>(path, FormData)` envía multipart sin fijar `Content-Type`; `httpGetBlob(path)` devuelve un `Blob` (descarga del Excel).
- Respuesta no 2xx → `ApiError { status, message, body }`; `message` sale de `error.message` del formato único del backend.
- Error de red → `ApiError` con `status: 0` y mensaje genérico.
- Petición abortada → se propaga el `AbortError` original (no se envuelve).
- 2xx con JSON malformado → `ApiError`.
- Sin `localStorage`/`sessionStorage`, sin `console.log` de respuestas.

## Feature `health` (patrón de referencia)

| Capa | Archivo | Rol |
|---|---|---|
| types | `types.ts` | `Health = { status: "ok" \| "degraded"; database: "up" \| "down"; checkedAt: Date }` |
| api | `api/health-api.ts` | `getHealth(signal)`; mapea `checked_at` → `checkedAt`; un `503` con cuerpo de health válido se devuelve como `degraded` (no lanza); otros errores propagan `ApiError` |
| hooks | `hooks/useHealth.ts` | `{ data, error, isLoading, refetch }`; `AbortController` al desmontar; expone solo `error.message` |
| pages | `pages/HealthPage.tsx` | estados: cargando (`role="status"`), ok, degradado, error (`role="alert"` + "Reintentar") |
| components | `components/HealthStatusCard.tsx` | tarjeta presentacional |
| routes | `routes.tsx` | ruta `/salud`, lazy (antes `/`; movida en R-002) |

## Navegación (R-002)

| Ruta | Feature | Página |
|---|---|---|
| `/` (index) | `inicio` | "Inicio" |
| `/carga` | `carga` | "Carga de datos" |
| `/lista` | `lista` | "Lista priorizada" |
| `/campanias` | `campanias` | "Campañas" |
| `/dashboard` | `dashboard` | "Dashboard" |
| `/salud` | `health` | `HealthPage` (fuera del menú) |
| `*` | — | "Página no encontrada" |

Las páginas de negocio son placeholders con `<h1>` hasta sus días del cronograma, salvo Inicio y Carga (R-003), Lista (R-004) y Campañas (R-009), abajo. Cada feature expone ya su capa `api/` (`types.ts`, `api/<feature>-api.ts`, `api/<feature>-api.handlers.ts`) según el [contrato](../API_CONTRACT.md): `inicio` (estado del sistema, alertas), `carga` (vista previa y confirmación con `FormData` campo `archivo`), `lista` (generar, última, por id, Excel, sugerencias, gestiones), `campanias` (listar, crear, editar, inactivar; el tipo de `planes` excluye `"DIARIO"`) y `dashboard` (`?mes=YYYY-MM` opcional). Los decimales (`score`, `tasaRenovacion`) se mantienen como `string`; `modeloVigente.version` es `string` (`"v1"`).

### Inicio y Carga (R-003, con MSW)

| Feature | Archivos | Comportamiento |
|---|---|---|
| `inicio` | `hooks/useEstadoSistema.ts`, `components/EstadoSistemaPanel.tsx`, `pages/InicioPage.tsx` | Pide `GET /sistema/estado` (con `AbortController`). `INICIALIZANDO` → "Inicializando datos históricos" (`role="status"`); `FALTAN_DATOS_HISTORICOS` → aviso de revisar la carpeta configurada (sin rutas); `LISTO` → "Sistema listo" y "Modelo de predicción: activo desde <fecha es-EC>", o "El modelo de predicción aún no está disponible" (R-005; antes versión y fecha de entrenamiento). Error `501`/`500` → `ErrorAlert` con "Reintentar". |
| `carga` | `hooks/useCarga.ts`, `components/{VistaPreviaCarga,ResumenCarga}.tsx`, `pages/CargaPage.tsx` | Estados `inicial` → `validando` → `vista-previa` → `enviando` → `confirmada`. Input `.xlsx` con etiqueta; otro tipo → mensaje local sin llamar a la API. Vista previa con conteos y `DataTable` de errores (`fila`/`columna`/`motivo`); "Confirmar" deshabilitado si hay errores, si `puedeConfirmar` es `false` (todo duplicado) o mientras envía (sin doble envío). Resumen tras confirmar: `filasGuardadas`, `filasDuplicadas`, `avisosEnlace`; `400`/`409`/`422` → `ErrorAlert` con el mensaje del servidor. Cambiar de archivo limpia la vista previa. |

**Carga contra la API real y resumen (R-007, D4-FE-01/02):** `ResumenCarga` y `VistaPreviaCarga` viven en `components/VistaPreviaCarga.tsx` (corrige la tabla anterior, que citaba un `ResumenCarga.tsx` aparte). Vista previa: filas leídas, válidas, con error, duplicadas, rango de vencimientos y tabla de errores "Fila / Columna (letra) / Motivo"; "Confirmar" deshabilitado si hay errores o no hay filas nuevas. Resumen tras confirmar: archivo, "Filas leídas", "Filas guardadas", "Filas duplicadas (no se guardaron)", "Socios enlazados con su historia", sección "Para revisar" con `avisosEnlace` (solo si hay avisos) y enlace "Ver la lista de socios por vencer" a `/lista`. `413` → `ErrorAlert` "El archivo supera el tamaño máximo permitido."; `422` al confirmar → mensaje del servidor y vuelve a la vista previa. Los handlers MSW (`carga-api.handlers.ts`) devuelven los mismos códigos y mensajes que el backend ([API_CONTRACT §Cargas](../API_CONTRACT.md#cargas-cu-01-r-007)); MSW sigue solo en pruebas y con `VITE_API_MOCKS=true`. Sustituye la nota de R-003 según la cual el resumen no mostraba `filasLeidas`. `router.edge.test.tsx`: la ruta `/` ahora pide `sistema/estado` en vez de `/health`.

**Carga en tres pasos (R-008):** elegir → revisar → confirmar. `useCarga` añade el estado `seleccionado` (`inicial` → `seleccionado` → `validando` → `vista-previa` → `enviando` → `confirmada`), expone `archivoSeleccionado` (solo el nombre) y `revisar()`. Elegir un `.xlsx` **no** llama a la API; "Revisar archivo" lanza `POST /cargas/vista-previa` (error → mensaje y vuelve a `seleccionado`, se puede reintentar); "Confirmar carga" (antes "Confirmar") guarda, con las mismas reglas de habilitación. Cambiar de archivo cancela la petición en curso y limpia vista previa, resumen y errores. `components/SelectorArchivo.tsx` (presentacional, un solo uso: no sube a `shared/ui`; sin CSS nuevo): botón nativo visible y enfocable "Seleccionar archivo de carga (.xlsx)" que dispara el `click` del `<input type="file" accept=".xlsx">` oculto (fuera del orden de tabulación, sigue asociado a la etiqueta "Archivo de la plantilla (.xlsx)" para pruebas y E2E), ayuda "Suba la plantilla oficial del mes." con `aria-describedby`, "Ningún archivo seleccionado" / "Archivo elegido: <nombre>" y error de extensión junto al selector. Sustituye la vista previa automática al elegir archivo de la tabla anterior.

**Inicio con consulta periódica (R-004):** mientras el estado es `INICIALIZANDO`, `useEstadoSistema` vuelve a pedirlo cada 5 s hasta `LISTO` o `FALTAN_DATOS_HISTORICOS`, y se detiene al desmontar (`AbortController` + `clearTimeout`).

### Lista priorizada, Excel e historial (R-004, contra el backend real)

| Feature | Archivos | Comportamiento |
|---|---|---|
| `lista` · API | `api/lista-api.ts`, `api/lista-api.handlers.ts`, `types.ts` | `generarLista`, `obtenerUltima` (`404` → `null`), `obtenerLista`, `listarListas` (`GET /listas`), `descargarExcel` (`Blob`). Convierte `snake_case` → camelCase; `score`, umbrales y `montoCobrado` siguen como `string` (nunca `parseFloat`); `fechaGeneracion` es fecha y `creadaEn` instante. `409` → `MENSAJE_SISTEMA_NO_LISTO`. R-005: `Prediccion.cedula: string \| null` (sin `correo`); `422` → error tipado con el mensaje del servidor; los handlers MSW usan cédulas ficticias y devuelven `422` para fecha pasada. |
| `lista` · página | `pages/ListaPage.tsx`, `hooks/useLista.ts`, `components/TablaLista.tsx` | R-005: "Fecha de la lista" (por defecto hoy local, `min` = hoy; vacía o anterior → error local sin llamar a la API), "Buscar socios que vencen en los próximos (días)" (1..31, defecto 30) y "Socios prioritarios a contactar" (K ≥ 1, defecto 25) → "Generar lista". Al entrar muestra la última lista. Dos tablas con `DataTable` y `RiskBadge`: "Socios prioritarios a contactar" (`dentroTopK`) y "Otros socios por vencer" (se oculta si está vacía), ambas por prioridad. Columnas (R-006, sin Celular en pantalla; el celular sigue en la API y, desde R-008, tampoco está en el Excel, que tiene las mismas columnas y tablas que la pantalla): Prioridad, Nombre, Cédula (`null` → "—"), Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales (sin el aporte entre paréntesis; "Sin factores de riesgo destacados" si no hay). No muestra score, columna Top, correo ni la versión del modelo. Aviso de datos antiguos en lenguaje llano si `advertenciaDatosAntiguos`; `409` → mensaje de sistema no listo; `422` → `ErrorAlert` con el mensaje. |
| `lista` · Excel | `components/DescargarExcelButton.tsx`, `hooks/useDescargarExcel.ts` | Descarga `GET /listas/{id}/excel` como archivo (`lista_<id>_<fecha>.xlsx`); deshabilitado mientras descarga; error → `ErrorAlert`. |
| `lista` · historial | `components/HistorialListas.tsx`, `hooks/useHistorialListas.ts` | "Listas anteriores" (`GET /listas`, más reciente primero); opciones (R-006) "<d mmm aaaa> · <N> prioritarios" (p. ej. "29 sep 2026 · 25 prioritarios"; singular "1 prioritario"), con N = `min(topK, totalItems)` porque `GET /listas` no trae el conteo de `dentroTopK` (sin cambio de contrato); abre una anterior con `GET /listas/{id}`. |
| `lista` · formato | `components/formatoFechas.ts` | R-006: funciones puras, sin `Date.now()`, aritmética en UTC (sin desfase de día en Ecuador). `fechaCorta(iso)` → "29 sep 2026" (meses con tabla fija `ene … dic`, sin punto; no `Intl` `month: 'short'`, que en es-EC da "sept." según el ICU). `rangoFechas(isoDesde, dias)` → "29 sep – 29 oct 2026"; si cruza de año, ambos años ("20 dic 2026 – 10 ene 2027"); en el mismo mes no se compacta ("1 oct – 15 oct 2026"). |

**Nombre de la lista (R-008; sustituye el título fijo de R-006 (d)):** campo "Nombre de la lista", primero de los parámetros (`label`, `maxLength` 80, error con `aria-describedby`). `useLista` propone `nombreSugerido(fecha)` = "Lista del " + `fechaCorta` (p. ej. "Lista del 29 sep 2026"), mismo formato que el backend; la sugerencia sigue a la fecha mientras el valor coincida con la sugerencia anterior y se respeta si el usuario lo edita (vuelve a seguirla si escribe exactamente la sugerencia actual). Vacío o solo espacios → "Escriba un nombre para la lista." sin llamar a la API; > 80 → "El nombre puede tener hasta 80 caracteres."; se envía recortado; `400` del servidor → `ErrorAlert`. `lista-api.ts` envía `nombre` solo si llega y mapea `nombre` en `ListaPriorizada` y `ListaResumen`; los handlers MSW usan el mismo formato por defecto y devuelven `400` para nombre inválido. El título (`h2` de `TablaLista`) es `lista.nombre` (texto literal, sin HTML) y "Listas anteriores" muestra "<nombre> · <N> prioritarios" (sustituye "<d mmm aaaa> · <N> prioritarios" de la tabla anterior).

Resumen de la lista (R-006): bajo el título (desde R-008, el nombre de la lista) van exactamente dos líneas, "Rango de fechas: <fechaGeneracion> – <fechaGeneracion + horizonteDias>" y "Socios priorizados para campañas: <n>" (n = filas `dentroTopK`). Se retiraron "Socios por vencer en los próximos…" y "Socios prioritarios a contactar: …" del resumen; los títulos de las dos tablas no cambian.

Etiquetas renombradas en R-005 (usuario no técnico): "Fecha de referencia" → "Fecha de la lista"; "Horizonte (días)" → "Buscar socios que vencen en los próximos (días)"; "Top K" → "Socios prioritarios a contactar"; "Factores principales" → "Motivos principales"; "Vencimiento" → "Vence el"; "Historial de listas" → "Listas anteriores"; en Inicio, "Versión del modelo" / "Fecha de entrenamiento" → "Modelo de predicción: activo desde <fecha>" (sin modelo: "El modelo de predicción aún no está disponible").

**Ayuda de la lista (R-007, D4-FE-03):** `components/AyudaLista.tsx` añade en la página Lista (con o sin lista generada) el botón "¿Cómo funciona esta lista?", que abre el `Modal` de `shared/ui` con texto estático resumido de [06](../../06-como-funciona-la-lista.md) (no se carga el `.md` en tiempo de ejecución). Desde R-008 tiene exactamente cuatro secciones ([06 §1–§4](../../06-como-funciona-la-lista.md)): "Qué hace la lista", "Socios prioritarios a contactar", "Niveles de riesgo: alto, medio y bajo" y "Motivos"; se retiraron "Qué datos se muestran" y "Casos frecuentes" y no menciona el celular. Cierra con "Cerrar" y `Escape`, y el foco vuelve al botón. Una prueba verifica que el texto no contiene "score", "Top K", "top", "horizonte", "percentil" ni "modelo v1".

### Campañas y gestión desde la Lista (R-009, día 5)

| Feature | Archivos | Comportamiento |
|---|---|---|
| `campanias` | `hooks/useCampanias.ts`, `pages/CampaniasPage.tsx`, `components/{TablaCampanias,FormularioCampania}.tsx` | Tabla (`DataTable`) con Nombre, Descripción, Niveles, Planes, Prioridad, Estado ("Activa"/"Inactiva") y etiqueta "Ejemplo". "Nueva campaña" y "Editar" abren `FormularioCampania` en `Modal`: Nombre, Descripción, casillas de niveles (Alto/Medio/Bajo) y planes (sin Diario), Prioridad 1..999; validación local antes de llamar a la API ("Escriba un nombre para la campaña.", "Elija al menos un nivel de riesgo.", "Elija al menos un plan.", "La prioridad debe ser un número entre 1 y 999."). "Inactivar" pide confirmación en `Modal`; no hay "Eliminar". Desde R-010, las filas inactivas muestran "Activar" (nombre accesible "Activar <nombre>") en lugar de "Inactivar", **sin ventana de confirmación**; la fila se actualiza en su sitio (`useCampanias.activar` → `activarCampania` → `POST /campanias/{id}/activar`). Error del servidor → `ErrorAlert`. El hook cancela con `AbortController`. |
| `lista` · gestión | `hooks/{useGestion,reglasGestion}.ts`, `components/{FormularioGestion,ResultadoGestion}.tsx` | `reglasGestion`: funciones puras (`rangoSeguimiento`, `fechaSugerida`, `opcionesPermitidas`, `validarResultado`) con las mismas reglas y casos de prueba que el dominio del backend; el servidor siempre decide y su `422`/`409` se muestra con `ErrorAlert`. `useGestion`: sin gestión pide las campañas sugeridas; con `gestionId` pide `GET /gestiones/{id}`; sin doble envío mientras envía. **Parte 1** (`FormularioGestion`, solo al crear): radios con las sugeridas y "No asignar campaña" (marcada si no hay sugerencias), "Fecha de seguimiento" con la sugerida y `min`/`max` del rango, "Responsable (opcional)"; plazo terminado → mensaje y "Crear gestión" deshabilitado. **Parte 2** (`ResultadoGestion`, gestión pendiente): contacto, campaña ofrecida y aceptada, "¿Renovó?", fecha del contacto, observaciones, responsable; las opciones incoherentes se deshabilitan; "Fecha de seguimiento" solo con Renovó = Pendiente. Gestión cerrada → solo lectura, sin botón de guardar. Accesibilidad: radios en `fieldset` con `legend`, errores con `aria-describedby`, foco gestionado por `Modal`. Sin CSS nuevo. |
| `lista` · tabla | `components/TablaLista.tsx`, `pages/ListaPage.tsx`, `api/lista-api.ts` | Las dos tablas añaden "Gestión" ("Sin gestión"/"Pendiente"/"Cerrada"), "Campaña" (nombre, "Sin campaña" o "—") y "Acción": "Gestionar", "Registrar resultado" o "Ver gestión", con `aria-label` que lleva la prioridad ("Gestionar prioridad 3") y **nunca** el nombre del socio. `lista-api.ts` mapea `gestion_id` → `gestionId`. Tras guardar, la página recarga la lista. |

`gestionId`, `gestionEstado` y `campaniaAsignada` son reales desde R-009 (antes `null`); `null` = el ciclo no tiene gestión.

**Gestión sin campaña (R-010, [ADR-009](../../adr/ADR-009-reactivar-campanias-y-gestion-sin-campania-cerrada.md)).** Con "No asignar campaña" marcada, `FormularioGestion` oculta "Fecha de seguimiento" y "Responsable (opcional)" y muestra el aviso "Sin campaña, la gestión queda cerrada y no tendrá seguimiento."; "Crear gestión" queda habilitado aunque el plazo de seguimiento haya terminado (solo para esta opción). `crearGestion` envía `fecha_seguimiento: null` y `responsable: null` (`DatosNuevaGestion.fechaSeguimiento: string | null`). Si la gestión devuelta está cerrada, `useGestion` llama a `onGuardada` y **cierra la ventana** (no pasa a la parte 2); la lista se recarga y la fila muestra "Cerrada", "Sin campaña" y solo "Ver gestión". Abrir una gestión cerrada sin campaña muestra únicamente "No se le asignó campaña" (sin preguntas, campos ni botón de guardar). Con campaña, todo sigue como en R-009.

**Ayuda de la lista (R-010).** `AyudaLista.tsx` añade las secciones "Campañas" y "Gestionar a un socio" a las cuatro existentes; mismo contenido que [06 §7–§8](../../06-como-funciona-la-lista.md), sin términos técnicos (la prueba comprueba que no aparecen `API`, `endpoint`, `null`, nombres de estados ni códigos).

## `shared/ui`

| Componente | Contrato |
|---|---|
| `DataTable<T>` | `columns: {key, header, render?}[]`, `rows`, `getRowKey`, `emptyMessage`, `caption` |
| `RiskBadge` | `nivel: "ALTO" \| "MEDIO" \| "BAJO"` → "Alto"/"Medio"/"Bajo" con los tokens `risk-high`/`risk-medium`/`risk-low` |
| `LoadingIndicator` | `role="status"`, texto accesible configurable |
| `ErrorAlert` | `role="alert"`, `message`, `onRetry?` → botón "Reintentar" |
| `Modal` | `open`, `title`, `onClose`; `role="dialog"`, `aria-modal`, `aria-labelledby`; cierra con `Escape` y "Cerrar"; foco al abrir |

## Estilos

Tokens (colores `ok`/`degraded`, `risk-high`/`risk-medium`/`risk-low`, tipografía, radios) declarados una sola vez en `src/index.css` dentro de `@theme` y consumidos por nombre en clases Tailwind. No hay CSS fuera de `index.css`. Aún no existe `06-estilos-y-design-system.md`.

## MSW (datos simulados)

- `mocks/handlers.ts` reúne con `import.meta.glob("../features/*/api/*.handlers.ts", { eager: true })` los `handlers` exportados por cada feature: un feature nuevo solo añade su archivo.
- Pruebas: `mocks/server.ts` (`setupServer`), iniciado en `src/test/setup.ts` con `onUnhandledRequest: "error"` (una petición sin handler hace fallar el test).
- Navegador: `mocks/browser.ts` (`setupWorker`), importado dinámicamente en `main.tsx` solo si `import.meta.env.DEV && config.apiMocks` (`VITE_API_MOCKS=true`), antes de montar. El build de producción no incluye el worker y la imagen Docker borra `dist/mockServiceWorker.js`.
- Los datos simulados son ficticios (sin cédulas reales). Limitación conocida: el handler de `GET /gestiones` devuelve `[]` sin filtro, mientras el backend responde `400`; solo afecta a los datos simulados. Desde R-009 los handlers de `campanias` y `lista` simulan campañas, sugerencias y gestiones con los mismos códigos (`400`, `404`, `409`, `422`); en el navegador con datos simulados las gestiones creadas no se recuerdan al recargar.

## Desarrollo local

`npm run dev` sirve en `http://localhost:5173` con proxy de Vite `/api` → `http://localhost:8000`. Con `VITE_API_MOCKS=true npm run dev` la API se simula con MSW (sin backend). En Docker, nginx hace el mismo proxy (ver [10-docker.md](../backend/10-docker.md)).

## Pruebas

270 pruebas Vitest al cierre de R-003 (unitarias de `core/http`, `api` de cada feature contra MSW, hooks, layout, router, `shared/ui`, páginas y componentes) y 1 E2E Playwright (`e2e/health.spec.ts` sobre `/salud`, `E2E_BASE_URL`, por defecto `http://localhost:8080`, requiere el stack levantado). Comandos en `Frontend/README.md`.

Al cierre de R-007: 404 pruebas Vitest y 2 E2E. `e2e/carga-lista-excel.spec.ts` recorre Carga (sube una plantilla, vista previa con 3 válidas y 0 errores, confirma, resumen con 3 guardadas) → Lista (genera con los valores por defecto, sin aviso de datos antiguos, aparece algún "SOCIO PRUEBA E2E") → "Descargar Excel" (`.xlsx` no vacío). La plantilla la genera `e2e/plantilla-sintetica.ts` con `exceljs` (**solo `devDependency`**, usada solo en `e2e/`): hoja `Registros`, títulos A..N oficiales, 3 filas MENSUAL con inicio hoy − 20 y vencimiento hoy + 10, cédulas módulo 10 únicas por ejecución. Solo se ejecuta contra el stack aislado (`E2E_BASE_URL=http://localhost:8081`, [10-docker](../backend/10-docker.md)); contra `8080` se salta a propósito para no confirmar cargas ficticias en la base con datos reales. Pendiente: `npm audit` reporta 2 avisos moderados por `uuid` < 11.1.1 vía `exceljs` (solo desarrollo; revisión del día 7).

Al cierre de R-009: 570 pruebas Vitest y 3 E2E. `e2e/campanias-gestion.spec.ts` recorre Campañas (3 de ejemplo, crea una) → Lista (genera, "Gestionar", crea la gestión, registra el resultado hasta "Cerrada", "Ver gestión" sin botón de guardar) → Excel con la columna "Gestión". Crea datos, así que solo corre contra el stack aislado (`8081`) y se salta contra `8080`.

Al cierre de R-010: 597 pruebas Vitest y 3 E2E. `e2e/campanias-gestion.spec.ts` añade: inactivar y volver a activar una campaña (vuelve a sugerirse) y gestionar un socio con "No asignar campaña" (la ventana se cierra; fila "Cerrada" / "Sin campaña" / "Ver gestión"; al abrirla, "No se le asignó campaña").
