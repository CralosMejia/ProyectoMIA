"""S8 (R-013): limites de entrada de ``GenerarListaDTO`` en el borde."""

import pytest
from pydantic import ValidationError

from app.application.listas.dtos import TOP_K_MAXIMO, GenerarListaDTO

pytestmark = pytest.mark.unit


def test_generar_lista_top_k_at_maximum_is_accepted() -> None:
    assert GenerarListaDTO(top_k=TOP_K_MAXIMO).top_k == TOP_K_MAXIMO


@pytest.mark.parametrize("top_k", [TOP_K_MAXIMO + 1, 10**9])
def test_generar_lista_top_k_above_maximum_raises(top_k: int) -> None:
    with pytest.raises(ValidationError):
        GenerarListaDTO(top_k=top_k)


def test_top_k_maximum_is_reasonable_for_the_domain() -> None:
    assert 25 <= TOP_K_MAXIMO <= 1000
