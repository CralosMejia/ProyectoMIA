-- Permisos del rol de la aplicacion sobre la base ACTUAL (S23, decision (a) de R-013).
--
-- Variables de psql obligatorias (las pasa quien lo ejecuta con -v):
--   app_user     rol de la aplicacion (LOGIN, sin superusuario; debe existir)
--   propietario  rol que crea las tablas (el de las migraciones, POSTGRES_USER)
--
-- Lo ejecutan Backend/db/roles/aplicar-roles.sh (servicio db-roles de compose, sobre
-- POSTGRES_DB) y scripts/restaurar-base.sh (sobre la base restaurada). Es idempotente:
-- puede ejecutarse cuantas veces se quiera con el mismo resultado.
--
-- Resultado: CONNECT a la base; USAGE en "public" sin CREATE (no ejecuta DDL);
-- SELECT, INSERT, UPDATE en las tablas y USAGE, SELECT en las secuencias; sin DELETE ni
-- TRUNCATE (nada del negocio se borra fisicamente). alembic_version es solo lectura.
-- Las tablas que el propietario cree despues (migraciones futuras) heredan los mismos
-- permisos por los privilegios por defecto.

\set ON_ERROR_STOP on
SET client_min_messages = warning;

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user') \gexec

-- Esquema: uso sin creacion (PostgreSQL 15+ ya no da CREATE a PUBLIC; se fija igualmente).
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_user";

-- Tablas existentes: se parte de cero para retirar cualquier permiso previo (DELETE, TRUNCATE...).
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :"app_user";
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO :"app_user";
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM :"app_user";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"app_user";

-- La version del esquema solo la cambia "migrate" (rol propietario).
SELECT format('REVOKE INSERT, UPDATE ON TABLE public.alembic_version FROM %I', :'app_user')
WHERE to_regclass('public.alembic_version') IS NOT NULL \gexec

-- Tablas y secuencias futuras creadas por el propietario.
ALTER DEFAULT PRIVILEGES FOR ROLE :"propietario" IN SCHEMA public
    REVOKE ALL ON TABLES FROM :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"propietario" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"propietario" IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM :"app_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"propietario" IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";
