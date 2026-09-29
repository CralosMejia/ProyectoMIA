# ADR-004 · Migración de datos del histórico al arrancar; el esquema solo por el servicio `migrate`

- **Estado:** aceptada · 2026-09-28 · R-002 (D1-OP-04)
- **Origen:** D-01 y D-02 de [04 §2](../04-pendientes-para-iniciar-desarrollo.md); CU-03 y RT-14 de [03](../03-casos-de-uso.md)
- **Se aparta de:** `.claude/rules/deploy.md` y `database.md` ("la aplicación nunca ejecuta las migraciones al arrancar"), solo para datos

## Contexto

El histórico 2025–2026 (`Control Gym *.xlsx`) debe cargarse una sola vez y entrenar el modelo v1 antes de que el sistema sea útil. El usuario eligió que ocurra automáticamente en el primer arranque con la base vacía (D-01 b), sin pasos manuales en el PC de Mtabolic. Las reglas del repositorio prohíben que la aplicación migre al arrancar.

## Decisión

- **Esquema:** solo Alembic, en un servicio `migrate` de Docker Compose que termina antes de que arranque el backend. El backend nunca ejecuta `alembic upgrade` ni `create_all`.
- **Datos (única excepción):** al arrancar, si `estado_sistema.migracion_historica = PENDIENTE` y no hay membresías, el backend lanza CU-03 **en segundo plano**, con un bloqueo en la base para que no corra dos veces (`EN_CURSO`).
- **Atomicidad** (D-02): datos del histórico, modelo v1 e intento `INICIAL` en una sola transacción. Si algo falla, se revierte todo, el estado vuelve a `PENDIENTE` y se reintenta en el siguiente arranque.
- Los libros llegan por un volumen de solo lectura (`HISTORICO_DIR`); no entran en las imágenes ni en git.
- Ninguna otra migración de datos se ejecuta al arrancar.

## Alternativas descartadas

- **Comando manual de migración (D-01 a):** descartado por el usuario; añade un paso de operación en el PC.
- **Migración de datos dentro del servicio `migrate` o en una revisión de Alembic:** mezcla esquema y datos y obliga a instalar pandas/scikit-learn en el servicio de migraciones.
- **Migración en primer plano bloqueando el arranque:** retrasa `/health`; queda solo como plan de contingencia (04 §6, riesgos).

## Consecuencias

- `/health` responde mientras la migración corre; las funciones que dependen del modelo no están disponibles hasta `COMPLETADA`.
- Transacción larga en el primer arranque; aceptable con un solo PC y una sola instancia.
- Las pruebas de CU-03 usan libros sintéticos; las cifras del notebook se verifican solo en local.
