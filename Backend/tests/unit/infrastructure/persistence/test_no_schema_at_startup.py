"""La app no crea tablas ni ejecuta migraciones al arrancar."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

APP_DIR = Path(__file__).resolve().parents[4] / "app"
FORBIDDEN = re.compile(
    r"\bcreate_all\s*\("
    r"|^\s*(import\s+alembic|from\s+alembic\b)"
    r"|\bcommand\.upgrade\s*\("
    r"|alembic\s+upgrade"
)


def test_app_sources_contain_no_create_all_or_alembic_upgrade() -> None:
    sources = sorted(APP_DIR.rglob("*.py"))
    assert sources, f"no se encontraron fuentes en {APP_DIR}"

    offenders = [
        f"{path.relative_to(APP_DIR)}:{lineno}: {line.strip()}"
        for path in sources
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if FORBIDDEN.search(line)
    ]

    assert offenders == []


@pytest.mark.parametrize(
    "line",
    [
        "Base.metadata.create_all(engine)",
        "from alembic import command",
        "import alembic",
        "command.upgrade(cfg, 'head')",
        "os.system('alembic upgrade head')",
    ],
)
def test_forbidden_pattern_detects_schema_creation_line(line: str) -> None:
    assert FORBIDDEN.search(line)
