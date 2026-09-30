# Mtabolic — apoyo a la retención

Aplicación web local que migra el histórico de membresías de Mtabolic, predice el riesgo de no renovación con el modelo del notebook y apoya la gestión de campañas de retención y su seguimiento. Alcance: `Documentation/DEVELOPMENT_GUIDELINES.md`.

Superproyecto con dos submódulos: `Backend/` y `Frontend/`. `Documentation/` es la fuente de verdad compartida.

Stack: **Backend** Python 3.12 + FastAPI (SQLAlchemy 2, Alembic, pytest) · **Base de datos** PostgreSQL 16 · **Frontend** React + TypeScript + Vite (Vitest, Playwright).
Arquitectura **en capas con responsabilidades desacopladas** en ambos lados; la dirección de dependencias es innegociable (detalle en `.claude/rules/backend.md` y `frontend.md`).

## Cómo responder a un mensaje del usuario

**Si el mensaje pide un cambio en el código, las pruebas, la base de datos o la infraestructura** —"implementa", "añade", "crea", "corrige", "refactoriza", "haz que", "falta", "termina"— **no empieces a programar y no pidas que escriba `/req`**: invoca la skill `req` con ese texto como argumento y ejecuta el harness completo hasta `DONE`, `BLOCKED` o `HALTED_CYCLE_LIMIT`.

Responde directamente, sin harness, cuando el mensaje sea:

- una pregunta sobre cómo funciona algo, dónde está algo o por qué se decidió algo;
- exploración, lectura o resumen de código o documentación;
- una operación de git, un comando puntual o una consulta de estado;
- un cambio trivial sin impacto en el comportamiento (una cadena de texto, un typo, formato).

Ante la duda, pregunta en una línea si quiere que lo ejecute con el harness.

`/commit` **solo** lo lanza el usuario. Nunca commitees por iniciativa propia.

## Flujo

`req` → planner → developer ⇄ security-reviewer ⇄ test-engineer → doc-agent → `DONE` → el usuario decide `/commit`.
Estados y contratos de cada agente: `HARNESS.md` (léelo solo cuando orquestes, y solo la sección que toca).
`/status` muestra el estado actual sin cargar nada más. `/next` retoma un requerimiento a medias.

## Contexto mínimo

- Lee **solo** lo que la tarea necesita. Nunca el repositorio entero ni toda la documentación.
- `Documentation/ACTION_PLAN.md` es el board vivo (corto). El detalle por producto está en `Documentation/products/P##-*.md`.
- `Documentation/Plan/**` es material de referencia humano y voluminoso: **no lo abras** sin que el usuario lo pida. (Borra esta línea si no vas a tener esa carpeta.)
- Explora el código con el grafo de su submódulo (`graphify query ... --graph`) antes que con `Grep`/`Glob`; antes de `Read` de un archivo largo, acota con `Grep`.
- Un requerimiento = una sesión. Al terminar, `/clear`.

## Reglas

`.claude/rules/` se carga solo cuando tocas archivos de esa área: `backend.md`, `frontend.md`, `database.md`, `deploy.md`. `git.md` se lee antes de cualquier operación de git. `graphify.md` se lee antes de explorar código o documentación (aplica a todos los agentes).

## Invariantes del proyecto — no se negocian

<!-- PERSONALIZAR: esta es la sección más importante del archivo. Son las reglas que ningún
     agente puede romper, cueste lo que cueste. Máximo 8, cada una verificable en una línea.
     Las de abajo son las que aplican a casi cualquier aplicación multiusuario: consérvalas si
     encajan, bórralas si no, y añade las propias del dominio. -->

- Sin login: el acceso se restringe por IP (CU-00). La regla "propietario desde el token" y el `user_id` de `.claude/rules/database.md` **no aplican**; no se exigen ni se prueban.
- Las escrituras que deben ser consistentes entre sí ocurren en la misma transacción.
- Nada crítico del negocio se borra físicamente: borrado lógico (`deleted_at`) o cambio de estado.
- Los valores exactos (dinero, cantidades, medidas) usan tipo decimal, nunca coma flotante.
- Fecha y hora vía una abstracción de reloj inyectable, nunca la del sistema directamente.
- Ningún secreto en el código, en archivos de configuración versionados ni en logs.
- No se implementa nada fuera del alcance de la versión actual ([`Documentation/DEVELOPMENT_GUIDELINES.md`](../Documentation/DEVELOPMENT_GUIDELINES.md) §Fuera de alcance; excepciones a estas invariantes en §Excepciones).
- El esquema lo migra solo el servicio `migrate`; la única migración de datos al arrancar es CU-03 (`Documentation/adr/ADR-004-migracion-datos-al-arrancar.md`).

## Navegación con graphify — obligatoria

Cada submódulo tiene su grafo: `Backend/graphify-out/graph.json` y `Frontend/graphify-out/graph.json` (Documentation no tiene; usa `Grep`). **Tú y todos los subagentes exploran el código primero con el grafo** para ahorrar tokens; `Grep`/`Glob`/`Read` vienen después y solo sobre lo que el grafo señaló. Protocolo completo: `.claude/rules/graphify.md` (léelo antes de explorar).

- Pregunta sobre el código → `graphify query "<pregunta>" --graph Backend/graphify-out/graph.json --budget 1500` (o la ruta de Frontend; ambos si la pregunta cruza lados) antes de abrir archivos.
- Relación entre dos piezas → `graphify path "A" "B" --graph <grafo>` · qué es un nodo → `graphify explain "X" --graph <grafo>`.
- Sin el `graph.json` del submódulo → avísalo en una línea y sugiere `/graphify Backend` o `/graphify Frontend`; no lo construyas por iniciativa propia.
- Al llegar a `DONE`, el orquestador refresca el grafo del submódulo que cambió con `graphify update Backend` / `graphify update Frontend` (sin LLM).
