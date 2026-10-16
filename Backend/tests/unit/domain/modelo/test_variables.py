"""Variables en T-30 (notebook MVP 7.2-7.4). Identidades inventadas, sin datos personales."""

import ast
import sys
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import app.domain.modelo as paquete
from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.historico.ciclos import MotivoCiclo, clasificar
from app.domain.modelo.variables import (
    CONJUNTO_COMPLETO,
    CONJUNTO_MODELO,
    CONJUNTO_SIN_FORMA_PAGO_NI_INICIO,
    DIAS_ANTES_PREDICCION,
    DURACION_ESTANDAR,
    PERIODO_REFERENCIA_FACTORES,
    VARIABLES_CATEGORICAS,
    VARIABLES_CATEGORICAS_MODELO,
    VARIABLES_EXCLUIBLES_M01,
    VARIABLES_NUMERICAS,
    VARIABLES_NUMERICAS_MODELO,
    CicloModelo,
    ConjuntoVariables,
    MedianasMonto,
    PeriodoReferencia,
    calcular_medianas,
    construir_variables,
    ordenar_para_entrenamiento,
)

pytestmark = pytest.mark.unit

SOCIO = "C:1700000001"
OTRO_SOCIO = "C:1700000002"


def ciclo(
    actividad: date,
    vence: date | None,
    *,
    clave: str = SOCIO,
    ref: int = 0,
    plan: Plan = Plan.MENSUAL,
    forma_pago: FormaPago = FormaPago.EFECTIVO,
    duracion: int | None = 30,
    monto: Decimal | None = Decimal("30"),
    aproximado: bool = False,
    excluido: bool = False,
    no_renovo: bool | None = None,
) -> CicloModelo:
    return CicloModelo(
        clave_socio=clave,
        ref=ref,
        plan=plan,
        forma_pago=forma_pago,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        duracion_dias=duracion,
        monto_cobrado=monto,
        inicio_aproximado=aproximado,
        excluido=excluido,
        no_renovo=no_renovo,
    )


MEDIANAS = MedianasMonto(por_plan={Plan.MENSUAL: Decimal("35")}, general=Decimal("40"))


# ---------------------------------------------------------------- parametros


def test_parametros_del_notebook() -> None:
    assert DIAS_ANTES_PREDICCION == 30
    assert VARIABLES_NUMERICAS == (
        "ciclos_previos",
        "antiguedad_dias",
        "duracion_modelo",
        "monto_actual",
        "monto_historico",
        "dias_desde_ultima_membresia",
    )
    assert VARIABLES_CATEGORICAS == ("plan", "forma_pago", "mes_vencimiento", "inicio_aproximado")
    assert {
        Plan.MENSUAL: 30,
        Plan.TRIMESTRAL: 90,
        Plan.SEMESTRAL: 180,
        Plan.ANUAL: 365,
        Plan.OTRO: 30,
    } == DURACION_ESTANDAR


def test_conjunto_modelo_es_la_variante_elegida_por_el_notebook() -> None:
    # R-015 T11: el notebook (12.11, regla (d)) adopta la variante sin forma_pago ni
    # inicio_aproximado; la app entrena exactamente con esas variables y en ese orden.
    assert ConjuntoVariables(VARIABLES_NUMERICAS, VARIABLES_CATEGORICAS) == CONJUNTO_COMPLETO
    assert (
        CONJUNTO_MODELO.numericas,
        CONJUNTO_MODELO.categoricas,
    ) == (VARIABLES_NUMERICAS_MODELO, VARIABLES_CATEGORICAS_MODELO)
    assert CONJUNTO_MODELO == CONJUNTO_SIN_FORMA_PAGO_NI_INICIO
    assert VARIABLES_NUMERICAS_MODELO == (
        "ciclos_previos",
        "antiguedad_dias",
        "duracion_modelo",
        "monto_actual",
        "monto_historico",
        "dias_desde_ultima_membresia",
    )
    assert VARIABLES_CATEGORICAS_MODELO == ("plan", "mes_vencimiento")


