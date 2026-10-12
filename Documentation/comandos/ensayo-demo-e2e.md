# Ensayo de la demostración en el stack aislado

Desplaza fechas de los datos de prueba del stack `mtabolic-e2e` (http://localhost:8081) para ensayar el escenario de [03 §21](../03-casos-de-uso.md) sin reloj simulado en ejecución: equivale a adelantar el reloj. Scripts: `scripts/ensayo-demo-e2e.ps1` (Windows) y `scripts/ensayo-demo-e2e.sh` (bash). Origen: R-013 (D7-OP-04, decisión (c)).

## Cuándo usarlo

Para enseñar las alertas de seguimiento (CU-09: "Para hoy" y "Vencidos") y la fecha de reentrenamiento perdida (CU-02: intento `OMITIDO`) sin esperar días reales. El recorrido completo con reloj inyectado también está automatizado en `Backend/tests/integration/api/test_escenario_demostracion.py`.

## Advertencias

- **Solo el stack `mtabolic-e2e`** con `.env.e2e`. Cualquier otro proyecto (también `proyectofinal`), subcomando o argumento inválido sale con código 1 **sin ejecutar ningún comando de Docker**. Además, dentro del contenedor comprueba que `POSTGRES_DB` termine en `_e2e`.
- Solo hace `UPDATE` de fechas (en una transacción); nunca `DELETE`, `DROP`, `TRUNCATE` ni `down`. La salida son conteos y fechas, sin datos personales.
- Ejecútelo desde una terminal sin las variables del `.env` exportadas ([10-docker §Stack E2E aislado](../docs/backend/10-docker.md)).

## Cómo ejecutarlo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\ensayo-demo-e2e.ps1 adelantar-seguimientos 1
powershell -ExecutionPolicy Bypass -File scripts\ensayo-demo-e2e.ps1 perder-fecha-reentrenamiento
```

```bash
scripts/ensayo-demo-e2e.sh adelantar-seguimientos 1
scripts/ensayo-demo-e2e.sh perder-fecha-reentrenamiento
```

Opcional `-p mtabolic-e2e` (único valor aceptado). Ayuda: `-h` / `--ayuda` (bash).

| Subcomando | Qué hace | Salida |
|---|---|---|
| `adelantar-seguimientos <dias>` | Resta `<dias>` (entero 1..60) a `fecha_seguimiento` de las gestiones `PENDIENTE` no borradas. | `Gestiones PENDIENTE desplazadas N dia(s) antes: <n>` |
| `perder-fecha-reentrenamiento` | Pone la próxima fecha programada de reentrenamiento en ayer (fecha de negocio, Ecuador UTC-5) y reinicia el backend; al arrancar, el planificador registra un `OMITIDO` y mueve la fecha 6 meses ([ADR-011](../adr/ADR-011-reglas-del-reentrenamiento.md)). Espera hasta 120 s. | `Intentos OMITIDO: antes a, despues b` y la nueva fecha |

## Guion del ensayo (03 §21)

1. Migración: cubierta por la instalación limpia con libros reales (`mtabolic-limpia`, [10-docker](../docs/backend/10-docker.md)).
2. Acceso: desde una IP no autorizada de la red interna → `403`; desde el PC por 8081 → la app.
3. Carga con error rechazada; corregida, confirmada.
4. Lista con la **fecha de hoy** ([ADR-006](../adr/ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md)); la comparación con el notebook al 31-08-2026 se hace con `Backend/scripts/verificar_lista.py --fecha 2026-08-31`.
5. Excel de la lista.
6. Dos campañas, sugerencias y una gestión con seguimiento = hoy + 1.
7. `adelantar-seguimientos 1` → "Para hoy" = 1; otra vez → "Vencidos" = 1.
8. Registrar resultado → gestión cerrada.
9. Dashboard del mes.
10. `docker compose -p mtabolic-e2e --env-file .env.e2e exec backend python -m app.cli reentrenar` → `CRITERIOS_NO_CUMPLIDOS` (el caso v2 lo cubre la suite de integración de R-011); `perder-fecha-reentrenamiento` → un `OMITIDO` más.

## Códigos de salida

- `0`: terminó bien.
- `1`: argumento, proyecto o precondición inválidos (sin tocar Docker), fallo de la base, migración histórica no `COMPLETADA` (no cambia nada) o el planificador no registró el `OMITIDO` en 120 s (¿`REENTRENAMIENTO_AUTOMATICO` activo?).

## Verificación

R-013: ensayo de los 10 pasos en 8081 completo sin fallos. El reinicio del backend muestra la salida propia de `docker compose restart` (observación cosmética T10-OBS-1, diferida).
