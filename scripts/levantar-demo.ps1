<#
.SYNOPSIS
  Levanta el stack de DEMOSTRACION (proyecto de compose "mtabolic-demo", R-019) con datos
  inventados, con un solo comando y sin configurar nada. Solo necesita Docker en marcha.

.DESCRIPTION
  1. Comprueba Docker y que los puertos 8083, 8003 y 5435 esten libres.
  2. Si no existe .env.demo, lo crea desde .env.demo.example con contrasenas aleatorias.
  3. Si la fecha de datos-demo\vigencia.txt ya paso y el demo nunca se levanto en este equipo,
     regenera datos-demo\ con un contenedor (no hace falta Python).
  4. Levanta el stack, espera a que el sistema este LISTO y muestra la direccion de la app.

  Seguridad:
  - El nombre del proyecto esta fijo (-p mtabolic-demo) y no se acepta otro: nunca toca los
    stacks proyectofinal ni mtabolic-e2e. Ninguna ruta de este script borra volumenes.
  - Un .env.demo existente no se cambia: su contrasena ya esta guardada en el volumen.
  - Las contrasenas no se imprimen nunca.

  Solo caracteres ASCII: Windows PowerShell 5 lee sin BOM como ANSI.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\levantar-demo.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Proyecto = 'mtabolic-demo'
$Volumen = "${Proyecto}_pgdata"
$Puertos = @(8083, 8003, 5435)
$UrlApp = 'http://localhost:8083'
$UrlEstado = 'http://127.0.0.1:8083/api/v1/sistema/estado'
$EsperaSegundos = 5
$LimiteSegundos = 900
$ImagenPython = 'python:3.12.13-slim-bookworm'
$VersionOpenpyxl = '3.1.5'
$MarcaPostgres = 'CAMBIAR_CONTRASENA_POSTGRES'
$MarcaApp = 'CAMBIAR_CONTRASENA_APP'

$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ArchivoCompose = Join-Path $Raiz 'compose.yaml'
$ArchivoEnv = Join-Path $Raiz '.env.demo'
$ArchivoEjemplo = Join-Path $Raiz '.env.demo.example'
$ArchivoVigencia = Join-Path (Join-Path $Raiz 'datos-demo') 'vigencia.txt'

function Salir-ConError([string]$Mensaje) {
    [Console]::Error.WriteLine("ERROR: $Mensaje")
    exit 1
}

function Ayuda-Logs {
    [Console]::Error.WriteLine("Para ver el detalle: docker compose -p $Proyecto --env-file .env.demo logs backend")
}

# Comando docker cuya salida no interesa. Con 'Stop', Windows PowerShell 5 convierte en
# excepcion lo que un programa escribe en stderr al redirigirlo.
function Docker-Responde([string[]]$Argumentos) {
    $previo = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker @Argumentos *> $null
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previo
    }
}

function Puerto-Ocupado([int]$Puerto) {
    # Primero la tabla del sistema: Windows deja abrir 127.0.0.1 aunque otro programa escuche en
    # 0.0.0.0, y ese choque no se ve al intentar abrir el puerto. Abrirlo detecta el resto,
    # como los puertos reservados por Hyper-V.
    if (Get-NetTCPConnection -State Listen -LocalPort $Puerto -ErrorAction SilentlyContinue) {
        return $true
    }
    $escucha = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Puerto)
    try {
        $escucha.Start()
        return $false
    }
    catch {
        return $true
    }
    finally {
        $escucha.Stop()
    }
}

function Contrasena-Aleatoria {
    $bytes = New-Object byte[] 32
    $generador = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generador.GetBytes($bytes)
    }
    finally {
        $generador.Dispose()
    }
    return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

function Crear-Env {
    $postgres = Contrasena-Aleatoria
    $app = Contrasena-Aleatoria
    if ($postgres -ceq $app) {
        Salir-ConError 'no se pudieron generar contrasenas aleatorias.'
    }
    $utf8SinBom = New-Object System.Text.UTF8Encoding($false)
    # Se escribe con la API de .NET: Set-Content -Encoding UTF8 agrega BOM en PowerShell 5 y
    # rompe la primera variable. Un clon en Windows puede traer el ejemplo con CRLF.
    $contenido = [System.IO.File]::ReadAllText($ArchivoEjemplo, $utf8SinBom)
    $contenido = $contenido.Replace("`r`n", "`n")
    $contenido = $contenido.Replace($MarcaPostgres, $postgres).Replace($MarcaApp, $app)
    $temporal = "$ArchivoEnv.tmp"
    [System.IO.File]::WriteAllText($temporal, $contenido, $utf8SinBom)
    [System.IO.File]::Move($temporal, $ArchivoEnv)
}

