# Backend

API FastAPI en capas (domain · application · infrastructure · api). Arquitectura: `../Documentation/docs/backend/01-arquitectura.md`. Contrato: `../Documentation/docs/API_CONTRACT.md`.

## Requisitos

Python 3.12 y un PostgreSQL 16 accesible (el de `compose.yaml` en la raíz sirve: `docker compose up -d db`).

## Instalación

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   ·   Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

### Dependencias de datos y ML (fijadas con `==` en `pyproject.toml`)

| Paquete | Versión |
|---|---|
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| scikit-learn | 1.8.0 |
| openpyxl | 3.1.5 |
| joblib | 1.6.0 |
| alembic | 1.20.0 |
| python-multipart | 0.0.32 |
| shap | 0.54.1 |

El notebook original corrió con Python 3.11.15 y no registra las versiones de la mayoría de sus librerías: estas son las estables compatibles con Python 3.12. **Excepción: scikit-learn se fija a 1.8.0, la versión del notebook** (R-004): con 1.9.1 el bosque cambia (24/25 del top iguales, probabilidades ±0,001–0,016); con 1.8.0 la lista de septiembre es idéntica. No se actualiza sin repetir `scripts/verificar_lista.py`. Se mantiene pandas 3.x: las cifras de referencia del notebook corresponden a pandas 3 y la conversión de fechas y montos de la app no usa pandas (detalle en `../Documentation/docs/backend/11-historico.md`). `mypy` ignora imports sin tipos solo para `sklearn.*`, `joblib.*` y `shap.*`. pandas, numpy, scikit-learn y shap están prohibidos en `domain` y `application` (contrato de `lint-imports`, ADR-002).

**shap 0.54.1 (R-017, mejora M03):** la misma versión del notebook; calcula los "Motivos principales" de la lista (ADR-015). Trae slicer 0.0.8 y tqdm 4.70.1 y **no** instala numba ni llvmlite; no cambia scikit-learn ni numpy. Las transitivas no están fijadas (no hay *lockfile*; diferido).

## Variables de entorno

Ver `../.env.example`. Mínimo para arrancar: `DATABASE_URL` (`postgresql+psycopg://...`), `CORS_ORIGINS`, `APP_ENV`. Para las pruebas de integración: `TEST_DATABASE_URL` (obligatoria; sin ella fallan) apuntando a una base cuyo nombre termine en `_test` (`app_db_test`); las pruebas de migración abortan en otro caso.

## Migraciones (Alembic)

`DATABASE_URL` debe estar en el entorno (`alembic.ini` no contiene URL).

| Qué | Comando |
|---|---|
| Aplicar | `alembic upgrade head` |
| Estado | `alembic current` |
| Diferencias ORM ↔ BD | `alembic check` |
| Revertir todo | `alembic downgrade base` (solo en una base de pruebas) |

En el stack de Docker las aplica el servicio `migrate` antes de arrancar el backend; la aplicación nunca migra al arrancar. Esquema: `../Documentation/docs/backend/09-esquema-base-de-datos.md`.

## Comandos (desde `Backend/`, con el venv activo)

| Qué | Comando |
|---|---|
| Lint | `ruff check .` |
| Formato | `ruff format --check .` |
| Tipos | `mypy app` |
| Capas | `lint-imports` |
| Pruebas | `pytest` (solo unitarias: `pytest -m unit`; integración: `pytest -m integration`) |
| Arranque local | `uvicorn app.main:app --reload` |

Con `uvicorn` local (sin Docker) el navegador llega desde `127.0.0.1`/`::1`, que están autorizadas: `http://localhost:8000/api/v1/health` y la documentación interactiva en `http://localhost:8000/docs`. En el stack de Docker, en cambio, el puerto `8000` (`8001` en e2e) responde `403` a todo salvo `GET /api/v1/health`: la API se consulta por el frontend, `http://localhost:8080/api/v1/...` (`8081` en e2e). Ver §Operación · Acceso por IP.

## Datos sintéticos de prueba

