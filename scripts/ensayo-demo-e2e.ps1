<#
.SYNOPSIS
  Ensayo de la demostracion (03, seccion 21) en el stack AISLADO mtabolic-e2e (R-013 T10, D7-OP-04).

.DESCRIPTION
  Desplaza fechas de los datos de prueba para ensayar CU-09 (alertas) y CU-02 (fecha de
  reentrenamiento perdida -> OMITIDO) sin reloj simulado en ejecucion: equivale a adelantar el
  reloj (decision (c) de R-013). Equivalente a scripts/ensayo-demo-e2e.sh.

  Subcomandos:
    adelantar-seguimientos <dias>
      Resta <dias> (1..60) a fecha_seguimiento de las gestiones PENDIENTE no borradas, en una
      sola transaccion, e imprime cuantas cambio. Con seguimiento = hoy + 1,
      "adelantar-seguimientos 1" la pone "para hoy" y otro "adelantar-seguimientos 1" la deja
      "vencida".
    perder-fecha-reentrenamiento
      Pone la proxima fecha programada de reentrenamiento en AYER (fecha de Ecuador, UTC-5) y
      reinicia el backend: al arrancar, el planificador registra un intento OMITIDO y mueve la
      proxima fecha 6 meses. Imprime cuantos OMITIDO habia antes y despues.

  Seguridad:
  - Proyecto FIJO mtabolic-e2e con .env.e2e. Cualquier otro proyecto (proyectofinal incluido),
    subcomando o argumento invalido sale con codigo 1 SIN ejecutar ningun comando docker.
  - Dentro del contenedor db se comprueba ademas que POSTGRES_DB termine en _e2e; si no, no se
    ejecuta nada.
  - Credenciales expandidas DENTRO del contenedor db (variables propias de postgres): no pasan
    por la linea de comandos del host ni se imprimen. No se muestra nada del .env.e2e.
  - Solo UPDATE de fechas; nunca DELETE, DROP, TRUNCATE ni down. La salida son conteos y
    fechas, sin datos personales.

.PARAMETER Subcomando
  adelantar-seguimientos | perder-fecha-reentrenamiento

.PARAMETER Dias
  Solo con adelantar-seguimientos: entero de 1 a 60.

.PARAMETER p
  Proyecto de compose; solo se acepta mtabolic-e2e (valor por defecto).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\ensayo-demo-e2e.ps1 adelantar-seguimientos 1
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\ensayo-demo-e2e.ps1 perder-fecha-reentrenamiento
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Subcomando = '',
    [Parameter(Position = 1)]
    [string]$Dias = '',
    [string]$p = 'mtabolic-e2e',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Resto = @()
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Proyecto = 'mtabolic-e2e'
$EnvNombre = '.env.e2e'
$DiasMax = 60
$EsperaMaxSeg = 120

function Salir-ConError([string]$Mensaje) {
    [Console]::Error.WriteLine("ERROR: $Mensaje")
    exit 1
}

$Uso = "Uso: ensayo-demo-e2e.ps1 adelantar-seguimientos <dias 1..$DiasMax> | perder-fecha-reentrenamiento [-p $Proyecto]"