def test_conjunto_sin_forma_pago_ni_inicio_quita_solo_esas_dos() -> None:
    assert VARIABLES_EXCLUIBLES_M01 == ("forma_pago", "inicio_aproximado")
    assert CONJUNTO_SIN_FORMA_PAGO_NI_INICIO.numericas == VARIABLES_NUMERICAS
    assert CONJUNTO_SIN_FORMA_PAGO_NI_INICIO.categoricas == ("plan", "mes_vencimiento")


@pytest.mark.parametrize(
    ("numericas", "categoricas"),
    [
        ((), ()),
        (("ciclos_previos", "desconocida"), ("plan",)),
        (("ciclos_previos",), ("plan", "plan")),
        (("plan",), ()),
    ],
)
def test_conjunto_variables_invalido_lanza_error(
    numericas: tuple[str, ...], categoricas: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError, match="variables"):
        ConjuntoVariables(numericas, categoricas)


def test_ciclo_modelo_es_inmutable() -> None:
    c = ciclo(date(2025, 1, 10), date(2025, 2, 9))
    with pytest.raises(FrozenInstanceError):
        c.excluido = True  # type: ignore[misc]  # se prueba la inmutabilidad


# ---------------------------------------------------------------- historial previo


def test_construir_variables_socio_con_dos_previos_resume_historial() -> None:
    previo_1 = ciclo(date(2025, 1, 10), date(2025, 2, 9), ref=1, monto=Decimal("30"))
    previo_2 = ciclo(date(2025, 2, 10), date(2025, 3, 12), ref=2, monto=None)
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=3)

    variables = construir_variables(actual, [previo_1, previo_2, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 2
    assert variables["monto_historico"] == Decimal("30")
    assert variables["dias_desde_ultima_membresia"] == 28
    assert variables["antiguedad_dias"] == (date(2025, 3, 10) - date(2025, 1, 10)).days == 59


def test_construir_variables_socio_nuevo_sin_historial() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 6, 8), duracion=90, plan=Plan.TRIMESTRAL)

    variables = construir_variables(actual, [actual], MEDIANAS)

    assert variables["ciclos_previos"] == 0
    assert variables["monto_historico"] == Decimal("0")
    assert isinstance(variables["monto_historico"], Decimal)
    assert variables["dias_desde_ultima_membresia"] is None
    # max(0, (venc - 30) - actividad): 2025-06-08 - 30 = 2025-05-09
    assert variables["antiguedad_dias"] == (date(2025, 5, 9) - date(2025, 3, 10)).days == 60


def test_construir_variables_antiguedad_nunca_es_negativa() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 3, 25), duracion=None)

    variables = construir_variables(actual, [], MEDIANAS)

    assert variables["antiguedad_dias"] == 0


