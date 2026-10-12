# Respaldo y restauración de la base

Copia de seguridad de la base de un stack y restauración en una base **nueva** del mismo stack. Scripts en la raíz del repositorio: `scripts/respaldar-base.{ps1,sh}` y `scripts/restaurar-base.{ps1,sh}`. Origen: R-013 (D7-BD-01).

## Qué hacen

- **Respaldo** (solo lectura): `pg_dump -Fc` de `POSTGRES_DB` dentro del contenedor `db` y copia al PC en `respaldos/<proyecto>-AAAAMMDD-HHMMSS.dump`, más `respaldos/<mismo>.conteos` con 9 líneas `tabla=n` (`socios`, `membresias`, `cargas`, `modelos`, `intentos_reentrenamiento`, `listas_priorizadas`, `predicciones`, `campanias`, `gestiones_retencion`).
- **Restauración**: crea una base nueva, restaura en ella el `.dump`, aplica los permisos del rol de la aplicación (`Backend/db/roles/permisos.sql`, si el rol existe; [ADR-012](../adr/ADR-012-rol-de-aplicacion-sin-superusuario.md)) y compara los 9 conteos con el `.conteos` del respaldo.

## Advertencias

- `respaldos/` está en `.gitignore`: **contiene datos personales de socios**. Guárdela fuera de carpetas compartidas.
- Proyectos permitidos (lista blanca): `proyectofinal` (`.env`, por defecto), `mtabolic-e2e` (`.env.e2e`) y `mtabolic-limpia` (`.env.limpia`). Otro nombre, o un `.env*` inexistente, sale con código 1 **sin ejecutar ningún comando de Docker**.
- El respaldo nunca ejecuta `DROP`, `DELETE`, `down` ni `restart`. Lee los conteos antes y después del volcado; si cambiaron (hubo escrituras durante el respaldo) **descarta el volcado** y sale con 1: repítalo.
- La restauración **solo crea una base nueva**: nunca renombra, sobrescribe ni borra bases; la base en uso no cambia. Poner en uso la restaurada es un paso manual ([Backend/README §5](../../Backend/README.md)).
- Las credenciales se expanden dentro del contenedor `db`; los scripts no imprimen nada del `.env`.
- Requiere Docker en marcha y el contenedor `db` del proyecto arriba.

## Cómo ejecutarlo

Desde cualquier carpeta (los scripts resuelven la raíz desde su propia ubicación).

Respaldo, Windows (PowerShell) y bash:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\respaldar-base.ps1                  # stack principal
powershell -ExecutionPolicy Bypass -File scripts\respaldar-base.ps1 -p mtabolic-e2e
```

```bash
scripts/respaldar-base.sh                    # stack principal
scripts/respaldar-base.sh -p mtabolic-e2e
```

Restauración:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\restaurar-base.ps1 respaldos\<archivo>.dump [-p proyecto] [-Base nombre]
```

```bash
scripts/restaurar-base.sh respaldos/<archivo>.dump [-p proyecto] [--base nombre]
```

- El `.conteos` debe estar junto al `.dump`, con el mismo nombre.
- Base por defecto: `app_db_restaurada_AAAAMMDDHHMMSS`. Un nombre propio debe cumplir `^[a-z_][a-z0-9_]{0,62}$`, no existir, no ser `postgres`/`template0`/`template1` y ser distinto de `POSTGRES_DB`; si no, código 1 sin crear nada.
- El rol de la aplicación se toma de `APP_DB_USER` (variable de la shell, si no la línea del `.env`, si no `mtabolic_app`). Si el rol aún no existe (S23 sin activar), avisa y omite sus permisos.

## Paso a paso

Respaldo: (1) conteos antes · (2) `pg_dump -Fc` en `/tmp` del contenedor · (3) `docker compose cp` al PC y borrado del temporal · (4) conteos después; si coinciden escribe el `.conteos`.

Restauración: (1) valida el nombre y que la base no exista · (2) `createdb` · (3) `pg_restore --no-owner --no-privileges --exit-on-error` · (4) permisos del rol de la aplicación · (5) compara conteos.

## Resultado esperado y códigos de salida

- Respaldo: muestra las rutas del `.dump` (tamaño en bytes) y del `.conteos` con los 9 conteos → `0`.
- Restauración: `Conteos iguales` con los 9 conteos y `Base restaurada: <nombre> (la base en uso no se ha modificado)` → `0`. Con diferencias, lista `tabla: respaldo -> restaurada` y sale con `1`: la base queda creada pero **no debe ponerse en uso**. Si falla `pg_restore`, la base nueva queda incompleta (el script no la borra).

## Verificación

R-013: respaldo y restauración en el stack `mtabolic-e2e` con conteos iguales y lectura como rol de la aplicación en la base restaurada; respaldo real del stack principal antes de activar S23, con conteos iguales tras la reconstrucción.
