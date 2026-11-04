#!/usr/bin/env bash
# Deja el stack E2E (proyecto de compose "mtabolic-e2e", http://localhost:8081) en uno de sus
# dos estados (R-022):
#
#   grabacion  datos inventados que parecen un gimnasio real, para grabar el demo: genera
#              datos-grabacion/ con la fecha de hoy (perfil "grabacion", en un contenedor: no
#              hace falta Python), levanta 8081 con esos libros, espera LISTO y siembra 4 meses
#              de listas, campanas y gestiones con los casos de uso de la app.
#   e2e        el estado de las pruebas E2E: libros sinteticos de Backend/tests/fixtures/historico
#              tal como dice .env.e2e. Despues:
#              cd Frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test --workers=1
#
# Uso:  bash scripts/preparar-8081.sh grabacion|e2e [--si]
#
# Seguridad:
# - BORRA todo lo que haya en 8081 (down -v del proyecto mtabolic-e2e). Pide confirmacion;
#   --si la da por respondida (uso no interactivo).
# - El proyecto esta fijo (-p mtabolic-e2e) y no se acepta otro: nunca toca proyectofinal ni
#   mtabolic-demo ni sus volumenes. Cualquier otro argumento sale con 1 sin ejecutar Docker.
# - Las contrasenas viven en .env.e2e (no versionado) y no se imprimen nunca.
set -euo pipefail

readonly PROYECTO="mtabolic-e2e"
readonly URL_APP="http://localhost:8081"
readonly URL_ESTADO="http://127.0.0.1:8081/api/v1/sistema/estado"
readonly ESPERA_SEGUNDOS=5
readonly LIMITE_SEGUNDOS=900
readonly IMAGEN_PYTHON="python:3.12.13-slim-bookworm"
readonly VERSION_OPENPYXL="3.1.5"
readonly DATOS_GRABACION="./datos-grabacion"
readonly SCRIPT_SIEMBRA_CONTENEDOR="/tmp/sembrar_grabacion.py"

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ
readonly ARCHIVO_COMPOSE="$RAIZ/compose.yaml"
readonly ARCHIVO_ENV="$RAIZ/.env.e2e"
readonly SCRIPT_SIEMBRA="$RAIZ/Backend/scripts/sembrar_grabacion.py"

error() {
  echo "ERROR: $*" >&2
  exit 1
}

uso() {
  echo "Uso: bash scripts/preparar-8081.sh grabacion|e2e [--si]" >&2
  exit 1
}

# --- Argumentos: se validan antes de tocar Docker ---------------------------------------
estado=""
confirmado="no"
for argumento in "$@"; do
  case "$argumento" in
    grabacion | e2e)
      [ -z "$estado" ] || uso
      estado="$argumento"
      ;;
    --si) confirmado="si" ;;
    *) uso ;;
  esac
done
[ -n "$estado" ] || uso

# Git Bash: docker.exe necesita rutas de Windows y MSYS no debe traducir argumentos como
# backend:/tmp/... (los convertiria en rutas de Windows dentro del contenedor).
ruta_docker() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}
COMPOSE_DOCKER="$(ruta_docker "$ARCHIVO_COMPOSE")"
ENV_DOCKER="$(ruta_docker "$ARCHIVO_ENV")"
SIEMBRA_DOCKER="$(ruta_docker "$SCRIPT_SIEMBRA")"
readonly COMPOSE_DOCKER ENV_DOCKER SIEMBRA_DOCKER

compose() {
  MSYS_NO_PATHCONV=1 docker compose -p "$PROYECTO" -f "$COMPOSE_DOCKER" --env-file "$ENV_DOCKER" "$@"
}

ayuda_logs() {
  echo "Para ver el detalle: docker compose -p $PROYECTO --env-file .env.e2e logs backend" >&2
}

# Las variables exportadas en la shell ganan a --env-file: un .env principal cargado haria que
# 8081 usara las credenciales, la base o los puertos de otro stack.
unset POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB APP_DB_USER APP_DB_PASSWORD \
  MIGRATE_DATABASE_URL DATABASE_URL CORS_ORIGINS APP_ENV HISTORICO_DIR DB_PORT BACKEND_PORT \
  FRONTEND_PORT IMAGE_TAG RED_INTERNA_SUBNET FRONTEND_IP IPS_PERMITIDAS HOSTS_PERMITIDOS

# --- Precondiciones ---------------------------------------------------------------------
[ -f "$ARCHIVO_COMPOSE" ] || error "no se encontro compose.yaml en $RAIZ."
[ -f "$ARCHIVO_ENV" ] || error "no se encontro .env.e2e (copie .env.e2e.example y ponga una contrasena local de prueba)."
[ -f "$SCRIPT_SIEMBRA" ] || error "no se encontro Backend/scripts/sembrar_grabacion.py."
command -v curl >/dev/null 2>&1 || error "no se encontro el comando curl."
command -v docker >/dev/null 2>&1 || error "Docker no esta instalado."
docker info >/dev/null 2>&1 || error "Docker no esta en marcha. Abra Docker Desktop y vuelva a intentarlo."
docker compose version >/dev/null 2>&1 || error "este Docker no incluye Compose v2."

