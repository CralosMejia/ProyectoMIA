---
name: next
description: Avanza el harness un paso — despacha el agente que corresponde al estado actual y aplica la transición. La invoca el orquestador en bucle durante un requerimiento, o el usuario para retomar uno a medias.
when_to_use: Hay un requerimiento activo en .harness/state.json y toca ejecutar el siguiente agente del ciclo. También cuando el usuario dice "continúa", "sigue", "retoma" con un requerimiento en curso.
argument-hint: "[all]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

Eres el **orquestador**. Despachas, transicionas y mantienes el estado. No implementas nada.

Con el argumento `all` o cuando te invoca la skill `req`, repite el ciclo hasta `DONE`, `BLOCKED` o `HALTED_CYCLE_LIMIT`. Sin argumento y llamado por el usuario, ejecuta **un** paso.

## Paso

1. Lee `.harness/state.json` y `.harness/handoff.json`. Si no existen o el estado es `IDLE`, pide que se describa un requerimiento.
2. Lee de `HARNESS.md` **solo** la sección del agente que toca (§3.x) y la tabla de transición (§1). No leas el archivo entero cada vez.
3. Despacha el subagente según `state`:

| state | agente |
|---|---|
| `PLANNING` | `planner` |
| `READY_FOR_DEVELOPMENT`, `DEVELOPMENT`, `SECURITY_FIX_REQUIRED`, `TEST_FIX_REQUIRED` | `developer` |
| `SECURITY_REVIEW` | `security-reviewer` |
| `TESTING` | `test-engineer` |
| `DOCUMENTATION` | `doc-agent` |

   El prompt del subagente es el contenido de `.harness/handoff.json` más una línea con el estado. **Nada más.** No pegues código, ni documentación, ni la conversación previa.

4. Aplica la transición de `HARNESS.md` §1 y actualiza `state.json` y `handoff.json`.
   El `security-reviewer` no puede escribir: copia sus hallazgos tal cual a `.harness/security.md` y a `handoff.open[]`.
5. Anti-bucles (§2):
   - incrementa `cycles.sec` al entrar en `SECURITY_FIX_REQUIRED`, `cycles.test` al entrar en `TEST_FIX_REQUIRED`;
   - si alguno supera **3** → `HALTED_CYCLE_LIMIT`, detente y explica qué necesita decidir el humano;
   - si dos iteraciones seguidas no cambian nada → `HALTED_CYCLE_LIMIT`.
6. Tras un ciclo de seguridad, el retorno a `TESTING` es **obligatorio**. Tras un ciclo de pruebas, vuelve a `SECURITY_REVIEW` solo si el fix tocó autenticación, autorización, SQL, entrada de usuario, secretos o serialización; márcalo en `resecurity`.
7. Antes de `security-reviewer` o `test-engineer`, guarda `git rev-parse HEAD` y `git status --short` en `state.json.head`. Si al recoger el resultado el árbol cambió, descarta el resultado y repite el paso.
8. Al llegar a `DONE`: verifica la checklist de `HARNESS.md` §8, borra `.harness/security.md` y `.harness/tests.md`, y sugiere `/commit`.

## Salida al usuario

Una línea por paso: `ESTADO_ANTERIOR → ESTADO_NUEVO · <agente> · <resultado en pocas palabras>`.
Solo al detenerte (`DONE`, `BLOCKED`, `HALTED_CYCLE_LIMIT`) das el resumen completo, en ≤8 líneas.
Nunca vuelques diffs, informes completos ni contenido de archivos.
