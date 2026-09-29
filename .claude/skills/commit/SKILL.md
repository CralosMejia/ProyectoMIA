---
name: commit
description: Commit del trabajo del requerimiento actual, con las precondiciones del harness verificadas.
disable-model-invocation: true
allowed-tools: Read, Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git rev-parse:*)
---

Commit gobernado por `.claude/rules/git.md`. Léelo antes de ejecutar.

## Precondiciones — verifícalas y aborta si alguna falla

1. `.harness/state.json` en `DOCUMENTATION` o `DONE`.
2. `security != "blocked"`.
3. `tests == "pass"`.
4. `git status` no muestra cambios sin explicar en la tarea.

Si alguna falla, no commitees: di cuál y qué hace falta.

## Procedimiento

1. Revisa `git diff` **buscando secretos**: claves, contraseñas, cadenas de conexión, secretos de firma, `.env`. Si aparece alguno, aborta y avisa.
2. Commitea **primero dentro de cada submódulo** afectado (`Backend/`, `Frontend/`), luego el superproyecto con el puntero actualizado y `Documentation/`.
   (Si el proyecto es un monorepo, omite este paso: un solo commit.)
3. Mensaje: `tipo(scope): descripción (R-###/T#)`. Un commit por tarea.
4. Rama `dev`. Si la rama actual es `main`, aborta.
5. **No** hagas `push` salvo que el usuario lo pida explícitamente.
6. Muestra los hashes creados, uno por línea.

Nunca uses `--no-verify` ni `--force`.
