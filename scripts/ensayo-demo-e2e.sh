#!/usr/bin/env bash
# Ensayo de la demostracion (03 §21) en el stack AISLADO mtabolic-e2e (R-013 T10, D7-OP-04).
#
# Desplaza fechas de los datos de prueba para ensayar CU-09 (alertas) y CU-02 (fecha de
# reentrenamiento perdida -> OMITIDO) sin reloj simulado en ejecucion: equivale a adelantar el
# reloj (decision (c) de R-013).
#
# Uso (desde cualquier carpeta; el .env.e2e se busca en la raiz del proyecto):
#   scripts/ensayo-demo-e2e.sh adelantar-seguimientos <dias>
#       Resta <dias> (1..60) a fecha_seguimiento de las gestiones PENDIENTE no borradas, en
#       una sola transaccion, e imprime cuantas cambio. Equivale a que pasen <dias> dias para
#       las alertas: con seguimiento = hoy + 1, "adelantar-seguimientos 1" la pone "para hoy"
#       y otro "adelantar-seguimientos 1" la deja "vencida".
#   scripts/ensayo-demo-e2e.sh perder-fecha-reentrenamiento
#       Pone la proxima fecha programada de reentrenamiento en AYER (fecha de Ecuador, UTC-5)
#       y reinicia el backend: al arrancar, el planificador registra un intento OMITIDO y
#       mueve la proxima fecha 6 meses. Imprime cuantos OMITIDO habia antes y despues.
#   scripts/ensayo-demo-e2e.sh -h | --ayuda
#   Opcional: "-p mtabolic-e2e" antes del subcomando (unico proyecto aceptado).
#
# Seguridad:
# - Proyecto FIJO mtabolic-e2e con .env.e2e. Cualquier otro proyecto (proyectofinal incluido),
#   subcomando o argumento invalido sale con codigo 1 SIN ejecutar ningun comando docker.
# - Dentro del contenedor db se comprueba ademas que POSTGRES_DB termine en _e2e; si no,
#   no se ejecuta nada.
# - Credenciales expandidas DENTRO del contenedor db (variables propias de postgres): no pasan
#   por la linea de comandos del host ni se imprimen. No se muestra nada del .env.e2e.
# - Solo UPDATE de fechas; nunca DELETE, DROP, TRUNCATE ni down. La salida son conteos y
#   fechas, sin datos personales.
set -euo pipefail

readonly PROYECTO="mtabolic-e2e"
readonly ENV_NOMBRE=".env.e2e"
readonly DIAS_MAX=60
readonly ESPERA_MAX_SEG=120

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ

error() {
  echo "ERROR: $*" >&2
  exit 1
}

uso() {
  cat <<EOF
Uso: $0 [-p $PROYECTO] adelantar-seguimientos <dias 1..$DIAS_MAX>
     $0 [-p $PROYECTO] perder-fecha-reentrenamiento
Solo actua sobre el proyecto de compose $PROYECTO ($ENV_NOMBRE).
EOF
}

# --- Argumentos (antes de cualquier comando docker) -------------------------------------
if [ "$#" -ge 1 ] && [ "$1" = "-p" ]; then
  [ "$#" -ge 2 ] || error "falta el nombre del proyecto tras -p."
  [ "$2" = "$PROYECTO" ] || error "proyecto no permitido: este script solo actua sobre $PROYECTO."
  shift 2
fi

[ "$#" -ge 1 ] || {
  uso >&2
  exit 1
}

SUBCOMANDO="$1"
shift
DIAS=""
case "$SUBCOMANDO" in
  -h | --ayuda)
    [ "$#" -eq 0 ] || error "argumento no reconocido: $1"
    uso
    exit 0
    ;;
  adelantar-seguimientos)
    [ "$#" -eq 1 ] || error "adelantar-seguimientos necesita exactamente un argumento: <dias 1..$DIAS_MAX>."
    case "$1" in
      '' | *[!0-9]*) error "dias debe ser un entero entre 1 y $DIAS_MAX." ;;
    esac
    # Sin ceros a la izquierda (evita octal y numeros enormes antes de compararlos).
    case "$1" in
      0*) error "dias debe ser un entero entre 1 y $DIAS_MAX." ;;
    esac
    [ "${#1}" -le 2 ] && [ "$1" -ge 1 ] && [ "$1" -le "$DIAS_MAX" ] ||
      error "dias debe ser un entero entre 1 y $DIAS_MAX."
    DIAS="$1"
    ;;
  perder-fecha-reentrenamiento)
    [ "$#" -eq 0 ] || error "perder-fecha-reentrenamiento no admite argumentos."
    ;;
  *) error "subcomando no reconocido: $SUBCOMANDO ($(uso | head -n 1))" ;;
