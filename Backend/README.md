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

El notebook original corrió con Python 3.11.15 y no registra las versiones de sus librerías: estas son las estables compatibles con Python 3.12, no las del notebook (riesgo al portar la lógica el día 2, en especial con pandas 3.x). `mypy` ignora imports sin tipos solo para `sklearn.*` y `joblib.*`. pandas, numpy y scikit-learn están prohibidos en `domain` y `application` (contrato de `lint-imports`, ADR-002).

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

## Docker

`docker build -t backend:dev .` — normalmente se construye desde la raíz con `docker compose up -d --build`. Detalle: `../Documentation/docs/backend/10-docker.md`.