`tests/fixtures/` contiene 2 libros históricos (`historico/`) y 5 plantillas (`plantillas/`: válida, cédula inválida, catálogo inválido, fechas inválidas, 501 filas), sin datos reales, y `esperado.py` con sus conteos. Para regenerarlos (determinista, mismos conteos):

```bash
python tests/fixtures/generar_fixtures.py
```

## Verificación con los libros reales (local, fuera de la suite)

```bash
python scripts/verificar_historico.py <carpeta con los libros Control Gym>
```

Imprime solo conteos "notebook vs obtenido" (nunca nombres, cédulas, contactos ni rutas) y no escribe archivos. Código de salida: `0` todo coincide o solo difieren las diferencias conocidas con su delta exacto, `1` cualquier otra diferencia, `2` carpeta sin libros. `pytest` no lo recoge. Los libros reales están en `.gitignore`.

```bash
python scripts/verificar_lista.py <carpeta con los libros Control Gym>
```

Compone en memoria, sin base de datos, lectura + limpieza + entrenamiento + lista al 2026-08-31 (horizonte 30, top 25) y la compara con la lista de septiembre del notebook M01 (§13.8), cuyas salidas lee de `../salidas` (git-ignorada; otra carpeta con `--referencia`): **todas** las filas, con probabilidad a 8 decimales, nivel (0,70/0,50), factores y orden (los empates se comparan por grupo). Necesita la sal de los códigos anónimos en `MTABOLIC_SAL_CODIGOS` o en `salidas/.sal_codigos` (nunca se imprime). Sale con `0` sin diferencias, `1` con alguna y `2` si faltan libros, salidas o sal; ante un error solo imprime su tipo. Resultado de R-015 con scikit-learn 1.8.0: `0`, 0 diferencias en 57 filas (ALTO 2, MEDIO 39, BAJO 16). Desde R-017 (M03) los factores comparados son los motivos SHAP y `referencia_factores` es solo informativa; resultado con shap 0.54.1: `0`, 0 diferencias en 57 filas y 146 motivos. Detalle: `../Documentation/docs/backend/12-modelo-y-listas.md`.

## Docker

`docker build -t backend:dev .` — normalmente se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.

### Primer arranque

1. En `.env` (raíz), `HISTORICO_DIR` apunta a la carpeta con los libros `*Control*Gym*.xlsx`; se monta de solo lectura en `/data/historico` (`HISTORICO_PATH`). Otros `.xlsx` de la carpeta (p. ej. la plantilla de carga) se ignoran.
2. `docker compose up -d --build` (desde cero: `docker compose down -v` antes). `migrate` aplica el esquema y termina con `0`; después arranca el `backend`.
3. El backend migra el histórico en segundo plano (CU-03) y entrena el modelo `v1`: `GET /api/v1/health` responde `200` desde el inicio y `GET http://localhost:8080/api/v1/sistema/estado` (por el frontend) pasa de `INICIALIZANDO` a `LISTO` (unos 5 s con los libros reales en la verificación de R-004). Con la base ya migrada, reiniciar el backend no vuelve a migrar. `MIGRAR_HISTORICO_AL_ARRANCAR=false` desactiva el lanzamiento (útil en pruebas).
4. Si faltan los libros o la migración falla, el estado es `FALTAN_DATOS_HISTORICOS` y la base queda sin datos del histórico (todo o nada); el motivo solo está en el log. Se corrige la carpeta y se reinicia el backend (`docker compose restart backend`) para reintentar.
5. Con el estado `LISTO`, el frontend en http://localhost:8080 permite generar la lista y descargar el Excel.

## Operación en el PC del gimnasio (D6-OP-01)

Guía para quien instala y mantiene la aplicación. Todos los comandos se ejecutan desde la **raíz del repositorio** (donde está `compose.yaml`), en PowerShell o bash. Ningún comando de esta sección borra datos salvo los que lo advierten expresamente.

### 1. Instalación

