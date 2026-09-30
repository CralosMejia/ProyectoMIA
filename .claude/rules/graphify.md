# Navegación con graphify — protocolo obligatorio

Cada submódulo tiene su propio grafo de conocimiento. **Consultar el grafo es el primer paso de toda exploración de código**: cuesta una fracción de los tokens de abrir archivos a mano y devuelve relaciones (quién llama a quién, qué capa depende de cuál) que `Grep` no ve.

| Área | Grafo | Resumen |
|---|---|---|
| Backend | `Backend/graphify-out/graph.json` | `Backend/graphify-out/GRAPH_REPORT.md` |
| Frontend | `Frontend/graphify-out/graph.json` | `Frontend/graphify-out/GRAPH_REPORT.md` |
| Documentation | sin grafo — usa `Grep`/`Glob` | — |

Los comandos se ejecutan desde la raíz del superproyecto y **siempre** llevan `--graph` apuntando al grafo del área (sin él, graphify busca `graphify-out/` en la raíz, que no existe). Si la tarea toca ambos lados, consulta los dos grafos por separado.

## Orden de exploración

1. **Grafo primero.** Antes de cualquier `Grep`/`Glob`/`Read` exploratorio (ejemplo con Backend; para Frontend cambia la ruta):
   - `graphify query "<pregunta en lenguaje natural>" --graph Backend/graphify-out/graph.json --budget 1500` — contexto amplio (BFS).
   - `graphify query "<pregunta>" --dfs --graph Backend/graphify-out/graph.json --budget 1500` — seguir un flujo concreto (p. ej. router → caso de uso → repositorio).
   - `graphify path "<NodoA>" "<NodoB>" --graph Backend/graphify-out/graph.json` — cómo se conectan dos piezas (impacto de un cambio, dependencias entre capas).
   - `graphify explain "<Nodo>" --graph Backend/graphify-out/graph.json` — qué es un módulo/clase y sus vecinos, sin abrir el archivo.
2. **Luego `Grep` acotado** solo sobre los archivos que el grafo señaló (usa el `source_location` que devuelve).
3. **`Read` al final**, solo del rango de líneas necesario.

Usa siempre `--budget` (1500 por defecto; súbelo solo si la respuesta quedó truncada y la necesitas).

## Agentes sin `Bash`

`planner`, `doc-agent` y `doc-curator` no ejecutan comandos: leen el `GRAPH_REPORT.md` del submódulo afectado (resumen por comunidades y nodos centrales) y, si hace falta un detalle, hacen `Grep` sobre su `graph.json` por el nombre del nodo.

## Cuándo NO usar el grafo

- Ya conoces la ruta exacta y la línea (viene en `files` del handoff o en un hallazgo): ve directo al archivo.
- Verificar el contenido **actual** de un archivo que acabas de editar: el grafo puede ir un paso atrás; la fuente de verdad es el archivo.
- Diffs de seguridad: el alcance es `git diff`; el grafo solo sirve para ver a quién afecta lo cambiado.
- Documentación: no tiene grafo; busca con `Grep`/`Glob`.

## Mantenimiento

- Si el `graph.json` de un submódulo **no existe**, dilo en una línea (el usuario lo construye con `/graphify Backend` o `/graphify Frontend`) y continúa con `Grep`/`Glob`. No lo construyas tú: la construcción completa consume modelo.
- Tras cambios de código, el grafo se refresca con `graphify update Backend` y/o `graphify update Frontend` (solo AST, sin LLM), según el submódulo que cambió. Lo lanza el orquestador al llegar a `DONE`; los subagentes no lo ejecutan.
- Si el grafo contradice el código, manda el código; anótalo en la salida para refrescar el grafo.
- `graphify-out/` está en el `.gitignore` de cada submódulo: el grafo es local y no se commitea.
