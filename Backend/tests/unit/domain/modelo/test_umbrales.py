"""Umbrales por percentiles y nivel de riesgo (CU-05, decision (d)). Datos inventados."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.common.enums import FormaPago, NivelRiesgo, Plan
from app.domain.common.exceptions import DomainError
from app.domain.modelo.umbrales import (
    PORCENTAJES_POR_DEFECTO,
    Umbrales,
    calcular_umbrales,
    meses_recientes_con_resultado,
    nivel_de,
)
from app.domain.modelo.variables import CicloModelo

pytestmark = pytest.mark.unit

DIEZ = [Decimal(i) / 10 for i in range(1, 11)]  # 0.1 ... 1.0


def test_calcular_umbrales_percentil_lineal() -> None:
    umbrales = calcular_umbrales(DIEZ)

    assert umbrales.alto == Decimal("0.82")
    assert umbrales.medio == Decimal("0.55")
    assert isinstance(umbrales.alto, Decimal)


def test_calcular_umbrales_no_depende_del_orden_de_entrada() -> None:
    assert calcular_umbrales(list(reversed(DIEZ))) == calcular_umbrales(DIEZ)


def test_porcentajes_por_defecto() -> None:
    assert PORCENTAJES_POR_DEFECTO == (20, 30, 50)
    assert calcular_umbrales(DIEZ).porcentajes == {"ALTO": 20, "MEDIO": 30, "BAJO": 50}


def test_niveles_con_diez_scores() -> None:
    umbrales = calcular_umbrales(DIEZ)
    niveles = [nivel_de(s, umbrales) for s in DIEZ]

    assert niveles.count(NivelRiesgo.ALTO) == 2
    assert niveles.count(NivelRiesgo.MEDIO) == 3
    assert niveles.count(NivelRiesgo.BAJO) == 5


def test_nivel_de_igual_al_umbral_queda_en_el_nivel_superior() -> None:
    umbrales = Umbrales(alto=Decimal("0.6"), medio=Decimal("0.4"), porcentajes={})

    assert nivel_de(Decimal("0.6"), umbrales) is NivelRiesgo.ALTO
    assert nivel_de(Decimal("0.4"), umbrales) is NivelRiesgo.MEDIO
    assert nivel_de(Decimal("0.39999999"), umbrales) is NivelRiesgo.BAJO


def test_niveles_con_mil_scores() -> None:
    scores = [Decimal(i) / 1000 for i in range(1, 1001)]
    umbrales = calcular_umbrales(scores)
    niveles = [nivel_de(s, umbrales) for s in scores]

    assert abs(niveles.count(NivelRiesgo.ALTO) - 200) <= 1
    assert abs(niveles.count(NivelRiesgo.MEDIO) - 300) <= 1
    assert abs(niveles.count(NivelRiesgo.BAJO) - 500) <= 1


def test_umbrales_cuantizados_a_ocho_decimales() -> None:
    scores = [Decimal("0.12345678"), Decimal("0.87654321"), Decimal("0.5")]

    umbrales = calcular_umbrales(scores)

    assert umbrales.alto == umbrales.alto.quantize(Decimal("0.00000001"))
    assert umbrales.medio == Decimal("0.5")


@pytest.mark.parametrize(
    ("maximo", "medio"),
    [("0.00000005", Decimal("0.00000002")), ("0.00000007", Decimal("0.00000004"))],
)
def test_calcular_umbrales_redondeo_bancario_a_ocho_decimales(maximo: str, medio: Decimal) -> None:
    # P50 de [0, x] = x/2, que cae justo en la mitad del octavo decimal: ROUND_HALF_EVEN.
    umbrales = calcular_umbrales([Decimal(0), Decimal(maximo)])

    assert umbrales.medio == medio


def test_calcular_umbrales_con_un_solo_score() -> None:
    umbrales = calcular_umbrales([Decimal("0.4")])

    assert umbrales.alto == umbrales.medio == Decimal("0.4")
    assert nivel_de(Decimal("0.4"), umbrales) is NivelRiesgo.ALTO


def test_porcentajes_que_no_suman_cien_lanzan_error() -> None:
    with pytest.raises(ValueError, match="100"):
        calcular_umbrales(DIEZ, (20, 30, 40))


def test_porcentajes_negativos_lanzan_error() -> None:
    with pytest.raises(ValueError):
        calcular_umbrales(DIEZ, (-10, 60, 50))


def test_sin_scores_lanza_error() -> None:
    with pytest.raises(DomainError):
        calcular_umbrales([])


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
