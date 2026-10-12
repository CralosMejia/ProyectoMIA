#!/usr/bin/env bash
# Respaldo de SOLO LECTURA de la base de un stack de compose (D7-BD-01).
#
# Genera en respaldos/ (carpeta no versionada: contiene datos personales de socios):
#   <proyecto>-AAAAMMDD-HHMMSS.dump     pg_dump -Fc de POSTGRES_DB
#   <proyecto>-AAAAMMDD-HHMMSS.conteos  9 lineas tabla=n con los conteos de la base respaldada
#
# Uso:
#   scripts/respaldar-base.sh                    stack principal (proyectofinal, .env)
#   scripts/respaldar-base.sh -p mtabolic-e2e    stack e2e (.env.e2e)
#   scripts/respaldar-base.sh -p mtabolic-limpia stack de instalacion limpia (.env.limpia)
#
# Seguridad:
# - Lista blanca de proyectos; cualquier otro nombre sale con codigo 1 sin ejecutar docker.
# - Solo lee: pg_dump y SELECT count(*). Nunca DROP, DELETE, down ni restart.
# - Las credenciales se expanden DENTRO del contenedor db (variables propias de postgres):
#   no pasan por la linea de comandos del host ni se imprimen. No se muestra nada del .env.
# - Conteos antes y despues del volcado: como la app nunca borra filas, si coinciden son
#   exactamente los del volcado; si no coinciden (hubo escrituras) se descarta y sale con 1.
set -euo pipefail

readonly TABLAS=(socios membresias cargas modelos intentos_reentrenamiento listas_priorizadas
  predicciones campanias gestiones_retencion)

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ

error() {
  echo "ERROR: $*" >&2
  exit 1
}

uso() {
  echo "Uso: $0 [-p proyectofinal|mtabolic-e2e|mtabolic-limpia]"
}

# --- Argumentos -------------------------------------------------------------------------
PROYECTO="proyectofinal"
while [ "$#" -gt 0 ]; do
  case "$1" in
    -p)
      [ "$#" -ge 2 ] || error "falta el nombre del proyecto tras -p."
      PROYECTO="$2"
      shift 2
      ;;
    -h | --ayuda)
      uso
      exit 0
      ;;
    *) error "argumento no reconocido: $1 ($(uso))" ;;
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
[ -f "$RAIZ/compose.yaml" ] || error "no se encontro compose.yaml en la raiz del proyecto ($RAIZ)."
[ -f "$RAIZ/$ENV_NOMBRE" ] || error "no se encontro el archivo $ENV_NOMBRE en la raiz del proyecto ($RAIZ)."
command -v docker >/dev/null 2>&1 || error "no se encontro el comando docker. Instale o inicie Docker Desktop."

# Rutas relativas a la raiz: funcionan igual en Linux, macOS y Git Bash (sin conversion de
# rutas de MSYS, que alteraria "db:/tmp/...").
cd "$RAIZ"
export MSYS_NO_PATHCONV=1

compose() {
  docker compose -p "$PROYECTO" -f compose.yaml --env-file "$ENV_NOMBRE" "$@"
}

SELLO="$(date +%Y%m%d-%H%M%S)"
readonly NOMBRE="${PROYECTO}-${SELLO}"
readonly DUMP="respaldos/${NOMBRE}.dump"
readonly CONTEOS="respaldos/${NOMBRE}.conteos"
readonly TMP_CONTENEDOR="/tmp/${NOMBRE}.dump"

limpiar_contenedor() {
  compose exec -T db rm -f "$TMP_CONTENEDOR" >/dev/null 2>&1 || true
}

# Una fila con un conteo por columna, en el orden de TABLAS (sin comillas en el SQL).
CONSULTA=""
for t in "${TABLAS[@]}"; do
  CONSULTA="${CONSULTA:+$CONSULTA, }(SELECT count(*) FROM $t)"
done
CONSULTA="SELECT $CONSULTA"
readonly CONSULTA

# Imprime una linea tabla=n por tabla; falla si la respuesta no tiene un numero por tabla.
leer_conteos() {
  local fila i
  local -a valores
  fila="$(compose exec -T db sh -c 'psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"' sh "$CONSULTA" |
    tr -d '\r' | tail -n 1)" || return 1
  IFS='|' read -r -a valores <<<"$fila"
  [ "${#valores[@]}" -eq "${#TABLAS[@]}" ] || return 1
  for i in "${!TABLAS[@]}"; do
    case "${valores[$i]}" in '' | *[!0-9]*) return 1 ;; esac
    printf '%s=%s\n' "${TABLAS[$i]}" "${valores[$i]}"
  done
}

mkdir -p respaldos

echo "=== Respaldo de la base del proyecto $PROYECTO (solo lectura) ==="
echo "[1/4] Conteos antes del volcado..."
antes="$(leer_conteos)" ||
  error "no se pudieron leer los conteos (el contenedor db del proyecto $PROYECTO esta en marcha?)."

trap limpiar_contenedor EXIT

echo "[2/4] Volcado con pg_dump -Fc dentro del contenedor db..."
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$1"' sh "$TMP_CONTENEDOR" ||
  error "fallo pg_dump."

echo "[3/4] Copiando el volcado a $DUMP..."
# compose cp escribe su barra de progreso en stderr: se captura y solo se muestra si falla.
if ! salida_cp="$(compose cp "db:$TMP_CONTENEDOR" "$DUMP" 2>&1 >/dev/null)"; then
  [ -z "$salida_cp" ] || printf '%s\n' "$salida_cp" >&2
  error "no se pudo copiar el volcado al PC."
fi
limpiar_contenedor
trap - EXIT
[ -s "$DUMP" ] || error "el volcado copiado esta vacio."

echo "[4/4] Conteos despues del volcado..."
despues="$(leer_conteos)" ||
  error "no se pudieron leer los conteos despues del volcado."
if [ "$antes" != "$despues" ]; then
  rm -f "$DUMP"
  error "la base cambio durante el respaldo (hubo escrituras); se descarto el volcado. Repita el respaldo."
fi

printf '%s\n' "$antes" >"$CONTEOS"

echo "Respaldo creado:"
echo "  $DUMP ($(wc -c <"$DUMP" | tr -d ' ') bytes)"
echo "  $CONTEOS"
printf '%s\n' "$antes" | sed 's/^/    /'
echo "Guarde la carpeta respaldos/ fuera de carpetas compartidas: contiene datos personales."
