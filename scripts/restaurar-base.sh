#!/usr/bin/env bash
# Restaura un respaldo de scripts/respaldar-base.sh en una base NUEVA del stack (D7-BD-01).
#
# Uso:
#   scripts/restaurar-base.sh <archivo.dump> [-p proyecto] [--base nombre]
#     -p      proyectofinal (.env, por defecto), mtabolic-e2e (.env.e2e) o mtabolic-limpia (.env.limpia)
#     --base  nombre de la base nueva (por defecto app_db_restaurada_AAAAMMDDHHMMSS);
#             debe cumplir ^[a-z_][a-z0-9_]{0,62}$, no existir y ser distinto de POSTGRES_DB.
#
# Pasos: createdb de la base nueva, pg_restore --no-owner --no-privileges --exit-on-error,
# permisos del rol de la aplicacion (Backend/db/roles/permisos.sql, si el rol existe) y
# comparacion de los 9 conteos con el archivo .conteos del respaldo: "Conteos iguales" y
# codigo 0, o la lista de diferencias y codigo 1.
#
# Seguridad:
# - Lista blanca de proyectos; nombre de base validado ANTES de crear nada.
# - Nunca renombra, sobrescribe ni borra bases: la base en uso no cambia. Poner en uso la
#   restaurada es un paso manual (Backend/README.md, seccion 5).
# - Las credenciales se expanden DENTRO del contenedor db; no se imprime nada del .env.
set -euo pipefail

readonly TABLAS=(socios membresias cargas modelos intentos_reentrenamiento listas_priorizadas
  predicciones campanias gestiones_retencion)
readonly PATRON_NOMBRE='^[a-z_][a-z0-9_]{0,62}$'

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ

error() {
  echo "ERROR: $*" >&2
  exit 1
}

uso() {
  echo "Uso: $0 <archivo.dump> [-p proyectofinal|mtabolic-e2e|mtabolic-limpia] [--base nombre]"
}

# --- Argumentos -------------------------------------------------------------------------
PROYECTO="proyectofinal"
DUMP=""
BASE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -p)
      [ "$#" -ge 2 ] || error "falta el nombre del proyecto tras -p."
      PROYECTO="$2"
      shift 2
      ;;
    --base)
      [ "$#" -ge 2 ] || error "falta el nombre de la base tras --base."
      BASE="$2"
      shift 2
      ;;
    -h | --ayuda)
      uso
      exit 0
      ;;
    -*) error "argumento no reconocido: $1 ($(uso))" ;;
    *)
      [ -z "$DUMP" ] || error "solo se admite un archivo de respaldo."
      DUMP="$1"
      shift
      ;;
  esac
done

case "$PROYECTO" in
  proyectofinal) ENV_NOMBRE=".env" ;;
  mtabolic-e2e) ENV_NOMBRE=".env.e2e" ;;
  mtabolic-limpia) ENV_NOMBRE=".env.limpia" ;;
  *) error "proyecto no permitido: solo proyectofinal, mtabolic-e2e o mtabolic-limpia." ;;
esac
readonly PROYECTO ENV_NOMBRE

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
[ -n "$DUMP" ] || error "falta el archivo de respaldo. $(uso)"
case "$DUMP" in *.dump) ;; *) error "el respaldo debe ser un archivo .dump de scripts/respaldar-base.sh." ;; esac
[ -f "$DUMP" ] && [ -s "$DUMP" ] || error "no existe el archivo de respaldo o esta vacio: $DUMP"
readonly CONTEOS_ESPERADOS_ARCHIVO="${DUMP%.dump}.conteos"
[ -f "$CONTEOS_ESPERADOS_ARCHIVO" ] || error "no existe el archivo de conteos del respaldo: $CONTEOS_ESPERADOS_ARCHIVO"

