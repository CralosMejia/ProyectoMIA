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

El notebook original corrió con Python 3.11.15 y no registra las versiones de la mayoría de sus librerías: estas son las estables compatibles con Python 3.12. **Excepción: scikit-learn se fija a 1.8.0, la versión del notebook** (R-004): con 1.9.1 el bosque cambia (24/25 del top iguales, probabilidades ±0,001–0,016); con 1.8.0 la lista de septiembre es idéntica. No se actualiza sin repetir `scripts/verificar_lista.py`. Se mantiene pandas 3.x: las cifras de referencia del notebook corresponden a pandas 3 y la conversión de fechas y montos de la app no usa pandas (detalle en `../Documentation/docs/backend/11-historico.md`). `mypy` ignora imports sin tipos solo para `sklearn.*` y `joblib.*`. pandas, numpy y scikit-learn están prohibidos en `domain` y `application` (contrato de `lint-imports`, ADR-002).

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

Con el servidor arriba: `http://localhost:8000/api/v1/health`, documentación interactiva en `http://localhost:8000/docs`.

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

Compone en memoria, sin base de datos, lectura + limpieza + entrenamiento del v1 + lista al 2026-08-31 (horizonte 30, top 25) y la compara con la lista de septiembre del notebook (§13.8): cartera, ya renovados, orden, probabilidades y factores del top 25 (el empate en el corte se compara como conjunto). Sale con `0` si coincide y `1` si no. Resultado de R-004 con scikit-learn 1.8.0: `0` (cartera 59, ya renovaron 2, a priorizar 57, 1.564 ciclos de entrenamiento, 25/25 iguales). Detalle: `../Documentation/docs/backend/12-modelo-y-listas.md`.

## Docker

`docker build -t backend:dev .` — normalmente se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.

### Primer arranque

1. En `.env` (raíz), `HISTORICO_DIR` apunta a la carpeta con los libros `*Control*Gym*.xlsx`; se monta de solo lectura en `/data/historico` (`HISTORICO_PATH`). Otros `.xlsx` de la carpeta (p. ej. la plantilla de carga) se ignoran.
2. `docker compose up -d --build` (desde cero: `docker compose down -v` antes). `migrate` aplica el esquema y termina con `0`; después arranca el `backend`.
3. El backend migra el histórico en segundo plano (CU-03) y entrena el modelo `v1`: `GET /api/v1/health` responde `200` desde el inicio y `GET /api/v1/sistema/estado` pasa de `INICIALIZANDO` a `LISTO` (unos 5 s con los libros reales en la verificación de R-004). Con la base ya migrada, reiniciar el backend no vuelve a migrar. `MIGRAR_HISTORICO_AL_ARRANCAR=false` desactiva el lanzamiento (útil en pruebas).
4. Si faltan los libros o la migración falla, el estado es `FALTAN_DATOS_HISTORICOS` y la base queda sin datos del histórico (todo o nada); el motivo solo está en el log. Se corrige la carpeta y se reinicia el backend (`docker compose restart backend`) para reintentar.
5. Con el estado `LISTO`, el frontend en http://localhost:8080 permite generar la lista y descargar el Excel.
