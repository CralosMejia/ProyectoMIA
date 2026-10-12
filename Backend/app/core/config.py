"""Configuracion de la aplicacion, cargada y validada desde variables de entorno."""

import re
from decimal import Decimal
from ipaddress import IPv4Network, IPv6Network, ip_network
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

WILDCARD_ORIGIN = "*"
ALLOWED_ORIGIN_SCHEMES = frozenset({"http", "https"})
DATABASE_URL_SCHEME = "postgresql+psycopg://"
DEBUG_ALLOWED_ENVS = frozenset({"development", "test"})
# Carpeta de los libros historicos dentro del contenedor (volumen :ro de HISTORICO_DIR).
HISTORICO_PATH_POR_DEFECTO = Path("/data/historico")

type RedPermitida = IPv4Network | IPv6Network
# CU-00: por defecto solo el propio equipo. Nunca existe un valor que "abra a todos".
IPS_PERMITIDAS_POR_DEFECTO: tuple[RedPermitida, ...] = (
    ip_network("127.0.0.1"),
    ip_network("::1"),
)
# S1 (R-013): nombres de host aceptados en la cabecera ``Host`` (sin puerto). Por defecto el
# propio equipo: nginx reenvia el Host del navegador y el healthcheck de Docker usa 127.0.0.1.
HOSTS_PERMITIDOS_POR_DEFECTO: tuple[str, ...] = ("localhost", "127.0.0.1")
_HOST_VALIDO = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")


def _redes_permitidas(valor: str) -> tuple[RedPermitida, ...]:
    """``"ip, cidr, ..."`` -> redes; los mensajes de error nunca repiten el valor recibido."""
    elementos = [elemento.strip() for elemento in valor.split(",") if elemento.strip()]
    if not elementos:
        raise ValueError("debe contener al menos una IP o un rango CIDR")
    redes: list[RedPermitida] = []
    for elemento in elementos:
        try:
            redes.append(ip_network(elemento, strict=False))
        except ValueError:
            raise ValueError(
                "cada elemento debe ser una IP o un rango CIDR valido, separados por coma"
            ) from None
    return tuple(redes)


def _hosts_permitidos(valor: str) -> tuple[str, ...]:
    """``"host, host"`` -> nombres en minusculas; sin comodines ni puertos (no repite el valor)."""
    hosts = tuple(h.strip().lower() for h in valor.split(",") if h.strip())
    if not hosts:
        raise ValueError("debe contener al menos un nombre de host")
    if not all(_HOST_VALIDO.match(h) for h in hosts):
        raise ValueError(
            "cada host debe ser un nombre o IPv4 sin comodines ni puerto, separados por coma"
        )
    return hosts


def _is_valid_origin(origin: str) -> bool:
    """``scheme://host[:port]`` con esquema http/https, sin credenciales, ruta ni query."""
    try:
        parts = urlsplit(origin)
        port_ok = parts.port is None or parts.port > 0
    except ValueError:
        return False
    return (
        parts.scheme in ALLOWED_ORIGIN_SCHEMES
        and bool(parts.hostname)
        and WILDCARD_ORIGIN not in parts.netloc
        and "@" not in parts.netloc
        and port_ok
        and not parts.path
        and not parts.query
        and not parts.fragment
        and not origin.endswith(("?", "#"))
    )


class Settings(BaseSettings):
    """Variables de entorno de la aplicacion.

    Falla rapido al instanciarse si falta una obligatoria. Los errores de validacion
    nombran la variable pero nunca incluyen su valor (``hide_input_in_errors``).
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    DATABASE_URL: SecretStr
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []
    APP_ENV: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    # CU-03 (ADR-004): migracion del historico en segundo plano al arrancar con la base vacia.
    HISTORICO_PATH: Path = HISTORICO_PATH_POR_DEFECTO
    MIGRAR_HISTORICO_AL_ARRANCAR: bool = True
    # CU-00: IPs o rangos CIDR autorizados, separados por coma (la IP sale de la conexion).
    IPS_PERMITIDAS: Annotated[tuple[RedPermitida, ...], NoDecode] = IPS_PERMITIDAS_POR_DEFECTO
    # CU-02: planificador del reentrenamiento dentro del backend (false en pruebas).
    # S1 (R-013): hosts aceptados en ``Host`` (DNS rebinding); separados por coma.
    HOSTS_PERMITIDOS: Annotated[tuple[str, ...], NoDecode] = HOSTS_PERMITIDOS_POR_DEFECTO
    REENTRENAMIENTO_AUTOMATICO: bool = True
    REENTRENAR_MIN_CICLOS_NUEVOS: int = Field(default=150, ge=0)
    REENTRENAR_MIN_COBERTURA_VENCIMIENTO: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)
    REENTRENAR_MIN_CASOS_POR_CLASE: int = Field(default=20, ge=0)
    REENTRENAR_MESES_COMPARACION: int = Field(default=3, ge=1)

    @field_validator("IPS_PERMITIDAS", mode="before")
    @classmethod
    def _parse_ips_permitidas(cls, value: object) -> object:
        """Texto de la variable -> redes; vacio o invalido falla (nunca se abre a todos)."""
        if isinstance(value, str):
            return _redes_permitidas(value)
        return value

    @field_validator("HOSTS_PERMITIDOS", mode="before")
    @classmethod
    def _parse_hosts_permitidos(cls, value: object) -> object:
        """Texto de la variable -> nombres de host; vacio o con comodin falla."""
        if isinstance(value, str):
            return _hosts_permitidos(value)
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Convierte ``"a,b"`` en ``["a", "b"]``, descartando espacios y elementos vacios."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _reject_wildcard(cls, origins: list[str]) -> list[str]:
        """CORS explicito por origen: el comodin esta prohibido."""
        if WILDCARD_ORIGIN in origins:
            raise ValueError("el origen comodin '*' no esta permitido; declare origenes explicitos")
        if not all(_is_valid_origin(origin) for origin in origins):
            # El mensaje no repite el valor recibido.
            raise ValueError("cada origen debe tener la forma http(s)://host[:puerto], sin ruta")
        return origins

    @field_validator("DATABASE_URL")
    @classmethod
    def _require_psycopg_scheme(cls, url: SecretStr) -> SecretStr:
        """Solo PostgreSQL con driver psycopg 3; el mensaje nunca incluye la URL."""
        if not url.get_secret_value().startswith(DATABASE_URL_SCHEME):
            raise ValueError(f"debe usar el esquema {DATABASE_URL_SCHEME}")
        return url

    @model_validator(mode="after")
    def _reject_debug_outside_explicit_dev_or_test(self) -> Self:
        """``debug`` expone tracebacks: solo con APP_ENV explicito ``development``/``test``.

        Falla cerrada: un despliegue que omite APP_ENV no hereda el valor por defecto
        para habilitar DEBUG.
        """
        if not self.DEBUG:
            return self
        if "APP_ENV" not in self.model_fields_set:
            raise ValueError("DEBUG=True exige declarar APP_ENV como 'development' o 'test'")
        if self.APP_ENV not in DEBUG_ALLOWED_ENVS:
            raise ValueError("DEBUG=True no esta permitido con APP_ENV='production'")
        return self
