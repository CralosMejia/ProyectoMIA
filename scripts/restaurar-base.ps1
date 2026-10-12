<#
.SYNOPSIS
  Restaura un respaldo de scripts\respaldar-base.ps1 en una base NUEVA del stack (D7-BD-01).

.DESCRIPTION
  Pasos: createdb de la base nueva, pg_restore --no-owner --no-privileges --exit-on-error,
  permisos del rol de la aplicacion (Backend\db\roles\permisos.sql, si el rol existe) y
  comparacion de los 9 conteos con el archivo .conteos del respaldo: "Conteos iguales" y
  codigo 0, o la lista de diferencias y codigo 1.

  Seguridad:
  - Lista blanca de proyectos: proyectofinal (.env), mtabolic-e2e (.env.e2e) y
    mtabolic-limpia (.env.limpia). Nombre de base validado ANTES de crear nada.
  - Nunca renombra, sobrescribe ni borra bases: la base en uso no cambia. Poner en uso la
    restaurada es un paso manual (Backend\README.md, seccion 5).
  - Las credenciales se expanden DENTRO del contenedor db; no se imprime nada del .env.

.PARAMETER Archivo
  Respaldo .dump (con su .conteos al lado).

.PARAMETER p
  Proyecto de compose (por defecto proyectofinal).

.PARAMETER Base
  Nombre de la base nueva (por defecto app_db_restaurada_AAAAMMDDHHMMSS). Debe cumplir
  ^[a-z_][a-z0-9_]{0,62}$, no existir y ser distinto de POSTGRES_DB.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\restaurar-base.ps1 respaldos\mtabolic-e2e-20261001-101500.dump -p mtabolic-e2e
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Archivo = '',
    [string]$p = 'proyectofinal',
    [string]$Base = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Tablas = @('socios', 'membresias', 'cargas', 'modelos', 'intentos_reentrenamiento',
    'listas_priorizadas', 'predicciones', 'campanias', 'gestiones_retencion')
# \A y \z anclan la cadena completa: en .NET '$' tambien acepta un salto de linea final.
$PatronNombre = '\A[a-z_][a-z0-9_]{0,62}\z'

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
$Permisos = Join-Path $Raiz 'Backend\db\roles\permisos.sql'

