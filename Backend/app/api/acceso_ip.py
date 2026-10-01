"""CU-00: filtro de acceso por IP (middleware ASGI puro; decision (h) de R-011).

La IP sale **solo** de la conexion (``scope["client"]``); ``X-Forwarded-For`` y
``Forwarded`` se ignoran (RN-00.3). Sin cliente o con una direccion que no es una IP -> 403.
Unica excepcion: ``GET /api/v1/health`` (RN-00.5, health check de Docker).

El 403 usa el formato unico de error y no anade cabeceras que describan el sistema. Se
registra como el middleware mas externo, de modo que tambien cubre ``OPTIONS`` (CORS) y
``/docs``. Cambiar la lista solo exige cambiar ``IPS_PERMITIDAS`` y reiniciar.
"""

import json
from collections.abc import Sequence
from ipaddress import IPv4Address, IPv6Address, ip_address

from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import HTTP_ERRORS, error_body
from app.core.config import RedPermitida

RUTA_EXENTA = "/api/v1/health"
_CODIGO, _MENSAJE = HTTP_ERRORS[403]
_CUERPO_403 = json.dumps(error_body(_CODIGO, _MENSAJE)).encode("utf-8")


def _ip_de(scope: Scope) -> IPv4Address | IPv6Address | None:
    cliente = scope.get("client")
    if not cliente:
        return None
    try:
        direccion = ip_address(cliente[0])
    except (ValueError, TypeError):
        return None
    if isinstance(direccion, IPv6Address) and direccion.ipv4_mapped is not None:
        return direccion.ipv4_mapped
    return direccion


class FiltroAccesoIp:
    """Deja pasar solo las peticiones cuya IP de conexion esta en ``redes``."""

    def __init__(self, app: ASGIApp, redes: Sequence[RedPermitida]) -> None:
        self._app = app
        self._redes = tuple(redes)

    def _permitida(self, scope: Scope) -> bool:
        ip = _ip_de(scope)
        return ip is not None and any(ip in red for red in self._redes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        tipo = scope["type"]
        if tipo not in ("http", "websocket"):  # lifespan
            await self._app(scope, receive, send)
            return
        exenta = tipo == "http" and scope["method"] == "GET" and scope["path"] == RUTA_EXENTA
        if exenta or self._permitida(scope):
            await self._app(scope, receive, send)
            return
        if tipo == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(_CUERPO_403)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _CUERPO_403})