ESPERADOS="$(tr -d '\r' <"$CONTEOS_ESPERADOS_ARCHIVO" | sed '/^[[:space:]]*$/d')"
i=0
while IFS= read -r linea; do
  [ "$i" -lt "${#TABLAS[@]}" ] || error "el archivo de conteos tiene mas lineas de las esperadas."
  [[ $linea =~ ^${TABLAS[$i]}=[0-9]+$ ]] ||
    error "el archivo de conteos no tiene el formato esperado (linea $((i + 1)): ${TABLAS[$i]}=n)."
  i=$((i + 1))
done <<<"$ESPERADOS"
[ "$i" -eq "${#TABLAS[@]}" ] || error "el archivo de conteos debe tener ${#TABLAS[@]} lineas tabla=n."
readonly ESPERADOS

if [ -z "$BASE" ]; then
  BASE="app_db_restaurada_$(date +%Y%m%d%H%M%S)"
fi
# [[ =~ ]] valida la cadena completa: un valor con salto de linea no pasa (con grep bastaba
# con que una de sus lineas cumpliera el patron).
[[ $BASE =~ $PATRON_NOMBRE ]] ||
  error "nombre de base no valido: debe cumplir $PATRON_NOMBRE."
case "$BASE" in
  postgres | template0 | template1) error "nombre de base reservado por PostgreSQL." ;;
esac
readonly BASE

[ -f "$RAIZ/compose.yaml" ] || error "no se encontro compose.yaml en la raiz del proyecto ($RAIZ)."
[ -f "$RAIZ/$ENV_NOMBRE" ] || error "no se encontro el archivo $ENV_NOMBRE en la raiz del proyecto ($RAIZ)."
[ -f "$RAIZ/Backend/db/roles/permisos.sql" ] || error "no se encontro Backend/db/roles/permisos.sql."
command -v docker >/dev/null 2>&1 || error "no se encontro el comando docker. Instale o inicie Docker Desktop."

# Rol de la aplicacion: la variable de la shell gana; si no, la linea APP_DB_USER del .env;
# si no, mtabolic_app. Solo se lee esa linea (no es secreta) y no se imprime nada del .env.
APP_USER="${APP_DB_USER:-}"
if [ -z "$APP_USER" ]; then
  APP_USER="$(grep -E '^[[:space:]]*APP_DB_USER[[:space:]]*=' "$RAIZ/$ENV_NOMBRE" | tail -n 1 | cut -d= -f2- | tr -d "\r\"' \t" || true)"
fi
APP_USER="${APP_USER:-mtabolic_app}"
[[ $APP_USER =~ $PATRON_NOMBRE ]] || error "APP_DB_USER no es un nombre de rol valido."
readonly APP_USER

# El respaldo se lee con una redireccion de bash (binario intacto) antes de cambiar de
# directorio; el resto usa rutas relativas a la raiz (sin conversion de rutas de MSYS).
exec 3<"$DUMP"
cd "$RAIZ"
export MSYS_NO_PATHCONV=1

compose() {
  docker compose -p "$PROYECTO" -f compose.yaml --env-file "$ENV_NOMBRE" "$@"
}

# psql como propietario sobre la base $1 con la consulta $2 (sin datos del .env en el host).
psql_en() {
  compose exec -T db sh -c 'psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$1" -c "$2"' sh "$1" "$2" | tr -d '\r'
}

# Cuenta las filas de pg_catalog.$1 cuya columna $2 vale $3 ($1 y $2 son literales de este
# script). El valor llega a psql como variable (-v valor=...) y se cita con :'valor': nunca
# se interpola en el texto SQL.
contar_en_catalogo() {
  printf "SELECT count(*) FROM pg_catalog.%s WHERE %s = :'valor';\n" "$1" "$2" |
    compose exec -T db sh -c 'psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -v valor="$1" -f -' sh "$3" |
    tr -d '\r'
}

readonly TMP_CONTENEDOR="/tmp/restaurar-${BASE}.dump"
limpiar_contenedor() {
  compose exec -T db rm -f "$TMP_CONTENEDOR" >/dev/null 2>&1 || true
}