1. Instale **Docker Desktop** (incluye Compose v2) y déjelo en marcha.
2. Cree el archivo de configuración a partir de la plantilla y rellene los valores marcador (`CAMBIAR_POR_CONTRASENA_LOCAL`, `HISTORICO_DIR`):

   ```bash
   cp .env.example .env
   ```

   La contraseña de la base debe ser URL-safe (p. ej. hexadecimal), porque se repite dentro de `DATABASE_URL` y `TEST_DATABASE_URL`. El `.env` no se versiona ni se comparte. En una instalación nueva active además el rol de la aplicación sin superusuario (§3.1).
3. Construya y arranque:

   ```bash
   docker compose up -d --build
   docker compose ps          # db, backend y frontend en "healthy"; migrate termina con 0
   ```

4. Abra http://localhost:8080. La primera vez, Inicio muestra "Inicializando" unos segundos mientras se migra el histórico y se entrena el modelo `v1` (§Primer arranque).

Para parar: `docker compose down` (conserva los datos). **`docker compose down -v` borra el volumen de la base y todos sus datos**: no lo use en el stack principal salvo que quiera empezar de cero (para eso existe el procedimiento de §6).

### 2. Libros históricos (`HISTORICO_DIR`)

- Copie los libros `Control Gym*.xlsx` en una carpeta del PC y ponga su ruta (absoluta, o relativa a `compose.yaml`) en `HISTORICO_DIR` del `.env`. Sin esa variable `docker compose` no arranca.
- La carpeta se monta en el backend como `/data/historico` **de solo lectura**: la aplicación nunca modifica los libros.
- Solo se leen los archivos `*Control*Gym*.xlsx`; los temporales de Excel (`~$*`) y cualquier otro `.xlsx` (p. ej. la plantilla de carga mensual) se ignoran.
- Los libros solo se leen en el primer arranque con la base vacía. Si faltan o tienen errores, el estado queda en `FALTAN_DATOS_HISTORICOS`: corrija la carpeta y ejecute `docker compose restart backend`.

### 3. Variables de entorno de operación

Todas son opcionales; sin ellas rigen los valores por defecto (de `compose.yaml` y de `app/core/config.py`). Se definen en el `.env` de la raíz y se aplican con `docker compose up -d`.

| Variable | Por defecto | Para qué |
|---|---|---|
| `IPS_PERMITIDAS` | `127.0.0.1,::1,<FRONTEND_IP>` | IPs o rangos CIDR, separados por coma, a los que responde el backend (CU-00). Vacío o `*` es un error: nunca se abre a todos. |
| `HOSTS_PERMITIDOS` | `localhost,127.0.0.1` | Nombres aceptados en la cabecera `Host` (sin puerto ni comodines, separados por coma). Otro `Host` → `400` (protección contra DNS rebinding, [ADR-013](../Documentation/adr/ADR-013-proteccion-host-y-origin.md)). Si se entra por otro nombre, añádalo aquí. |
| `RED_INTERNA_SUBNET` | `172.30.0.0/24` | Subred fija de la red interna de compose. |
| `FRONTEND_IP` | `172.30.0.10` | IP fija del contenedor del frontend (nginx) dentro de esa subred. |
| `REENTRENAMIENTO_AUTOMATICO` | `true` | Activa el planificador del reentrenamiento dentro del backend (§4). |
| `REENTRENAR_MIN_CICLOS_NUEVOS` | `150` | Ciclos nuevos evaluables mínimos para reentrenar. |
| `REENTRENAR_MIN_COBERTURA_VENCIMIENTO` | `0.60` | Fracción mínima (0–1) de membresías nuevas con fecha de vencimiento. |
| `REENTRENAR_MIN_CASOS_POR_CLASE` | `20` | Mínimo de ciclos nuevos que renovaron y, por separado, que no renovaron. |
| `REENTRENAR_MESES_COMPARACION` | `3` | Meses más recientes con los que se compara (PR-AUC) el candidato con el modelo vigente. |

Notas:

