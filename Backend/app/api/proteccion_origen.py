"""S1 (R-013): filtro de ``Host`` y de ``Origin`` (middleware ASGI puro).

Sin login, la autorizacion es solo por IP (CU-00) y detras de nginx todo llega desde la IP
del frontend. Por eso se cierran dos vectores del navegador:

- **DNS rebinding**: la cabecera ``Host`` (sin puerto, en minusculas) debe estar en
  ``HOSTS_PERMITIDOS``; si no -> ``400 bad_request``.
- **CSRF** con peticiones "simples" (formularios, ``fetch`` no-cors): un metodo distinto de
  ``GET``/``HEAD``/``OPTIONS`` con ``Origin`` que no es el propio (``scheme://Host``) ni esta en
  ``CORS_ORIGINS`` -> ``403 forbidden``. Sin ``Origin``, se rechaza si
  ``Sec-Fetch-Site: cross-site``.

Las respuestas usan el formato unico de error y nunca repiten el host ni el origen recibidos.
"""

import json
from collections.abc import Sequence
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import HTTP_ERRORS, error_body

METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})


def _cuerpo(status: int) -> bytes:
    codigo, mensaje = HTTP_ERRORS[status]
    return json.dumps(error_body(codigo, mensaje)).encode("utf-8")


_CUERPO_400 = _cuerpo(400)
_CUERPO_403 = _cuerpo(403)


def _cabecera(scope: Scope, nombre: bytes) -> str | None:
    for clave, valor in scope.get("headers", ()):
        if clave.lower() == nombre:
            return str(valor.decode("latin-1"))
    return None


def _nombre_host(host: str) -> str | None:
    """``"LocalHost:8080"`` -> ``"localhost"``; ``None`` si la cabecera no es un host valido."""
    try:
        nombre = urlsplit("//" + host).hostname
    except ValueError:
        return None
    return nombre or None


class FiltroHostYOrigen:
    """Rechaza ``Host`` no permitidos y escrituras desde otro origen."""

    def __init__(self, app: ASGIApp, hosts: Sequence[str], origenes: Sequence[str]) -> None:
        self._app = app
        self._hosts = frozenset(h.lower() for h in hosts)
        self._origenes = frozenset(o.lower() for o in origenes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        tipo = scope["type"]
        if tipo not in ("http", "websocket"):  # lifespan
            await self._app(scope, receive, send)
            return
        host = (_cabecera(scope, b"host") or "").strip().lower()
        nombre = _nombre_host(host)
        if nombre is None or nombre not in self._hosts:
            await self._rechazar(scope, send, 400, _CUERPO_400)
            return
        if tipo == "http" and not self._origen_aceptado(scope, host):
            await self._rechazar(scope, send, 403, _CUERPO_403)
            return
        await self._app(scope, receive, send)

    def _origen_aceptado(self, scope: Scope, host: str) -> bool:
        if scope["method"] in METODOS_SEGUROS:
            return True
        origen = _cabecera(scope, b"origin")
        if origen is None:
            return (_cabecera(scope, b"sec-fetch-site") or "").strip().lower() != "cross-site"
        origen = origen.strip().lower()
        return origen in self._origenes or origen == f"{scope.get('scheme', 'http')}://{host}"

    @staticmethod
    async def _rechazar(scope: Scope, send: Send, status: int, cuerpo: bytes) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(cuerpo)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": cuerpo})