# --- Argumentos (antes de cualquier comando docker) -------------------------------------
if ($p -cne $Proyecto) {
    Salir-ConError "proyecto no permitido: este script solo actua sobre $Proyecto."
}
# "-h"/"--ayuda" llegan a $Resto (PowerShell los toma por nombres de parametro).
if ($Subcomando -eq '' -and @($Resto).Count -eq 1 -and $Resto[0] -cin @('-h', '--ayuda')) {
    Write-Host $Uso
    exit 0
}
if (@($Resto).Count -gt 0) {
    Salir-ConError "argumento no reconocido: $($Resto[0])"
}
switch -CaseSensitive ($Subcomando) {
    'adelantar-seguimientos' {
        # Entero sin ceros a la izquierda, de 1 a 60.
        if ($Dias -notmatch '^[1-9][0-9]?$' -or [int]$Dias -gt $DiasMax) {
            Salir-ConError "dias debe ser un entero entre 1 y $DiasMax."
        }
        $NumeroDias = [int]$Dias
    }
    'perder-fecha-reentrenamiento' {
        if ($Dias -ne '') { Salir-ConError 'perder-fecha-reentrenamiento no admite argumentos.' }
    }
    default {
        [Console]::Error.WriteLine($Uso)
        Salir-ConError "subcomando no reconocido: '$Subcomando'."
    }
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

function Invoke-Compose {
    param([string[]]$Argumentos)
    & docker compose -p $Proyecto -f $ComposeFile --env-file $EnvFile @Argumentos
}

# Sin comillas dobles en los argumentos para que Windows PowerShell 5.1 no las altere al
# llamar a docker: el SQL entra por la entrada estandar de psql (-f -), en una transaccion.
# Aborta (codigo 3) dentro del contenedor si la base no es la del stack e2e.
$ShPsql = 'case $POSTGRES_DB in *_e2e) ;; *) echo la base del contenedor no es de e2e, no se toca nada >&2; exit 3 ;; esac; ' +
    'psql -X -At -1 -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB -f -'

# Ejecuta una sentencia SQL fija (sin entrada del usuario salvo los dias, ya validados como
# entero 1..60) y devuelve la ultima linea del resultado, o $null si fallo.
function Invoke-SqlE2e([string]$Sql) {
    $salida = $Sql | Invoke-Compose -Argumentos @('exec', '-T', 'db', 'sh', '-c', $ShPsql)
    if ($LASTEXITCODE -ne 0) { return $null }
    return ([string](@($salida) | Select-Object -Last 1)).Trim()
}

$SqlOmitidos = "SELECT count(*) FROM intentos_reentrenamiento WHERE resultado = 'OMITIDO';"
# Fecha de negocio = Ecuador, UTC-5 fijo (igual que hoy_en_negocio del backend).
$SqlHoyNegocio = "((now() AT TIME ZONE 'UTC') - interval '5 hours')::date"

switch -CaseSensitive ($Subcomando) {
    'adelantar-seguimientos' {
        Write-Host "=== ${Proyecto}: adelantar seguimientos $NumeroDias dia(s) ==="
        $cambiadas = Invoke-SqlE2e ("WITH c AS (UPDATE gestiones_retencion SET fecha_seguimiento = fecha_seguimiento - $NumeroDias, " +
            "updated_at = now() WHERE estado = 'PENDIENTE' AND deleted_at IS NULL RETURNING 1) SELECT count(*) FROM c;")
        if ($null -eq $cambiadas) {
            Salir-ConError "no se pudo actualizar (el contenedor db del proyecto $Proyecto esta en marcha?)."
        }
        if ($cambiadas -notmatch '^\d+$') { Salir-ConError 'respuesta inesperada de la base.' }
        Write-Host "Gestiones PENDIENTE desplazadas $NumeroDias dia(s) antes: $cambiadas"
    }

    'perder-fecha-reentrenamiento' {
        Write-Host "=== ${Proyecto}: perder la fecha programada de reentrenamiento ==="
        $antes = Invoke-SqlE2e $SqlOmitidos
        if ($null -eq $antes) {
            Salir-ConError "no se pudo leer la base (el contenedor db del proyecto $Proyecto esta en marcha?)."
        }
        if ($antes -notmatch '^\d+$') { Salir-ConError 'respuesta inesperada de la base.' }
        $fecha = Invoke-SqlE2e ("WITH c AS (UPDATE estado_sistema SET proxima_fecha_reentrenamiento = $SqlHoyNegocio - 1, " +
            "updated_at = now() WHERE id = 1 AND migracion_historica = 'COMPLETADA' RETURNING proxima_fecha_reentrenamiento) " +
            "SELECT coalesce(max(proxima_fecha_reentrenamiento)::text, 'NINGUNA') FROM c;")
        if ($null -eq $fecha) { Salir-ConError 'no se pudo actualizar la fecha programada.' }
        if ($fecha -ceq 'NINGUNA') {
            Salir-ConError 'la migracion historica no esta COMPLETADA; no se cambio nada.'
        }
        Write-Host "Proxima fecha programada puesta en $fecha (ayer). Reiniciando el backend..."
        Invoke-Compose -Argumentos @('restart', 'backend') | Out-Null
        if ($LASTEXITCODE -ne 0) { Salir-ConError 'no se pudo reiniciar el backend.' }

        $esperado = [int]$antes + 1
        $despues = [int]$antes
        $segundos = 0
        while ($segundos -lt $EsperaMaxSeg) {
            Start-Sleep -Seconds 3
            $segundos += 3
            $valor = Invoke-SqlE2e $SqlOmitidos
            if ($null -eq $valor -or $valor -notmatch '^\d+$') { continue }
            $despues = [int]$valor
            if ($despues -ge $esperado) { break }
        }
        Write-Host "Intentos OMITIDO: antes $antes, despues $despues"
        if ($despues -lt $esperado) {
            Salir-ConError "el planificador no registro el OMITIDO en ${EsperaMaxSeg}s (REENTRENAMIENTO_AUTOMATICO activo?)."
        }
        $proxima = Invoke-SqlE2e "SELECT coalesce(proxima_fecha_reentrenamiento::text, 'NINGUNA') FROM estado_sistema WHERE id = 1;"
        if ($null -eq $proxima) { Salir-ConError 'no se pudo leer la proxima fecha.' }
        Write-Host "Nueva proxima fecha programada: $proxima"
    }
}
exit 0