def test_construir_variables_previo_con_misma_actividad_no_cuenta() -> None:
    mismo_dia = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=1)
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2)

    variables = construir_variables(actual, [mismo_dia, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 0


def test_construir_variables_previo_excluido_no_cuenta() -> None:
    excluido = ciclo(date(2025, 1, 10), None, ref=1, excluido=True)
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2)

    variables = construir_variables(actual, [excluido, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 0
    assert variables["monto_historico"] == Decimal("0")


def test_construir_variables_previo_de_otro_socio_no_cuenta() -> None:
    ajeno = ciclo(date(2025, 1, 10), date(2025, 2, 9), ref=1, clave=OTRO_SOCIO)
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2)

    variables = construir_variables(actual, [ajeno, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 0


def test_construir_variables_el_propio_ciclo_nunca_cuenta() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=7)

    variables = construir_variables(actual, [actual, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 0


def test_construir_variables_previo_pendiente_si_cuenta() -> None:
    # El notebook (7.2) usa como historial evaluables y pendientes: solo filtra los excluidos.
    pendiente = ciclo(date(2025, 1, 10), date(2025, 2, 9), ref=1, no_renovo=None)
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2)

    variables = construir_variables(actual, [pendiente, actual], MEDIANAS)

    assert variables["ciclos_previos"] == 1
    assert variables["monto_historico"] == Decimal("30")


def test_construir_variables_ciclo_posterior_no_cuenta() -> None:
    posterior = ciclo(date(2025, 5, 10), date(2025, 6, 9), ref=1, monto=Decimal("99"))
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2)

    variables = construir_variables(actual, [actual, posterior], MEDIANAS)

    assert variables["ciclos_previos"] == 0
    assert variables["monto_historico"] == Decimal("0")
    assert variables["dias_desde_ultima_membresia"] is None


# ---------------------------------------------------------------- corte T-30 (M01, anti-fuga)


def _historial_base_para_ciclo_corto() -> tuple[CicloModelo, list[CicloModelo]]:
    """Ciclo de 20 dias: T = 2025-04-09, T-30 = 2025-03-10, actividad 2025-03-20.

    El historial mezcla previos con actividad <= T-30 (conocidos en T-30) y registros del
    socio con actividad > T-30 (el previo del 2025-03-15 es anterior al ciclo, pero posterior
    a T-30: con la logica sin corte contaba).
    """
    actual = ciclo(date(2025, 3, 20), date(2025, 4, 9), ref=10, duracion=20)
    conocidos = [
        ciclo(date(2025, 1, 10), date(2025, 2, 9), ref=1, monto=Decimal("30")),
        ciclo(date(2025, 2, 8), date(2025, 3, 10), ref=2, monto=Decimal("32.50")),
        ciclo(date(2025, 1, 5), date(2025, 2, 4), ref=3, clave=OTRO_SOCIO, monto=Decimal("50")),
    ]
    posteriores = [
        ciclo(date(2025, 3, 15), date(2025, 4, 14), ref=4, monto=Decimal("31")),
        ciclo(date(2025, 4, 1), date(2025, 5, 1), ref=5, monto=Decimal("33")),
    ]
    return actual, [*conocidos, *posteriores, actual]


def test_construir_variables_datos_posteriores_a_t30_alterados_no_cambian_variables() -> None:
    actual, historial = _historial_base_para_ciclo_corto()
    t30 = date(2025, 3, 10)
    conocidos = [c for c in historial if c is actual or c.fecha_actividad <= t30]
    base = construir_variables(actual, historial, MEDIANAS)

    alterados = [
        # Se quitan todos los registros con actividad > T-30.
        conocidos,
        # Se alteran montos, planes, formas de pago y fechas (siempre > T-30).
        [
            *conocidos,
            ciclo(
                date(2025, 3, 11),
                date(2025, 6, 9),
                ref=4,
                plan=Plan.TRIMESTRAL,
                forma_pago=FormaPago.TARJETA_DATAFAST,
                duracion=90,
                monto=Decimal("999"),
            ),
            ciclo(date(2025, 3, 19), date(2025, 4, 18), ref=5, monto=None),
        ],
        # Se anaden ciclos nuevos y duplicados del socio posteriores a T-30.
        [
            *historial,
            ciclo(date(2025, 3, 11), date(2025, 4, 10), ref=6, monto=Decimal("1")),
            ciclo(date(2025, 3, 15), date(2025, 4, 14), ref=7, monto=Decimal("31")),
            ciclo(date(2025, 5, 1), date(2025, 6, 1), ref=8, monto=Decimal("2")),
        ],
        # Los registros de otros socios no influyen en ningun caso.
        [*conocidos, ciclo(date(2025, 3, 1), date(2025, 3, 31), ref=9, clave=OTRO_SOCIO)],
    ]
    for variante in alterados:
        assert construir_variables(actual, variante, MEDIANAS) == base

    assert tuple(base) == VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS


def test_construir_variables_previo_en_t30_cuenta_y_en_t29_no() -> None:
    actual = ciclo(date(2025, 3, 20), date(2025, 4, 9), ref=10, duracion=20)
    en_t30 = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=1, monto=Decimal("30"))
    en_t29 = ciclo(date(2025, 3, 11), date(2025, 4, 10), ref=2, monto=Decimal("40"))

    con_t30 = construir_variables(actual, [en_t30, actual], MEDIANAS)
    con_t29 = construir_variables(actual, [en_t29, actual], MEDIANAS)

    assert con_t30["ciclos_previos"] == 1
    assert con_t30["monto_historico"] == Decimal("30")
    assert con_t30["dias_desde_ultima_membresia"] == 10
    assert con_t29["ciclos_previos"] == 0
    assert con_t29["monto_historico"] == Decimal("0")
    assert con_t29["dias_desde_ultima_membresia"] is None


def test_construir_variables_antiguedad_solo_con_previos_hasta_t30() -> None:
    actual = ciclo(date(2025, 3, 20), date(2025, 4, 9), ref=10, duracion=20)
    posterior_a_t30 = ciclo(date(2025, 3, 12), date(2025, 4, 11), ref=1)

    variables = construir_variables(actual, [posterior_a_t30, actual], MEDIANAS)

    # Sin previos conocidos en T-30: primera = actividad del propio ciclo (> T-30) -> 0.
    assert variables["antiguedad_dias"] == 0


def test_construir_variables_sin_vencimiento_lanza_error() -> None:
    with pytest.raises(ValueError, match="vencimiento"):
        construir_variables(ciclo(date(2025, 3, 10), None), [], MEDIANAS)


# ---------------------------------------------------------------- medianas y monto_actual


def test_calcular_medianas_por_plan_y_general_en_decimal() -> None:
    ciclos = [
        ciclo(date(2025, 1, 1), date(2025, 1, 31), ref=i, monto=Decimal(m))
        for i, m in enumerate(["10", "20", "30", "40"])
    ] + [
        ciclo(date(2025, 1, 1), date(2025, 4, 1), ref=9, plan=Plan.TRIMESTRAL, monto=Decimal("90")),
        ciclo(date(2025, 1, 1), date(2025, 4, 1), ref=10, plan=Plan.ANUAL, monto=None),
    ]

    medianas = calcular_medianas(ciclos)

    assert medianas.por_plan[Plan.MENSUAL] == Decimal("25")
    assert isinstance(medianas.por_plan[Plan.MENSUAL], Decimal)
    assert medianas.por_plan[Plan.TRIMESTRAL] == Decimal("90")
    assert Plan.ANUAL not in medianas.por_plan
    assert medianas.general == Decimal("30")


def test_calcular_medianas_ignora_excluidos() -> None:
    ciclos = [
        ciclo(date(2025, 1, 1), date(2025, 1, 31), ref=1, monto=Decimal("10")),
        ciclo(date(2025, 1, 1), None, ref=2, monto=Decimal("1000"), excluido=True),
    ]

    medianas = calcular_medianas(ciclos)

    assert medianas.por_plan == {Plan.MENSUAL: Decimal("10")}
    assert medianas.general == Decimal("10")


def test_calcular_medianas_incluye_pendientes_y_general_es_decimal() -> None:
    ciclos = [
        ciclo(date(2025, 1, 1), date(2025, 1, 31), ref=1, monto=Decimal("10"), no_renovo=True),
        ciclo(date(2025, 1, 1), date(2025, 1, 31), ref=2, monto=Decimal("15"), no_renovo=None),
    ]

    medianas = calcular_medianas(ciclos)

    assert medianas.por_plan == {Plan.MENSUAL: Decimal("12.5")}
    assert medianas.general == Decimal("12.5")
    assert isinstance(medianas.general, Decimal)


def test_calcular_medianas_sin_montos_general_es_none() -> None:
    medianas = calcular_medianas([ciclo(date(2025, 1, 1), date(2025, 1, 31), monto=None)])

    assert medianas.por_plan == {}
    assert medianas.general is None


def test_calcular_medianas_solo_de_entrenamiento_no_cambia_con_montos_ajenos() -> None:
    # M01 (b): las medianas salen solo de los ciclos de entrenamiento que se le pasan; los
    # montos de validacion/prediccion (aunque esten en el historial) no las mueven.
    entrenamiento = [
        ciclo(date(2025, 1, 1), date(2025, 1, 31), ref=1, monto=Decimal("20")),
        ciclo(date(2025, 2, 1), date(2025, 3, 3), ref=2, monto=Decimal("40")),
    ]
    otros = [ciclo(date(2026, 1, 1), date(2026, 1, 31), ref=3, monto=Decimal("1000"))]
    otros_alterados = [ciclo(date(2026, 1, 1), date(2026, 1, 31), ref=3, monto=Decimal("1"))]
    medianas = calcular_medianas(entrenamiento)
    a_predecir = ciclo(date(2026, 2, 1), date(2026, 3, 3), ref=4, monto=None)

    con_otros = construir_variables(a_predecir, [*entrenamiento, *otros, a_predecir], medianas)
    con_alterados = construir_variables(
        a_predecir, [*entrenamiento, *otros_alterados, a_predecir], medianas
    )

    assert medianas.por_plan == {Plan.MENSUAL: Decimal("30")}
    assert medianas.general == Decimal("30")
    assert con_otros["monto_actual"] == con_alterados["monto_actual"] == Decimal("30")
    assert medianas == calcular_medianas(entrenamiento)


def test_monto_actual_usa_el_monto_si_existe() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), monto=Decimal("27.50"))

    assert construir_variables(actual, [], MEDIANAS)["monto_actual"] == Decimal("27.50")


