"""Indicadores del piloto (M04, R-018 T1): verificacion T+30 y los cinco indicadores.

Datos inventados.
"""

from collections.abc import Hashable
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.common.enums import FormaPago, Plan
from app.domain.modelo.piloto import (
    TOP_PILOTO,
    CasoPiloto,
    EstadoIndicador,
    EstadoVerificacion,
    MontoMembresia,
    Verificacion,
    calcular_indicadores,
    verificar_renovacion,
)
from app.domain.modelo.reentrenamiento import etiquetar_ciclos
from app.domain.modelo.variables import CicloModelo

pytestmark = pytest.mark.unit

T = date(2026, 8, 10)
CORTE_VERIFICADO = date(2026, 9, 9)  # T + 30


def ciclo(
    ref: int,
    socio: str,
    actividad: date,
    vence: date | None,
    plan: Plan = Plan.MENSUAL,
) -> CicloModelo:
    return CicloModelo(
        clave_socio=socio,
        ref=ref,
        plan=plan,
        forma_pago=FormaPago.EFECTIVO,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        duracion_dias=None if vence is None else (vence - actividad).days,
        monto_cobrado=Decimal("40.00"),
        inicio_aproximado=False,
        excluido=False,
        no_renovo=None,
    )


BASE = ciclo(1, "a", date(2026, 7, 10), T)


# ---------------------------------------------------------------- verificar_renovacion


def test_top_piloto_es_25() -> None:
    assert TOP_PILOTO == 25


def test_verificar_renovacion_antes_de_t_mas_30_es_pendiente() -> None:
    otra = ciclo(2, "a", date(2026, 8, 12), date(2026, 9, 12))

    resultado = verificar_renovacion(1, [BASE, otra], date(2026, 9, 8))

    assert resultado == Verificacion(EstadoVerificacion.PENDIENTE)


def test_verificar_renovacion_vencimiento_posterior_al_corte_es_pendiente() -> None:
    resultado = verificar_renovacion(1, [BASE], date(2026, 8, 1))

    assert resultado.estado is EstadoVerificacion.PENDIENTE


def test_verificar_renovacion_actividad_en_t_mas_30_renovo_con_esa_membresia() -> None:
    otra = ciclo(2, "a", date(2026, 9, 9), date(2026, 10, 9))

    resultado = verificar_renovacion(1, [BASE, otra], CORTE_VERIFICADO)

    assert resultado == Verificacion(EstadoVerificacion.RENOVO, renovacion=2)


def test_verificar_renovacion_actividad_el_mismo_dia_de_t_renovo() -> None:
    otra = ciclo(2, "a", T, T + timedelta(days=30))

    resultado = verificar_renovacion(1, [BASE, otra], CORTE_VERIFICADO)

    assert resultado == Verificacion(EstadoVerificacion.RENOVO, renovacion=2)


def test_verificar_renovacion_actividad_en_t_mas_31_no_renovo() -> None:
    otra = ciclo(2, "a", date(2026, 9, 10), date(2026, 10, 10))

    resultado = verificar_renovacion(1, [BASE, otra], date(2026, 9, 30))

    assert resultado == Verificacion(EstadoVerificacion.NO_RENOVO)


def test_verificar_renovacion_solo_diario_en_ventana_no_renovo() -> None:
    diario = ciclo(2, "a", date(2026, 8, 20), date(2026, 8, 21), plan=Plan.DIARIO)

    resultado = verificar_renovacion(1, [BASE, diario], CORTE_VERIFICADO)

    assert resultado.estado is EstadoVerificacion.NO_RENOVO


def test_verificar_renovacion_de_otro_socio_no_cuenta() -> None:
    ajena = ciclo(2, "b", date(2026, 8, 20), date(2026, 9, 20))

    resultado = verificar_renovacion(1, [BASE, ajena], CORTE_VERIFICADO)

    assert resultado.estado is EstadoVerificacion.NO_RENOVO


def test_verificar_renovacion_dos_en_ventana_elige_menor_actividad_y_ref() -> None:
    tardia = ciclo(2, "a", date(2026, 8, 25), date(2026, 9, 25))
    empate_mayor = ciclo(9, "a", date(2026, 8, 15), date(2026, 9, 15))
    empate_menor = ciclo(5, "a", date(2026, 8, 15), date(2026, 9, 15))

    resultado = verificar_renovacion(
        1, [BASE, tardia, empate_mayor, empate_menor], CORTE_VERIFICADO
    )

    assert resultado == Verificacion(EstadoVerificacion.RENOVO, renovacion=5)


