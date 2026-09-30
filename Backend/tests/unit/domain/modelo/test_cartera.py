"""Cartera en el horizonte, renovados y priorizacion (notebook MVP 13.8). Datos inventados."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.common.enums import FormaPago, Plan
from app.domain.modelo.cartera import (
    CicloPuntuado,
    priorizar,
    seleccionar_cartera,
    ya_renovo,
)
from app.domain.modelo.variables import CicloModelo

pytestmark = pytest.mark.unit

FECHA = date(2026, 8, 31)
HORIZONTE = 30


def ciclo(
    vence: date | None = date(2026, 9, 15),
    *,
    clave: str = "C:1700000001",
    ref: int = 0,
    plan: Plan = Plan.MENSUAL,
    duracion: int | None = 30,
    actividad: date = date(2026, 8, 16),
) -> CicloModelo:
    return CicloModelo(
        clave_socio=clave,
        ref=ref,
        plan=plan,
        forma_pago=FormaPago.EFECTIVO,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        duracion_dias=duracion,
        monto_cobrado=None,
        inicio_aproximado=False,
        excluido=True,
        no_renovo=None,
    )


# ---------------------------------------------------------------- cartera


@pytest.mark.parametrize(
    ("vence", "dentro"),
    [
        (date(2026, 8, 31), False),
        (date(2026, 9, 1), True),
        (date(2026, 9, 30), True),
        (date(2026, 10, 1), False),
    ],
)
def test_seleccionar_cartera_limites_del_horizonte(vence: date, dentro: bool) -> None:
    c = ciclo(vence)

    assert (c in seleccionar_cartera([c], FECHA, HORIZONTE)) is dentro


def test_seleccionar_cartera_sin_vencimiento_queda_fuera() -> None:
    assert seleccionar_cartera([ciclo(None)], FECHA, HORIZONTE) == []


def test_seleccionar_cartera_excluye_diario() -> None:
    assert seleccionar_cartera([ciclo(plan=Plan.DIARIO, duracion=None)], FECHA, HORIZONTE) == []


@pytest.mark.parametrize(
    ("duracion", "dentro"), [(21, False), (22, True), (400, True), (401, False), (None, True)]
)
def test_seleccionar_cartera_duracion_plausible(duracion: int | None, dentro: bool) -> None:
    c = ciclo(duracion=duracion)

    assert (c in seleccionar_cartera([c], FECHA, HORIZONTE)) is dentro


def test_seleccionar_cartera_conserva_el_orden_de_entrada() -> None:
    a = ciclo(date(2026, 9, 20), ref=1)
    b = ciclo(date(2026, 9, 2), ref=2)

    assert seleccionar_cartera([a, b], FECHA, HORIZONTE) == [a, b]


@pytest.mark.parametrize("horizonte", [0, -5])
def test_seleccionar_cartera_horizonte_invalido_lanza_error(horizonte: int) -> None:
    with pytest.raises(ValueError, match="horizonte"):
        seleccionar_cartera([ciclo()], FECHA, horizonte)


def test_seleccionar_cartera_horizonte_de_un_dia_solo_incluye_el_dia_siguiente() -> None:
    manana = ciclo(date(2026, 9, 1), ref=1)
    pasado = ciclo(date(2026, 9, 2), ref=2)

    assert seleccionar_cartera([manana, pasado], FECHA, 1) == [manana]


# ---------------------------------------------------------------- ya_renovo


def test_ya_renovo_con_membresia_posterior_no_diaria() -> None:
    actual = ciclo(ref=1)
    posterior = ciclo(date(2026, 10, 20), ref=2, actividad=date(2026, 8, 20))

    assert ya_renovo(actual, [actual, posterior]) is True


def test_ya_renovo_con_membresia_posterior_diaria_es_falso() -> None:
    actual = ciclo(ref=1)
    diario = ciclo(date(2026, 8, 21), ref=2, plan=Plan.DIARIO, actividad=date(2026, 8, 20))

    assert ya_renovo(actual, [actual, diario]) is False


def test_ya_renovo_de_otro_socio_es_falso() -> None:
    actual = ciclo(ref=1)
    ajeno = ciclo(ref=2, clave="C:1700000009", actividad=date(2026, 8, 20))

    assert ya_renovo(actual, [actual, ajeno]) is False


def test_ya_renovo_membresia_anterior_o_misma_fecha_es_falso() -> None:
    actual = ciclo(ref=1)
    anterior = ciclo(date(2026, 8, 15), ref=2, actividad=date(2026, 7, 16))
    mismo_dia = ciclo(ref=3)

    assert ya_renovo(actual, [anterior, mismo_dia]) is False


def test_ya_renovo_con_posterior_excluida_no_diaria_es_verdadero() -> None:
    # El notebook (13.8) usa todos los registros no DIARIO, aunque su ciclo quede excluido.
    actual = ciclo(ref=1)
    implausible = ciclo(date(2028, 1, 1), ref=2, duracion=500, actividad=date(2026, 8, 20))

    assert ya_renovo(actual, [actual, implausible]) is True


def test_ya_renovo_la_propia_membresia_nunca_cuenta() -> None:
    actual = ciclo(ref=1)

    assert ya_renovo(actual, [actual]) is False


# ---------------------------------------------------------------- priorizar


def puntuado(
    membresia_id: int, score: str, *, clave: str | None = None, vence: date = date(2026, 9, 15)
) -> CicloPuntuado:
    return CicloPuntuado(
        membresia_id=membresia_id,
        clave_socio=clave if clave is not None else f"C:{membresia_id:010d}",
        fecha_vencimiento=vence,
        score=Decimal(score),
    )


def test_priorizar_ordena_por_score_descendente() -> None:
    filas = priorizar([puntuado(1, "0.2"), puntuado(2, "0.9"), puntuado(3, "0.5")], 2, FECHA)

    assert [f.ciclo.membresia_id for f in filas] == [2, 3, 1]
    assert [f.prioridad for f in filas] == [1, 2, 3]
    assert [f.dentro_top_k for f in filas] == [True, True, False]


def test_priorizar_empates_por_vencimiento_y_despues_por_id() -> None:
    filas = priorizar(
        [
            puntuado(5, "0.5", vence=date(2026, 9, 20)),
            puntuado(4, "0.5", vence=date(2026, 9, 10)),
            puntuado(3, "0.5", vence=date(2026, 9, 20)),
        ],
        25,
        FECHA,
    )

    assert [f.ciclo.membresia_id for f in filas] == [4, 3, 5]


def test_priorizar_una_fila_por_socio_la_de_mayor_score() -> None:
    filas = priorizar(
        [
            puntuado(1, "0.4", clave="S"),
            puntuado(2, "0.8", clave="S"),
            puntuado(3, "0.6", clave="T"),
        ],
        25,
        FECHA,
    )

    assert [f.ciclo.membresia_id for f in filas] == [2, 3]
    assert [f.prioridad for f in filas] == [1, 2]


def test_priorizar_mismo_socio_con_empate_conserva_el_vencimiento_mas_cercano() -> None:
    filas = priorizar(
        [
            puntuado(8, "0.7", clave="S", vence=date(2026, 9, 25)),
            puntuado(9, "0.7", clave="S", vence=date(2026, 9, 5)),
        ],
        25,
        FECHA,
    )

    assert [f.ciclo.membresia_id for f in filas] == [9]


def test_priorizar_top_k_exacto_marca_solo_las_k_primeras() -> None:
    filas = priorizar([puntuado(i, f"0.{i}") for i in range(1, 6)], 1, FECHA)

    assert [f.dentro_top_k for f in filas] == [True, False, False, False, False]


def test_priorizar_top_k_mayor_que_n_marca_todas() -> None:
    filas = priorizar([puntuado(1, "0.4"), puntuado(2, "0.3")], 25, FECHA)

    assert sum(f.dentro_top_k for f in filas) == 2


def test_priorizar_dias_para_vencer() -> None:
    (fila,) = priorizar([puntuado(1, "0.4", vence=date(2026, 9, 30))], 25, FECHA)

    assert fila.dias_para_vencer == 30


def test_priorizar_vacia_devuelve_lista_vacia() -> None:
    assert priorizar([], 25, FECHA) == []


def test_priorizar_top_k_invalido_lanza_error() -> None:
    with pytest.raises(ValueError, match="top_k"):
        priorizar([puntuado(1, "0.4")], 0, FECHA)
