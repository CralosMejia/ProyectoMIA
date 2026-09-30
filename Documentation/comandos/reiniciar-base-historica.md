# Reiniciar la base a solo datos históricos

Deja la base del stack principal (proyecto Docker `proyectofinal`, http://localhost:8080) como recién instalada: solo con el histórico de los libros `Control Gym*.xlsx` y el modelo v1. Scripts: `scripts/reiniciar-base-historica.ps1` (Windows) y `scripts/reiniciar-base-historica.sh` (bash), en la raíz del repositorio. Origen: R-008.

## Qué hace

Borra la base del stack principal y la vuelve a crear. Al arrancar, el sistema migra automáticamente los libros históricos de `HISTORICO_DIR` y entrena el modelo v1 (idéntico al anterior, [ADR-004](../adr/ADR-004-migracion-datos-al-arrancar.md)). Resultado: solo histórico, sin cargas mensuales ni listas.

## Cuándo usarlo

Para empezar las pruebas desde cero, después de haber hecho cargas o listas de prueba en el stack principal.

## Advertencias

- **Borra definitivamente** todas las cargas mensuales, los socios agregados por esas cargas, las listas y las predicciones (y cualquier otro dato del volumen principal, como campañas y gestiones cuando existan). **No se puede deshacer.**
- Es una operación manual y explícita del usuario, no una función de la aplicación: la aplicación sigue sin borrar datos ([DEVELOPMENT_GUIDELINES §Excepciones](../DEVELOPMENT_GUIDELINES.md)).
- **No toca** el stack de pruebas `mtabolic-e2e` (8081): el script fija el proyecto `proyectofinal` y no acepta otro.
- Requiere Docker en marcha y un `.env` en la raíz con `HISTORICO_DIR` apuntando a la carpeta con los libros `Control Gym*.xlsx`.
- Ejecútelo desde una terminal sin las variables del `.env` exportadas: las variables de la shell ganan a `--env-file` ([10-docker §Stack E2E aislado](../docs/backend/10-docker.md)).

## Cómo ejecutarlo

Desde cualquier carpeta (el script resuelve la raíz desde su propia ubicación). Pide escribir exactamente `BORRAR`; cualquier otra respuesta cancela sin tocar nada.

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\reiniciar-base-historica.ps1
```

Bash (Linux, macOS o Git Bash):

```bash
scripts/reiniciar-base-historica.sh
```

Sin preguntar (uso no interactivo, **borra sin confirmación**): `-Si` en PowerShell, `--si` en bash.

## Paso a paso

1. Comprueba que existen `compose.yaml` y `.env` en la raíz y que están disponibles `docker` y `curl`. Si falta algo, sale con error antes de ejecutar cualquier comando de Docker.
2. Muestra qué se borrará y pide la confirmación `BORRAR` (salvo con `-Si` / `--si`).
3. `docker compose -p proyectofinal -f compose.yaml --env-file .env down -v` (borra contenedores y el volumen de la base principal).
4. `docker compose -p proyectofinal -f compose.yaml --env-file .env up -d` (recrea la base; el servicio `migrate` aplica el esquema y el backend migra el histórico y entrena el modelo v1).
5. Consulta `GET /api/v1/sistema/estado` hasta que esté `LISTO` (espera como máximo 15 minutos).
6. Muestra los conteos de `socios`, `membresias`, `cargas`, `listas_priorizadas` y `predicciones`, sin imprimir credenciales.

## Resultado esperado

Estado `LISTO` con modelo v1 y los conteos:

| Tabla | Filas |
|---|---|
| `socios` | 1.410 |
| `membresias` | 2.748 |
| `cargas` | 1 (la migración histórica) |
| `listas_priorizadas` | 0 |
| `predicciones` | 0 |

## Códigos de salida y errores

- `0`: terminó bien o se canceló (sin tocar nada).
- Distinto de `0`: falta una precondición (`compose.yaml`, `.env`, `docker`, `curl`), falló un comando de Docker, el estado quedó en `FALTAN_DATOS_HISTORICOS` o se agotaron los 15 minutos. El script muestra el último estado.

**Si termina en `FALTAN_DATOS_HISTORICOS`:** los libros no se encontraron o la migración falló. Revise que `HISTORICO_DIR` en `.env` apunte a la carpeta con los `Control Gym*.xlsx` y reinicie el backend (`docker compose -p proyectofinal restart backend`); la migración se reintenta al arrancar ([10-docker §Uso](../docs/backend/10-docker.md)). Si hace falta, vuelva a ejecutar el script.

## Verificación

Comprobados la sintaxis (`bash -n` y el parser de PowerShell) y la cancelación sin tocar Docker. La ejecución real no se lanzó en R-008 porque la base principal tenía listas del usuario; la misma operación hecha a mano antes dio el resultado esperado.