- `RED_INTERNA_SUBNET` y `FRONTEND_IP` se definen **juntas** (la IP dentro de la subred). El stack e2e usa por defecto otra subred (tercer octeto distinto) para que no choque con la principal.
- `compose.yaml` pasa al contenedor `IPS_PERMITIDAS`, `HOSTS_PERMITIDOS`, `REENTRENAMIENTO_AUTOMATICO` y los cuatro `REENTRENAR_*`, así que todas son configurables desde el `.env`; si no se definen, rigen los valores por defecto de la tabla.
- `CORS_ORIGINS` es también la lista de orígenes aceptados en peticiones que modifican datos: una petición distinta de `GET`/`HEAD`/`OPTIONS` con un `Origin` que no es el propio ni está en esa lista (o sin `Origin` y con `Sec-Fetch-Site: cross-site`) recibe `403` (CSRF). En operación debe contener **solo** el origen del frontend (`http://localhost:8080`).

#### 3.1 Rol de la aplicación sin superusuario (S23)

La aplicación se conecta con un rol propio sin superusuario, sin `CREATE` en el esquema y sin `DELETE` ni `TRUNCATE`; las migraciones siguen con el rol propietario ([ADR-012](../Documentation/adr/ADR-012-rol-de-aplicacion-sin-superusuario.md)). El servicio `db-roles` crea o actualiza ese rol en cada `docker compose up` (idempotente).

| Variable | Valor |
|---|---|
| `APP_DB_USER` | Nombre del rol (por defecto `mtabolic_app`; distinto de `POSTGRES_USER`). |
| `APP_DB_PASSWORD` | Contraseña URL-safe (p. ej. hexadecimal) distinta de `POSTGRES_PASSWORD`. |
| `MIGRATE_DATABASE_URL` | URL con el rol **propietario** (`POSTGRES_USER`): la usa `migrate`. |
| `DATABASE_URL` | URL con el **rol de la aplicación**: la usa el backend. |

Para activarlo en un stack existente: (1) haga un respaldo (§5); (2) defina las cuatro variables en el `.env` (sin mostrar la contraseña en pantalla ni en capturas); (3) `docker compose up -d --build` **sin `-v`**; (4) compruebe que `db-roles` y `migrate` terminaron en `0` y que Inicio muestra `LISTO`. Reversión no destructiva: volver a la `DATABASE_URL` del propietario y `docker compose up -d`.

Transición: si `APP_DB_PASSWORD` falta o está vacía, `db-roles` solo avisa y todo sigue con el rol propietario (comportamiento anterior a R-013). `TEST_DATABASE_URL` sigue siempre con el propietario (las pruebas necesitan DDL). Residual: el propietario sigue siendo superusuario del clúster (imagen oficial de PostgreSQL).

#### Acceso por IP: por qué se entra por el puerto 8080

El navegador nunca habla directo con el backend: entra por el frontend (nginx, puerto `8080`), que reenvía `/api/...` al backend dentro de la red de Docker. Por eso el backend ve la **IP fija del contenedor del frontend**, no la del navegador, y esa IP es la que está autorizada por defecto. Consecuencias:

- `http://localhost:8080/api/v1/...` funciona; `http://localhost:8000/...` responde `403` salvo `GET /api/v1/health` (que siempre responde, para el health check).
- Los puertos se publican solo en `127.0.0.1`: la aplicación solo es accesible desde el propio PC.
- Si cambia `RED_INTERNA_SUBNET`/`FRONTEND_IP` y `IPS_PERMITIDAS` deja de incluir la IP del frontend, **toda** la aplicación responde `403`. Si define `IPS_PERMITIDAS` a mano, incluya siempre la `FRONTEND_IP`.

### 4. Reentrenamiento automático (CU-02)

Con `REENTRENAMIENTO_AUTOMATICO=true`, el backend revisa **al arrancar y después cada hora**, y actúa como mucho una vez por día (fecha de Ecuador). Solo revisa si el histórico ya está migrado y hay un modelo vigente. Compara la fecha de hoy con la próxima fecha programada (`proxima_fecha_reentrenamiento` en `GET /api/v1/sistema/estado`):

