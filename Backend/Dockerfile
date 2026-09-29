# syntax=docker/dockerfile:1
# Imagen del Backend: build y runtime separados. Sin herramientas de desarrollo en runtime.
# Toda la configuracion entra por variables de entorno en tiempo de ejecucion.

ARG PYTHON_IMAGE=python:3.12.13-slim-bookworm

# ------------------------------------------------------------------ build
FROM ${PYTHON_IMAGE} AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /src

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Solo dependencias de runtime (sin el extra [dev]): el paquete se instala no editable.
COPY pyproject.toml ./
COPY app ./app
RUN pip install . \
    && pip uninstall -y pip setuptools wheel

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    APP_ENV=production

# pip/setuptools/wheel de la imagen base no se necesitan en runtime.
RUN python -m pip uninstall -y pip setuptools wheel \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=build /opt/venv /opt/venv

WORKDIR /srv
# Migraciones: las ejecuta solo el servicio "migrate" (alembic upgrade head), nunca la app.
COPY alembic.ini ./
COPY alembic ./alembic
USER app:app

EXPOSE 8000

# 503 (base de datos caida) o sin respuesta -> urlopen lanza excepcion -> unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4); sys.exit(0)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