def test_verificar_renovacion_sin_vencimiento_es_sin_dato() -> None:
    sin_vence = ciclo(1, "a", date(2026, 7, 10), None)

    resultado = verificar_renovacion(1, [sin_vence], CORTE_VERIFICADO)

    assert resultado == Verificacion(EstadoVerificacion.SIN_DATO)


def test_verificar_renovacion_ref_inexistente_es_sin_dato() -> None:
    resultado = verificar_renovacion(99, [BASE], CORTE_VERIFICADO)

    assert resultado == Verificacion(EstadoVerificacion.SIN_DATO)


def test_verificar_renovacion_sin_corte_es_pendiente() -> None:
    resultado = verificar_renovacion(1, [BASE], None)

    assert resultado.estado is EstadoVerificacion.PENDIENTE


def _sinteticos() -> list[CicloModelo]:
    d = date
    return [
        ciclo(1, "a", d(2026, 1, 5), d(2026, 2, 5)),
        ciclo(2, "a", d(2026, 2, 5), d(2026, 3, 5)),  # renueva justo en T de 1
        ciclo(3, "a", d(2026, 4, 10), d(2026, 5, 10)),  # 2 no renueva (04-10 > 04-04)
        ciclo(4, "a", d(2026, 6, 9), d(2026, 7, 9)),  # 3 renueva en T+30
        ciclo(5, "b", d(2026, 1, 1), d(2026, 4, 1)),
        ciclo(6, "b", d(2026, 4, 15), d(2026, 4, 16), plan=Plan.DIARIO),  # no cuenta
        ciclo(7, "b", d(2026, 5, 2), d(2026, 6, 2)),  # T+31 de 5: no renueva
        ciclo(8, "c", d(2026, 2, 1), d(2026, 3, 1)),
        ciclo(9, "c", d(2026, 2, 1), d(2026, 3, 1)),  # duplicado exacto: se cuentan entre si
        ciclo(10, "d", d(2026, 3, 1), None),  # sin vencimiento: excluido
        ciclo(11, "d", d(2026, 3, 1), d(2026, 3, 10)),  # duracion implausible
        ciclo(12, "e", d(2025, 1, 1), d(2025, 2, 1)),  # fuera de rango
        ciclo(13, "f", d(2026, 3, 3), d(2026, 4, 3)),
        ciclo(14, "f", d(2026, 3, 20), d(2026, 4, 20)),  # renovacion anticipada: no cuenta
        ciclo(15, "f", d(2026, 4, 25), d(2026, 5, 25)),  # renueva 13 (T+22) y 14 (T+5)
        ciclo(16, "g", d(2026, 8, 1), d(2026, 9, 1)),  # pendiente
        ciclo(17, "g", d(2026, 9, 2), d(2026, 10, 2)),  # vence despues del corte
        ciclo(18, "h", d(2026, 5, 5), d(2026, 6, 5)),
        ciclo(19, "h", d(2026, 6, 5), d(2026, 7, 5), plan=Plan.TRIMESTRAL),
        ciclo(20, "h", d(2026, 7, 4), d(2026, 8, 4), plan=Plan.OTRO),
        ciclo(21, "i", d(2026, 6, 1), d(2026, 7, 1)),
        ciclo(22, "j", d(2026, 5, 31), d(2026, 7, 1), plan=Plan.SEMESTRAL),
        ciclo(23, "j", d(2026, 7, 31), d(2026, 8, 31)),
        ciclo(24, "k", d(2026, 1, 15), d(2026, 2, 15), plan=Plan.DIARIO),
    ]


def test_verificar_renovacion_coincide_con_etiquetar_ciclos() -> None:
    ciclos = _sinteticos()
    corte = date(2026, 9, 15)

    etiquetados = etiquetar_ciclos(ciclos, corte)

    evaluables = 0
    for original, etiquetado in zip(ciclos, etiquetados, strict=True):
        resultado = verificar_renovacion(original.ref, ciclos, corte)
        if etiquetado.no_renovo is None:
            continue
        evaluables += 1
        esperado = (
            EstadoVerificacion.NO_RENOVO if etiquetado.no_renovo else EstadoVerificacion.RENOVO
        )
        assert resultado.estado is esperado, original.ref
    assert evaluables >= 12
    assert len(ciclos) >= 20