# --- Precondiciones (antes de cualquier comando docker) ---------------------------------
if ([string]::IsNullOrWhiteSpace($Archivo)) {
    Salir-ConError 'falta el archivo de respaldo. Uso: restaurar-base.ps1 <archivo.dump> [-p proyecto] [-Base nombre]'
}
if (-not $Archivo.EndsWith('.dump')) {
    Salir-ConError 'el respaldo debe ser un archivo .dump de scripts\respaldar-base.ps1.'
}
if (-not (Test-Path -LiteralPath $Archivo -PathType Leaf) -or (Get-Item -LiteralPath $Archivo).Length -eq 0) {
    Salir-ConError "no existe el archivo de respaldo o esta vacio: $Archivo"
}
$Dump = (Resolve-Path -LiteralPath $Archivo).Path
$ArchivoConteos = $Dump.Substring(0, $Dump.Length - '.dump'.Length) + '.conteos'
if (-not (Test-Path -LiteralPath $ArchivoConteos -PathType Leaf)) {
    Salir-ConError "no existe el archivo de conteos del respaldo: $ArchivoConteos"
}
$lineasEsperadas = @(Get-Content -LiteralPath $ArchivoConteos | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
if ($lineasEsperadas.Count -ne $Tablas.Count) {
    Salir-ConError "el archivo de conteos debe tener $($Tablas.Count) lineas tabla=n."
}
for ($i = 0; $i -lt $Tablas.Count; $i++) {
    if ($lineasEsperadas[$i] -cnotmatch "^$($Tablas[$i])=\d+$") {
        Salir-ConError "el archivo de conteos no tiene el formato esperado (linea $($i + 1): $($Tablas[$i])=n)."
    }
}

if ([string]::IsNullOrEmpty($Base)) {
    $Base = 'app_db_restaurada_' + (Get-Date -Format 'yyyyMMddHHmmss')
}
if ($Base -cnotmatch $PatronNombre) {
    Salir-ConError "nombre de base no valido: debe cumplir $PatronNombre."
}
if (@('postgres', 'template0', 'template1') -ccontains $Base) {
    Salir-ConError 'nombre de base reservado por PostgreSQL.'
}

if (-not (Test-Path -LiteralPath $ComposeFile -PathType Leaf)) {
    Salir-ConError "no se encontro compose.yaml en la raiz del proyecto ($Raiz)."
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    Salir-ConError "no se encontro el archivo $EnvNombre en la raiz del proyecto ($Raiz)."
}
if (-not (Test-Path -LiteralPath $Permisos -PathType Leaf)) {
    Salir-ConError 'no se encontro Backend\db\roles\permisos.sql.'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Salir-ConError 'no se encontro el comando docker. Instale o inicie Docker Desktop.'
}

# Rol de la aplicacion: la variable de entorno gana; si no, la linea APP_DB_USER del .env;
# si no, mtabolic_app. Solo se lee esa linea (no es secreta) y no se imprime nada del .env.
$AppUser = $env:APP_DB_USER
if ([string]::IsNullOrWhiteSpace($AppUser)) {
    $linea = Select-String -LiteralPath $EnvFile -Pattern '^\s*APP_DB_USER\s*=' | Select-Object -Last 1
    if ($null -ne $linea) {
        $AppUser = ($linea.Line -split '=', 2)[1].Trim().Trim('"', "'")
    }
}
if ([string]::IsNullOrWhiteSpace($AppUser)) { $AppUser = 'mtabolic_app' }
if ($AppUser -cnotmatch $PatronNombre) {
    Salir-ConError 'APP_DB_USER no es un nombre de rol valido.'
}

function Invoke-Compose {
    param([string[]]$Argumentos)
    & docker compose -p $Proyecto -f $ComposeFile --env-file $EnvFile @Argumentos
}

# psql como propietario sobre la base $BaseDestino. Sin comillas dobles en los argumentos
# para que Windows PowerShell 5.1 no las altere; los nombres ya estan validados.
function Invoke-Psql([string]$BaseDestino, [string]$Sql) {
    $sh = 'psql -X -At -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d ' + $BaseDestino + ' -c ''' + ($Sql -replace "'", "'\''") + ''''
    $salida = Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', $sh)
    if ($LASTEXITCODE -ne 0) { return $null }
    return ([string](@($salida) | Select-Object -Last 1)).Trim()
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

$TmpDump = "/tmp/restaurar-$Base.dump"
$TmpPermisos = "/tmp/permisos-$Base.sql"
function Limpiar-Contenedor {
    try { Invoke-Compose -Argumentos @('exec', '-T', 'db', 'rm', '-f', $TmpDump, $TmpPermisos) | Out-Null } catch { }
}

Write-Host "=== Restauracion en una base NUEVA (proyecto $Proyecto, base $Base) ==="
Write-Host '[1/5] Comprobando el nombre de la base...'
$baseEnUso = Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', 'printf %s $POSTGRES_DB')
if ($LASTEXITCODE -ne 0) {
    Salir-ConError "no se pudo consultar el contenedor db del proyecto $Proyecto (esta en marcha?)."
}
$baseEnUso = ([string](@($baseEnUso) | Select-Object -Last 1)).Trim()
if ([string]::IsNullOrEmpty($baseEnUso)) { Salir-ConError 'no se pudo leer POSTGRES_DB del contenedor db.' }
if ($Base -ceq $baseEnUso) {
    Salir-ConError 'la base nueva no puede llamarse igual que la base en uso (POSTGRES_DB).'
}
$existe = Invoke-Psql 'postgres' "SELECT count(*) FROM pg_database WHERE datname = '$Base'"
if ($null -eq $existe) { Salir-ConError 'no se pudo comprobar si la base existe.' }
if ($existe -ne '0') { Salir-ConError 'ya existe una base con ese nombre; elija otro con -Base.' }

Write-Host '[2/5] Creando la base nueva...'
Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', ('createdb -U $POSTGRES_USER -O $POSTGRES_USER ' + $Base))
if ($LASTEXITCODE -ne 0) { Salir-ConError 'no se pudo crear la base nueva.' }

Write-Host '[3/5] Restaurando el respaldo (pg_restore --no-owner --no-privileges --exit-on-error)...'
# docker compose cp copia el binario sin que PowerShell lo altere.
$codigoCopia = Copiar-SinProgreso @('cp', $Dump, "db:$TmpDump")
if ($codigoCopia -ne 0) {
    Limpiar-Contenedor
    Salir-ConError "no se pudo copiar el respaldo al contenedor db. La base $Base quedo creada y vacia."
}
Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', ('pg_restore -U $POSTGRES_USER -d ' + $Base + ' --no-owner --no-privileges --exit-on-error ' + $TmpDump))
if ($LASTEXITCODE -ne 0) {
    Limpiar-Contenedor
    Salir-ConError "fallo pg_restore. La base $Base quedo incompleta: no la ponga en uso (este script nunca borra bases)."
}

Write-Host '[4/5] Permisos del rol de la aplicacion...'
$rol = Invoke-Psql 'postgres' "SELECT count(*) FROM pg_roles WHERE rolname = '$AppUser'"
if ($null -eq $rol) {
    Limpiar-Contenedor
    Salir-ConError 'no se pudo comprobar el rol de la aplicacion.'
}
if ($rol -eq '1') {
    $codigo = Copiar-SinProgreso @('cp', $Permisos, "db:$TmpPermisos")
    if ($codigo -eq 0) {
        Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', ('psql -X -q -1 -v ON_ERROR_STOP=1 -v VERBOSITY=terse -U $POSTGRES_USER -d ' + $Base + ' -v app_user=' + $AppUser + ' -v propietario=$POSTGRES_USER -f ' + $TmpPermisos)) | Out-Null
        $codigo = $LASTEXITCODE
    }
    if ($codigo -ne 0) {
        Limpiar-Contenedor
        Salir-ConError "no se pudieron aplicar los permisos del rol de la aplicacion a $Base."
    }
    Write-Host '  Permisos aplicados.'
}
else {
    Write-Host '  AVISO: el rol de la aplicacion no existe todavia (S23 sin activar); se omiten sus permisos.'
}
Limpiar-Contenedor

Write-Host '[5/5] Comparando conteos con el respaldo...'
$consulta = 'SELECT ' + (($Tablas | ForEach-Object { "(SELECT count(*) FROM $_)" }) -join ', ')
$fila = Invoke-Psql $Base $consulta
if ($null -eq $fila) { Salir-ConError "no se pudieron leer los conteos de $Base." }
$valores = $fila -split '\|'
if ($valores.Count -ne $Tablas.Count) { Salir-ConError "respuesta inesperada al leer los conteos de $Base." }

$diferencias = @()
$obtenidos = @()
for ($i = 0; $i -lt $Tablas.Count; $i++) {
    $obtenido = "$($Tablas[$i])=$($valores[$i])"
    $obtenidos += $obtenido
    if ($obtenido -cne $lineasEsperadas[$i]) {
        $diferencias += "  $($Tablas[$i]): $(($lineasEsperadas[$i] -split '=', 2)[1]) -> $($valores[$i])"
    }
}

if ($diferencias.Count -eq 0) {
    Write-Host 'Conteos iguales'
    foreach ($o in $obtenidos) { Write-Host "  $o" }
    Write-Host "Base restaurada: $Base (la base en uso no se ha modificado)."
    exit 0
}

[Console]::Error.WriteLine('Conteos distintos (tabla: respaldo -> restaurada):')
foreach ($d in $diferencias) { [Console]::Error.WriteLine($d) }
[Console]::Error.WriteLine("La base $Base quedo creada pero no coincide con el respaldo: no la ponga en uso.")
exit 1