esac
readonly SUBCOMANDO DIAS

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
[ -f "$RAIZ/compose.yaml" ] || error "no se encontro compose.yaml en la raiz del proyecto ($RAIZ)."
[ -f "$RAIZ/$ENV_NOMBRE" ] || error "no se encontro el archivo $ENV_NOMBRE en la raiz del proyecto ($RAIZ)."
command -v docker >/dev/null 2>&1 || error "no se encontro el comando docker. Instale o inicie Docker Desktop."

cd "$RAIZ"
export MSYS_NO_PATHCONV=1

compose() {
  docker compose -p "$PROYECTO" -f compose.yaml --env-file "$ENV_NOMBRE" "$@"
}

# Ejecuta una sentencia SQL fija (sin entrada del usuario salvo DIAS, ya validado como entero
# 1..60) en una sola transaccion e imprime la ultima linea del resultado. Aborta (codigo 3)
# dentro del contenedor si la base no es la del stack e2e.
psql_e2e() {
  compose exec -T db sh -c '
    case "$POSTGRES_DB" in
      *_e2e) ;;
      *) echo "la base del contenedor no es de e2e (*_e2e); no se toca nada." >&2; exit 3 ;;
    esac
    psql -X -At -1 -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"
  ' sh "$1" | tr -d '\r' | tail -n 1
}

entero() {
  case "$1" in '' | *[!0-9]*) return 1 ;; esac
}

readonly SQL_OMITIDOS="SELECT count(*) FROM intentos_reentrenamiento WHERE resultado = 'OMITIDO'"
# Fecha de negocio = Ecuador, UTC-5 fijo (igual que hoy_en_negocio del backend).
readonly SQL_HOY_NEGOCIO="((now() AT TIME ZONE 'UTC') - interval '5 hours')::date"

case "$SUBCOMANDO" in
  adelantar-seguimientos)
    echo "=== $PROYECTO: adelantar seguimientos $DIAS dia(s) ==="
    cambiadas="$(psql_e2e "WITH c AS (UPDATE gestiones_retencion SET fecha_seguimiento = fecha_seguimiento - $DIAS, updated_at = now() WHERE estado = 'PENDIENTE' AND deleted_at IS NULL RETURNING 1) SELECT count(*) FROM c")" ||
      error "no se pudo actualizar (el contenedor db del proyecto $PROYECTO esta en marcha?)."
    entero "$cambiadas" || error "respuesta inesperada de la base."
    echo "Gestiones PENDIENTE desplazadas $DIAS dia(s) antes: $cambiadas"
    ;;

  perder-fecha-reentrenamiento)
    echo "=== $PROYECTO: perder la fecha programada de reentrenamiento ==="
    antes="$(psql_e2e "$SQL_OMITIDOS")" ||
      error "no se pudo leer la base (el contenedor db del proyecto $PROYECTO esta en marcha?)."
    entero "$antes" || error "respuesta inesperada de la base."
    fecha="$(psql_e2e "WITH c AS (UPDATE estado_sistema SET proxima_fecha_reentrenamiento = $SQL_HOY_NEGOCIO - 1, updated_at = now() WHERE id = 1 AND migracion_historica = 'COMPLETADA' RETURNING proxima_fecha_reentrenamiento) SELECT coalesce(max(proxima_fecha_reentrenamiento)::text, 'NINGUNA') FROM c")" ||
      error "no se pudo actualizar la fecha programada."
    [ "$fecha" != "NINGUNA" ] || error "la migracion historica no esta COMPLETADA; no se cambio nada."
    echo "Proxima fecha programada puesta en $fecha (ayer). Reiniciando el backend..."
    compose restart backend >/dev/null || error "no se pudo reiniciar el backend."
    despues="$antes"
    esperado=$((antes + 1))
    segundos=0
    while [ "$segundos" -lt "$ESPERA_MAX_SEG" ]; do
      sleep 3
      segundos=$((segundos + 3))
      valor="$(psql_e2e "$SQL_OMITIDOS" 2>/dev/null)" || continue
      entero "$valor" || continue
      despues="$valor"
      [ "$despues" -lt "$esperado" ] || break
    done
    echo "Intentos OMITIDO: antes $antes, despues $despues"
    [ "$despues" -ge "$esperado" ] ||
      error "el planificador no registro el OMITIDO en ${ESPERA_MAX_SEG}s (REENTRENAMIENTO_AUTOMATICO activo?)."
    proxima="$(psql_e2e "SELECT coalesce(proxima_fecha_reentrenamiento::text, 'NINGUNA') FROM estado_sistema WHERE id = 1")" ||
      error "no se pudo leer la proxima fecha."
    echo "Nueva proxima fecha programada: $proxima"
    ;;
esac
exit 0
