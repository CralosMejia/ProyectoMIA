"""Formato unico de error, CORS y arranque seguro, contra la app real (PostgreSQL real).

Aislamiento entre usuarios: NO APLICA. Estas pruebas cubren manejadores globales de
error y CORS; no exponen ni consultan datos de ningun usuario.
"""

import logging
import traceback
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.engine import URL

from app.api.openapi import error_responses, raise_not_implemented
from app.core.config import Settings
from app.domain.common.exceptions import DomainError
from app.main import create_app

pytestmark = pytest.mark.integration

ALLOWED_ORIGIN = "http://localhost:5173"
OTHER_ORIGIN = "http://evil.example"
BOOM_PATH = "/api/v1/_test/boom"
DOMAIN_PATH = "/api/v1/_test/domain"
VALIDATION_PATH = "/api/v1/_test/validation"
NOT_IMPLEMENTED_PATH = "/api/v1/_test/not-implemented"
FORBIDDEN_PATH = "/api/v1/_test/forbidden"
INTERNAL_DETAIL = "detalle interno SELECT * FROM secret_table en /srv/app/main.py"


class _Payload(BaseModel):
    quantity: int = Field(gt=0)


class _SampleDomainError(DomainError):
    pass


@pytest.fixture
def app(test_database_url: URL) -> FastAPI:
    settings = Settings(
        DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
        APP_ENV="test",
        CORS_ORIGINS=[ALLOWED_ORIGIN],
    )
    application = create_app(settings)

    @application.get(BOOM_PATH)
    def boom() -> None:
        raise RuntimeError(INTERNAL_DETAIL)

    @application.get(DOMAIN_PATH)
    def domain_rule() -> None:
        raise _SampleDomainError("La cantidad supera el limite permitido.")

    @application.get(NOT_IMPLEMENTED_PATH)
    def not_implemented() -> None:
        raise_not_implemented()

    @application.get(FORBIDDEN_PATH)
    def forbidden() -> None:
        raise HTTPException(status_code=403)

    @application.post(VALIDATION_PATH)
    def validation(payload: _Payload) -> _Payload:
        return payload

    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as test_client:
        yield test_client


def _assert_error_shape(body: object, code: str) -> None:
    assert isinstance(body, dict)
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message"}
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["message"]


def test_get_unknown_route_returns_404_with_unique_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/no-existe")

    assert response.status_code == 404
    _assert_error_shape(response.json(), "not_found")