def test_monto_actual_none_usa_la_mediana_del_plan() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), monto=None)

    assert construir_variables(actual, [], MEDIANAS)["monto_actual"] == Decimal("35")


def test_monto_actual_plan_sin_mediana_usa_la_general() -> None:
    actual = ciclo(date(2025, 3, 10), date(2026, 3, 10), plan=Plan.ANUAL, duracion=365, monto=None)

    assert construir_variables(actual, [], MEDIANAS)["monto_actual"] == Decimal("40")


# ---------------------------------------------------------------- duracion y categoricas


@pytest.mark.parametrize(
    ("plan", "esperado"),
    [(Plan.TRIMESTRAL, 90), (Plan.OTRO, 30), (Plan.MENSUAL, 30), (Plan.ANUAL, 365)],
)
def test_duracion_modelo_none_usa_duracion_estandar(plan: Plan, esperado: int) -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), plan=plan, duracion=None)

    assert construir_variables(actual, [], MEDIANAS)["duracion_modelo"] == esperado


def test_duracion_modelo_none_con_diario_queda_none() -> None:
    # El mapa del notebook no tiene DIARIO: .map() da NaN y el imputador del pipeline lo rellena.
    actual = ciclo(date(2025, 3, 10), date(2025, 3, 11), plan=Plan.DIARIO, duracion=None)

    assert construir_variables(actual, [], MEDIANAS)["duracion_modelo"] is None


