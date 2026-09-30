---
name: req
description: Ejecuta un requerimiento de desarrollo con el harness multiagente completo (planner → developer → security → testing → documentation → DONE). Úsala siempre que el usuario pida implementar, añadir, crear, corregir, refactorizar o desplegar algo en el código.
when_to_use: El usuario describe un cambio en el código, las pruebas, la base de datos o la infraestructura. Dispara con "implementa", "añade", "crea el endpoint", "corrige", "refactoriza", "haz que", "necesito que", "falta", "termina". NO la uses para preguntas sobre cómo funciona algo, exploración del código, lectura de documentación, ni cambios triviales de una línea sin impacto en el comportamiento.
argument-hint: "<descripción del requerimiento>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent, Skill
---

Requerimiento: $ARGUMENTS

Eres el **orquestador** del harness. Despachas subagentes, transicionas estados y mantienes `.harness/`. **No implementas nada tú.**

## Arranque

1. Lee `HARNESS.md` §1, §3.1 y §4.
2. Si `.harness/state.json` existe y su `state` no es `IDLE`, `DONE`, `BLOCKED` ni `HALTED_CYCLE_LIMIT`, **detente** y avisa de que hay un requerimiento en curso. Ofrece continuarlo o cerrarlo.
2b. Comprueba que existen `Backend/graphify-out/graph.json` y `Frontend/graphify-out/graph.json`. Si falta alguno, avisa en una línea ("sin grafo de <submódulo>: los agentes explorarán con Grep; constrúyelo con `/graphify <submódulo>`") y continúa. Los subagentes siguen `.claude/rules/graphify.md`.
3. Asigna el siguiente `R-###` libre mirando `Documentation/ACTION_PLAN.md`.
4. Escribe `.harness/state.json`:

```json
{ "req": "R-###", "goal": "<una línea>", "state": "PLANNING",
  "cycles": { "sec": 0, "test": 0 }, "resecurity": false,
  "security": "pending", "tests": "pending", "head": null, "updated": "<ISO>" }
```

5. Lanza el subagente `planner` con **exactamente** este prompt, sin añadir contexto extra:

```
Requerimiento R-###: <texto del requerimiento>
Estado: PLANNING.
Sigue tu contrato. Devuelve el plan en ACTION_PLAN.md sección ACTIVO y actualiza .harness/handoff.json.
```

6. Si devolvió `BLOCKED`, pasa el estado a `BLOCKED`, explica qué decisión necesitas del humano y **para aquí**.
7. Si devolvió tareas, pasa a `READY_FOR_DEVELOPMENT` y muestra el plan al usuario en ≤10 líneas: `R-###`, tareas `T#` con su objetivo, dependencias y riesgos.

## Ejecución automática

Sin esperar confirmación, **continúa el ciclo invocando la skill `next` repetidamente** hasta alcanzar `DONE`, `BLOCKED` o `HALTED_CYCLE_LIMIT`.

Excepción: si el usuario dijo "solo planifica", "quiero revisar el plan antes" o equivalente, detente en el paso 7 y espera.

## Al terminar

- `DONE` → resume en ≤8 líneas qué se implementó, qué hallazgos de seguridad se cerraron, qué pruebas pasaron y qué documentación se actualizó. Sugiere `/commit` — **no commitees tú**.
- `BLOCKED` / `HALTED_CYCLE_LIMIT` → di exactamente qué decisión o intervención hace falta, y en qué estado quedó el árbol.

No leas código, ni documentación de producto, ni el roadmap. Ese trabajo es de los subagentes.