def test_post_health_method_not_allowed_returns_405_with_unique_error_format(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    _assert_error_shape(response.json(), "method_not_allowed")


def test_unhandled_exception_returns_500_generic_message_and_logs_it(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = client.get(BOOM_PATH)

    assert response.status_code == 500
    _assert_error_shape(response.json(), "internal_error")
    text = response.text
    for leaked in ("Traceback", "RuntimeError", "SELECT", "secret_table", "/srv/", ".py"):
        assert leaked not in text
    # S6 (R-013): se registra el tipo de la excepcion, sin mensaje ni traza (DETAIL de SQL).
    assert any("RuntimeError" in record.getMessage() for record in caplog.records), (
        "el error 500 debe quedar registrado en el log con el tipo de la excepcion"
    )


def test_unhandled_exception_log_has_no_message_nor_traceback(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        client.get(BOOM_PATH)

    assert caplog.records
    for record in caplog.records:
        assert record.exc_info is None
        assert record.exc_text is None
        assert "secret_table" not in record.getMessage()
        assert "SELECT" not in record.getMessage()


def test_unhandled_exception_does_not_propagate_to_the_server(app: FastAPI) -> None:
    """El servidor (uvicorn) registraria la traza completa si la excepcion se re-lanzara."""
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=True) as cliente:
        response = cliente.get(BOOM_PATH)

    assert response.status_code == 500
    _assert_error_shape(response.json(), "internal_error")


def test_domain_error_returns_422_with_unique_error_format(client: TestClient) -> None:
    response = client.get(DOMAIN_PATH)

    assert response.status_code == 422
    _assert_error_shape(response.json(), "domain_rule_violated")
    assert response.json()["error"]["message"] == "La cantidad supera el limite permitido."


def test_request_validation_error_returns_400_with_unique_error_format(
    client: TestClient,
) -> None:
    response = client.post(VALIDATION_PATH, json={"quantity": -1})

    assert response.status_code == 400
    _assert_error_shape(response.json(), "validation_error")
    assert "-1" not in response.json()["error"]["message"]


def test_preflight_from_allowed_origin_returns_allow_origin_header(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


def test_preflight_from_unlisted_origin_has_no_allow_origin_header(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": OTHER_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers


def test_simple_request_from_unlisted_origin_has_no_allow_origin_header(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health", headers={"Origin": OTHER_ORIGIN})

    assert "access-control-allow-origin" not in response.headers


def test_get_unknown_route_message_is_not_framework_default_nor_path(client: TestClient) -> None:
    response = client.get("/api/v1/no-existe")

    message = response.json()["error"]["message"]
    assert message != "Not Found"
    assert "no-existe" not in message


def test_unhandled_exception_log_record_is_error_level_with_request_path(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        client.get(BOOM_PATH)

    records = [r for r in caplog.records if "RuntimeError" in r.getMessage()]
    assert records
    assert all(r.levelno >= logging.ERROR for r in records)
    assert any(BOOM_PATH in r.getMessage() for r in records)


def test_simple_request_from_allowed_origin_returns_allow_origin_and_credentials(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_preflight_from_allowed_origin_never_echoes_wildcard(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.headers.get("access-control-allow-origin") != "*"


def test_preflight_from_origin_differing_only_in_port_has_no_allow_origin_header(
    client: TestClient,
) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5174", "Access-Control-Request-Method": "GET"},
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_middleware_with_credentials_has_explicit_origins_only(app: FastAPI) -> None:
    from starlette.middleware.cors import CORSMiddleware

    (cors,) = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    options = cors.kwargs
    if options.get("allow_credentials"):
        assert options["allow_origins"]
        assert all(origin != "*" for origin in options["allow_origins"])


def test_cors_middleware_never_combines_wildcard_with_credentials(app: FastAPI) -> None:
    from starlette.middleware.cors import CORSMiddleware

    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert len(cors) == 1
    options = cors[0].kwargs
    assert "*" not in options["allow_origins"]
    assert options["allow_origins"] == [ALLOWED_ORIGIN]
    assert options.get("allow_origin_regex") is None


@pytest.mark.parametrize(
    "malformed",
    [
        # Esquema roto: Settings lo rechaza; model_construct salta la validacion para
        # ejercitar la defensa del lifespan (ArgumentError de SQLAlchemy).
        "postgresql+psycopg//app_user:{pw}@localhost/appdb",
        # Esquema valido, puerto no numerico: ValueError al parsear la URL.
        "postgresql+psycopg://app_user:{pw}@localhost:notaport/appdb",
        "postgresql+psycopg://app_user:{pw}@[::1/appdb",
    ],
)
def test_startup_with_malformed_database_url_raises_without_exposing_password(
    malformed: str,
) -> None:
    known_credential = "known-startup-pw-4f9a"
    settings = Settings.model_construct(
        DATABASE_URL=SecretStr(malformed.format(pw=known_credential)),
        CORS_ORIGINS=[],
        APP_ENV="test",
        DEBUG=False,
    )
    application = create_app(settings)

    with (
        pytest.raises(RuntimeError) as exc_info,
        TestClient(application, client=("127.0.0.1", 50000)),
    ):
        pass

    rendered = "".join(traceback.format_exception(exc_info.value))
    assert "DATABASE_URL" in str(exc_info.value)
    assert known_credential not in rendered
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_raise_not_implemented_returns_501_with_unique_error_format(client: TestClient) -> None:
    response = client.get(NOT_IMPLEMENTED_PATH)

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "code": "not_implemented",
            "message": "Esta funcion aun no esta disponible.",
        }
    }


def test_forbidden_message_does_not_mention_session(client: TestClient) -> None:
    response = client.get(FORBIDDEN_PATH)

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "El acceso no esta permitido desde este equipo.",
        }
    }


def test_error_responses_builds_example_in_unique_error_format_per_code() -> None:
    responses = error_responses(400, 501)

    assert set(responses) == {400, 501}
    bad_request = responses[400]["content"]["application/json"]["example"]
    assert bad_request["error"]["code"] == "validation_error"
    not_implemented = responses[501]["content"]["application/json"]["example"]
    assert not_implemented == {
        "error": {
            "code": "not_implemented",
            "message": "Esta funcion aun no esta disponible.",
        }
    }
    for entry in responses.values():
        assert entry["description"]
        assert entry["model"].__name__ == "ErrorResponseDTO"


@pytest.mark.parametrize("code", [400, 403, 404, 409, 413, 422, 501])
def test_error_responses_supports_every_catalog_code(code: int) -> None:
    example = error_responses(code)[code]["content"]["application/json"]["example"]

    _assert_error_shape(example, example["error"]["code"])


def test_error_responses_unknown_code_raises_value_error() -> None:
    with pytest.raises(ValueError, match="418"):
        error_responses(418)
