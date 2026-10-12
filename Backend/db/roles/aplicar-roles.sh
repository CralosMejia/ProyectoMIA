#!/bin/sh
# Crea o actualiza el rol de la aplicacion (S23) y le aplica los permisos de permisos.sql
# sobre POSTGRES_DB. Lo ejecuta el servicio "db-roles" de compose en cada "up", antes de
# "migrate". Idempotente: dos ejecuciones seguidas terminan ambas en 0 con el mismo estado.
#
# Variables de entorno:
#   POSTGRES_USER       rol propietario (el de las migraciones). Obligatoria.
#   POSTGRES_DB         base a la que se aplican los permisos. Obligatoria.
#   PGHOST, PGPASSWORD  conexion del propietario (las lee psql; nunca se imprimen).
#   APP_DB_USER         rol de la aplicacion (por defecto mtabolic_app).
#   APP_DB_PASSWORD     su contrasena. La lee psql con \getenv: no pasa por la linea de
#                       comandos ni se escribe en ningun archivo o log.
#   APP_DB_ROL_OPCIONAL si vale 1 y APP_DB_PASSWORD esta vacia, avisa y termina en 0 sin
#                       cambiar nada (transicion: el backend sigue con el rol propietario).
#
# Salida: solo "Roles aplicados" (o el aviso/error, que nombra la variable, nunca su valor).
set -eu

DIR_ROLES=$(cd "$(dirname "$0")" && pwd)

SALTO='
'

error() {
  echo "ERROR: $*" >&2
  exit 1
}

# grep valida linea a linea: un valor con salto de linea pasaria si una de sus lineas cumple
# el patron, asi que antes se rechaza cualquier salto de linea.
nombre_valido() {
  case "$1" in
    *"$SALTO"*) return 1 ;;
  esac
  printf '%s' "$1" | grep -Eq '^[a-z_][a-z0-9_]{0,62}$'
}

POSTGRES_USER=${POSTGRES_USER:-}
POSTGRES_DB=${POSTGRES_DB:-}
APP_DB_USER=${APP_DB_USER:-mtabolic_app}
APP_DB_PASSWORD=${APP_DB_PASSWORD:-}

[ -n "$POSTGRES_USER" ] || error "POSTGRES_USER esta vacia."
[ -n "$POSTGRES_DB" ] || error "POSTGRES_DB esta vacia."

if [ -z "$APP_DB_PASSWORD" ]; then
  if [ "${APP_DB_ROL_OPCIONAL:-0}" = "1" ]; then
    echo "AVISO: APP_DB_PASSWORD no esta definida: no se crea el rol de la aplicacion y el backend sigue conectado con el rol propietario (S23 pendiente). Defina APP_DB_USER, APP_DB_PASSWORD y MIGRATE_DATABASE_URL en el .env y cambie DATABASE_URL al rol de la aplicacion." >&2
    exit 0
  fi
  error "APP_DB_PASSWORD esta vacia."
fi

nombre_valido "$APP_DB_USER" || error "APP_DB_USER no es un nombre de rol valido (minusculas, digitos y _, maximo 63, sin empezar por digito)."
nombre_valido "$POSTGRES_USER" || error "POSTGRES_USER no es un nombre de rol valido."
[ "$APP_DB_USER" != "$POSTGRES_USER" ] || error "APP_DB_USER debe ser distinto de POSTGRES_USER."
case "$APP_DB_USER" in
  postgres | pg_*) error "APP_DB_USER no puede ser un rol reservado de PostgreSQL." ;;
esac
[ -f "$DIR_ROLES/permisos.sql" ] || error "no se encontro permisos.sql junto a este script."

export APP_DB_PASSWORD

# Todo en una transaccion (-1). VERBOSITY terse: un error no muestra el texto de la sentencia
# (que podria contener la contrasena). Si el propietario es superusuario, la sesion tampoco
# deja la sentencia fallida en el log del servidor (log_min_error_statement = panic) ni
# registra las sentencias aunque alguien active log_statement (log_statement = none).
psql -X -q -1 -v ON_ERROR_STOP=1 -v VERBOSITY=terse -v SHOW_CONTEXT=never \
  -d "$POSTGRES_DB" \
  -v app_user="$APP_DB_USER" -v propietario="$POSTGRES_USER" \
  -f - -f "$DIR_ROLES/permisos.sql" >/dev/null <<'SQL'
\set ON_ERROR_STOP on
SET client_min_messages = warning;
SELECT set_config('log_min_error_statement', 'panic', true)
WHERE (SELECT rolsuper FROM pg_roles WHERE rolname = current_user);
SELECT set_config('log_statement', 'none', true)
WHERE (SELECT rolsuper FROM pg_roles WHERE rolname = current_user);
\getenv app_pass APP_DB_PASSWORD
SELECT format('CREATE ROLE %I LOGIN', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user') \gexec
ALTER ROLE :"app_user" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
    INHERIT PASSWORD :'app_pass';
\unset app_pass
SQL

echo "Roles aplicados"
