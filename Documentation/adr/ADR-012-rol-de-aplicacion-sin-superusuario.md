# ADR-012 · La aplicación se conecta con un rol sin superusuario; las migraciones con el propietario

- **Estado:** aceptada · 2026-10-01 · R-013 (día 7)
- **Origen:** hallazgo S23 (abierto desde R-002) · `.claude/rules/deploy.md` §Base de datos en producción · decisiones (a), (b) de R-013

## Contexto

Hasta R-012 el backend y `migrate` usaban el mismo rol, `POSTGRES_USER`, que en la imagen oficial de PostgreSQL es superusuario del clúster. Una inyección o un error del código tendría permisos de DDL, de borrado y de administración. La regla de despliegue pide un rol de aplicación sin superusuario ni `CREATE` sobre el esquema, y otro distinto con DDL para las migraciones. El stack principal ya tiene datos reales: la solución debe aplicarse sin recrear el volumen.

## Decisión

1. **Rol de la aplicación** `APP_DB_USER` (por defecto `mtabolic_app`): `LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`; `CONNECT`; `USAGE` en `public` sin `CREATE`; `SELECT, INSERT, UPDATE` en tablas y `USAGE, SELECT` en secuencias; **sin `DELETE` ni `TRUNCATE`** (la base refuerza "nada del negocio se borra físicamente"); `alembic_version` solo lectura. El backend lo usa por `DATABASE_URL`.
2. **Migraciones con el propietario** por `MIGRATE_DATABASE_URL` (servicio `migrate`). Pruebas de integración y scripts de respaldo/restauración también con el propietario.
3. **Servicio `db-roles`** de un solo uso (misma imagen `postgres:16.15-alpine`) antes de `migrate` en cada `up`: crea o actualiza el rol, aplica `Backend/db/roles/permisos.sql` y fija `ALTER DEFAULT PRIVILEGES FOR ROLE <propietario>` para tablas futuras. Idempotente; vale para volúmenes nuevos y existentes. La contraseña llega como variable de `psql`, con `log_statement` desactivado en esa sesión; nunca en archivos ni logs.
4. **Transición:** sin `APP_DB_PASSWORD`, `db-roles` solo avisa y todo sigue con el propietario. Activado en el stack principal en R-013 tras un respaldo, con reversión no destructiva (volver a la `DATABASE_URL` anterior).

## Alternativas descartadas

- **Crear el rol en un script de `docker-entrypoint-initdb.d`:** solo corre con el volumen vacío; no sirve para el principal.
- **Crear el rol en una migración de Alembic:** mezcla administración del clúster con el esquema y pondría una contraseña al alcance de `migrate`.
- **Dar `DELETE` al rol de la app:** el código no lo necesita (verificado: `app/` sin `DELETE`/`TRUNCATE`/DDL).
- **Convertir al propietario en no superusuario:** exige otro superusuario de arranque distinto del de la imagen oficial; diferido.

## Consecuencias

- Un error o una inyección en el backend ya no puede crear, alterar ni borrar tablas o filas.
- Una migración futura que cree tablas hereda los permisos; si necesitara `DELETE` para la app, exige cambiar `permisos.sql` y este ADR.
- `.env` gana tres variables (`APP_DB_USER`, `APP_DB_PASSWORD`, `MIGRATE_DATABASE_URL`) y `DATABASE_URL` cambia de rol ([10-docker](../docs/backend/10-docker.md), [Backend/README §3.1](../../Backend/README.md)).
- **Residual:** el propietario sigue siendo superusuario del clúster.
