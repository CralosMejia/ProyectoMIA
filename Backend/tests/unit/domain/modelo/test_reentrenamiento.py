"""Reglas de dominio del reentrenamiento (CU-02, decisiones (d) y (e) de R-011).

Datos inventados.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.historico.ciclos import etiquetar
from app.domain.historico.registro import RegistroHistorico
from app.domain.modelo.reentrenamiento import (
    INTERVALO_MESES,
    AccionProgramada,
    CriteriosReentrenamiento,
    accion_programada,
    es_ciclo_nuevo,
    etiquetar_ciclos,
    evaluar_criterios,
    fechas_perdidas,
    proxima_tras_omitido,
)
from app.domain.modelo.variables import (
    VARIABLES_CATEGORICAS,
    VARIABLES_NUMERICAS,
    CicloModelo,
    ValorVariable,
)

pytestmark = pytest.mark.unit

CORTE = date(2026, 9, 30)


def _ciclo(
    socio: str,
    ref: int,
    actividad: date,
    vence: date | None,
    plan: Plan = Plan.MENSUAL,
    duracion: int | None = 30,
    excluido: bool = False,
    no_renovo: bool | None = None,
) -> CicloModelo:
    return CicloModelo(
        clave_socio=socio,
        ref=ref,
        plan=plan,
        forma_pago=FormaPago.SIN_DATO,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        duracion_dias=duracion,
        monto_cobrado=None,
        inicio_aproximado=False,
        excluido=excluido,
        no_renovo=no_renovo,
    )


# ---------------------------------------------------------------- etiquetar_ciclos


def test_etiquetar_ciclos_con_renovacion_en_ventana_no_renovo_false() -> None:
    actual = _ciclo("A", 1, date(2026, 7, 1), date(2026, 7, 31))
    renovacion = _ciclo("A", 2, date(2026, 8, 10), date(2026, 9, 9))

    resultado = etiquetar_ciclos([actual, renovacion], CORTE)

    assert resultado[0].no_renovo is False
    assert resultado[0].excluido is False


def test_etiquetar_ciclos_renovacion_en_el_borde_t_mas_30_cuenta() -> None:
    actual = _ciclo("A", 1, date(2026, 7, 1), date(2026, 7, 31))
    renovacion = _ciclo("A", 2, date(2026, 8, 30), date(2026, 9, 29))

    assert etiquetar_ciclos([actual, renovacion], CORTE)[0].no_renovo is False


def test_etiquetar_ciclos_sin_renovacion_no_renovo_true() -> None:
    actual = _ciclo("A", 1, date(2026, 7, 1), date(2026, 7, 31))
    otro_socio = _ciclo("B", 2, date(2026, 8, 10), date(2026, 9, 9))
    fuera_de_ventana = _ciclo("A", 3, date(2026, 8, 31), date(2026, 9, 30))

    resultado = etiquetar_ciclos([actual, otro_socio, fuera_de_ventana], CORTE)

    assert resultado[0].no_renovo is True


def test_etiquetar_ciclos_renovacion_diaria_no_cuenta() -> None:
    actual = _ciclo("A", 1, date(2026, 7, 1), date(2026, 7, 31))
    diario = _ciclo("A", 2, date(2026, 8, 5), date(2026, 8, 5), plan=Plan.DIARIO, duracion=None)

    resultado = etiquetar_ciclos([actual, diario], CORTE)

    assert resultado[0].no_renovo is True
    assert resultado[1].excluido is True
    assert resultado[1].no_renovo is None


def test_etiquetar_ciclos_ventana_incompleta_pendiente_no_excluido() -> None:
    pendiente = _ciclo("A", 1, date(2026, 8, 20), date(2026, 9, 19))

    resultado = etiquetar_ciclos([pendiente], CORTE)[0]

    assert resultado.no_renovo is None
    assert resultado.excluido is False


def test_etiquetar_ciclos_reemplaza_etiquetas_previas() -> None:
    viejo = _ciclo("A", 1, date(2026, 8, 20), date(2026, 9, 19), excluido=True, no_renovo=True)

    resultado = etiquetar_ciclos([viejo], CORTE)[0]

    assert resultado.excluido is False
    assert resultado.no_renovo is None
    assert resultado.ref == 1


def test_etiquetar_ciclos_conserva_orden_y_datos() -> None:
    ciclos = [
        _ciclo("B", 7, date(2026, 5, 1), date(2026, 5, 31)),
        _ciclo("A", 3, date(2026, 6, 1), date(2026, 6, 30)),
    ]

    resultado = etiquetar_ciclos(ciclos, CORTE)

    assert [c.ref for c in resultado] == [7, 3]
    assert resultado[0] == replace(ciclos[0], no_renovo=True)


def _registro(
    identidad: str, fila: int, actividad: date, vence: date | None, plan: Plan, duracion: int | None
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


def test_etiquetar_ciclos_mismo_resultado_que_etiquetar_del_historico() -> None:
    datos: list[tuple[str, date, date | None, Plan, int | None]] = [
        ("A", date(2026, 6, 1), date(2026, 6, 30), Plan.MENSUAL, 29),
        ("A", date(2026, 6, 30), date(2026, 7, 30), Plan.MENSUAL, 30),  # renovacion en T
        ("A", date(2026, 6, 30), date(2026, 7, 30), Plan.MENSUAL, 30),  # duplicado exacto
        ("A", date(2026, 7, 15), date(2026, 7, 15), Plan.DIARIO, None),
        ("B", date(2026, 3, 1), date(2026, 5, 30), Plan.TRIMESTRAL, 90),
        ("B", date(2026, 9, 1), date(2026, 10, 1), Plan.MENSUAL, 30),  # vence tras el corte
        ("C", date(2026, 8, 25), date(2026, 9, 24), Plan.MENSUAL, 30),  # ventana incompleta
        ("C", date(2024, 1, 1), date(2024, 1, 31), Plan.MENSUAL, 30),  # fecha fuera de rango
        ("D", date(2026, 1, 1), None, Plan.OTRO, None),  # sin vencimiento
        ("D", date(2026, 1, 1), date(2026, 1, 11), Plan.OTRO, 10),  # duracion implausible
    ]
    registros = [
        _registro(identidad, fila, actividad, vence, plan, duracion)
        for fila, (identidad, actividad, vence, plan, duracion) in enumerate(datos)
    ]
    ciclos = [
        _ciclo(r.identidad, fila, r.fecha_actividad, r.fecha_vencimiento, r.plan, r.duracion_dias)
        for fila, r in enumerate(registros)
    ]

    esperados = [
        (
            e.estado is EstadoCiclo.EXCLUIDO,
            e.no_renovo if e.estado is EstadoCiclo.EVALUABLE else None,
        )
        for e in etiquetar(registros, CORTE)
    ]
    obtenidos = [(c.excluido, c.no_renovo) for c in etiquetar_ciclos(ciclos, CORTE)]

    assert obtenidos == esperados
    assert (False, False) in obtenidos and (False, True) in obtenidos
    assert (False, None) in obtenidos and (True, None) in obtenidos


# ---------------------------------------------------------------- es_ciclo_nuevo

CORTE_VIGENTE = date(2026, 8, 31)


def test_es_ciclo_nuevo_ventana_incompleta_al_corte_vigente_true() -> None:
    # 2026-08-02 + 30 = 2026-09-01 > 2026-08-31: el modelo vigente no pudo etiquetarlo.
    ciclo = _ciclo("A", 1, date(2026, 7, 3), date(2026, 8, 2), no_renovo=True)

    assert es_ciclo_nuevo(ciclo, CORTE_VIGENTE) is True


def test_es_ciclo_nuevo_ventana_completa_justo_en_el_corte_vigente_false() -> None:
    # 2026-08-01 + 30 = 2026-08-31, que no es > 2026-08-31: ya era evaluable para el vigente.
    ciclo = _ciclo("A", 1, date(2026, 7, 2), date(2026, 8, 1), no_renovo=True)

    assert es_ciclo_nuevo(ciclo, CORTE_VIGENTE) is False


def test_es_ciclo_nuevo_vencimiento_anterior_false() -> None:
    ciclo = _ciclo("A", 1, date(2026, 6, 1), date(2026, 7, 1), no_renovo=False)

    assert es_ciclo_nuevo(ciclo, CORTE_VIGENTE) is False


def test_es_ciclo_nuevo_no_evaluable_false() -> None:
    pendiente = _ciclo("A", 1, date(2026, 8, 20), date(2026, 9, 19), no_renovo=None)
    excluido = _ciclo("A", 2, date(2026, 8, 5), date(2026, 9, 5), excluido=True)
    sin_vencimiento = _ciclo("A", 3, date(2026, 8, 5), None, no_renovo=True)

    assert es_ciclo_nuevo(pendiente, CORTE_VIGENTE) is False
    assert es_ciclo_nuevo(excluido, CORTE_VIGENTE) is False
    assert es_ciclo_nuevo(sin_vencimiento, CORTE_VIGENTE) is False


# ---------------------------------------------------------------- criterios

FILA_COMPLETA: dict[str, ValorVariable] = {
    nombre: None for nombre in VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS
}


def _nuevos(renovaron: int, no_renovaron: int) -> list[CicloModelo]:
    vence = date(2026, 8, 15)
    return [
        _ciclo(f"S{i}", i, date(2026, 7, 16), vence, no_renovo=i >= renovaron)
        for i in range(renovaron + no_renovaron)
    ]


def _vencimientos(con: int, sin: int) -> list[date | None]:
    return [date(2026, 9, 1)] * con + [None] * sin


def test_criterios_por_defecto() -> None:
    criterios = CriteriosReentrenamiento()

    assert criterios.min_ciclos_nuevos == 150
    assert criterios.min_cobertura_vencimiento == Decimal("0.60")
    assert criterios.min_casos_por_clase == 20
    assert criterios.meses_comparacion == 3
    assert INTERVALO_MESES == 6


def test_evaluar_criterios_todo_cumplido_sin_motivos() -> None:
    assert evaluar_criterios(_nuevos(75, 75), _vencimientos(60, 40), [FILA_COMPLETA]) == []


def test_evaluar_criterios_149_ciclos_nuevos_motivo_de_ciclos() -> None:
    motivos = evaluar_criterios(_nuevos(74, 75), _vencimientos(60, 40), [FILA_COMPLETA])

    assert motivos == ["Hay 149 ciclos nuevos evaluables; se necesitan al menos 150."]


def test_evaluar_criterios_19_de_una_clase_motivo_de_clase() -> None:
    motivos = evaluar_criterios(_nuevos(19, 131), _vencimientos(60, 40), [FILA_COMPLETA])

    assert motivos == [
        "Entre los ciclos nuevos hay 19 que renovaron y 131 que no renovaron; "
        "se necesitan al menos 20 de cada clase."
    ]


def test_evaluar_criterios_19_que_no_renovaron_motivo_de_clase() -> None:
    motivos = evaluar_criterios(_nuevos(131, 19), _vencimientos(60, 40), [FILA_COMPLETA])

    assert len(motivos) == 1
    assert "131 que renovaron y 19 que no renovaron" in motivos[0]


def test_evaluar_criterios_cobertura_59_motivo_de_cobertura() -> None:
    motivos = evaluar_criterios(_nuevos(75, 75), _vencimientos(59, 41), [FILA_COMPLETA])

    assert motivos == [
        "Solo el 59.00 % de las membresias nuevas tiene fecha de vencimiento; "
        "se necesita al menos el 60.00 %."
    ]


def test_evaluar_criterios_sin_membresias_nuevas_motivo_de_cobertura() -> None:
    motivos = evaluar_criterios(_nuevos(75, 75), [], [FILA_COMPLETA])

    assert motivos == ["No hay membresias nuevas desde el ultimo entrenamiento."]


def test_evaluar_criterios_fila_sin_una_columna_motivo_de_columnas() -> None:
    incompleta = {k: v for k, v in FILA_COMPLETA.items() if k != "mes_vencimiento"}

    motivos = evaluar_criterios(_nuevos(75, 75), _vencimientos(60, 40), [FILA_COMPLETA, incompleta])

    assert motivos == ["El conjunto de entrenamiento no tiene las columnas que exige el modelo."]


def test_evaluar_criterios_sin_filas_de_entrenamiento_motivo_de_columnas() -> None:
    motivos = evaluar_criterios(_nuevos(75, 75), _vencimientos(60, 40), [])

    assert motivos == ["El conjunto de entrenamiento no tiene las columnas que exige el modelo."]


def test_evaluar_criterios_acumula_motivos_en_orden() -> None:
    motivos = evaluar_criterios(_nuevos(10, 10), [], [])

    assert len(motivos) == 4
    assert motivos[0].startswith("Hay 20 ciclos nuevos")
    assert motivos[1].startswith("No hay membresias nuevas")
    assert motivos[2].startswith("Entre los ciclos nuevos")
    assert motivos[3].startswith("El conjunto de entrenamiento")


def test_evaluar_criterios_usa_umbrales_configurados() -> None:
    criterios = CriteriosReentrenamiento(
        min_ciclos_nuevos=4,
        min_cobertura_vencimiento=Decimal("0.50"),
        min_casos_por_clase=2,
        meses_comparacion=1,
    )

    assert evaluar_criterios(_nuevos(2, 2), _vencimientos(1, 1), [FILA_COMPLETA], criterios) == []


def test_criterios_rechaza_valores_invalidos() -> None:
    with pytest.raises(ValueError):
        CriteriosReentrenamiento(min_cobertura_vencimiento=Decimal("1.5"))
    with pytest.raises(ValueError):
        CriteriosReentrenamiento(min_ciclos_nuevos=-1)
    with pytest.raises(ValueError):
        CriteriosReentrenamiento(meses_comparacion=0)


# ---------------------------------------------------------------- decision programada

HOY = date(2026, 9, 30)


def test_accion_programada_hoy_ejecutar() -> None:
    assert accion_programada(HOY, date(2026, 9, 30)) is AccionProgramada.EJECUTAR


def test_accion_programada_ayer_omitir() -> None:
    assert accion_programada(HOY, date(2026, 9, 29)) is AccionProgramada.OMITIR


def test_accion_programada_manana_o_sin_fecha_esperar() -> None:
    assert accion_programada(HOY, date(2026, 10, 1)) is AccionProgramada.ESPERAR
    assert accion_programada(HOY, None) is AccionProgramada.ESPERAR


def test_proxima_tras_omitido_seis_meses_despues_de_la_perdida() -> None:
    assert proxima_tras_omitido(date(2026, 9, 27), HOY) == date(2027, 3, 27)


def test_proxima_tras_omitido_suma_hasta_no_quedar_en_el_pasado() -> None:
    assert proxima_tras_omitido(date(2025, 1, 10), HOY) == date(2027, 1, 10)


def test_proxima_tras_omitido_puede_caer_hoy() -> None:
    assert proxima_tras_omitido(date(2026, 3, 30), HOY) == HOY


def test_proxima_tras_omitido_no_arrastra_el_recorte_de_fin_de_mes() -> None:
    # 2025-08-31 + 6 = 2026-02-28, pero + 12 = 2026-08-31 (no 2026-08-28) y + 18 = 2027-02-28.
    assert proxima_tras_omitido(date(2025, 8, 31), HOY) == date(2027, 2, 28)


def test_fechas_perdidas_una_sola_fecha() -> None:
    assert fechas_perdidas(date(2026, 9, 27), HOY) == [date(2026, 9, 27)]


def test_fechas_perdidas_cada_seis_meses_hasta_antes_de_hoy() -> None:
    assert fechas_perdidas(date(2025, 1, 10), HOY) == [
        date(2025, 1, 10),
        date(2025, 7, 10),
        date(2026, 1, 10),
        date(2026, 7, 10),
    ]


def test_fechas_perdidas_hoy_o_futura_no_hay_ninguna() -> None:
    assert fechas_perdidas(HOY, HOY) == []
    assert fechas_perdidas(date(2027, 3, 30), HOY) == []


def test_fechas_perdidas_terminan_justo_antes_de_la_proxima() -> None:
    programada = date(2025, 3, 31)
    perdidas = fechas_perdidas(programada, HOY)
    assert perdidas[-1] < HOY <= proxima_tras_omitido(programada, HOY)
