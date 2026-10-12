<#
.SYNOPSIS
  Respaldo de SOLO LECTURA de la base de un stack de compose (D7-BD-01).

.DESCRIPTION
  Genera en respaldos\ (carpeta no versionada: contiene datos personales de socios):
    <proyecto>-AAAAMMDD-HHMMSS.dump     pg_dump -Fc de POSTGRES_DB
    <proyecto>-AAAAMMDD-HHMMSS.conteos  9 lineas tabla=n con los conteos de la base respaldada

  Seguridad:
  - Lista blanca de proyectos: proyectofinal (.env), mtabolic-e2e (.env.e2e) y
    mtabolic-limpia (.env.limpia). Cualquier otro nombre sale con codigo 1 sin ejecutar docker.
  - Solo lee: pg_dump y SELECT count(*). Nunca DROP, DELETE, down ni restart.
  - Las credenciales se expanden DENTRO del contenedor db (variables propias de postgres):
    no pasan por la linea de comandos del host ni se imprimen. No se muestra nada del .env.
  - Conteos antes y despues del volcado: como la app nunca borra filas, si coinciden son
    exactamente los del volcado; si no coinciden (hubo escrituras) se descarta y sale con 1.
  - El volcado se genera dentro del contenedor y se copia con "docker compose cp", lo que
    evita que PowerShell altere el archivo binario.

.PARAMETER p
  Proyecto de compose (por defecto proyectofinal).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\respaldar-base.ps1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\respaldar-base.ps1 -p mtabolic-e2e
#>
[CmdletBinding()]
param(
    [string]$p = 'proyectofinal'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Tablas = @('socios', 'membresias', 'cargas', 'modelos', 'intentos_reentrenamiento',
    'listas_priorizadas', 'predicciones', 'campanias', 'gestiones_retencion')

function Salir-ConError([string]$Mensaje) {
    [Console]::Error.WriteLine("ERROR: $Mensaje")
    exit 1
}

$Proyecto = $p
switch -CaseSensitive ($Proyecto) {
    'proyectofinal' { $EnvNombre = '.env' }
    'mtabolic-e2e' { $EnvNombre = '.env.e2e' }
    'mtabolic-limpia' { $EnvNombre = '.env.limpia' }
    default { Salir-ConError 'proyecto no permitido: solo proyectofinal, mtabolic-e2e o mtabolic-limpia.' }
}

$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ComposeFile = Join-Path $Raiz 'compose.yaml'
$EnvFile = Join-Path $Raiz $EnvNombre

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    Salir-ConError "no se encontro compose.yaml en la raiz del proyecto ($Raiz)."
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Salir-ConError "no se encontro el archivo $EnvNombre en la raiz del proyecto ($Raiz)."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Salir-ConError 'no se encontro el comando docker. Instale o inicie Docker Desktop.'
}

$Sello = Get-Date -Format 'yyyyMMdd-HHmmss'
$Nombre = "$Proyecto-$Sello"
$DirRespaldos = Join-Path $Raiz 'respaldos'
$Dump = Join-Path $DirRespaldos "$Nombre.dump"
$Conteos = Join-Path $DirRespaldos "$Nombre.conteos"
$TmpContenedor = "/tmp/$Nombre.dump"

# Una fila con un conteo por columna, en el orden de $Tablas. Sin comillas dobles en los
# argumentos para que Windows PowerShell 5.1 no las altere al llamar a docker.
$Consulta = 'SELECT ' + (($Tablas | ForEach-Object { "(SELECT count(*) FROM $_)" }) -join ', ')
$ShConteos = 'psql -X -At -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -c ''' + $Consulta + ''''

function Invoke-Compose {
    param([string[]]$Argumentos)
    & docker compose -p $Proyecto -f $ComposeFile --env-file $EnvFile @Argumentos
}

# docker compose cp escribe su barra de progreso en stderr: se captura y solo se muestra si
# la copia falla. Devuelve el codigo de salida de docker.
function Copiar-SinProgreso([string[]]$Argumentos) {
    $ErrorActionPreference = 'Continue'
    $salida = Invoke-Compose -Argumentos $Argumentos 2>&1
    $codigo = $LASTEXITCODE
    if ($codigo -ne 0) {
        @($salida) | ForEach-Object { [Console]::Error.WriteLine([string]$_) }
    }
    return $codigo
}

function Leer-Conteos {
    $salida = Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', $ShConteos)
    if ($LASTEXITCODE -ne 0) { return $null }
    $valores = ([string](@($salida) | Select-Object -Last 1)).Trim() -split '\|'
    if ($valores.Count -ne $Tablas.Count) { return $null }
    $lineas = for ($i = 0; $i -lt $Tablas.Count; $i++) {
        if ($valores[$i] -notmatch '^\d+$') { return $null }
        "$($Tablas[$i])=$($valores[$i])"
    }
    return ($lineas -join "`n")
}

function Limpiar-Contenedor {
    try { Invoke-Compose -Argumentos @('exec', '-T', 'db', 'rm', '-f', $TmpContenedor) | Out-Null } catch { }
}

New-Item -ItemType Directory -Force -Path $DirRespaldos | Out-Null

Write-Host "=== Respaldo de la base del proyecto $Proyecto (solo lectura) ==="
Write-Host '[1/4] Conteos antes del volcado...'
$antes = Leer-Conteos
if ($null -eq $antes) {
    Salir-ConError "no se pudieron leer los conteos (el contenedor db del proyecto $Proyecto esta en marcha?)."
}

Write-Host '[2/4] Volcado con pg_dump -Fc dentro del contenedor db...'
Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', "pg_dump -U `$POSTGRES_USER -d `$POSTGRES_DB -Fc -f $TmpContenedor")
if ($LASTEXITCODE -ne 0) {
    Limpiar-Contenedor
    Salir-ConError 'fallo pg_dump.'
}

Write-Host "[3/4] Copiando el volcado a respaldos\$Nombre.dump..."
$codigoCopia = Copiar-SinProgreso @('cp', "db:$TmpContenedor", $Dump)
Limpiar-Contenedor
if ($codigoCopia -ne 0) {
    Salir-ConError 'no se pudo copiar el volcado al PC.'
}
if (-not (Test-Path -LiteralPath $Dump -PathType Leaf) -or (Get-Item -LiteralPath $Dump).Length -eq 0) {
    Salir-ConError 'el volcado copiado esta vacio.'
}

Write-Host '[4/4] Conteos despues del volcado...'
$despues = Leer-Conteos
if ($null -eq $despues) {
    Salir-ConError 'no se pudieron leer los conteos despues del volcado.'
}
if ($antes -cne $despues) {
    Remove-Item -LiteralPath $Dump -Force
    Salir-ConError 'la base cambio durante el respaldo (hubo escrituras); se descarto el volcado. Repita el respaldo.'
}

# UTF-8 sin BOM y fin de linea LF: el mismo formato que genera respaldar-base.sh.
[System.IO.File]::WriteAllText($Conteos, $antes + "`n", (New-Object System.Text.UTF8Encoding($false)))

Write-Host 'Respaldo creado:'
Write-Host "  respaldos\$Nombre.dump ($((Get-Item -LiteralPath $Dump).Length) bytes)"
Write-Host "  respaldos\$Nombre.conteos"
foreach ($linea in ($antes -split "`n")) { Write-Host "    $linea" }
Write-Host 'Guarde la carpeta respaldos\ fuera de carpetas compartidas: contiene datos personales.'
exit 0