if [ "$confirmado" != "si" ]; then
  echo "Esto BORRA todo lo que haya en $URL_APP (proyecto $PROYECTO: base, listas y gestiones)"
  echo "y lo deja en el estado '$estado'. No toca el stack principal ni el demo."
  read -r -p "Continuar? [s/N] " respuesta || respuesta=""
  case "$respuesta" in
    s | S | si | SI | Si) ;;
    *)
      echo "Sin cambios."
      exit 0
      ;;
  esac
fi

# --- Datos de la grabacion ----------------------------------------------------------------
generar_datos() {
  local fecha="$1" raiz_docker="$RAIZ"
  if raiz_windows="$(cd "$RAIZ" && pwd -W 2>/dev/null)"; then
    raiz_docker="$raiz_windows"
  fi
  mkdir -p "$RAIZ/datos-grabacion"
  # Solo se borra lo que el generador escribe, y solo dentro de datos-grabacion/.
  rm -f "$RAIZ"/datos-grabacion/*.xlsx "$RAIZ/datos-grabacion/vigencia.txt"
  MSYS_NO_PATHCONV=1 docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env "FECHA_BASE=$fecha" \
    --env HOME=/tmp \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --mount "type=bind,source=$raiz_docker/Backend/scripts,target=/generador,readonly" \
    --mount "type=bind,source=$raiz_docker/datos-grabacion,target=/salida" \
    "$IMAGEN_PYTHON" \
    sh -c "pip install --quiet --no-cache-dir --disable-pip-version-check --target /tmp/deps openpyxl==$VERSION_OPENPYXL && PYTHONPATH=/tmp/deps python /generador/generar_dataset_demo.py --perfil grabacion --fecha-base \$FECHA_BASE --salida /salida" ||
    error "no se pudieron generar los datos de la grabacion."
}

esperar_listo() {
  local inicio=$SECONDS ultimo cuerpo estado_sistema transcurrido
  while :; do
    cuerpo="$(curl -s --max-time 5 "$URL_ESTADO" || true)"
    estado_sistema="$(printf '%s' "$cuerpo" | sed -n 's/.*"estado"[[:space:]]*:[[:space:]]*"\([A-Z_]*\)".*/\1/p' | head -n 1)"
    ultimo="${estado_sistema:-SIN_RESPUESTA}"
    transcurrido=$((SECONDS - inicio))
    echo "  ${transcurrido}s: $ultimo"
    case "$ultimo" in
      LISTO) return 0 ;;
      FALTAN_DATOS_HISTORICOS)
        echo "ERROR: el sistema termino en $ultimo." >&2
        ayuda_logs
        exit 1
        ;;
    esac
    if [ "$transcurrido" -ge "$LIMITE_SEGUNDOS" ]; then
      echo "ERROR: tiempo agotado. Ultimo estado: $ultimo" >&2
      ayuda_logs
      exit 1
    fi
    sleep "$ESPERA_SEGUNDOS"
  done
}

if [ "$estado" = "grabacion" ]; then
  hoy="$(date +%F)"
  echo "[1/5] Generando datos-grabacion/ con fecha $hoy (datos inventados)..."
  generar_datos "$hoy"
  # Gana a HISTORICO_DIR de .env.e2e solo en este comando.
  export HISTORICO_DIR="$DATOS_GRABACION"
else
  echo "[1/5] Datos: libros sinteticos de la E2E (.env.e2e)."
fi

echo "[2/5] Borrando 8081 (down -v, solo el proyecto $PROYECTO)..."
compose down -v --remove-orphans || error "no se pudo bajar $PROYECTO."

echo "[3/5] Levantando 8081 (reconstruye las imagenes; puede tardar)..."
if ! compose up -d --build; then
  echo "ERROR: no se pudo levantar $PROYECTO." >&2
  ayuda_logs
  exit 1
fi

echo "[4/5] Esperando a que el sistema este listo (maximo $((LIMITE_SEGUNDOS / 60)) min)..."
esperar_listo

if [ "$estado" = "grabacion" ]; then
  echo "[5/5] Sembrando listas, campanas y gestiones de los 4 meses anteriores..."
  compose cp "$SIEMBRA_DOCKER" "backend:$SCRIPT_SIEMBRA_CONTENEDOR" >/dev/null ||
    error "no se pudo copiar el script de siembra al contenedor."
  if ! compose exec -T backend python "$SCRIPT_SIEMBRA_CONTENEDOR"; then
    echo "ERROR: la siembra fallo." >&2
    ayuda_logs
    exit 1
  fi
  echo
  echo "Listo para grabar: abra $URL_APP (datos inventados)."
  echo "Para volver al estado de la E2E: bash scripts/preparar-8081.sh e2e"
else
  echo "[5/5] Sin siembra en el estado e2e."
  echo
  echo "Listo: $URL_APP en el estado de la E2E. Ahora: cd Frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test --workers=1"
fi
