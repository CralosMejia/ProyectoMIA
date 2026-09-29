---
paths:
  - "**/.github/workflows/**"
  - "**/Dockerfile"
  - "**/compose.yaml"
  - "**/*.dockerignore"
  - "**/.env.example"
---

# Reglas — Despliegue e infraestructura

Referencia larga: `Documentation/docs/backend/10-docker.md`, `11-ci-cd.md`.

## Pipeline

Orden obligatorio en cada push y PR:

```
1. instalar dependencias  2. lint + tipos + capas (ruff, mypy, lint-imports) y build del frontend  3. pruebas unitarias
4. pruebas de integración (base de datos efímera en contenedor)  5. build de imagen/artefacto
6. [solo main] migraciones   7. [solo main] deploy   8. [solo main] health check
```

- El despliegue automático ocurre **solo desde `main`**.
- Las **migraciones se ejecutan antes** de desplegar la nueva versión, como paso separado. Si la migración falla, el despliegue se detiene y no se publica la imagen.
- Si el health check falla tras desplegar, se revierte a la imagen anterior.
- Un pipeline en rojo bloquea el merge. No se desactiva un paso para "desbloquear".

## Contenedores

- `Dockerfile` multi-stage: build y runtime separados. Backend: imagen `python:3.12-slim` fijada, dependencias instaladas en la etapa de build, sin compiladores ni herramientas de desarrollo en runtime, servido con `uvicorn`/`gunicorn` sin `--reload`. Frontend: build de Vite servido como estáticos (nginx); la imagen final no lleva `node_modules` ni fuentes.
- La imagen corre como usuario **no root**.
- Imágenes base fijadas por versión, nunca `latest`.
- `.dockerignore` excluye artefactos de build, dependencias, `.git/` y `.env`.
- Health check expuesto y consumido por la plataforma.
- **PostgreSQL 16 corre en Docker** (`postgres:16-alpine`, versión fijada, volumen nombrado) en desarrollo y en CI; en CI como `services:` del job con `pg_isready` como health check. Detalle en `Plantilla/05-docker-y-base-de-datos.md`.

## Configuración y secretos

- Toda la configuración entra por **variables de entorno**. Nada de valores por entorno incrustados en la imagen.
- Los secretos viven en el gestor de la plataforma y en los secrets del CI. Nunca en el repo, ni en `compose.yaml`, ni en configuración versionada, ni en logs de CI.
- Al arrancar, la aplicación valida que las variables obligatorias existen y falla rápido con un mensaje que **no** revela el valor.
- `.env.example` documenta cada variable con un valor marcador. Cuando se añade una variable nueva, se actualiza en el mismo cambio.
- El secreto de firma de tokens: mínimo 32 caracteres, distinto por entorno, nunca reutilizado entre desarrollo y producción.
- Si un job de CI necesita construir el host de la aplicación (por ejemplo para generar o aplicar migraciones), declara valores **placeholder** para las variables obligatorias, claramente marcados como no reales, y la conexión real solo por el parámetro explícito del comando.

## Base de datos en producción

- La aplicación **nunca** ejecuta las migraciones al arrancar.
- Copia de seguridad verificada antes de una migración que altera datos existentes.
- Las credenciales de la base de datos rotan sin necesidad de redesplegar la imagen.
- La aplicación se conecta con un rol sin privilegios de superusuario ni de `CREATE` sobre el esquema; las migraciones usan un rol distinto con permisos de DDL.
- Conexión con `sslmode=require` (o superior) fuera de desarrollo.
- Copias con `pg_dump` / backups gestionados de la plataforma, con restauración probada.

## Red

- CORS explícito por origen. Comodín con credenciales está prohibido.
- HTTPS obligatorio; HSTS activo en producción.
- Cabeceras de seguridad configuradas en la API, no en el frontend.

## Finalización

Un cambio de infraestructura está terminado cuando: el pipeline pasa completo, la imagen construye y arranca localmente con `compose.yaml`, el health check responde, `.env.example` está al día y el documento de Docker o CI refleja el cambio.

## Prohibido

- Desplegar desde una máquina local a producción.
- Cambiar workflows de CI para saltar pruebas o el paso de migración.
- Poner secretos en `compose.yaml` o en configuración del frontend.
- Desplegar con la suite en rojo.
- Ejecutar migraciones a mano contra producción fuera del pipeline sin registro de la operación.