def test_duracion_modelo_usa_la_duracion_si_existe() -> None:
    actual = ciclo(date(2025, 3, 10), date(2025, 6, 9), plan=Plan.TRIMESTRAL, duracion=91)

    assert construir_variables(actual, [], MEDIANAS)["duracion_modelo"] == 91


def test_variables_categoricas_como_texto() -> None:
    actual = ciclo(
        date(2026, 8, 6),
        date(2026, 9, 5),
        plan=Plan.TRIMESTRAL,
        forma_pago=FormaPago.TARJETA_DATAFAST,
        aproximado=True,
    )

    variables = construir_variables(actual, [], MEDIANAS)

    assert variables["mes_vencimiento"] == "2026-09"
    assert variables["inicio_aproximado"] == "True"
    assert variables["plan"] == "TRIMESTRAL"
    assert variables["forma_pago"] == "TARJETA_DATAFAST"
    assert type(variables["plan"]) is str
    assert type(variables["forma_pago"]) is str


def test_inicio_aproximado_falso_como_texto() -> None:
    actual = ciclo(date(2026, 1, 6), date(2026, 2, 5))

    assert construir_variables(actual, [], MEDIANAS)["inicio_aproximado"] == "False"


def test_construir_variables_devuelve_todas_las_variables_y_ningun_float() -> None:
    previo = ciclo(date(2025, 1, 10), date(2025, 2, 9), ref=1, monto=Decimal("30.25"))
    actual = ciclo(date(2025, 3, 10), date(2025, 4, 9), ref=2, monto=None)

    variables = construir_variables(actual, [previo, actual], MEDIANAS)

    assert tuple(variables) == VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS
    assert not any(isinstance(valor, float) for valor in variables.values())


