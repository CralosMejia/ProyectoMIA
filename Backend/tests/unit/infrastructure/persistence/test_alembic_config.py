"""Configuracion de Alembic (T6) y contrato ADR-002, sin base de datos.

``alembic current`` sin ``DATABASE_URL`` falla en ``env.py`` antes de conectar, por lo que
estas pruebas no necesitan PostgreSQL.
"""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[4]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
SECRET_MARKER = "S3cr3tValor-no-debe-salir"  # noqa: S105 - marcador ficticio de la prueba


def run_alembic(*args: str, database_url: str | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    if database_url is not None:
        env["DATABASE_URL"] = database_url
    return subprocess.run(  # noqa: S603 - argumentos fijos de la prueba
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


# ------------------------------------------------------------------ T6: DATABASE_URL
@pytest.mark.parametrize("database_url", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_alembic_current_without_database_url_exits_nonzero_naming_the_variable(
    database_url: str | None,
) -> None:
    result = run_alembic("current", database_url=database_url)
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stdout + result.stderr


def test_alembic_current_with_wrong_scheme_exits_nonzero_without_showing_value() -> None:
    url = f"mysql://usuario:{SECRET_MARKER}@127.0.0.1:3306/app_db"
    result = run_alembic("current", database_url=url)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "DATABASE_URL" in output
    assert SECRET_MARKER not in output
    assert "usuario" not in output


def test_alembic_ini_contains_no_url_or_credentials() -> None:
    content = ALEMBIC_INI.read_text(encoding="utf-8").lower()
    assert "postgresql" not in content
    assert "sqlalchemy.url" not in content
    assert "password" not in content


# ------------------------------------------------------------------ T7/T8: cadena de revisiones
def test_revision_chain_is_0001_to_0008_with_single_head() -> None:
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    assert script.get_heads() == ["0008"]
    assert script.get_revision("0001").down_revision is None
    assert script.get_revision("0002").down_revision == "0001"
    assert script.get_revision("0003").down_revision == "0002"
    assert script.get_revision("0004").down_revision == "0003"
    assert script.get_revision("0005").down_revision == "0004"
    assert script.get_revision("0006").down_revision == "0005"
    assert script.get_revision("0007").down_revision == "0006"
    assert script.get_revision("0008").down_revision == "0007"


# ------------------------------------------------------------------ ADR-002
def test_import_linter_forbids_data_libraries_in_domain_and_application() -> None:
    config = tomllib.loads((BACKEND_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    linter = config["tool"]["importlinter"]
    assert linter["include_external_packages"] is True
    matching = [
        c
        for c in linter["contracts"]
        if c["type"] == "forbidden"
        and {"app.domain", "app.application"} <= set(c["source_modules"])
        and {"pandas", "numpy", "sklearn"} <= set(c["forbidden_modules"])
    ]
    assert len(matching) == 1
    assert not matching[0].get("ignore_imports")
