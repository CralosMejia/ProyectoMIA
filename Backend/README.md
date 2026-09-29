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
| scikit-learn | 1.9.1 |
| openpyxl | 3.1.5 |
| joblib | 1.6.0 |
| alembic | 1.20.0 |
| python-multipart | 0.0.32 |

El notebook original corrió con Python 3.11.15 y no registra las versiones de sus librerías: estas son las estables compatibles con Python 3.12, no las del notebook. Se mantiene pandas 3.x: las cifras de referencia del notebook corresponden a pandas 3 y la conversión de fechas y montos de la app no usa pandas (detalle en `../Documentation/docs/backend/11-historico.md`). `mypy` ignora imports sin tipos solo para `sklearn.*` y `joblib.*`. pandas, numpy y scikit-learn están prohibidos en `domain` y `application` (contrato de `lint-imports`, ADR-002).

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

## Docker

`docker build -t backend:dev .` — normalmente se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.
