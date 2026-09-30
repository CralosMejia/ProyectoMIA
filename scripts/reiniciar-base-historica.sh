#!/usr/bin/env bash
# Reinicia la base del stack PRINCIPAL (proyecto de compose "proyectofinal") dejando solo
# el historico: borra el volumen (down -v), vuelve a levantar el stack (up -d), espera a que
# la migracion historica termine (estado LISTO) y muestra los conteos finales.
#
# OPERACION IRREVERSIBLE: borra cargas por plantilla, listas, predicciones y todo lo demas
# del volumen principal. Es una accion manual y explicita del usuario, no una funcion de la app.
#
# Uso:
#   scripts/reiniciar-base-historica.sh          pide escribir BORRAR para continuar
#   scripts/reiniciar-base-historica.sh --si     no pregunta (uso no interactivo; con cuidado)
#
# Seguridad:
# - El nombre del proyecto esta fijo (-p proyectofinal) y no se acepta otro. El stack E2E
#   aislado (mtabolic-e2e) nunca se toca desde este script.
# - compose.yaml y .env se resuelven desde la ubicacion del script (funciona desde cualquier
#   directorio actual). Las credenciales solo las lee docker compose; el script no las imprime.
set -euo pipefail

readonly PROYECTO="proyectofinal"
readonly ESPERA_SEGUNDOS=5
readonly LIMITE_SEGUNDOS=900

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ
readonly COMPOSE_FILE_RAIZ="$RAIZ/compose.yaml"
readonly ENV_FILE_RAIZ="$RAIZ/.env"

error() {
  echo "ERROR: $*" >&2
  exit 1
}

# --- Argumentos -------------------------------------------------------------------------
SIN_PREGUNTAR=0
for arg in "$@"; do
  case "$arg" in
    --si) SIN_PREGUNTAR=1 ;;
    -h | --ayuda)
      echo "Uso: $0 [--si]"
      echo "  --si   no pide confirmacion (borra sin preguntar)."
      exit 0
      ;;
    *) error "argumento no reconocido: $arg (solo se admite --si)." ;;
  esac
done

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
[ -f "$COMPOSE_FILE_RAIZ" ] || error "no se encontro compose.yaml en la raiz del proyecto ($RAIZ)."
[ -f "$ENV_FILE_RAIZ" ] || error "no se encontro el archivo .env en la raiz del proyecto ($RAIZ). Copie .env.example a .env y rellenelo."
command -v docker >/dev/null 2>&1 || error "no se encontro el comando docker. Instale o inicie Docker Desktop."
command -v curl >/dev/null 2>&1 || error "no se encontro el comando curl."

# Puerto del backend: la variable de la shell gana (igual que en docker compose); si no, la
# linea BACKEND_PORT del .env; si no, 8000. Solo se lee esa linea y no se imprime nada del .env.
PUERTO="${BACKEND_PORT:-}"
if [ -z "$PUERTO" ]; then
  PUERTO="$(grep -E '^[[:space:]]*BACKEND_PORT[[:space:]]*=' "$ENV_FILE_RAIZ" | tail -n 1 | cut -d= -f2- | tr -d "\r\"' \t" || true)"
fi
PUERTO="${PUERTO:-8000}"
case "$PUERTO" in
  '' | *[!0-9]*) error "BACKEND_PORT no es un numero de puerto valido." ;;
esac
readonly URL_ESTADO="http://127.0.0.1:${PUERTO}/api/v1/sistema/estado"

compose() {
  docker compose -p "$PROYECTO" -f "$COMPOSE_FILE_RAIZ" --env-file "$ENV_FILE_RAIZ" "$@"
}

# --- Confirmacion -----------------------------------------------------------------------
cat <<EOF
=== Reinicio de la base PRINCIPAL (proyecto de compose: $PROYECTO) ===
Se borrara TODO el volumen de la base principal, sin vuelta atras:
  - cargas por plantilla confirmadas,
  - listas priorizadas y sus predicciones,
  - y todo lo demas guardado en esa base.
Despues se levanta el stack de nuevo: se vuelve a migrar el historico y se reentrena
el modelo v1 (identico al actual). El stack E2E aislado no se toca.
EOF

if [ "$SIN_PREGUNTAR" -eq 1 ]; then
  echo "Confirmacion omitida (--si)."
else
  printf 'Escriba BORRAR para continuar: '
  respuesta=""
  IFS= read -r respuesta || true
  respuesta="${respuesta%$'\r'}"
  if [ "$respuesta" != "BORRAR" ]; then
    echo "Cancelado. No se ha modificado nada."
    exit 0
  fi
fi

# --- Reinicio ---------------------------------------------------------------------------
echo "[1/4] Deteniendo el stack y borrando el volumen principal (down -v)..."
compose down -v

echo "[2/4] Levantando el stack (up -d)..."
compose up -d

echo "[3/4] Esperando a que el sistema este LISTO (maximo $((LIMITE_SEGUNDOS / 60)) min)..."
inicio=$SECONDS
ultimo="SIN_RESPUESTA"
while :; do
  cuerpo="$(curl -s --max-time 5 "$URL_ESTADO" || true)"
  estado="$(printf '%s' "$cuerpo" | sed -n 's/.*"estado"[[:space:]]*:[[:space:]]*"\([A-Z_]*\)".*/\1/p' | head -n 1)"
  ultimo="${estado:-SIN_RESPUESTA}"
  transcurrido=$((SECONDS - inicio))
  echo "  ${transcurrido}s: $ultimo"
  case "$ultimo" in
    LISTO) break ;;
    FALTAN_DATOS_HISTORICOS)
      echo "ERROR: el sistema termino en FALTAN_DATOS_HISTORICOS (revise los libros historicos y el log del backend)." >&2
      exit 1
      ;;
  esac
  if [ "$transcurrido" -ge "$LIMITE_SEGUNDOS" ]; then
    echo "ERROR: tiempo agotado sin llegar a LISTO. Ultimo estado: $ultimo" >&2
    exit 1
  fi
  sleep "$ESPERA_SEGUNDOS"
done

echo "[4/4] Conteos finales:"
# Las credenciales se expanden DENTRO del contenedor db (variables propias de postgres):
# no pasan por la linea de comandos del host ni aparecen en la salida.
conteos="$(compose exec -T db sh -c 'psql -X -At -U $POSTGRES_USER -d $POSTGRES_DB -c '\''SELECT (SELECT count(*) FROM socios), (SELECT count(*) FROM membresias), (SELECT count(*) FROM cargas), (SELECT count(*) FROM listas_priorizadas), (SELECT count(*) FROM predicciones)'\''')"
conteos="$(printf '%s' "$conteos" | tr -d '\r')"
IFS='|' read -r n_socios n_membresias n_cargas n_listas n_predicciones <<<"$conteos"
echo "  socios:             $n_socios"
echo "  membresias:         $n_membresias"
echo "  cargas:             $n_cargas"
echo "  listas_priorizadas: $n_listas"
echo "  predicciones:       $n_predicciones"
echo "Reinicio terminado: base principal solo con el historico."