# ---------------------------------------------------------------- calcular_indicadores

_R = EstadoVerificacion


def _caso(
    ref: int, contactado: bool = False, dias_antes: int | None = None, vence: date | None = T
) -> CasoPiloto:
    fecha = None if dias_antes is None or vence is None else vence - timedelta(days=dias_antes)
    return CasoPiloto(ref=ref, vencimiento=vence, contactado=contactado, fecha_contacto=fecha)


def _escenario_parcial() -> tuple[
    list[CasoPiloto], dict[Hashable, Verificacion], dict[Hashable, MontoMembresia]
]:
    casos = [
        _caso(0, contactado=True, dias_antes=10),
        _caso(1, contactado=True, dias_antes=5),
        _caso(2, contactado=True, dias_antes=0),  # el mismo dia de T: no es "antes"
        _caso(3, contactado=True),  # sin fecha de contacto
        _caso(4, contactado=True),
        *(_caso(i) for i in range(5, 25)),
    ]
    resultados: dict[Hashable, Verificacion] = {
        0: Verificacion(_R.RENOVO, 100),
        1: Verificacion(_R.RENOVO, 101),
        2: Verificacion(_R.NO_RENOVO),
        3: Verificacion(_R.RENOVO, 103),
        4: Verificacion(_R.PENDIENTE),
    }
    resto = [_R.NO_RENOVO] * 11 + [_R.RENOVO] * 5 + [_R.PENDIENTE] * 4
    for ref, estado in zip(range(5, 25), resto, strict=True):
        resultados[ref] = Verificacion(estado, 200 + ref if estado is _R.RENOVO else None)
    montos: dict[Hashable, MontoMembresia] = {
        100: MontoMembresia(monto_cobrado=Decimal("40.0000"), monto_facturado=Decimal("45")),
        101: MontoMembresia(monto_cobrado=None, monto_facturado=Decimal("35.5000")),
        103: MontoMembresia(monto_cobrado=None, monto_facturado=None),
    }
    return casos, resultados, montos


def test_calcular_indicadores_escenario_parcial_valores_exactos() -> None:
    casos, resultados, montos = _escenario_parcial()

    ind = calcular_indicadores(casos, resultados, montos)

    assert (ind.n_top, ind.sin_dato) == (25, 0)
    p = ind.precision_top25
    assert p.valor == Decimal("0.60000000")
    assert (p.numerador, p.denominador, p.n, p.pendientes) == (12, 20, 25, 5)
    assert p.estado is EstadoIndicador.PARCIAL

    a = ind.contactados_antes_vencimiento
    assert a.valor == Decimal("0.08000000")
    assert (a.numerador, a.denominador, a.n, a.pendientes) == (2, 25, 25, 0)
    assert a.estado is EstadoIndicador.COMPLETO

    d = ind.dias_anticipacion
    assert d.valor == Decimal("5.0")
    assert str(d.valor) == "5.0"
    assert d.n == 3
    assert d.estado is EstadoIndicador.COMPLETO

    t = ind.tasa_renovacion_contactados
    assert t.valor == Decimal("0.75000000")
    assert (t.numerador, t.denominador, t.n, t.pendientes) == (3, 4, 5, 1)
    assert t.estado is EstadoIndicador.PARCIAL

    m = ind.monto_retenido
    assert m.total == Decimal("75.50")
    assert str(m.total) == "75.50"
    assert (m.renovaciones, m.renovaciones_sin_monto, m.n, m.pendientes) == (3, 1, 4, 1)
    assert m.estado is EstadoIndicador.PARCIAL


def test_calcular_indicadores_dias_anticipacion_redondea_a_un_decimal() -> None:
    casos = [_caso(0, True, 1), _caso(1, True, 1), _caso(2, True, 0)]  # 2/3 -> 0.7
    resultados = {i: Verificacion(_R.PENDIENTE) for i in range(3)}

    ind = calcular_indicadores(casos, resultados, {})

    assert ind.dias_anticipacion.valor == Decimal("0.7")


