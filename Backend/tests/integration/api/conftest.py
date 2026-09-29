"""Fixtures de las pruebas de contrato de la API (app real contra PostgreSQL real)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import URL

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def contract_app(test_database_url: URL) -> FastAPI:
    settings = Settings(
        DATABASE_URL=SecretStr(test_database_url.render_as_string(hide_password=False)),
        APP_ENV="test",
    )
    return create_app(settings)


@pytest.fixture
def contract_client(contract_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(contract_app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def openapi_spec(contract_client: TestClient) -> dict[str, Any]:
    response = contract_client.get("/openapi.json")
    assert response.status_code == 200
    spec: dict[str, Any] = response.json()
    return spec
