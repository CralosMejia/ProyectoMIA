import pytest
from pydantic import ValidationError

from app.core.config import Settings

pytestmark = pytest.mark.unit

FAKE_DB_CREDENTIAL = "fake-credential-for-tests"
DB_URL = f"postgresql+psycopg://app_user:{FAKE_DB_CREDENTIAL}@localhost:5432/appdb"
ENV_VARS = (
    "DATABASE_URL",
    "CORS_ORIGINS",
    "APP_ENV",
    "DEBUG",
    "HISTORICO_PATH",
    "MIGRAR_HISTORICO_AL_ARRANCAR",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_settings_without_database_url_raises_error_naming_variable_without_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_value = "http://leak-check.example"
    monkeypatch.setenv("CORS_ORIGINS", other_value)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert other_value not in message
    assert "input_value" not in message


def test_settings_invalid_value_error_does_not_include_the_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("DEBUG", "not-a-bool-" + FAKE_DB_CREDENTIAL)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "DEBUG" in message
    assert FAKE_DB_CREDENTIAL not in message


def test_settings_cors_origins_comma_separated_returns_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080")

    settings = Settings()

    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://localhost:8080"]


def test_settings_cors_origins_strips_spaces_and_empty_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:5173 , ,http://localhost:8080 ")

    settings = Settings()

    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://localhost:8080"]


@pytest.mark.parametrize("value", ["*", "http://localhost:5173,*"])
def test_settings_cors_origins_wildcard_is_rejected(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", value)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "CORS_ORIGINS" in str(exc_info.value)


def test_settings_defaults_debug_false_and_no_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = Settings()

    assert settings.DEBUG is False
    assert settings.CORS_ORIGINS == []
    assert settings.APP_ENV == "development"


def test_settings_app_env_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", "production")

    assert Settings().APP_ENV == "production"


def test_settings_app_env_unknown_value_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", "staging-x")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_repr_and_str_do_not_expose_database_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = Settings()

    assert FAKE_DB_CREDENTIAL not in repr(settings)
    assert FAKE_DB_CREDENTIAL not in str(settings)
    assert settings.DATABASE_URL.get_secret_value() == DB_URL


def test_settings_missing_database_url_error_is_missing_type_for_that_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings()

    errors = exc_info.value.errors()
    assert [(e["loc"], e["type"]) for e in errors] == [(("DATABASE_URL",), "missing")]


def test_settings_cors_origins_empty_string_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", "")

    assert Settings().CORS_ORIGINS == []


def test_settings_cors_origins_single_origin_returns_one_item_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    assert Settings().CORS_ORIGINS == ["http://localhost:5173"]


def test_settings_cors_origins_wildcard_with_spaces_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, * ")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "CORS_ORIGINS" in message
    assert FAKE_DB_CREDENTIAL not in message


def test_settings_model_dump_masks_database_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = Settings()

    assert FAKE_DB_CREDENTIAL not in str(settings.model_dump())
    assert FAKE_DB_CREDENTIAL not in settings.model_dump_json()
    assert FAKE_DB_CREDENTIAL not in f"{settings.DATABASE_URL}"


def test_settings_production_with_debug_true_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "DEBUG" in message
    assert FAKE_DB_CREDENTIAL not in message


def test_settings_production_with_debug_false_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings()

    assert settings.APP_ENV == "production"
    assert settings.DEBUG is False


@pytest.mark.parametrize("env", ["development", "test"])
def test_settings_debug_true_outside_production_is_accepted(
    monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("APP_ENV", env)
    monkeypatch.setenv("DEBUG", "true")

    assert Settings().DEBUG is True


@pytest.mark.parametrize(
    "origin",
    [
        "null",
        "localhost:5173",
        "//localhost:5173",
        "http://localhost:5173/",
        "http://localhost:5173/app",
        "http://localhost:5173?x=1",
        "http://localhost:5173#frag",
        "http://user@localhost:5173",
        "ftp://localhost:5173",
        "file:///etc/passwd",
        "http://",
        "http://localhost:notaport",
        "http://*.example.com",
    ],
)
def test_settings_cors_origins_malformed_origin_is_rejected(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", f"http://localhost:8080,{origin}")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "CORS_ORIGINS" in str(exc_info.value)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "https://app.example.com",
        "https://app.example.com:8443",
        "http://127.0.0.1:8080",
    ],
)
def test_settings_cors_origins_well_formed_origin_is_accepted(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("CORS_ORIGINS", origin)

    settings = Settings()

    assert [origin] == settings.CORS_ORIGINS


@pytest.mark.parametrize(
    "invalid_url",
    [
        f"mysql://app_user:{FAKE_DB_CREDENTIAL}@localhost:5432/appdb",
        f"postgresql://app_user:{FAKE_DB_CREDENTIAL}@localhost:5432/appdb",
        f"postgresql+psycopg//app_user:{FAKE_DB_CREDENTIAL}@localhost/appdb",
    ],
)
def test_settings_invalid_database_url_error_does_not_include_password(
    monkeypatch: pytest.MonkeyPatch, invalid_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", invalid_url)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert FAKE_DB_CREDENTIAL not in message
    assert FAKE_DB_CREDENTIAL not in repr(exc_info.value)
    assert FAKE_DB_CREDENTIAL not in str(exc_info.value.errors(include_input=False))


def test_settings_debug_true_without_explicit_app_env_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S14: sin APP_ENV explicito la guarda no puede fallar abierta con DEBUG=True.
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "DEBUG" in message
    assert "APP_ENV" in message
    assert FAKE_DB_CREDENTIAL not in message


def test_settings_debug_false_without_explicit_app_env_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("DEBUG", "false")

    assert Settings().DEBUG is False


def test_settings_historico_defaults_to_container_path_and_migrates_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = Settings()

    assert settings.HISTORICO_PATH.as_posix() == "/data/historico"
    assert settings.MIGRAR_HISTORICO_AL_ARRANCAR is True


def test_settings_historico_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("HISTORICO_PATH", "/otra/carpeta")
    monkeypatch.setenv("MIGRAR_HISTORICO_AL_ARRANCAR", "false")

    settings = Settings()

    assert settings.HISTORICO_PATH.as_posix() == "/otra/carpeta"
    assert settings.MIGRAR_HISTORICO_AL_ARRANCAR is False