def test_calcular_indicadores_contacto_despues_de_t_da_anticipacion_negativa() -> None:
    casos = [_caso(0, True, -4)]

    ind = calcular_indicadores(casos, {0: Verificacion(_R.PENDIENTE)}, {})

    assert ind.dias_anticipacion.valor == Decimal("-4.0")
    assert ind.contactados_antes_vencimiento.numerador == 0


def test_calcular_indicadores_no_contactado_con_fecha_no_cuenta() -> None:
    casos = [_caso(0, contactado=False, dias_antes=3)]

    ind = calcular_indicadores(casos, {0: Verificacion(_R.NO_RENOVO)}, {})

    assert ind.contactados_antes_vencimiento.numerador == 0
    assert ind.dias_anticipacion.valor is None
    assert ind.tasa_renovacion_contactados.estado is EstadoIndicador.SIN_DATOS


def test_calcular_indicadores_todos_pendientes() -> None:
    casos = [_caso(0, True, 3), _caso(1)]
    resultados = {0: Verificacion(_R.PENDIENTE), 1: Verificacion(_R.PENDIENTE)}

    ind = calcular_indicadores(casos, resultados, {})

    p = ind.precision_top25
    assert (p.valor, p.estado, p.pendientes, p.n) == (None, EstadoIndicador.PENDIENTE, 2, 2)
    t = ind.tasa_renovacion_contactados
    assert (t.valor, t.estado, t.pendientes, t.n) == (None, EstadoIndicador.PENDIENTE, 1, 1)
    m = ind.monto_retenido
    assert (m.total, m.estado, m.pendientes) == (None, EstadoIndicador.PENDIENTE, 1)


def test_calcular_indicadores_todos_verificados_completo_y_monto_cero() -> None:
    casos = [_caso(0, True, 2), _caso(1, True, 1)]
    resultados = {0: Verificacion(_R.NO_RENOVO), 1: Verificacion(_R.NO_RENOVO)}

    ind = calcular_indicadores(casos, resultados, {})

    assert ind.precision_top25.valor == Decimal("1.00000000")
    assert ind.precision_top25.estado is EstadoIndicador.COMPLETO
    assert ind.tasa_renovacion_contactados.valor == Decimal("0.00000000")
    assert ind.monto_retenido.total == Decimal("0.00")
    assert str(ind.monto_retenido.total) == "0.00"
    assert ind.monto_retenido.estado is EstadoIndicador.COMPLETO


def test_calcular_indicadores_caso_sin_dato_queda_fuera_de_los_n() -> None:
    casos = [_caso(0, True, 2), _caso(1, True, 2, vence=None)]
    resultados = {0: Verificacion(_R.NO_RENOVO), 1: Verificacion(_R.SIN_DATO)}

    ind = calcular_indicadores(casos, resultados, {})

    assert (ind.n_top, ind.sin_dato) == (2, 1)
    assert ind.precision_top25.n == 1
    assert ind.contactados_antes_vencimiento.denominador == 1
    assert ind.dias_anticipacion.n == 1
    assert ind.tasa_renovacion_contactados.n == 1


def test_calcular_indicadores_resultado_ausente_cuenta_como_sin_dato() -> None:
    ind = calcular_indicadores([_caso(0)], {}, {})

    assert ind.sin_dato == 1
    assert ind.precision_top25.estado is EstadoIndicador.SIN_DATOS


def test_calcular_indicadores_sin_casos_todo_sin_datos() -> None:
    ind = calcular_indicadores([], {}, {})

    assert (ind.n_top, ind.sin_dato) == (0, 0)
    for bloque in (
        ind.precision_top25,
        ind.contactados_antes_vencimiento,
        ind.tasa_renovacion_contactados,
    ):
        assert (bloque.valor, bloque.n, bloque.estado) == (None, 0, EstadoIndicador.SIN_DATOS)
    assert (ind.dias_anticipacion.valor, ind.dias_anticipacion.estado) == (
        None,
        EstadoIndicador.SIN_DATOS,
    )
    assert (ind.monto_retenido.total, ind.monto_retenido.estado) == (
        None,
        EstadoIndicador.SIN_DATOS,
    )
