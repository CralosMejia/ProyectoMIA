# App web de no renovaciones (Mtabolic)

Superproyecto con `Backend/` (FastAPI), `Frontend/` (React) y `Documentation/` (fuente de verdad: [Documentation/README.md](Documentation/README.md)).

## Levantar el stack

Requisito: Docker con Compose v2.

```bash
cp .env.example .env        # sustituir los valores marcador; contraseña URL-safe (p. ej. hex)
docker compose up -d --build
docker compose ps           # db, backend y frontend en estado healthy
```

| URL | Qué |
|---|---|
| http://localhost:8080 | Frontend |
| http://localhost:8000/api/v1/health | Health del backend |
| http://localhost:8000/docs | OpenAPI interactivo |

Con la base vacía y `HISTORICO_DIR` apuntando a los libros `Control Gym*.xlsx`, el backend migra el histórico y entrena el modelo v1 al arrancar; Inicio pasa a "Sistema listo" en segundos ([Backend/README.md](Backend/README.md) §Primer arranque).

Parar: `docker compose down` (añadir `-v` borra el volumen de la base de datos).

Desarrollo y pruebas de cada parte: [Backend/README.md](Backend/README.md) · [Frontend/README.md](Frontend/README.md). Detalle de contenedores: [10-docker.md](Documentation/docs/backend/10-docker.md).
