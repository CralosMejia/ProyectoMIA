"""Caso de uso GenerarLista (CU-04, CU-05) con dobles en memoria.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00).
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO
from app.application.listas.generar_lista import (
    MENSAJE_FECHA_PASADA,
    FechaReferenciaPasadaError,
    GenerarLista,
    SistemaNoListoError,
    medianas_de,
)
from app.domain.common.enums import EstadoMigracion, NivelRiesgo, Plan
from tests.unit.application.listas.dobles import (
    Almacen,
    PredictorPorMonto,
    RelojFijo,
    membresia,
    modelo,
    unidad_de_trabajo,
)

pytestmark = pytest.mark.unit

FECHA = date(2026, 8, 31)


def escenario() -> Almacen:
    """Seis socios sinteticos alrededor de la fecha 2026-08-31 con horizonte 30."""
    return Almacen(
        membresias=[
            # socio 1: ciclo anterior (historial) + ciclo en cartera con score 0.80
            membresia(9, 1, date(2026, 7, 10), date(2026, 8, 10), monto=Decimal("35")),
            membresia(1, 1, date(2026, 8, 10), date(2026, 9, 10), monto=Decimal("80")),
            # socio 2: vence en el horizonte pero ya renovo (actividad posterior)
            membresia(2, 2, date(2026, 8, 15), date(2026, 9, 15), monto=Decimal("99")),
            membresia(
                3, 2, date(2026, 8, 25), date(2026, 11, 25), plan=Plan.TRIMESTRAL, monto=None
            ),
            # socio 3: pase diario en el horizonte
            membresia(4, 3, date(2026, 9, 4), date(2026, 9, 5), plan=Plan.DIARIO),
            # socio 4: dos ciclos en cartera con la misma actividad -> una sola fila (0.50)
            membresia(5, 4, date(2026, 8, 20), date(2026, 9, 20), monto=Decimal("50")),
            membresia(6, 4, date(2026, 8, 20), date(2026, 9, 19), monto=Decimal("30")),
            # socio 5: score 0.70
            membresia(7, 5, date(2026, 8, 25), date(2026, 9, 25), monto=Decimal("70")),
            # socio 6: sin monto -> mediana del plan MENSUAL (45) -> 0.45
            membresia(8, 6, date(2026, 8, 28), date(2026, 9, 28), monto=None),
        ],
        modelos=[modelo(11, 1)],
        cargas=[datetime(2026, 8, 30, 15, 0, tzinfo=UTC)],
    )


def generar(
    almacen: Almacen,
    predictor: PredictorPorMonto | None = None,
    dto: GenerarListaDTO | None = None,
) -> tuple[ListaPriorizadaDTO, PredictorPorMonto]:
    predictor = predictor or PredictorPorMonto()
    caso = GenerarLista(unidad_de_trabajo(almacen), predictor, almacen.reloj)
    resultado = caso.ejecutar(dto or GenerarListaDTO(fecha_referencia=FECHA, top_k=2))
    return resultado, predictor


def test_ejecutar_excludes_renewed_and_daily_one_row_per_socio_sorted_by_score() -> None:
    lista, _ = generar(escenario())

    assert [i.score for i in lista.items] == [
        Decimal("0.8"),
        Decimal("0.7"),
        Decimal("0.5"),
        Decimal("0.45"),
    ]
    assert [i.prioridad for i in lista.items] == [1, 2, 3, 4]
    nombres = [i.socio_nombre for i in lista.items]
    assert nombres == [f"Socio Sintetico {s}" for s in (1, 5, 4, 6)]
    assert all(i.plan is not Plan.DIARIO for i in lista.items)


def test_ejecutar_marks_exactly_min_k_n_rows_inside_top_k() -> None:
    con_dos, _ = generar(escenario())
    con_diez, _ = generar(escenario(), dto=GenerarListaDTO(fecha_referencia=FECHA, top_k=10))

    assert [i.dentro_top_k for i in con_dos.items] == [True, True, False, False]
    assert all(i.dentro_top_k for i in con_diez.items)


def test_ejecutar_assigns_levels_with_model_thresholds_and_keeps_model_data() -> None:
    lista, predictor = generar(escenario())

    assert [i.nivel_riesgo for i in lista.items] == [
        NivelRiesgo.ALTO,
        NivelRiesgo.ALTO,
        NivelRiesgo.MEDIO,
        NivelRiesgo.BAJO,
    ]
    assert lista.modelo_version == "v1"
    assert lista.umbral_alto == Decimal("0.70000000")
    assert lista.umbral_medio == Decimal("0.50000000")
    assert predictor.llamadas[0][0] == b"artefacto-v1"


def test_ejecutar_builds_variables_with_history_and_model_medians() -> None:
    _, predictor = generar(escenario())

    filas = predictor.llamadas[0][1]
    assert len(filas) == 5  # socios 1, 4 (dos ciclos), 5 y 6
    por_monto = {f["monto_actual"]: f for f in filas}
    assert por_monto[Decimal("80")]["ciclos_previos"] == 1
    assert por_monto[Decimal("80")]["monto_historico"] == Decimal("35")
    assert Decimal("45") in por_monto  # mediana del plan para el socio sin monto


def test_ejecutar_saves_dias_para_vencer_monto_y_factores() -> None:
    lista, _ = generar(escenario())

    primero = lista.items[0]
    assert primero.dias_para_vencer == 10
    assert primero.monto_cobrado == Decimal("80")
    assert primero.fecha_vencimiento == date(2026, 9, 10)
    assert primero.factores_principales == ["Plan: MENSUAL (+0,10)"]
    assert lista.items[-1].factores_principales == []
    assert lista.items[-1].monto_cobrado is None


def test_ejecutar_persists_list_and_predictions_in_one_unit_of_work() -> None:
    almacen = escenario()

    lista, _ = generar(almacen)

    assert almacen.commits == 1
    nueva, predicciones, _ = almacen.listas[lista.id]
    assert nueva.modelo_id == 11
    assert nueva.fecha_generacion == FECHA
    assert (nueva.horizonte_dias, nueva.top_k) == (30, 2)
    assert len(predicciones) == 4
    assert {p.socio_id for p in predicciones} == {1, 4, 5, 6}


def test_ejecutar_without_date_uses_clock_today() -> None:
    almacen = escenario()
    almacen.reloj = RelojFijo(datetime(2026, 8, 31, 23, 0, tzinfo=UTC))

    lista, _ = generar(almacen, dto=GenerarListaDTO(top_k=2))

    assert lista.fecha_generacion == FECHA
    assert len(lista.items) == 4


def test_ejecutar_predictor_failure_does_not_commit() -> None:
    almacen = escenario()

    with pytest.raises(RuntimeError):
        generar(almacen, predictor=PredictorPorMonto(error=RuntimeError("fallo")))

    assert almacen.commits == 0


@pytest.mark.parametrize("estado", [EstadoMigracion.PENDIENTE, EstadoMigracion.EN_CURSO])
def test_ejecutar_migration_not_completed_raises_sistema_no_listo(
    estado: EstadoMigracion,
) -> None:
    almacen = escenario()
    almacen.estado = estado

    with pytest.raises(SistemaNoListoError):
        generar(almacen)
    assert almacen.listas == {}


def test_ejecutar_without_current_model_raises_sistema_no_listo() -> None:
    almacen = escenario()
    almacen.modelos = []

    with pytest.raises(SistemaNoListoError):
        generar(almacen)


def test_ejecutar_empty_portfolio_returns_valid_empty_list_without_predicting() -> None:
    almacen = escenario()
    predictor = PredictorPorMonto()

    lista, _ = generar(
        almacen, predictor, GenerarListaDTO(fecha_referencia=date(2027, 6, 1), top_k=2)
    )

    assert lista.items == []
    assert predictor.llamadas == []
    assert almacen.commits == 1


def test_ejecutar_old_data_warning_61_days_is_true() -> None:
    almacen = escenario()
    almacen.cargas = [datetime(2026, 7, 1, 10, 0, tzinfo=UTC)]

    lista, _ = generar(almacen)

    assert lista.advertencia_datos_antiguos is True


def test_ejecutar_old_data_warning_exactly_30_days_is_false() -> None:
    almacen = escenario()
    almacen.cargas = [datetime(2026, 8, 1, 10, 0, tzinfo=UTC)]

    lista, _ = generar(almacen)

    assert lista.advertencia_datos_antiguos is False


def test_medianas_de_reads_decimal_text_from_metadata() -> None:
    medianas = medianas_de({"medianas_monto": {"por_plan": {"MENSUAL": "45.5"}, "general": "50"}})

    assert medianas.por_plan == {Plan.MENSUAL: Decimal("45.5")}
    assert medianas.general == Decimal("50")


def test_medianas_de_accepts_json_text_and_null_general() -> None:
    medianas = medianas_de({"medianas_monto": '{"por_plan": {}, "general": null}'})

    assert medianas.por_plan == {}
    assert medianas.general is None


def test_medianas_de_without_key_raises() -> None:
    with pytest.raises(ValueError, match="medianas"):
        medianas_de({})


# ------------------------------------------------ R-005: fecha >= hoy, horizonte y cedula

HOY = date(2026, 9, 29)
RELOJ_HOY = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)


def escenario_cedulas(*, sin_cedula: tuple[int, ...] = (2, 4)) -> Almacen:
    """Cinco socios que vencen en los proximos 30 dias desde 2026-09-29.

    Scores (monto / 100): socio 1 -> 0.80, 2 -> 0.75, 3 -> 0.60, 4 -> 0.55, 5 -> 0.40.
    El socio 1 tiene ademas un ciclo anterior (historial) con monto 35.
    """
    montos = {1: "80", 2: "75", 3: "60", 4: "55", 5: "40"}
    membresias = [
        membresia(
            20,
            1,
            date(2026, 7, 20),
            date(2026, 8, 20),
            monto=Decimal("35"),
        ),
    ]
    for socio, monto in montos.items():
        membresias.append(
            membresia(
                socio,
                socio,
                date(2026, 9, socio),
                date(2026, 10, socio),
                monto=Decimal(monto),
                con_cedula=socio not in sin_cedula,
            )
        )
    return Almacen(
        membresias=membresias,
        modelos=[modelo(11, 1)],
        cargas=[datetime(2026, 9, 28, 15, 0, tzinfo=UTC)],
        reloj=RelojFijo(RELOJ_HOY),
    )


def test_ejecutar_past_date_raises_without_saving_or_predicting() -> None:
    almacen = escenario_cedulas()
    predictor = PredictorPorMonto()

    with pytest.raises(FechaReferenciaPasadaError) as error:
        generar(almacen, predictor, GenerarListaDTO(fecha_referencia=date(2026, 9, 28)))

    assert str(error.value) == MENSAJE_FECHA_PASADA
    assert almacen.listas == {}
    assert almacen.commits == 0
    assert predictor.llamadas == []


@pytest.mark.parametrize("fecha", [date(2026, 9, 29), date(2026, 10, 15)])
def test_ejecutar_today_or_future_date_saves_the_list(fecha: date) -> None:
    almacen = escenario_cedulas()

    lista, _ = generar(almacen, dto=GenerarListaDTO(fecha_referencia=fecha))

    assert lista.fecha_generacion == fecha
    assert almacen.commits == 1


@pytest.mark.parametrize(
    "instante",
    [RELOJ_HOY, datetime(2026, 9, 30, 2, 0, tzinfo=UTC)],
)
def test_ejecutar_without_date_uses_business_today_in_ecuador(instante: datetime) -> None:
    almacen = escenario_cedulas()
    almacen.reloj = RelojFijo(instante)

    lista, _ = generar(almacen, dto=GenerarListaDTO())

    assert lista.fecha_generacion == HOY


def test_generar_lista_dto_horizon_accepts_31() -> None:
    assert GenerarListaDTO(horizonte_dias=31).horizonte_dias == 31


@pytest.mark.parametrize("horizonte", [0, 32])
def test_generar_lista_dto_horizon_out_of_range_raises(horizonte: int) -> None:
    with pytest.raises(ValidationError):
        GenerarListaDTO(horizonte_dias=horizonte)


def test_ejecutar_excludes_socios_without_cedula_before_predicting_and_top_k() -> None:
    almacen = escenario_cedulas()

    lista, predictor = generar(almacen, dto=GenerarListaDTO(fecha_referencia=HOY, top_k=2))

    nombres = [i.socio_nombre for i in lista.items]
    assert nombres == [f"Socio Sintetico {s}" for s in (1, 3, 5)]
    assert [i.prioridad for i in lista.items] == [1, 2, 3]
    assert [i.score for i in lista.items] == [Decimal("0.8"), Decimal("0.6"), Decimal("0.4")]
    assert [i.dentro_top_k for i in lista.items] == [True, True, False]
    assert all(i.cedula is not None for i in lista.items)
    filas = predictor.llamadas[0][1]
    assert len(filas) == 3
    socio_1 = next(f for f in filas if f["monto_actual"] == Decimal("80"))
    assert socio_1["ciclos_previos"] == 1
    assert socio_1["monto_historico"] == Decimal("35")


def test_ejecutar_all_without_cedula_returns_valid_empty_list() -> None:
    almacen = escenario_cedulas(sin_cedula=(1, 2, 3, 4, 5))
    predictor = PredictorPorMonto()

    lista, _ = generar(almacen, predictor, GenerarListaDTO(fecha_referencia=HOY, top_k=2))

    assert lista.items == []
    assert predictor.llamadas == []
    assert almacen.commits == 1


def test_ejecutar_past_date_does_not_read_memberships() -> None:
    almacen = escenario_cedulas()

    with pytest.raises(FechaReferenciaPasadaError):
        generar(almacen, dto=GenerarListaDTO(fecha_referencia=date(2026, 9, 28)))

    assert almacen.lecturas_membresias == 0


def test_ejecutar_past_date_by_business_today_near_midnight_utc_raises() -> None:
    # 2026-09-30T02:00Z es aun 2026-09-29 en Ecuador: 09-29 vale, 09-28 no.
    almacen = escenario_cedulas()
    almacen.reloj = RelojFijo(datetime(2026, 9, 30, 2, 0, tzinfo=UTC))

    lista, _ = generar(almacen, dto=GenerarListaDTO(fecha_referencia=HOY))
    with pytest.raises(FechaReferenciaPasadaError):
        generar(almacen, dto=GenerarListaDTO(fecha_referencia=date(2026, 9, 28)))

    assert lista.fecha_generacion == HOY


def test_ejecutar_socio_without_cedula_is_not_saved_in_predictions() -> None:
    almacen = escenario_cedulas()

    lista, _ = generar(almacen, dto=GenerarListaDTO(fecha_referencia=HOY, top_k=2))

    _, predicciones, _ = almacen.listas[lista.id]
    assert {p.socio_id for p in predicciones} == {1, 3, 5}
    assert sum(p.dentro_top_k for p in predicciones) == 2


def test_ejecutar_never_logs_cedulas_or_names(caplog: pytest.LogCaptureFixture) -> None:
    almacen = escenario_cedulas()
    caplog.set_level(logging.DEBUG)

    lista, _ = generar(almacen, dto=GenerarListaDTO(fecha_referencia=HOY, top_k=2))
    with pytest.raises(FechaReferenciaPasadaError) as error:
        generar(almacen, dto=GenerarListaDTO(fecha_referencia=date(2026, 9, 1)))

    sensibles = [i.socio_nombre for i in lista.items] + [i.cedula for i in lista.items]
    textos = [r.getMessage() for r in caplog.records] + [str(error.value)]
    assert not any(s and s in t for s in sensibles for t in textos)
    assert "Socio Sintetico" not in str(error.value)
