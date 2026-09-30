"""Reglas de una campana: validacion, normalizacion, compatibilidad y orden (R-009 T1).

Decisiones (e) y (f) del plan. Solo libreria estandar; sin base de datos.
"""

import pytest

from app.domain.campanias.campania import (
    CampaniaInvalidaError,
    DatosCampania,
    clave_orden,
    es_compatible,
)
from app.domain.common.enums import NivelRiesgo, Plan
from app.domain.common.exceptions import DomainError

pytestmark = pytest.mark.unit

ALTO, MEDIO, BAJO = NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO


def _crear(**cambios: object) -> DatosCampania:
    valores: dict[str, object] = {
        "nombre": "Renovacion",
        "descripcion": None,
        "niveles": [ALTO],
        "planes": [Plan.MENSUAL],
        "prioridad": 1,
        **cambios,
    }
    return DatosCampania.crear(**valores)  # type: ignore[arg-type]  # valores de prueba


def test_crear_recorta_y_normaliza_en_orden_canonico() -> None:
    datos = DatosCampania.crear(
        nombre="  Renovación  ",
        descripcion="  ",
        niveles=[MEDIO, ALTO, MEDIO],
        planes=[Plan.TRIMESTRAL, Plan.MENSUAL],
        prioridad=1,
    )

    assert datos.nombre == "Renovación"
    assert datos.descripcion is None
    assert datos.niveles_riesgo == (ALTO, MEDIO)
    assert datos.planes == (Plan.MENSUAL, Plan.TRIMESTRAL)
    assert datos.prioridad == 1


def test_crear_descripcion_se_recorta() -> None:
    assert _crear(descripcion="  Llamar al socio.  ").descripcion == "Llamar al socio."


def test_crear_todos_los_planes_de_campania_en_orden_canonico() -> None:
    datos = _crear(
        niveles=[BAJO, MEDIO, ALTO],
        planes=[Plan.OTRO, Plan.ANUAL, Plan.SEMESTRAL, Plan.TRIMESTRAL, Plan.MENSUAL],
    )

    assert datos.niveles_riesgo == (ALTO, MEDIO, BAJO)
    assert datos.planes == (Plan.MENSUAL, Plan.TRIMESTRAL, Plan.SEMESTRAL, Plan.ANUAL, Plan.OTRO)


@pytest.mark.parametrize(
    "cambios",
    [
        {"nombre": "   "},
        {"nombre": ""},
        {"nombre": "x" * 121},
        {"descripcion": "x" * 501},
        {"niveles": []},
        {"planes": []},
        {"planes": [Plan.DIARIO]},
        {"planes": [Plan.MENSUAL, Plan.DIARIO]},
        {"prioridad": 0},
        {"prioridad": 1000},
    ],
    ids=[
        "nombre-espacios",
        "nombre-vacio",
        "nombre-121",
        "descripcion-501",
        "sin-niveles",
        "sin-planes",
        "plan-diario",
        "plan-diario-mezclado",
        "prioridad-0",
        "prioridad-1000",
    ],
)
def test_crear_datos_invalidos_lanza_campania_invalida(cambios: dict[str, object]) -> None:
    with pytest.raises(CampaniaInvalidaError) as excinfo:
        _crear(**cambios)

    assert isinstance(excinfo.value, DomainError)
    assert str(excinfo.value)


def test_crear_mensaje_de_error_no_repite_el_nombre_recibido() -> None:
    nombre = "Maria Fernanda Lopez " * 10

    with pytest.raises(CampaniaInvalidaError) as excinfo:
        _crear(nombre=nombre)

    assert "Maria" not in str(excinfo.value)


@pytest.mark.parametrize(
    "cambios",
    [
        {"nombre": "x" * 120},
        {"nombre": "  " + "x" * 120 + "  "},
        {"descripcion": "x" * 500},
        {"prioridad": 999},
    ],
    ids=["nombre-120", "nombre-120-con-espacios", "descripcion-500", "prioridad-999"],
)
def test_crear_limites_validos_se_aceptan(cambios: dict[str, object]) -> None:
    _crear(**cambios)


def test_datos_campania_es_inmutable() -> None:
    datos = _crear()

    with pytest.raises(AttributeError):
        datos.nombre = "otro"  # type: ignore[misc]  # se comprueba que es frozen


@pytest.mark.parametrize(
    ("activa", "niveles", "planes", "nivel", "plan", "esperado"),
    [
        (True, (BAJO,), (Plan.MENSUAL,), ALTO, Plan.MENSUAL, False),
        (True, (ALTO,), (Plan.MENSUAL,), ALTO, Plan.ANUAL, False),
        (False, (ALTO, MEDIO), (Plan.MENSUAL,), ALTO, Plan.MENSUAL, False),
        (True, (ALTO, MEDIO), (Plan.MENSUAL,), ALTO, Plan.MENSUAL, True),
        (True, (ALTO,), (Plan.MENSUAL, Plan.OTRO), ALTO, Plan.DIARIO, False),
    ],
    ids=["nivel-no-aplica", "plan-no-aplica", "inactiva", "compatible", "plan-diario"],
)
def test_es_compatible(
    activa: bool,
    niveles: tuple[NivelRiesgo, ...],
    planes: tuple[Plan, ...],
    nivel: NivelRiesgo,
    plan: Plan,
    esperado: bool,
) -> None:
    assert es_compatible(activa, niveles, planes, nivel, plan) is esperado


def test_clave_orden_prioridad_nombre_sin_mayusculas_e_id() -> None:
    campanias = [(1, 2, "b"), (2, 1, "Zeta"), (3, 1, "alfa")]

    ordenadas = sorted(campanias, key=lambda c: clave_orden(c[1], c[2], c[0]))

    assert [c[2] for c in ordenadas] == ["alfa", "Zeta", "b"]


def test_clave_orden_empate_final_por_id() -> None:
    campanias = [(9, 1, "Igual"), (4, 1, "igual")]

    ordenadas = sorted(campanias, key=lambda c: clave_orden(c[1], c[2], c[0]))

    assert [c[0] for c in ordenadas] == [4, 9]
