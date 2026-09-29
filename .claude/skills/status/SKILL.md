---
name: status
description: Muestra el estado actual del harness sin cargar contexto adicional.
disable-model-invocation: true
allowed-tools: Read
---

Lee **solo** `.harness/state.json`, `.harness/handoff.json` y, si existen, `.harness/security.md` y `.harness/tests.md`.

Si no existe `.harness/state.json`, di que no hay ningún requerimiento en curso y sugiere `/req`.

Imprime una tabla compacta y nada más:

```
Requerimiento  R-### — <goal>
Estado         <state>          Ciclos  sec <n>/3 · test <n>/3
Tarea          T# — <goal de la tarea>
Archivos       <n> rutas
Seguridad      clean | blocked (<n> critical, <n> high)
Pruebas        pass | fail (<n> fallos) | pending
Abiertos       S1 high · T2 — <una línea cada uno>
Siguiente      /next  →  <agente>
```

No abras `ACTION_PLAN.md`, ni `HARNESS.md`, ni código, ni documentación. No hagas análisis. Este comando debe costar menos de 1000 tokens.
