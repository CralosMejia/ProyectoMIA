# Preparar 8081: estado de grabación o estado de la E2E

Deja el stack aislado `mtabolic-e2e` (http://localhost:8081) en uno de dos estados con un solo comando: **`grabacion`** (datos inventados que parecen un gimnasio real, para grabar el demo o capturar figuras) o **`e2e`** (el estado que esperan las pruebas Playwright). Scripts: `scripts/preparar-8081.ps1` (Windows) y `scripts/preparar-8081.sh` (bash). Origen: R-022.

## Advertencias

- **Borra todo lo que haya en 8081**: hace `docker compose down -v` **solo** del proyecto `mtabolic-e2e` (base, listas, gestiones). El proyecto está fijo; nunca toca `proyectofinal` (8080) ni `mtabolic-demo` ni sus volúmenes. Un argumento inválido sale con código 1 sin ejecutar Docker.
- Pide confirmación `[s/N]`; `-Si` (PowerShell) o `--si` (bash) la da por respondida. Con cualquier otra respuesta sale sin cambios.
- Necesita `.env.e2e` (copia de `.env.e2e.example`); limpia de la shell las variables que ganarían a `--env-file`. Las contraseñas no se imprimen.
- Reconstruye las imágenes (`--build`) y espera `LISTO` hasta 15 minutos.

## Cómo ejecutarlo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 grabacion
powershell -ExecutionPolicy Bypass -File scripts\preparar-8081.ps1 e2e -Si
```

```bash
bash scripts/preparar-8081.sh grabacion
bash scripts/preparar-8081.sh e2e --si
```

## Qué hace `grabacion`

1. Genera `datos-grabacion/` con la fecha de hoy (perfil `grabacion` de `Backend/scripts/generar_dataset_demo.py`, en un contenedor Python: no hace falta Python en el equipo). Nombres inventados sin la marca "Demo", cédulas `0999…`, celulares `0900…`, correos `@example.com`, transacciones `GRAB-…`. La carpeta está en `.gitignore`: **no se versiona** y se regenera en cada ejecución.
2. Levanta 8081 con `HISTORICO_DIR=./datos-grabacion` y espera a que la migración de arranque (CU-03) termine en `LISTO`.
3. Siembra con `Backend/scripts/sembrar_grabacion.py`, dentro del contenedor `backend` y **solo con los casos de uso de la app** (sin SQL a mano), **mes a mes con relojes fijos**: para cada uno de los **4 meses pasados**, el día 1 genera la lista (top 25, horizonte 31), crea las gestiones del top 25 con una campaña sugerida, registra contactos (de 20 días antes al día siguiente del vencimiento), ofertas, aceptaciones y resultados, y el día 1 del mes siguiente confirma la plantilla del mes (CU-01). Al final genera la **lista de hoy**. Campañas: "Congela 7 días gratis", "Trimestral con descuento", "Clase de prueba con un amigo" y "Llamada de bienvenida de vuelta". Todas las gestiones pasadas quedan cerradas (no generan alertas). Solo corre sobre una base `*_e2e`; es idempotente; la salida son conteos por mes, sin datos personales.

## Qué hace `e2e`

Baja 8081 (`down -v`) y lo levanta con `.env.e2e` tal cual (libros de `Backend/tests/fixtures/historico`), sin siembra. Después corre la E2E:

```bash
cd Frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test --workers=1
```

La E2E se corre **siempre después de `e2e`**, nunca sobre el estado `grabacion`.

## Qué mirar en el Dashboard (estado `grabacion`)

Con hoy = 2026-11-03 (los meses se desplazan con la fecha de ejecución):

| Mes | Estado del piloto | Para qué sirve |
|---|---|---|
| 2026-07, 2026-08, 2026-09 | Resultado final (completo) | Grabar los dos gráficos de "¿Cómo le fue a la lista del mes?" con cifras definitivas |
| 2026-10 | Parcial ("Faltan X socios por confirmar") | Enseñar que el resultado se conoce 30 días después del vencimiento |
| 2026-11 | Pendiente ("Todavía es pronto") | Lista de hoy con socios de riesgo alto, para Lista, Campañas y Seguimiento |

## Cómo leer las cifras

- **La renovación de los contactados es baja (10–20 %)** y es esperable: el top 25 son los socios **de mayor riesgo** de no renovar, no una muestra del gimnasio.
- **El resumen del mes ("Renovaron") puede no coincidir con el gráfico del piloto**: el resumen cuenta las gestiones del mes, incluidos socios fuera del top 25 o no contactados en el piloto; el gráfico solo mira a los 25 primeros de la última lista del mes y sus contactados ([M04](../mejoras/M04-indicadores-del-piloto.md)).
- Las cifras son resultados observados de datos inventados: no demuestran efecto de las campañas.

## Volver al estado anterior

`preparar-8081 e2e` deja 8081 listo para las pruebas. Para el escenario de alertas y reentrenamiento perdido sobre el estado E2E: [ensayo-demo-e2e.md](ensayo-demo-e2e.md). Detalle del stack: [backend/10 §Stack E2E aislado](../docs/backend/10-docker.md).
