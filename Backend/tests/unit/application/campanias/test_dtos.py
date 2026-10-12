"""S8 (R-013): ``CampaniaEntradaDTO`` acota el tamano de sus listas en el borde."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.application.campanias.dtos import MAX_ELEMENTOS_FILTRO, CampaniaEntradaDTO

pytestmark = pytest.mark.unit


def _datos(**cambios: Any) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "nombre": "Campania ficticia",
        "niveles_riesgo": ["ALTO"],
        "planes": ["MENSUAL"],
        "prioridad": 1,
    }
    datos.update(cambios)
    return datos


def test_campania_entrada_lists_with_repeated_values_up_to_limit_are_accepted() -> None:
    dto = CampaniaEntradaDTO.model_validate(
        _datos(
            niveles_riesgo=["ALTO", "MEDIO", "ALTO"],
            planes=["MENSUAL"] * MAX_ELEMENTOS_FILTRO,
        )
    )

    assert len(dto.planes) == MAX_ELEMENTOS_FILTRO


@pytest.mark.parametrize("campo,valor", [("niveles_riesgo", "ALTO"), ("planes", "MENSUAL")])
def test_campania_entrada_list_above_limit_raises(campo: str, valor: str) -> None:
    with pytest.raises(ValidationError):
        CampaniaEntradaDTO.model_validate(_datos(**{campo: [valor] * (MAX_ELEMENTOS_FILTRO + 1)}))


def test_campania_entrada_huge_list_raises() -> None:
    with pytest.raises(ValidationError):
        CampaniaEntradaDTO.model_validate(_datos(planes=["MENSUAL"] * 100_000))
