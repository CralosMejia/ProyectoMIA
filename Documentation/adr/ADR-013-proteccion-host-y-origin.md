# ADR-013 · Filtro de `Host` y `Origin` contra DNS rebinding y CSRF

- **Estado:** aceptada · 2026-10-01 · R-013 (día 7)
- **Origen:** hallazgo S1 (high) de la revisión de seguridad única R-001..R-012 (D7-OP-02) · complementa [ADR-010](ADR-010-acceso-por-ip-detras-de-nginx.md)

## Contexto

Sin login, la única autorización es la IP (CU-00), y detrás de nginx todas las peticiones llegan con la IP autorizada del frontend. Un sitio malicioso abierto en el navegador del PC podría (1) apuntar un dominio propio a `127.0.0.1` (DNS rebinding) y leer la API como si fuera del mismo origen, o (2) enviar formularios o `fetch` "simples" a `http://localhost:8080/api/...` (CSRF) para crear campañas, gestiones o cargas. CORS no impide ninguna de las dos.

## Decisión

1. **Middleware ASGI** `app/api/proteccion_origen.py` (antes de cualquier endpoint, también `/health`):
   - `Host` (sin puerto, en minúsculas) fuera de `HOSTS_PERMITIDOS` (por defecto `localhost,127.0.0.1`) → `400 bad_request`.
   - Método distinto de `GET`/`HEAD`/`OPTIONS` con `Origin` que no es `scheme://Host` ni está en `CORS_ORIGINS` → `403 forbidden`. Sin `Origin`, se rechaza si `Sec-Fetch-Site: cross-site`.
   - Respuestas con el formato único de error, sin repetir el host ni el origen.
2. **nginx:** un `server` `default_server` responde `444` a cualquier `Host` distinto de `localhost`/`127.0.0.1`; cabeceras CSP (`'self'`), `Permissions-Policy`, COOP/CORP `same-origin` y `Cache-Control: no-store` en `/api/`.
3. `CORS_ORIGINS` en operación lista **solo** el origen del frontend (S26).

## Alternativas descartadas

- **Token CSRF:** sin sesión ni login no hay dónde ligarlo; comprobar `Origin` cubre el caso con navegadores actuales.
- **`TrustedHostMiddleware` de Starlette:** solo cubre `Host`; un middleware propio resuelve ambos con el formato único de error.
- **Solo en nginx:** el backend quedaría sin protección si se publica de otra forma; se hace en ambos (defensa en profundidad).

## Consecuencias

- Entrar por otro nombre (p. ej. el nombre del PC) exige añadirlo a `HOSTS_PERMITIDOS` y a `server_name` de nginx.
- Con TLS delante, `scope["scheme"]` debe reflejar `https` (S18): queda diferido con el resto de TLS.
- Abrir la aplicación a otro PC sigue sin implementarse (S5, ADR-010).
