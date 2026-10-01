# ADR-010 · Acceso por IP en el backend, detrás de nginx, sin confiar en `X-Forwarded-For`

- **Estado:** aceptada · 2026-09-30 · R-011 (día 6)
- **Origen:** [03 §3](../03-casos-de-uso.md) (CU-00, RN-00.3 y RN-00.5) · decisión (h) de R-011

## Contexto

CU-00 pide restringir el acceso por IP tomada de la conexión, sin cuentas y sin confiar en cabeceras de IP reenviada. En Docker, el navegador no habla con el backend: llega a nginx (`frontend`), que reenvía `/api/` al backend. El backend ve por tanto la IP del contenedor nginx, nunca la del navegador. RN-00.3 ya preveía revisar la regla si había un proxy delante.

## Decisión

1. **Middleware ASGI** (`app/api/acceso_ip.py`) que compara la IP de la conexión con `IPS_PERMITIDAS` (IPs o rangos CIDR; por defecto `127.0.0.1,::1`; vacío, `*` o inválido → el backend no arranca, sin mostrar el valor). `X-Forwarded-For` y `Forwarded` se ignoran. Sin cliente → `403`.
2. Solo `GET /api/v1/health` está exento. Todo lo demás (incluidos `OPTIONS`, `/docs` y `/openapi.json`) responde `403 forbidden` con el formato único de error y el mensaje "El acceso no esta permitido desde este equipo.".
3. **Red fija en compose:** la red `interna` tiene subred fija y `frontend` una IP fija (`RED_INTERNA_SUBNET`, `FRONTEND_IP`), autorizada por defecto. Principal `172.30.0.0/24` / `.10`; el stack E2E deriva otra subred (`172.30.120.0/24`) para que ambos convivan.
4. La protección efectiva frente a otros equipos sigue siendo publicar los puertos solo en `127.0.0.1`.
5. El frontend muestra la página "Acceso no permitido" ante cualquier `403 forbidden`.

## Alternativas descartadas

- **Confiar en `X-Forwarded-For` de nginx:** contradice RN-00.3; queda diferido ([03 §20](../03-casos-de-uso.md)).
- **Filtrar solo en nginx:** el backend quedaría abierto a cualquier proceso que llegue a su puerto; además CU-00 sitúa la regla en el backend.
- **Autorizar toda la subred de Docker:** cualquier contenedor de la red pasaría el filtro.

## Consecuencias

- Desde el host, el backend por 8000/8001 da `403` salvo `/health`; todo se usa por 8080/8081.
- Todos los navegadores llegan con la misma IP (la de nginx): el backend no distingue equipos. **Abrir la app a otro PC no está implementado**; exigiría filtrar por IP también en nginx y publicar fuera de loopback.
- Las pruebas de API usan un cliente con IP `127.0.0.1`.
- Detalle: [API_CONTRACT](../docs/API_CONTRACT.md), [10-docker](../docs/backend/10-docker.md), [Backend/README §Operación](../../Backend/README.md).
