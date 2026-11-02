#!/usr/bin/env bash
# Levanta el stack de DEMOSTRACION (proyecto de compose "mtabolic-demo", R-019) con datos
# inventados, con un solo comando y sin configurar nada. Solo necesita Docker en marcha.
#
# Uso (desde cualquier carpeta):  bash scripts/levantar-demo.sh
#
# Que hace:
#   1. Comprueba Docker y que los puertos 8083, 8003 y 5435 esten libres.
#   2. Si no existe .env.demo, lo crea desde .env.demo.example con contrasenas aleatorias.
#   3. Si la fecha de datos-demo/vigencia.txt ya paso y el demo nunca se levanto en este equipo,
#      regenera datos-demo/ con un contenedor (no hace falta Python).
#   4. Levanta el stack, espera a que el sistema este LISTO y muestra la direccion de la app.
#
# Seguridad:
# - El nombre del proyecto esta fijo (-p mtabolic-demo) y no se acepta otro: nunca toca los
#   stacks proyectofinal ni mtabolic-e2e. Ninguna ruta de este script borra volumenes.
# - Un .env.demo existente no se cambia: su contrasena ya esta guardada en el volumen.
# - Las contrasenas no se imprimen nunca.
set -euo pipefail

readonly PROYECTO="mtabolic-demo"
readonly VOLUMEN="${PROYECTO}_pgdata"
readonly PUERTOS="8083 8003 5435"
readonly URL_APP="http://localhost:8083"
readonly URL_ESTADO="http://127.0.0.1:8083/api/v1/sistema/estado"
readonly ESPERA_SEGUNDOS=5
readonly LIMITE_SEGUNDOS=900
readonly IMAGEN_PYTHON="python:3.12.13-slim-bookworm"
readonly VERSION_OPENPYXL="3.1.5"
readonly MARCA_POSTGRES="CAMBIAR_CONTRASENA_POSTGRES"
readonly MARCA_APP="CAMBIAR_CONTRASENA_APP"
readonly LARGO_CONTRASENA=64

DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR_SCRIPT/.." && pwd)"
readonly RAIZ
readonly ARCHIVO_COMPOSE="$RAIZ/compose.yaml"
readonly ARCHIVO_ENV="$RAIZ/.env.demo"
readonly ARCHIVO_EJEMPLO="$RAIZ/.env.demo.example"
readonly ARCHIVO_VIGENCIA="$RAIZ/datos-demo/vigencia.txt"

error() {
  echo "ERROR: $*" >&2
  exit 1
}

compose() {
  docker compose -p "$PROYECTO" -f "$ARCHIVO_COMPOSE" --env-file "$ARCHIVO_ENV" "$@"
}

ayuda_logs() {
  echo "Para ver el detalle: docker compose -p $PROYECTO --env-file .env.demo logs backend" >&2
}

# Las variables exportadas en la shell ganan a --env-file: un .env principal cargado haria que
# el demo usara las credenciales o los puertos de otro stack.
unset POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB APP_DB_USER APP_DB_PASSWORD \
  MIGRATE_DATABASE_URL DATABASE_URL CORS_ORIGINS APP_ENV HISTORICO_DIR DB_PORT BACKEND_PORT \
  FRONTEND_PORT IMAGE_TAG RED_INTERNA_SUBNET FRONTEND_IP IPS_PERMITIDAS HOSTS_PERMITIDOS

if [ "$#" -ne 0 ]; then
  error "este comando no admite argumentos."
fi

# --- Precondiciones: nada de esto crea archivos ni contenedores -------------------------
[ -f "$ARCHIVO_COMPOSE" ] || error "no se encontro compose.yaml en $RAIZ."
[ -f "$ARCHIVO_EJEMPLO" ] || error "no se encontro .env.demo.example en $RAIZ."
[ -f "$ARCHIVO_VIGENCIA" ] || error "no se encontro datos-demo/vigencia.txt en $RAIZ."
command -v curl >/dev/null 2>&1 || error "no se encontro el comando curl."
command -v docker >/dev/null 2>&1 || error "Docker no esta instalado. Instale Docker Desktop (https://www.docker.com/products/docker-desktop/) y vuelva a ejecutar este comando."
docker info >/dev/null 2>&1 || error "Docker no esta en marcha. Abra Docker Desktop, espere a que diga que esta listo y vuelva a ejecutar este comando."
docker compose version >/dev/null 2>&1 || error "este Docker no incluye Compose v2. Actualice Docker Desktop."

