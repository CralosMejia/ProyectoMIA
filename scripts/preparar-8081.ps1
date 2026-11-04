<#
.SYNOPSIS
  Deja el stack E2E (proyecto de compose "mtabolic-e2e", http://localhost:8081) en uno de sus
  dos estados (R-022): grabacion o e2e.

.DESCRIPTION
  grabacion  datos inventados que parecen un gimnasio real, para grabar el demo: genera
             datos-grabacion\ con la fecha de hoy (perfil "grabacion", en un contenedor: no
             hace falta Python), levanta 8081 con esos libros, espera LISTO y siembra 4 meses
             de listas, campanas y gestiones con los casos de uso de la app.
  e2e        el estado de las pruebas E2E: libros sinteticos de Backend\tests\fixtures\historico
             tal como dice .env.e2e. Despues:
             cd Frontend; $env:E2E_BASE_URL='http://localhost:8081'; npx playwright test --workers=1

  Seguridad:
  - BORRA todo lo que haya en 8081 (down -v del proyecto mtabolic-e2e). Pide confirmacion;
    -Si la da por respondida (uso no interactivo).
  - El proyecto esta fijo (-p mtabolic-e2e) y no se acepta otro: nunca toca proyectofinal ni
    mtabolic-demo ni sus volumenes. Cualquier otro argumento sale con 1 sin ejecutar Docker.
  - Las contrasenas viven en .env.e2e (no versionado) y no se imprimen nunca.

  Solo caracteres ASCII: Windows PowerShell 5 lee sin BOM como ANSI.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 grabacion
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 e2e -Si
#>
param(
    [Parameter(Position = 0)][string]$Estado = '',
    [switch]$Si,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Resto = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Proyecto = 'mtabolic-e2e'
$UrlApp = 'http://localhost:8081'
$UrlEstado = 'http://127.0.0.1:8081/api/v1/sistema/estado'
$EsperaSegundos = 5
$LimiteSegundos = 900
$ImagenPython = 'python:3.12.13-slim-bookworm'
$VersionOpenpyxl = '3.1.5'
$DatosGrabacion = './datos-grabacion'
$ScriptSiembraContenedor = '/tmp/sembrar_grabacion.py'

$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ArchivoCompose = Join-Path $Raiz 'compose.yaml'
$ArchivoEnv = Join-Path $Raiz '.env.e2e'
$ScriptSiembra = Join-Path (Join-Path (Join-Path $Raiz 'Backend') 'scripts') 'sembrar_grabacion.py'
$CarpetaGrabacion = Join-Path $Raiz 'datos-grabacion'

function Salir-ConError([string]$Mensaje) {
    [Console]::Error.WriteLine("ERROR: $Mensaje")
    exit 1
}

function Uso {
    [Console]::Error.WriteLine('Uso: powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 grabacion|e2e [-Si]')
    exit 1
}

function Ayuda-Logs {
    [Console]::Error.WriteLine("Para ver el detalle: docker compose -p $Proyecto --env-file .env.e2e logs backend")
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

# docker compose escribe el progreso en stderr: en PowerShell 5 no debe volverse excepcion.
function Compose([string[]]$Argumentos) {
    $previo = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker compose -p $Proyecto -f $ArchivoCompose --env-file $ArchivoEnv @Argumentos | Out-Host
        return ($LASTEXITCODE -eq 0)
    }
    finally {
        $ErrorActionPreference = $previo
    }
}

# --- Argumentos: se validan antes de tocar Docker ---------------------------------------
# Tambien se acepta --si, como en la version para bash.
foreach ($extra in $Resto) {
    if ($extra -ceq '--si') { $Si = [switch]::Present } else { Uso }
}
if ($Estado -cne 'grabacion' -and $Estado -cne 'e2e') { Uso }

# Las variables de entorno ganan a --env-file: un .env principal cargado haria que 8081 usara
# las credenciales, la base o los puertos de otro stack.
foreach ($variable in @(
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'APP_DB_USER', 'APP_DB_PASSWORD',
        'MIGRATE_DATABASE_URL', 'DATABASE_URL', 'CORS_ORIGINS', 'APP_ENV', 'HISTORICO_DIR',
        'DB_PORT', 'BACKEND_PORT', 'FRONTEND_PORT', 'IMAGE_TAG', 'RED_INTERNA_SUBNET',
        'FRONTEND_IP', 'IPS_PERMITIDAS', 'HOSTS_PERMITIDOS')) {
    Remove-Item -LiteralPath "Env:\$variable" -ErrorAction SilentlyContinue
}

# --- Precondiciones ---------------------------------------------------------------------
if (-not (Test-Path -LiteralPath $ArchivoCompose -PathType Leaf)) { Salir-ConError "no se encontro compose.yaml en $Raiz." }
if (-not (Test-Path -LiteralPath $ArchivoEnv -PathType Leaf)) {
    Salir-ConError 'no se encontro .env.e2e (copie .env.e2e.example y ponga una contrasena local de prueba).'
}
if (-not (Test-Path -LiteralPath $ScriptSiembra -PathType Leaf)) { Salir-ConError 'no se encontro Backend\scripts\sembrar_grabacion.py.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Salir-ConError 'Docker no esta instalado.' }
if (-not (Docker-Responde @('info'))) { Salir-ConError 'Docker no esta en marcha. Abra Docker Desktop y vuelva a intentarlo.' }
if (-not (Docker-Responde @('compose', 'version'))) { Salir-ConError 'este Docker no incluye Compose v2.' }

if (-not $Si) {
    Write-Host "Esto BORRA todo lo que haya en $UrlApp (proyecto ${Proyecto}: base, listas y gestiones)"
    Write-Host "y lo deja en el estado '$Estado'. No toca el stack principal ni el demo."
    $respuesta = Read-Host 'Continuar? [s/N]'
    if (@('s', 'si') -notcontains ([string]$respuesta).Trim().ToLowerInvariant()) {
        Write-Host 'Sin cambios.'
        exit 0
    }
}

function Generar-Datos([string]$Fecha) {
    if (-not (Test-Path -LiteralPath $CarpetaGrabacion -PathType Container)) {
        New-Item -ItemType Directory -Path $CarpetaGrabacion | Out-Null
    }
    # Solo se borra lo que el generador escribe, y solo dentro de datos-grabacion\.
    Get-ChildItem -LiteralPath $CarpetaGrabacion -File |
        Where-Object { $_.Extension -eq '.xlsx' -or $_.Name -eq 'vigencia.txt' } |
        Remove-Item -Force
    $generador = Join-Path (Join-Path $Raiz 'Backend') 'scripts'
    $comando = "pip install --quiet --no-cache-dir --disable-pip-version-check --target /tmp/deps openpyxl==$VersionOpenpyxl && PYTHONPATH=/tmp/deps python /generador/generar_dataset_demo.py --perfil grabacion --fecha-base `$FECHA_BASE --salida /salida"
    $previo = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & docker run --rm `
            --env "FECHA_BASE=$Fecha" `
            --env HOME=/tmp `
            --env PYTHONDONTWRITEBYTECODE=1 `
            --mount "type=bind,source=$generador,target=/generador,readonly" `
            --mount "type=bind,source=$CarpetaGrabacion,target=/salida" `
            $ImagenPython `
            sh -c $comando
        $codigo = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previo
    }
    if ($codigo -ne 0) { Salir-ConError 'no se pudieron generar los datos de la grabacion.' }
}

function Esperar-Listo {
    $reloj = [System.Diagnostics.Stopwatch]::StartNew()
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
        if ($ultimo -eq 'LISTO') { return }
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
}

if ($Estado -eq 'grabacion') {
    $hoy = (Get-Date).ToString('yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
    Write-Host "[1/5] Generando datos-grabacion\ con fecha $hoy (datos inventados)..."
    Generar-Datos $hoy
    # Gana a HISTORICO_DIR de .env.e2e solo en este proceso.
    $env:HISTORICO_DIR = $DatosGrabacion
}
else {
    Write-Host '[1/5] Datos: libros sinteticos de la E2E (.env.e2e).'
}

Write-Host "[2/5] Borrando 8081 (down -v, solo el proyecto $Proyecto)..."
if (-not (Compose @('down', '-v', '--remove-orphans'))) { Salir-ConError "no se pudo bajar $Proyecto." }

Write-Host '[3/5] Levantando 8081 (reconstruye las imagenes; puede tardar)...'
if (-not (Compose @('up', '-d', '--build'))) {
    [Console]::Error.WriteLine("ERROR: no se pudo levantar $Proyecto.")
    Ayuda-Logs
    exit 1
}

Write-Host "[4/5] Esperando a que el sistema este listo (maximo $($LimiteSegundos / 60) min)..."
Esperar-Listo

if ($Estado -eq 'grabacion') {
    Write-Host '[5/5] Sembrando listas, campanas y gestiones de los 4 meses anteriores...'
    if (-not (Compose @('cp', $ScriptSiembra, "backend:$ScriptSiembraContenedor"))) {
        Salir-ConError 'no se pudo copiar el script de siembra al contenedor.'
    }
    if (-not (Compose @('exec', '-T', 'backend', 'python', $ScriptSiembraContenedor))) {
        [Console]::Error.WriteLine('ERROR: la siembra fallo.')
        Ayuda-Logs
        exit 1
    }
    Write-Host ''
    Write-Host "Listo para grabar: abra $UrlApp (datos inventados)."
    Write-Host 'Para volver al estado de la E2E: powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 e2e'
}
else {
    Write-Host '[5/5] Sin siembra en el estado e2e.'
    Write-Host ''
    Write-Host "Listo: $UrlApp en el estado de la E2E. Ahora: cd Frontend; `$env:E2E_BASE_URL='http://localhost:8081'; npx playwright test --workers=1"
}
