"""Aserciones comunes de las pruebas de contrato (endpoints publicados en ``501``)."""

from typing import Any

import httpx
from pydantic import TypeAdapter

NOT_IMPLEMENTED_BODY = {
    "error": {"code": "not_implemented", "message": "Esta funcion aun no esta disponible."}
}


def assert_not_implemented(response: httpx.Response) -> None:
    assert response.status_code == 501
    assert response.json() == NOT_IMPLEMENTED_BODY


def assert_validation_error(response: httpx.Response) -> None:
    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"


def operation(spec: dict[str, Any], method: str, path: str) -> dict[str, Any]:
    paths = spec["paths"]
    assert path in paths, f"falta la ruta {path} en /openapi.json"
    assert method in paths[path], f"falta {method.upper()} {path} en /openapi.json"
    op: dict[str, Any] = paths[path][method]
    return op


def json_example(op: dict[str, Any], status_code: int) -> Any:
    responses = op["responses"]
    assert str(status_code) in responses, f"falta la respuesta {status_code}"
    content = responses[str(status_code)].get("content", {})
    assert "application/json" in content, f"la respuesta {status_code} no declara JSON"
    media = content["application/json"]
    assert "example" in media, f"la respuesta {status_code} no declara ejemplo"
    return media["example"]


def assert_operation_contract(
    spec: dict[str, Any],
    method: str,
    path: str,
    success_code: int,
    error_codes: tuple[int, ...],
    success_type: Any | None = None,
) -> dict[str, Any]:
    """Comprueba ejemplos de exito y de cada error; valida el de exito contra su DTO."""
    op = operation(spec, method, path)
    if success_type is not None:
        example = json_example(op, success_code)
        TypeAdapter(success_type).validate_python(example)
    for code in error_codes:
        example = json_example(op, code)
        assert set(example) == {"error"}
        assert set(example["error"]) == {"code", "message"}
        schema_ref = op["responses"][str(code)]["content"]["application/json"]["schema"]
        assert schema_ref["$ref"].endswith("/ErrorResponseDTO")
    return op


def request_body_schema_name(op: dict[str, Any]) -> str:
    ref: str = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    return ref.rsplit("/", 1)[-1]
