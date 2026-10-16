"""Umbrales fijos del notebook y nivel de riesgo (CU-05, R-015 T11). Datos inventados."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.common.enums import FormaPago, NivelRiesgo, Plan
from app.domain.common.exceptions import DomainError
from app.domain.modelo.umbrales import (
    UMBRAL_ALTO,
    UMBRAL_MEDIO,
    Umbrales,
    meses_recientes_con_resultado,
    nivel_de,
    umbrales_fijos,
)
from app.domain.modelo.variables import CicloModelo

pytestmark = pytest.mark.unit

DIEZ = [Decimal(i) / 10 for i in range(1, 11)]  # 0.1 ... 1.0


def test_umbrales_fijos_son_los_cortes_del_notebook() -> None:
    # Notebook 13.2: ALTO si p >= 0,70; MEDIO si p >= 0,50; si no, BAJO.
    assert (Decimal("0.70"), Decimal("0.50")) == (UMBRAL_ALTO, UMBRAL_MEDIO)
    umbrales = umbrales_fijos(DIEZ)
    assert (umbrales.alto, umbrales.medio) == (Decimal("0.70"), Decimal("0.50"))
    assert isinstance(umbrales.alto, Decimal)


def test_umbrales_fijos_no_dependen_de_los_scores() -> None:
    bajos = umbrales_fijos([Decimal("0.1"), Decimal("0.2")])
    altos = umbrales_fijos([Decimal("0.9"), Decimal("0.95")])

    assert (bajos.alto, bajos.medio) == (altos.alto, altos.medio) == (UMBRAL_ALTO, UMBRAL_MEDIO)


def test_umbrales_fijos_porcentajes_son_la_reparticion_observada_de_los_scores() -> None:
    # DIEZ: 0.7, 0.8, 0.9, 1.0 -> ALTO (40 %); 0.5, 0.6 -> MEDIO (20 %); 0.1..0.4 -> BAJO (40 %).
    assert umbrales_fijos(DIEZ).porcentajes == {"ALTO": 40, "MEDIO": 20, "BAJO": 40}


def test_umbrales_fijos_porcentajes_redondeo_bancario_a_entero() -> None:
    # 1 de 8 = 12,5 % -> 12; 3 de 8 = 37,5 % -> 38; 4 de 8 = 50 %.
    scores = [Decimal("0.75")] + [Decimal("0.55")] * 3 + [Decimal("0.2")] * 4

    assert umbrales_fijos(scores).porcentajes == {"ALTO": 12, "MEDIO": 38, "BAJO": 50}


def test_umbrales_fijos_sin_scores_lanza_error() -> None:
    with pytest.raises(DomainError):
        umbrales_fijos([])


@pytest.mark.parametrize(
    ("score", "nivel"),
    [
        ("0.71019972", NivelRiesgo.ALTO),
        ("0.70000000", NivelRiesgo.ALTO),
        ("0.69999999", NivelRiesgo.MEDIO),
        ("0.69706115", NivelRiesgo.MEDIO),
        ("0.50000000", NivelRiesgo.MEDIO),
        ("0.49999999", NivelRiesgo.BAJO),
        ("0", NivelRiesgo.BAJO),
        ("1", NivelRiesgo.ALTO),
    ],
)
def test_nivel_de_con_los_umbrales_fijos(score: str, nivel: NivelRiesgo) -> None:
    assert nivel_de(Decimal(score), umbrales_fijos([Decimal(score)])) is nivel


def test_nivel_de_igual_al_umbral_queda_en_el_nivel_superior() -> None:
    umbrales = Umbrales(alto=Decimal("0.6"), medio=Decimal("0.4"), porcentajes={})

    assert nivel_de(Decimal("0.6"), umbrales) is NivelRiesgo.ALTO
    assert nivel_de(Decimal("0.4"), umbrales) is NivelRiesgo.MEDIO
    assert nivel_de(Decimal("0.39999999"), umbrales) is NivelRiesgo.BAJO


# ---------------------------------------------------------------- meses recientes


def ciclo(
    vence: date, *, ref: int, excluido: bool = False, no_renovo: bool | None = True
) -> CicloModelo:
    return CicloModelo(
        clave_socio=f"C:{ref:010d}",
        ref=ref,
        plan=Plan.MENSUAL,
        forma_pago=FormaPago.EFECTIVO,
        fecha_actividad=vence,
        fecha_vencimiento=vence,
        duracion_dias=30,
        monto_cobrado=None,
        inicio_aproximado=False,
        excluido=excluido,
        no_renovo=no_renovo,
    )


def test_meses_recientes_con_resultado_toma_los_tres_ultimos_meses() -> None:
    evaluables = [ciclo(date(2026, mes, 15), ref=mes) for mes in range(4, 9)]
    pendiente = ciclo(date(2026, 9, 10), ref=9, no_renovo=None)
    excluido = ciclo(date(2026, 8, 20), ref=10, excluido=True, no_renovo=None)

    recientes = meses_recientes_con_resultado([*evaluables, pendiente, excluido])

    assert [c.ref for c in recientes] == [6, 7, 8]


def test_meses_recientes_incluye_todos_los_ciclos_de_esos_meses() -> None:
    ciclos = [
        ciclo(date(2026, 8, 1), ref=1),
        ciclo(date(2026, 5, 1), ref=2),
        ciclo(date(2026, 8, 31), ref=3, no_renovo=False),
        ciclo(date(2026, 6, 1), ref=4),
        ciclo(date(2026, 7, 1), ref=5),
    ]

    assert [c.ref for c in meses_recientes_con_resultado(ciclos)] == [1, 3, 4, 5]


def test_meses_recientes_con_n_parametrizable() -> None:
    ciclos = [ciclo(date(2026, mes, 15), ref=mes) for mes in range(4, 9)]

    assert [c.ref for c in meses_recientes_con_resultado(ciclos, n=1)] == [8]


def test_meses_recientes_con_menos_meses_que_n_devuelve_todos() -> None:
    ciclos = [ciclo(date(2026, 8, 15), ref=1), ciclo(date(2026, 7, 15), ref=2)]

    assert [c.ref for c in meses_recientes_con_resultado(ciclos)] == [1, 2]


def test_meses_recientes_n_invalido_lanza_error() -> None:
    with pytest.raises(ValueError):
        meses_recientes_con_resultado([ciclo(date(2026, 8, 1), ref=1)], n=0)


def test_meses_recientes_sin_evaluables_lanza_error() -> None:
    with pytest.raises(ValueError):
        meses_recientes_con_resultado([])
    with pytest.raises(DomainError):
        meses_recientes_con_resultado([ciclo(date(2026, 8, 1), ref=1, no_renovo=None)])
