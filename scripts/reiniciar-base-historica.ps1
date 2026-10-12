<#
.SYNOPSIS
  Reinicia la base del stack PRINCIPAL (proyecto de compose "proyectofinal") dejando solo el historico.

.DESCRIPTION
  Borra el volumen (down -v), vuelve a levantar el stack (up -d), espera a que la migracion
  historica termine (estado LISTO) y muestra los conteos finales.

  OPERACION IRREVERSIBLE: borra cargas por plantilla, listas, predicciones y todo lo demas del
  volumen principal. Es una accion manual y explicita del usuario, no una funcion de la app.

  Seguridad:
  - El nombre del proyecto esta fijo (-p proyectofinal) y no se acepta otro. El stack E2E
    aislado (mtabolic-e2e) nunca se toca desde este script.
  - compose.yaml y .env se resuelven desde la ubicacion del script (funciona desde cualquier
    directorio actual). Las credenciales solo las lee docker compose; el script no las imprime.

.PARAMETER Si
  No pide confirmacion (uso no interactivo; borra sin preguntar).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\reiniciar-base-historica.ps1
#>
[CmdletBinding()]
param(
    [switch]$Si
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Proyecto = 'proyectofinal'
$EsperaSegundos = 5
$LimiteSegundos = 900

$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ComposeFile = Join-Path $Raiz 'compose.yaml'
$EnvFile = Join-Path $Raiz '.env'

function Salir-ConError([string]$Mensaje) {
    [Console]::Error.WriteLine("ERROR: $Mensaje")
    exit 1
}

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    Salir-ConError "no se encontro compose.yaml en la raiz del proyecto ($Raiz)."
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Salir-ConError "no se encontro el archivo .env en la raiz del proyecto ($Raiz). Copie .env.example a .env y rellenelo."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Salir-ConError 'no se encontro el comando docker. Instale o inicie Docker Desktop.'
}

# Puerto del FRONTEND: el estado se consulta por nginx (/api), porque desde R-011 (CU-00) el
# puerto del backend responde 403 al host salvo /api/v1/health. La variable de entorno gana
# (igual que en docker compose); si no, la linea FRONTEND_PORT del .env; si no, 8080. Solo se
# lee esa linea y no se imprime nada del .env.
$Puerto = $env:FRONTEND_PORT
if ([string]::IsNullOrWhiteSpace($Puerto)) {
    $linea = Select-String -LiteralPath $EnvFile -Pattern '^\s*FRONTEND_PORT\s*=' | Select-Object -Last 1
    if ($null -ne $linea) {
        $Puerto = ($linea.Line -split '=', 2)[1].Trim().Trim('"', "'")
    }
}
if ([string]::IsNullOrWhiteSpace($Puerto)) { $Puerto = '8080' }
if ($Puerto -notmatch '^\d+$') {
    Salir-ConError 'FRONTEND_PORT no es un numero de puerto valido.'
}
$UrlEstado = "http://127.0.0.1:$Puerto/api/v1/sistema/estado"

function Invoke-Compose {
    param([string[]]$Argumentos)
    & docker compose -p $Proyecto -f $ComposeFile --env-file $EnvFile @Argumentos
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine("ERROR: fallo 'docker compose $($Argumentos[0])' (codigo $LASTEXITCODE).")
        exit $LASTEXITCODE
    }
}

# --- Confirmacion -----------------------------------------------------------------------
Write-Host "=== Reinicio de la base PRINCIPAL (proyecto de compose: $Proyecto) ==="
Write-Host 'Se borrara TODO el volumen de la base principal, sin vuelta atras:'
Write-Host '  - cargas por plantilla confirmadas,'
Write-Host '  - listas priorizadas y sus predicciones,'
Write-Host '  - y todo lo demas guardado en esa base.'
Write-Host 'Despues se levanta el stack de nuevo: se vuelve a migrar el historico y se reentrena'
Write-Host 'el modelo v1 (identico al actual). El stack E2E aislado no se toca.'

if ($Si) {
    Write-Host 'Confirmacion omitida (-Si).'
}
else {
    $respuesta = Read-Host 'Escriba BORRAR para continuar'
    if ($respuesta -cne 'BORRAR') {
        Write-Host 'Cancelado. No se ha modificado nada.'
        exit 0
    }
}

# --- Reinicio ---------------------------------------------------------------------------
Write-Host '[1/4] Deteniendo el stack y borrando el volumen principal (down -v)...'
Invoke-Compose -Argumentos @('down', '-v')

Write-Host '[2/4] Levantando el stack (up -d)...'
Invoke-Compose -Argumentos @('up', '-d')

Write-Host "[3/4] Esperando a que el sistema este LISTO (maximo $($LimiteSegundos / 60) min)..."
$reloj = [System.Diagnostics.Stopwatch]::StartNew()
$ultimo = 'SIN_RESPUESTA'
while ($true) {
    try {
        $respuestaApi = Invoke-RestMethod -Uri $UrlEstado -Method Get -TimeoutSec 5
        $ultimo = [string]$respuestaApi.estado
        if ([string]::IsNullOrWhiteSpace($ultimo)) { $ultimo = 'SIN_RESPUESTA' }
    }
    catch {
        $ultimo = 'SIN_RESPUESTA'
    }
    $transcurrido = [int]$reloj.Elapsed.TotalSeconds
    Write-Host "  ${transcurrido}s: $ultimo"
    if ($ultimo -eq 'LISTO') { break }
    if ($ultimo -eq 'FALTAN_DATOS_HISTORICOS') {
        Salir-ConError 'el sistema termino en FALTAN_DATOS_HISTORICOS (revise los libros historicos y el log del backend).'
    }
    if ($transcurrido -ge $LimiteSegundos) {
        Salir-ConError "tiempo agotado sin llegar a LISTO. Ultimo estado: $ultimo"
    }
    Start-Sleep -Seconds $EsperaSegundos
}

Write-Host '[4/4] Conteos finales:'
# Las credenciales se expanden DENTRO del contenedor db (variables propias de postgres):
# no pasan por la linea de comandos del host ni aparecen en la salida. Sin comillas dobles
# en el argumento para que Windows PowerShell 5.1 no las altere al llamar a docker.
$consulta = 'psql -X -At -U $POSTGRES_USER -d $POSTGRES_DB -c ''SELECT (SELECT count(*) FROM socios), (SELECT count(*) FROM membresias), (SELECT count(*) FROM cargas), (SELECT count(*) FROM listas_priorizadas), (SELECT count(*) FROM predicciones)'''
$salida = & docker compose -p $Proyecto -f $ComposeFile --env-file $EnvFile exec -T db sh -c $consulta
if ($LASTEXITCODE -ne 0) {
    Salir-ConError "no se pudieron leer los conteos (codigo $LASTEXITCODE)."
}
$valores = ([string](@($salida) | Select-Object -Last 1)).Trim() -split '\|'
if ($valores.Count -ne 5) {
    Salir-ConError 'respuesta inesperada al leer los conteos.'
}
Write-Host "  socios:             $($valores[0])"
Write-Host "  membresias:         $($valores[1])"
Write-Host "  cargas:             $($valores[2])"
Write-Host "  listas_priorizadas: $($valores[3])"
Write-Host "  predicciones:       $($valores[4])"
Write-Host 'Reinicio terminado: base principal solo con el historico.'