# ---------------------------------------------------------------- orden de entrenamiento


def test_ordenar_para_entrenamiento_por_socio_actividad_y_vencimiento() -> None:
    a = ciclo(date(2025, 3, 1), date(2025, 3, 31), clave="B", ref=1)
    b = ciclo(date(2025, 1, 1), date(2025, 1, 31), clave="B", ref=2)
    c = ciclo(date(2025, 2, 1), date(2025, 3, 3), clave="A", ref=3)
    d = ciclo(date(2025, 2, 1), date(2025, 3, 2), clave="A", ref=4)

    ordenados = ordenar_para_entrenamiento([a, b, c, d])

    assert [x.ref for x in ordenados] == [4, 3, 2, 1]


def test_ordenar_para_entrenamiento_es_estable() -> None:
    primero = ciclo(date(2025, 2, 1), date(2025, 3, 3), ref=1)
    segundo = ciclo(date(2025, 2, 1), date(2025, 3, 3), ref=2)
    tercero = ciclo(date(2025, 2, 1), date(2025, 3, 3), ref=3)

    assert [x.ref for x in ordenar_para_entrenamiento([segundo, primero, tercero])] == [2, 1, 3]


# ---------------------------------------------------------------- clasificar acepta CicloModelo


def test_clasificar_acepta_ciclo_modelo() -> None:
    corte = date(2026, 8, 31)
    evaluable = ciclo(date(2026, 6, 15), date(2026, 7, 15))
    diario = ciclo(date(2026, 7, 1), date(2026, 7, 2), plan=Plan.DIARIO, duracion=1)

    assert clasificar(evaluable, corte) == (EstadoCiclo.EVALUABLE, MotivoCiclo.EVALUABLE)
    assert clasificar(diario, corte) == (EstadoCiclo.EXCLUIDO, MotivoCiclo.PASE_DIARIO)


# ---------------------------------------------------------------- dependencias


def test_dominio_del_modelo_solo_usa_libreria_estandar() -> None:
    directorio = Path(paquete.__file__).parent
    for ruta in directorio.glob("*.py"):
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                modulos = [nodo.module]
            else:
                continue
            for modulo in modulos:
                assert modulo.split(".")[0] in sys.stdlib_module_names or modulo.startswith(
                    "app.domain"
                ), f"{ruta.name} importa {modulo}"


# ---------------------------------------------------------------- periodo de referencia de factores


def test_periodo_referencia_por_defecto_es_x_train_con_margen_de_30_dias() -> None:
    # M01 (g): X_train del notebook = particion de entrenamiento = vencimiento < 2025-12-02
    # (2026-01-01 - 30 d), sin limite inferior (asignar_particion de la seccion 7.3).
    assert PeriodoReferencia(date.min, date(2025, 12, 2)) == PERIODO_REFERENCIA_FACTORES
    assert PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2024, 12, 2), date(2025, 1, 1)))
    assert PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2025, 11, 1), date(2025, 12, 1)))
    assert not PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2025, 11, 2), date(2025, 12, 2)))
    assert not PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2025, 12, 1), date(2025, 12, 31)))
    assert PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2024, 12, 1), date(2024, 12, 31)))
    assert not PERIODO_REFERENCIA_FACTORES.contiene(ciclo(date(2025, 3, 1), None))


def test_periodo_referencia_es_parametrizable() -> None:
    periodo = PeriodoReferencia(date(2026, 1, 1), date(2027, 1, 1))

    assert periodo.contiene(ciclo(date(2026, 1, 1), date(2026, 1, 31)))
    assert not periodo.contiene(ciclo(date(2025, 12, 1), date(2025, 12, 31)))


def test_periodo_referencia_invertido_lanza_error() -> None:
    with pytest.raises(ValueError, match="periodo"):
        PeriodoReferencia(date(2026, 1, 1), date(2026, 1, 1))