| Situación | Acción | Qué pasa |
|---|---|---|
| Sin fecha programada, o la fecha es futura | `ESPERAR` | Nada. |
| La fecha es hoy | `EJECUTAR` | Intenta reentrenar (abajo). |
| La fecha ya pasó (el PC estuvo apagado) | `OMITIR` | Registra un intento `OMITIDO` por cada fecha perdida (no se recupera) y programa la siguiente 6 meses después de la última; si esa cae hoy, reentrena a continuación. |

Al reentrenar se comprueban los criterios: ciclos nuevos evaluables ≥ `REENTRENAR_MIN_CICLOS_NUEVOS`; membresías nuevas con vencimiento ≥ `REENTRENAR_MIN_COBERTURA_VENCIMIENTO`; al menos `REENTRENAR_MIN_CASOS_POR_CLASE` que renovaron y otros tantos que no; y datos con todas las columnas del modelo. Si se cumplen, se entrena un candidato y se compara su PR-AUC con la del vigente sobre los últimos `REENTRENAR_MESES_COMPARACION` meses. Cada intento queda registrado con uno de estos resultados:

| Resultado | Significado |
|---|---|
| `ENTRENADO` | Hay una versión nueva vigente y se programa la próxima fecha. |
| `CRITERIOS_NO_CUMPLIDOS` | Faltan datos; el motivo dice qué criterio no se cumple. El vigente sigue. |
| `NO_SUPERA_VIGENTE` | El candidato es peor que el vigente; el vigente sigue. |
| `OMITIDO` | Fecha programada perdida. |
| `FALLIDO` | Error al entrenar o guardar; no se guarda nada a medias y el vigente sigue. Solo el tipo de error queda en el log (`docker compose logs backend`). |

Un bloqueo en la base impide dos reentrenamientos a la vez (planificador y comando manual): el segundo termina sin tocar nada.

#### Comando manual

Reentrena **ahora**, con los mismos criterios, sin mirar la fecha programada (solo la mueve si resulta `ENTRENADO`):

```bash
docker compose exec backend python -m app.cli reentrenar
```

Imprime una línea con el resultado y el motivo (sin datos de socios). Códigos de salida:

| Código | Cuándo |
|---|---|
| `0` | Intento registrado: `ENTRENADO`, `CRITERIOS_NO_CUMPLIDOS` o `NO_SUPERA_VIGENTE`. |
| `1` | `FALLIDO`, el sistema aún no está listo (histórico sin migrar o sin modelo) o configuración inválida. |
| `2` | Ya hay un reentrenamiento en curso (o se llamó sin subcomando). |

Si resulta `ENTRENADO`, las listas que se generen desde ese momento usan el modelo nuevo (las ya generadas no cambian). Para probarlo sin afectar el modelo real, use el stack e2e: `docker compose -p mtabolic-e2e --env-file .env.e2e exec backend python -m app.cli reentrenar`.

Desde R-015 los ciclos se etiquetan al **corte de los datos** (el más reciente entre el corte del modelo vigente y el día de la última carga por plantilla, sin pasar de hoy), y el candidato se entrena sin los ciclos que vencen en los 30 días previos al periodo de comparación.

#### Adoptar un modelo nuevo sin criterios (`adoptar-modelo`, R-015)

Pone en uso un modelo entrenado **ahora** con todos los ciclos evaluables, sin los criterios ni la comparación de CU-02. Se usó una vez, el 2026-10-15, para adoptar el modelo de la mejora M01 (v2). **No es idempotente:** cada ejecución crea una versión nueva; no lo repita sin motivo.

```bash
# 1) respaldo previo (sección 5)  2) adoptar
docker compose exec backend python -m app.cli adoptar-modelo
```

Guarda en una sola transacción la versión vigente + 1 como vigente y un intento `MANUAL`/`ENTRENADO` "Adopción del modelo M01"; la versión anterior se conserva y las listas ya generadas no cambian. No mueve la próxima fecha de reentrenamiento. Si el entrenamiento falla no guarda nada.

| Código | Cuándo |
|---|---|
| `0` | Versión nueva en uso (imprime "vN en uso"). |
| `1` | Sistema no listo o sin modelo vigente, fallo del entrenamiento, base inaccesible o configuración inválida. |
| `2` | Ya hay un reentrenamiento en curso. |

