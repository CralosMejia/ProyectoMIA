"""Configuracion de la aplicacion, cargada y validada desde variables de entorno."""

from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

WILDCARD_ORIGIN = "*"
ALLOWED_ORIGIN_SCHEMES = frozenset({"http", "https"})
DATABASE_URL_SCHEME = "postgresql+psycopg://"
DEBUG_ALLOWED_ENVS = frozenset({"development", "test"})


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
