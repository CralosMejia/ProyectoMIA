"""PR-AUC (average precision) exacta en Decimal (CU-02, decision (d) de R-011). Datos inventados."""

from decimal import Decimal

import pytest

from app.domain.common.exceptions import DomainError
from app.domain.modelo.metricas import pr_auc

pytestmark = pytest.mark.unit


def _d(*valores: str) -> list[Decimal]:
    return [Decimal(v) for v in valores]


def test_pr_auc_ejemplo_de_sklearn_redondea_a_ocho_decimales() -> None:
    resultado = pr_auc(_d("0.1", "0.4", "0.35", "0.8"), [0, 0, 1, 1])

    assert resultado == Decimal("0.83333333")
    assert isinstance(resultado, Decimal)


def test_pr_auc_ranking_perfecto_es_uno() -> None:
    assert pr_auc(_d("0.9", "0.8", "0.2", "0.1"), [1, 1, 0, 0]) == 1


def test_pr_auc_ranking_invertido() -> None:
    # Positivos al final: precisiones 1/3 y 2/4 -> (1/3 + 1/2) / 2 = 0.41666667
    assert pr_auc(_d("0.9", "0.8", "0.2", "0.1"), [0, 0, 1, 1]) == Decimal("0.41666667")


def test_pr_auc_empates_usan_un_umbral_por_valor_distinto() -> None:
    # Umbral 0.5 incluye los tres empatados: recall 1, precision 2/3 -> 0.66666667
    assert pr_auc(_d("0.5", "0.5", "0.5", "0.1"), [1, 0, 1, 0]) == Decimal("0.66666667")


def test_pr_auc_empate_total_es_la_prevalencia() -> None:
    assert pr_auc(_d("0.3", "0.3", "0.3", "0.3"), [1, 0, 0, 0]) == Decimal("0.25")


def test_pr_auc_no_depende_del_orden_de_entrada() -> None:
    scores = _d("0.1", "0.4", "0.35", "0.8")
    etiquetas = [0, 0, 1, 1]

    assert pr_auc(list(reversed(scores)), list(reversed(etiquetas))) == pr_auc(scores, etiquetas)


def test_pr_auc_sin_positivos_lanza_value_error() -> None:
    with pytest.raises(ValueError):
        pr_auc(_d("0.1", "0.2"), [0, 0])


def test_pr_auc_listas_vacias_lanza_value_error() -> None:
    with pytest.raises(ValueError):
        pr_auc([], [])


def test_pr_auc_longitudes_distintas_lanza_value_error() -> None:
    with pytest.raises(ValueError):
        pr_auc(_d("0.1", "0.2"), [1])


def test_pr_auc_etiqueta_fuera_de_cero_uno_lanza_value_error() -> None:
    with pytest.raises(ValueError):
        pr_auc(_d("0.1", "0.2"), [1, 2])


def test_pr_auc_errores_son_de_dominio() -> None:
    with pytest.raises(DomainError):
        pr_auc(_d("0.1"), [0])
