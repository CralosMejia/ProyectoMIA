"""El router de health no depende de infraestructura ni de SQLAlchemy.

Complementa ``lint-imports``: el contrato de capas cubre ``app.infrastructure``, pero
SQLAlchemy es un paquete externo y no queda cubierto por el contrato.
"""

import ast
from pathlib import Path

import pytest

import app.api.routers.health as health_router

FORBIDDEN_PREFIXES = ("app.infrastructure", "sqlalchemy", "psycopg")


def _imported_modules(source: str) -> list[str]:
    modules: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _is_forbidden(module: str) -> bool:
    return any(module == p or module.startswith(f"{p}.") for p in FORBIDDEN_PREFIXES)


def test_health_router_imports_no_infrastructure_nor_sqlalchemy() -> None:
    source = Path(health_router.__file__).read_text(encoding="utf-8")

    forbidden = [m for m in _imported_modules(source) if _is_forbidden(m)]

    assert forbidden == []


@pytest.mark.parametrize(
    "source",
    [
        "import sqlalchemy",
        "from sqlalchemy import text",
        "from sqlalchemy.orm import Session",
        "from app.infrastructure.persistence.database import create_database_engine",
        "import app.infrastructure.clock.system_clock",
    ],
)
def test_forbidden_import_detector_flags_forbidden_source(source: str) -> None:
    assert any(_is_forbidden(m) for m in _imported_modules(source))


def test_forbidden_import_detector_allows_application_imports() -> None:
    source = "from app.application.health.dtos import HealthDTO\nimport fastapi"

    assert not any(_is_forbidden(m) for m in _imported_modules(source))
