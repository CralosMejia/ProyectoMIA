"""Sin TEST_DATABASE_URL las pruebas de integracion fallan (no se saltan en silencio)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration import conftest as integration_conftest

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[3]
PROBE_TESTS = "tests/integration/infrastructure/test_database_probe.py"


@pytest.mark.parametrize("value", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_require_test_database_url_missing_or_blank_fails_naming_variable(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("TEST_DATABASE_URL", value)

    with pytest.raises(pytest.fail.Exception, match="TEST_DATABASE_URL no esta definida"):
        integration_conftest._require_test_database_url()


def test_integration_suite_without_test_database_url_fails_and_does_not_skip() -> None:
    env = {k: v for k, v in os.environ.items() if k != "TEST_DATABASE_URL"}

    result = subprocess.run(  # noqa: S603 - argumentos fijos, sin entrada externa
        [sys.executable, "-m", "pytest", PROBE_TESTS, "-q", "-p", "no:cacheprovider", "-rA"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 1, output
    assert "TEST_DATABASE_URL no esta definida" in output
    assert "skipped" not in output.lower()
    assert " passed" not in output