echo "=== Restauracion en una base NUEVA (proyecto $PROYECTO, base $BASE) ==="
echo "[1/5] Comprobando el nombre de la base..."
base_en_uso="$(compose exec -T db sh -c 'printf %s "$POSTGRES_DB"' | tr -d '\r')" ||
  error "no se pudo consultar el contenedor db del proyecto $PROYECTO (esta en marcha?)."
[ -n "$base_en_uso" ] || error "no se pudo leer POSTGRES_DB del contenedor db."
[ "$BASE" != "$base_en_uso" ] || error "la base nueva no puede llamarse igual que la base en uso (POSTGRES_DB)."
existe="$(contar_en_catalogo pg_database datname "$BASE")" ||
  error "no se pudo comprobar si la base existe."
[ "$existe" = "0" ] || error "ya existe una base con ese nombre; elija otro con --base."

echo "[2/5] Creando la base nueva..."
compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$1"' sh "$BASE" ||
  error "no se pudo crear la base nueva."

trap limpiar_contenedor EXIT
echo "[3/5] Restaurando el respaldo (pg_restore --no-owner --no-privileges --exit-on-error)..."
compose exec -T db sh -c 'cat >"$1"' sh "$TMP_CONTENEDOR" <&3 ||
  error "no se pudo copiar el respaldo al contenedor db. La base $BASE quedo creada y vacia."
exec 3<&-
compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --no-owner --no-privileges --exit-on-error "$2"' sh "$BASE" "$TMP_CONTENEDOR" ||
  error "fallo pg_restore. La base $BASE quedo incompleta: no la ponga en uso (este script nunca borra bases)."
limpiar_contenedor
trap - EXIT

echo "[4/5] Permisos del rol de la aplicacion..."
rol="$(contar_en_catalogo pg_roles rolname "$APP_USER")" ||
  error "no se pudo comprobar el rol de la aplicacion."
if [ "$rol" = "1" ]; then
  compose exec -T db sh -c 'psql -X -q -1 -v ON_ERROR_STOP=1 -v VERBOSITY=terse -U "$POSTGRES_USER" -d "$1" -v app_user="$2" -v propietario="$POSTGRES_USER" -f -' \
    sh "$BASE" "$APP_USER" <Backend/db/roles/permisos.sql >/dev/null ||
    error "no se pudieron aplicar los permisos del rol de la aplicacion a $BASE."
  echo "  Permisos aplicados."
else
  echo "  AVISO: el rol de la aplicacion no existe todavia (S23 sin activar); se omiten sus permisos."
fi

echo "[5/5] Comparando conteos con el respaldo..."
CONSULTA=""
for t in "${TABLAS[@]}"; do
  CONSULTA="${CONSULTA:+$CONSULTA, }(SELECT count(*) FROM $t)"
done
fila="$(psql_en "$BASE" "SELECT $CONSULTA" | tail -n 1)" || error "no se pudieron leer los conteos de $BASE."
IFS='|' read -r -a valores <<<"$fila"
[ "${#valores[@]}" -eq "${#TABLAS[@]}" ] || error "respuesta inesperada al leer los conteos de $BASE."
obtenidos=""
for i in "${!TABLAS[@]}"; do
  obtenidos="${obtenidos}${TABLAS[$i]}=${valores[$i]}"$'\n'
done
obtenidos="${obtenidos%$'\n'}"

if [ "$obtenidos" = "$ESPERADOS" ]; then
  echo "Conteos iguales"
  printf '%s\n' "$obtenidos" | sed 's/^/  /'
  echo "Base restaurada: $BASE (la base en uso no se ha modificado)."
  exit 0
fi

echo "Conteos distintos (tabla: respaldo -> restaurada):" >&2
paste -d' ' <(printf '%s\n' "$ESPERADOS") <(printf '%s\n' "$obtenidos") |
  while read -r esperado obtenido; do
    [ "$esperado" = "$obtenido" ] || echo "  ${esperado%%=*}: ${esperado#*=} -> ${obtenido#*=}" >&2
  done
echo "La base $BASE quedo creada pero no coincide con el respaldo: no la ponga en uso." >&2
exit 1