Para ensayarlo primero: `docker compose -p mtabolic-e2e --env-file .env.e2e exec backend python -m app.cli adoptar-modelo`. Vuelta atrás: restaurar el respaldo. Decisión: `../Documentation/adr/ADR-014-modelo-m01-adopcion-y-cortes-de-riesgo.md`.

### 5. Respaldo y restauración de la base

Use los scripts de la raíz (detalle, opciones y códigos de salida en [`Documentation/comandos/respaldo-y-restauracion.md`](../Documentation/comandos/respaldo-y-restauracion.md)). Las credenciales se expanden **dentro** del contenedor `db`: no hace falta escribir ninguna contraseña y no se imprime nada del `.env`. Los respaldos quedan en `respaldos/` (git-ignorada): contienen datos personales de socios; guárdelos fuera de cualquier carpeta compartida.

**Hacer un respaldo** (solo lectura; `pg_dump -Fc` dentro del contenedor y copia al PC, lo que evita que PowerShell altere el binario). Genera `respaldos/<proyecto>-AAAAMMDD-HHMMSS.dump` y su `.conteos` (9 tablas); si la base cambia durante el volcado, lo descarta:

```bash
scripts/respaldar-base.sh                          # bash; stack principal
powershell -ExecutionPolicy Bypass -File scripts\respaldar-base.ps1   # Windows
```

**Restaurar en una base nueva** (no toca la base en uso; nunca renombra, sobrescribe ni borra). Crea `app_db_restaurada_AAAAMMDDHHMMSS` (o `--base nombre` / `-Base nombre`), aplica los permisos del rol de la aplicación y compara los conteos con el `.conteos` del respaldo (`Conteos iguales` → código 0):

```bash
scripts/restaurar-base.sh respaldos/<archivo>.dump [--base app_db_restaurada]
powershell -ExecutionPolicy Bypass -File scripts\restaurar-base.ps1 respaldos\<archivo>.dump [-Base app_db_restaurada]
```

Ambos aceptan `-p mtabolic-e2e` o `-p mtabolic-limpia` (lista blanca; otro nombre sale con código 1 sin tocar Docker).

**Poner en uso la base restaurada** (solo si se perdió o dañó la actual; los comandos suponen que se restauró con `--base app_db_restaurada`, si no cambie el nombre). No borra nada: la base actual se renombra a `app_db_anterior` y se conserva. Detenga antes la aplicación para que no haya conexiones abiertas:

```bash
docker compose stop frontend backend
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d postgres -c "ALTER DATABASE \"$POSTGRES_DB\" RENAME TO app_db_anterior" -c "ALTER DATABASE app_db_restaurada RENAME TO \"$POSTGRES_DB\""'
docker compose start backend frontend
```

Compruebe en http://localhost:8080 que el sistema está `LISTO` y los datos son los esperados. Conserve `app_db_anterior` hasta estar seguro; eliminarla (`dropdb`) es **definitivo**.

### 6. Reiniciar la base a solo datos históricos

Para dejar la base como recién instalada (solo histórico y modelo `v1`), use el procedimiento con confirmación explícita de [`Documentation/comandos/reiniciar-base-historica.md`](../Documentation/comandos/reiniciar-base-historica.md). **Borra definitivamente** cargas, listas, campañas y gestiones del stack principal: haga antes un respaldo (§5). Desde R-013 el script espera `LISTO` por el puerto del frontend (`FRONTEND_PORT`, por defecto 8080), porque el backend por 8000 responde `403`.

### 7. Ensayo de la demostración (stack aislado)

Para ensayar alertas y la fecha de reentrenamiento perdida sin esperar días reales, en el stack `mtabolic-e2e` (único aceptado): `scripts/ensayo-demo-e2e.sh adelantar-seguimientos <1..60>` y `scripts/ensayo-demo-e2e.sh perder-fecha-reentrenamiento` (o los `.ps1`). Guion en [`Documentation/comandos/ensayo-demo-e2e.md`](../Documentation/comandos/ensayo-demo-e2e.md).
