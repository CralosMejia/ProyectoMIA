"""Ciclos y etiqueta T..T+30. Identidades inventadas."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.common.exceptions import DomainError
from app.domain.historico.ciclos import (
    DIAS_OBSERVACION,
    DIAS_RENOVACION_ANTICIPADA,
    FECHA_MINIMA_RAZONABLE,
    MotivoCiclo,
    clasificar,
    etiquetar,
    fecha_corte,
)
from app.domain.historico.registro import RegistroHistorico

pytestmark = pytest.mark.unit

CORTE = date(2026, 8, 31)


def registro(
    vence: date | None = date(2026, 7, 15),
    *,
    identidad: str = "C:1700000001",
    plan: Plan = Plan.MENSUAL,
    duracion: int | None = 30,
    actividad: date = date(2026, 6, 15),
    fila: int = 1,
) -> RegistroHistorico:
    return RegistroHistorico(
        identidad=identidad,
        cedula=None,
        nombre="Socio Inventado",
        nombre_normalizado="SOCIO INVENTADO",
        plan=plan,
        plan_original=None,
        forma_pago=FormaPago.SIN_DATO,
        forma_pago_original=None,
        fecha_inicio=actividad,
        fecha_vencimiento=vence,
        fecha_actividad=actividad,
        inicio_aproximado=False,
        duracion_dias=duracion,
        monto_cobrado=None,
        referencia=(2026, "JUNIO", fila),
    )


# ---------------------------------------------------------------- parametros


def test_parametros_del_notebook() -> None:
    assert date(2024, 12, 1) == FECHA_MINIMA_RAZONABLE
    assert DIAS_OBSERVACION == 30
    assert DIAS_RENOVACION_ANTICIPADA == 0


# ---------------------------------------------------------------- fecha de corte


def test_fecha_corte_devuelve_ultimo_dia_del_mes_maximo() -> None:
    assert fecha_corte([date(2026, 8, 1), date(2025, 1, 1)]) == date(2026, 8, 31)


def test_fecha_corte_febrero_bisiesto() -> None:
    assert fecha_corte([date(2024, 2, 1)]) == date(2024, 2, 29)


def test_fecha_corte_diciembre() -> None:
    assert fecha_corte(iter([date(2025, 12, 1)])) == date(2025, 12, 31)


def test_fecha_corte_lista_vacia_lanza_value_error() -> None:
    with pytest.raises(ValueError) as error:
        fecha_corte([])
    assert isinstance(error.value, DomainError)


# ---------------------------------------------------------------- clasificar


@pytest.mark.parametrize(
    ("reg", "esperado"),
    [
        (registro(None), (EstadoCiclo.EXCLUIDO, MotivoCiclo.SIN_VENCIMIENTO)),
        (registro(date(2024, 11, 30)), (EstadoCiclo.EXCLUIDO, MotivoCiclo.FECHA_FUERA_DE_RANGO)),
        (
            registro(date(2026, 9, 5)),
            (EstadoCiclo.EXCLUIDO, MotivoCiclo.VENCIMIENTO_POSTERIOR_AL_CORTE),
        ),
        (registro(plan=Plan.DIARIO), (EstadoCiclo.EXCLUIDO, MotivoCiclo.PASE_DIARIO)),
        (registro(duracion=21), (EstadoCiclo.EXCLUIDO, MotivoCiclo.DURACION_IMPLAUSIBLE)),
        (registro(duracion=401), (EstadoCiclo.EXCLUIDO, MotivoCiclo.DURACION_IMPLAUSIBLE)),
        (registro(duracion=-3), (EstadoCiclo.EXCLUIDO, MotivoCiclo.DURACION_IMPLAUSIBLE)),
        (registro(duracion=22), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        (registro(duracion=400), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        (registro(duracion=None), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        # Caso del tutor: T+30 = 2026-09-19 > corte.
        (registro(date(2026, 8, 20)), (EstadoCiclo.PENDIENTE, MotivoCiclo.VENTANA_INCOMPLETA)),
        # T+30 = 2026-08-31 = corte: limite inclusivo.
        (registro(date(2026, 8, 1)), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        (registro(date(2026, 8, 2)), (EstadoCiclo.PENDIENTE, MotivoCiclo.VENTANA_INCOMPLETA)),
        (registro(date(2026, 7, 15)), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        (registro(date(2024, 12, 1)), (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)),
        (registro(CORTE), (EstadoCiclo.PENDIENTE, MotivoCiclo.VENTANA_INCOMPLETA)),
    ],
)
def test_clasificar_aplica_reglas_en_orden(
    reg: RegistroHistorico, esperado: tuple[EstadoCiclo, MotivoCiclo]
) -> None:
    assert clasificar(reg, CORTE) == esperado


def test_clasificar_diario_sin_vencimiento_prioriza_sin_vencimiento() -> None:
    assert clasificar(registro(None, plan=Plan.DIARIO), CORTE) == (
        EstadoCiclo.EXCLUIDO,
        MotivoCiclo.SIN_VENCIMIENTO,
    )


def test_clasificar_diario_con_duracion_implausible_prioriza_pase_diario() -> None:
    assert clasificar(registro(plan=Plan.DIARIO, duracion=1), CORTE) == (
        EstadoCiclo.EXCLUIDO,
        MotivoCiclo.PASE_DIARIO,
    )


def test_clasificar_fuera_de_rango_prioriza_sobre_diario() -> None:
    assert clasificar(registro(date(2024, 1, 1), plan=Plan.DIARIO), CORTE)[1] is (
        MotivoCiclo.FECHA_FUERA_DE_RANGO
    )


# ---------------------------------------------------------------- etiquetar

T = date(2026, 7, 15)


def _etiqueta_del_primero(otros: list[RegistroHistorico]) -> tuple[bool | None, date | None]:
    ciclos = etiquetar([registro(T, fila=1), *otros], CORTE)
    return ciclos[0].no_renovo, ciclos[0].fecha_renovacion


@pytest.mark.parametrize("dias", [0, 1, 15, 30])
def test_etiquetar_renovacion_dentro_de_ventana_renovo(dias: int) -> None:
    otra = registro(None, actividad=T + timedelta(days=dias), fila=2)

    assert _etiqueta_del_primero([otra]) == (False, T + timedelta(days=dias))


@pytest.mark.parametrize("dias", [-1, 31])
def test_etiquetar_renovacion_fuera_de_ventana_no_renovo(dias: int) -> None:
    otra = registro(None, actividad=T + timedelta(days=dias), fila=2)

    assert _etiqueta_del_primero([otra]) == (True, None)


def test_etiquetar_fecha_renovacion_es_la_minima_de_la_ventana() -> None:
    otras = [
        registro(None, actividad=T + timedelta(days=20), fila=2),
        registro(None, actividad=T + timedelta(days=5), fila=3),
        registro(None, actividad=T + timedelta(days=12), fila=4),
    ]

    assert _etiqueta_del_primero(otras) == (False, T + timedelta(days=5))


def test_etiquetar_membresia_de_otro_socio_no_cuenta() -> None:
    otra = registro(None, identidad="N:OTRO SOCIO", actividad=T + timedelta(days=3), fila=2)

    assert _etiqueta_del_primero([otra]) == (True, None)


def test_etiquetar_pase_diario_no_cuenta_como_renovacion() -> None:
    otra = registro(None, plan=Plan.DIARIO, actividad=T + timedelta(days=3), fila=2)

    assert _etiqueta_del_primero([otra]) == (True, None)


def test_etiquetar_usa_fecha_actividad_de_la_renovacion_aunque_su_inicio_sea_aproximado() -> None:
    base = registro(None, actividad=T + timedelta(days=17), fila=2)
    aproximada = replace(base, fecha_inicio=None, inicio_aproximado=True)

    assert _etiqueta_del_primero([aproximada]) == (False, T + timedelta(days=17))


def test_etiquetar_caso_del_tutor_con_renovacion_posterior_sigue_pendiente() -> None:
    tutor = registro(date(2026, 8, 20), fila=1)
    renovacion = registro(None, actividad=date(2026, 8, 25), fila=2)

    ciclo = etiquetar([tutor, renovacion], CORTE)[0]

    assert (ciclo.estado, ciclo.motivo) == (EstadoCiclo.PENDIENTE, MotivoCiclo.VENTANA_INCOMPLETA)
    assert ciclo.no_renovo is None
    assert ciclo.fecha_renovacion is None


def test_etiquetar_limite_inclusivo_con_renovacion_el_dia_del_corte() -> None:
    limite = registro(date(2026, 8, 1), fila=1)
    renovacion = registro(None, actividad=CORTE, fila=2)

    ciclo = etiquetar([limite, renovacion], CORTE)[0]

    assert ciclo.estado is EstadoCiclo.EVALUABLE
    assert (ciclo.no_renovo, ciclo.fecha_renovacion) == (False, CORTE)


def test_etiquetar_otro_evaluable_del_mismo_socio_cuenta_como_renovacion() -> None:
    siguiente = registro(date(2026, 8, 1), actividad=T + timedelta(days=2), fila=2)

    assert _etiqueta_del_primero([siguiente]) == (False, T + timedelta(days=2))


def test_etiquetar_sin_registros_devuelve_lista_vacia() -> None:
    assert etiquetar([], CORTE) == []


def test_etiquetar_el_propio_registro_nunca_es_su_renovacion() -> None:
    propio = registro(T, actividad=T, fila=1)

    ciclos = etiquetar([propio], CORTE)

    assert ciclos[0].no_renovo is True
    assert ciclos[0].fecha_renovacion is None


def test_etiquetar_duplicado_exacto_en_la_ventana_si_cuenta() -> None:
    original = registro(T, actividad=T, fila=1)
    duplicado = registro(T, actividad=T, fila=1)

    ciclos = etiquetar([original, duplicado], CORTE)

    assert [c.no_renovo for c in ciclos] == [False, False]
    assert [c.fecha_renovacion for c in ciclos] == [T, T]


def test_etiquetar_pendientes_y_excluidos_sin_etiqueta() -> None:
    pendiente = registro(date(2026, 8, 20), fila=1)
    excluido = registro(None, fila=2)
    renovacion = registro(None, actividad=date(2026, 8, 25), fila=3)

    ciclos = etiquetar([pendiente, excluido, renovacion], CORTE)

    assert (ciclos[0].estado, ciclos[0].motivo) == (
        EstadoCiclo.PENDIENTE,
        MotivoCiclo.VENTANA_INCOMPLETA,
    )
    assert (ciclos[1].estado, ciclos[1].motivo) == (
        EstadoCiclo.EXCLUIDO,
        MotivoCiclo.SIN_VENCIMIENTO,
    )
    for ciclo in ciclos:
        assert ciclo.no_renovo is None
        assert ciclo.fecha_renovacion is None


def test_etiquetar_conserva_orden_y_registro() -> None:
    registros = [registro(T, fila=1), registro(None, fila=2)]

    ciclos = etiquetar(registros, CORTE)

    assert [c.registro for c in ciclos] == registros


def test_etiquetar_repr_no_contiene_datos_personales() -> None:
    ciclo = etiquetar([registro(T, identidad="C:0999888777")], CORTE)[0]

    assert "0999888777" not in repr(ciclo)
    assert "INVENTADO" not in repr(ciclo).upper()