function Regenerar-Datos([string]$Fecha) {
    $generador = Join-Path (Join-Path $Raiz 'Backend') 'scripts'
    $salida = Join-Path $Raiz 'datos-demo'
    $comando = "pip install --quiet --no-cache-dir --disable-pip-version-check --target /tmp/deps openpyxl==$VersionOpenpyxl && PYTHONPATH=/tmp/deps python /generador/generar_dataset_demo.py --fecha-base `$FECHA_BASE --salida /salida"
    & docker run --rm `
        --env "FECHA_BASE=$Fecha" `
        --env HOME=/tmp `
        --env PYTHONDONTWRITEBYTECODE=1 `
        --mount "type=bind,source=$generador,target=/generador,readonly" `
        --mount "type=bind,source=$salida,target=/salida" `
        $ImagenPython `
        sh -c $comando
    if ($LASTEXITCODE -ne 0) {
        Salir-ConError 'no se pudieron regenerar los datos del demo.'
    }
}

# Las variables de entorno ganan a --env-file: un .env principal cargado haria que el demo
# usara las credenciales o los puertos de otro stack.
foreach ($variable in @(
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'APP_DB_USER', 'APP_DB_PASSWORD',
        'MIGRATE_DATABASE_URL', 'DATABASE_URL', 'CORS_ORIGINS', 'APP_ENV', 'HISTORICO_DIR',
        'DB_PORT', 'BACKEND_PORT', 'FRONTEND_PORT', 'IMAGE_TAG', 'RED_INTERNA_SUBNET',
        'FRONTEND_IP', 'IPS_PERMITIDAS', 'HOSTS_PERMITIDOS')) {
    Remove-Item -LiteralPath "Env:\$variable" -ErrorAction SilentlyContinue
}

# --- Precondiciones: nada de esto crea archivos ni contenedores -------------------------
foreach ($requerido in @($ArchivoCompose, $ArchivoEjemplo, $ArchivoVigencia)) {
    if (-not (Test-Path -LiteralPath $requerido -PathType Leaf)) {
        Salir-ConError "no se encontro $requerido."
    }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Salir-ConError 'Docker no esta instalado. Instale Docker Desktop (https://www.docker.com/products/docker-desktop/) y vuelva a ejecutar este comando.'
}
if (-not (Docker-Responde @('info'))) {
    Salir-ConError 'Docker no esta en marcha. Abra Docker Desktop, espere a que diga que esta listo y vuelva a ejecutar este comando.'
}
if (-not (Docker-Responde @('compose', 'version'))) {
    Salir-ConError 'este Docker no incluye Compose v2. Actualice Docker Desktop.'
}

# Un puerto publicado por el propio demo no cuenta: asi una segunda ejecucion termina bien.
$puertosPropios = (& docker ps --filter "label=com.docker.compose.project=$Proyecto" --format '{{.Ports}}') -join ' '
foreach ($puerto in $Puertos) {
    if ($puertosPropios.Contains(":$puerto->")) { continue }
    if (Puerto-Ocupado $puerto) {
        Salir-ConError "el puerto $puerto ya esta ocupado por otro programa. Cierre ese programa y vuelva a ejecutar este comando."
    }
}

# --- Configuracion ----------------------------------------------------------------------
if (Test-Path -LiteralPath $ArchivoEnv -PathType Leaf) {
    Write-Host '[1/4] Configuracion: .env.demo ya existe, no se cambia.'
}
else {
    Write-Host '[1/4] Configuracion: creando .env.demo con contrasenas aleatorias...'
    Crear-Env
}

# --- Datos ------------------------------------------------------------------------------
$vigencia = ([System.IO.File]::ReadAllText($ArchivoVigencia)).Trim()
if ($vigencia -notmatch '^\d{4}-\d{2}-\d{2}$') {
    Salir-ConError 'datos-demo\vigencia.txt no contiene una fecha AAAA-MM-DD.'
}
$hoy = (Get-Date).ToString('yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
if ([string]::CompareOrdinal($hoy, $vigencia) -gt 0) {
    if (Docker-Responde @('volume', 'inspect', $Volumen)) {
        Write-Host "[2/4] Datos: AVISO, pasaron de su vigencia ($vigencia); las listas pueden salir vacias."
        Write-Host '      Para renovarlos hay que borrar el demo y volver a levantarlo (ver GUIA-RAPIDA.md).'
    }
    else {
        Write-Host "[2/4] Datos: la vigencia ($vigencia) ya paso; regenerando datos-demo\ con fecha $hoy..."
        Regenerar-Datos $hoy
    }
}
else {
    Write-Host "[2/4] Datos: vigentes hasta $vigencia."
}

# --- Arranque ---------------------------------------------------------------------------
Write-Host '[3/4] Levantando el demo (la primera vez tarda varios minutos: descarga y construye)...'
& docker compose -p $Proyecto -f $ArchivoCompose --env-file $ArchivoEnv up -d --build
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine('ERROR: no se pudo levantar el demo.')
    Ayuda-Logs
    exit 1
}

Write-Host "[4/4] Esperando a que el sistema este listo (maximo $($LimiteSegundos / 60) min)..."
$reloj = [System.Diagnostics.Stopwatch]::StartNew()
$ultimo = 'SIN_RESPUESTA'
while ($true) {
    try {
        $respuesta = Invoke-RestMethod -Uri $UrlEstado -Method Get -TimeoutSec 5
        $ultimo = [string]$respuesta.estado
        if ([string]::IsNullOrWhiteSpace($ultimo)) { $ultimo = 'SIN_RESPUESTA' }
    }
    catch {
        $ultimo = 'SIN_RESPUESTA'
    }
    $transcurrido = [int]$reloj.Elapsed.TotalSeconds
    Write-Host "  ${transcurrido}s: $ultimo"
    if ($ultimo -eq 'LISTO') { break }
    if ($ultimo -eq 'FALTAN_DATOS_HISTORICOS') {
        [Console]::Error.WriteLine("ERROR: el sistema termino en $ultimo.")
        Ayuda-Logs
        exit 1
    }
    if ($transcurrido -ge $LimiteSegundos) {
        [Console]::Error.WriteLine("ERROR: tiempo agotado. Ultimo estado: $ultimo")
        Ayuda-Logs
        exit 1
    }
    Start-Sleep -Seconds $EsperaSegundos
}

Write-Host ''
Write-Host "Listo. Abra $UrlApp en el navegador."
Write-Host 'Los datos son inventados: las cifras no son las de la tesis.'
