---
paths:
  - ".gitmodules"
  - "**/.gitignore"
  - "**/.gitattributes"
---

# Reglas — Git

Esta regla se carga bajo demanda. El developer y el orquestador la **leen antes de cualquier operación de git**.

## Topología del repositorio

La raíz es un superproyecto. `Backend/` y `Frontend/` son **submódulos** con su propio historial.
(Si prefieres monorepo, borra esta sección y la del puntero: todo lo demás sigue aplicando.)

- Se commitea **dentro del submódulo primero**, luego el puntero actualizado en el superproyecto.
- Un requerimiento que toca ambos lados produce hasta 3 commits: `Backend`, `Frontend`, superproyecto (+`Documentation/`).
- Nunca se commitea el puntero de un submódulo apuntando a un commit que no está pusheado.

## Ramas

- Todo el desarrollo ocurre en **`dev`**. Nunca directamente sobre `main`.
- `main` está protegida: solo versiones estables desplegadas o listas para desplegar.
- El único camino a `main` es un merge o PR desde `dev`, y solo cuando se va a producción.
- Sin push directo a `main`.

## Cuándo se commitea

Solo en un **hito lógico y estable**. Un commit exige, todo a la vez:

- la tarea `T#` completa (no a medias);
- build correcto;
- suite de pruebas del área en verde;
- sin hallazgos `critical`/`high` abiertos;
- estado del harness en `DOCUMENTATION` o `DONE`.

**Nunca se commitea con pruebas rotas o build fallido.** El hook `.claude/hooks/guard-commit.mjs` bloquea el intento.

## Formato del mensaje

```
tipo(scope): descripción en imperativo (R-###/T#)
```

- Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
- El Task ID entre paréntesis es **obligatorio** cuando el commit viene del harness.
- Un commit = una tarea. Nada de commits que mezclan tareas sin relación.

## Concurrencia entre agentes

- **Solo el orquestador ejecuta comandos de git que escriben.** Ningún subagente hace `commit`, `push`, `checkout`, `reset`, `stash` ni `rebase`.
- Antes de lanzar agentes en paralelo, el orquestador registra `git rev-parse HEAD` y `git status --short`. Si el árbol cambió al recoger los resultados, se descartan y se repiten.
- Dos tareas en paralelo solo si sus conjuntos de archivos son disjuntos.
- Antes de empezar una tarea nueva: `git status` limpio o cambios explicados.

## Secretos

- `.env` **nunca** se commitea; `.env.example` sí, con valores marcador.
- Antes de commitear: revisar el diff en busca de claves, contraseñas, cadenas de conexión y secretos de firma.
- Si un secreto llegó al historial: rotarlo primero, limpiar el historial después, y anotarlo.

## Etiquetas y merge

- Etiqueta al cerrar cada producto demostrable: `v0.1.0-p01`, `v1.0.0`.
- **Listo para merge a `main`** cuando: todas las tareas del producto `P##` están en `DONE`, CI en verde, migraciones probadas sobre base con datos, y el producto es demostrable de punta a punta.

## Prohibido

- `git push --force` sobre `dev` o `main`.
- `git commit --no-verify` (salta el guard).
- Commits automáticos "de guardado" al terminar cada archivo.
- Commitear artefactos: `bin/`, `obj/`, `dist/`, `node_modules/`, `coverage/`, `.harness/`.