# Un puerto publicado por el propio demo no cuenta: asi una segunda ejecucion termina bien.
puertos_propios="$(docker ps --filter "label=com.docker.compose.project=$PROYECTO" --format '{{.Ports}}')"
for puerto in $PUERTOS; do
  case "$puertos_propios" in
    *":$puerto->"*) continue ;;
  esac
  if (: <"/dev/tcp/127.0.0.1/$puerto") 2>/dev/null; then
    error "el puerto $puerto ya esta ocupado por otro programa. Cierre ese programa y vuelva a ejecutar este comando."
  fi
done

# --- Configuracion ----------------------------------------------------------------------
contrasena_aleatoria() {
  od -An -tx1 -N32 /dev/urandom | tr -d ' \n'
}

crear_env() {
  local temporal="$ARCHIVO_ENV.tmp" contenido postgres app
  postgres="$(contrasena_aleatoria)"
  app="$(contrasena_aleatoria)"
  if [ "${#postgres}" -ne "$LARGO_CONTRASENA" ] || [ "${#app}" -ne "$LARGO_CONTRASENA" ] || [ "$postgres" = "$app" ]; then
    error "no se pudieron generar contrasenas aleatorias."
  fi
  # Sin sed: las contrasenas no pasan por la linea de comandos de ningun proceso. El CR se quita
  # porque un clon en Windows puede traer el ejemplo con CRLF.
  contenido="$(tr -d '\r' <"$ARCHIVO_EJEMPLO")"
  contenido="${contenido//$MARCA_POSTGRES/$postgres}"
  contenido="${contenido//$MARCA_APP/$app}"
  (
    umask 077
    printf '%s\n' "$contenido" >"$temporal"
  )
  mv "$temporal" "$ARCHIVO_ENV"
}

if [ -f "$ARCHIVO_ENV" ]; then
  echo "[1/4] Configuracion: .env.demo ya existe, no se cambia."
else
  echo "[1/4] Configuracion: creando .env.demo con contrasenas aleatorias..."
  crear_env
fi

# --- Datos ------------------------------------------------------------------------------
regenerar_datos() {
  local fecha="$1" raiz_docker="$RAIZ"
  # Git Bash: docker.exe necesita la ruta de Windows y MSYS no debe traducir los argumentos.
  if raiz_windows="$(cd "$RAIZ" && pwd -W 2>/dev/null)"; then
    raiz_docker="$raiz_windows"
  fi
  MSYS_NO_PATHCONV=1 docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env "FECHA_BASE=$fecha" \
    --env HOME=/tmp \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --mount "type=bind,source=$raiz_docker/Backend/scripts,target=/generador,readonly" \
    --mount "type=bind,source=$raiz_docker/datos-demo,target=/salida" \
    "$IMAGEN_PYTHON" \
    sh -c "pip install --quiet --no-cache-dir --disable-pip-version-check --target /tmp/deps openpyxl==$VERSION_OPENPYXL && PYTHONPATH=/tmp/deps python /generador/generar_dataset_demo.py --fecha-base \$FECHA_BASE --salida /salida" ||
    error "no se pudieron regenerar los datos del demo."
}

vigencia="$(tr -d '\r\n ' <"$ARCHIVO_VIGENCIA")"
case "$vigencia" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) error "datos-demo/vigencia.txt no contiene una fecha AAAA-MM-DD." ;;
esac
hoy="$(date +%F)"
if [[ "$hoy" > "$vigencia" ]]; then
  if docker volume inspect "$VOLUMEN" >/dev/null 2>&1; then
    echo "[2/4] Datos: AVISO, pasaron de su vigencia ($vigencia); las listas pueden salir vacias."
    echo "      Para renovarlos hay que borrar el demo y volver a levantarlo (ver GUIA-RAPIDA.md)."
  else
    echo "[2/4] Datos: la vigencia ($vigencia) ya paso; regenerando datos-demo/ con fecha $hoy..."
    regenerar_datos "$hoy"
  fi
else
  echo "[2/4] Datos: vigentes hasta $vigencia."
fi

# --- Arranque ---------------------------------------------------------------------------
echo "[3/4] Levantando el demo (la primera vez tarda varios minutos: descarga y construye)..."
if ! compose up -d --build; then
  echo "ERROR: no se pudo levantar el demo." >&2
  ayuda_logs
  exit 1
fi

echo "[4/4] Esperando a que el sistema este listo (maximo $((LIMITE_SEGUNDOS / 60)) min)..."
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

echo
echo "Listo. Abra $URL_APP en el navegador."
echo "Los datos son inventados: las cifras no son las de la tesis."
