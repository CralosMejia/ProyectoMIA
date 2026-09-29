from enum import StrEnum

import pytest

from app.domain.common.enums import (
    PLANES_CAMPANIA,
    RESPUESTAS_ACEPTACION,
    RESPUESTAS_OFRECIMIENTO,
    RESPUESTAS_RENOVACION,
    DisparadorReentrenamiento,
    EstadoCiclo,
    EstadoGestion,
    EstadoMigracion,
    EstadoRegistro,
    FormaPago,
    NivelRiesgo,
    OrigenMembresia,
    Plan,
    Respuesta,
    ResultadoReentrenamiento,
    TipoCarga,
)

pytestmark = pytest.mark.unit


def _values(enum_cls: type[StrEnum]) -> set[str]:
    return {member.value for member in enum_cls}


def test_plan_values_match_catalog_exactly() -> None:
    assert _values(Plan) == {"MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL", "DIARIO", "OTRO"}


def test_forma_pago_values_match_catalog_exactly() -> None:
    assert _values(FormaPago) == {
        "EFECTIVO",
        "TRANSFERENCIA",
        "TARJETA_DATAFAST",
        "OTRO",
        "SIN_DATO",
    }


def test_estado_ciclo_values_match_catalog_exactly() -> None:
    assert _values(EstadoCiclo) == {"EVALUABLE", "PENDIENTE", "EXCLUIDO"}


def test_nivel_riesgo_values_match_catalog_exactly() -> None:
    assert _values(NivelRiesgo) == {"ALTO", "MEDIO", "BAJO"}


def test_estado_gestion_values_match_catalog_exactly() -> None:
    assert _values(EstadoGestion) == {"PENDIENTE", "CERRADA"}


def test_origen_membresia_values_match_catalog_exactly() -> None:
    assert _values(OrigenMembresia) == {"HISTORICO", "PLANTILLA"}


def test_estado_registro_values_match_catalog_exactly() -> None:
    assert _values(EstadoRegistro) == {
        "NUEVO",
        "RENOVACION",
        "CONGELAMIENTO",
        "REINGRESO",
        "BAJA",
    }


def test_tipo_carga_values_match_catalog_exactly() -> None:
    assert _values(TipoCarga) == {"MIGRACION_HISTORICA", "PLANTILLA"}


def test_estado_migracion_values_match_catalog_exactly() -> None:
    assert _values(EstadoMigracion) == {"PENDIENTE", "EN_CURSO", "COMPLETADA"}


def test_disparador_reentrenamiento_values_match_catalog_exactly() -> None:
    assert _values(DisparadorReentrenamiento) == {"PROGRAMADO", "MANUAL", "INICIAL"}


def test_resultado_reentrenamiento_values_match_catalog_exactly() -> None:
    assert _values(ResultadoReentrenamiento) == {
        "ENTRENADO",
        "CRITERIOS_NO_CUMPLIDOS",
        "NO_SUPERA_VIGENTE",
        "OMITIDO",
        "FALLIDO",
    }


def test_respuesta_values_match_catalog_exactly() -> None:
    assert _values(Respuesta) == {"SI", "NO", "PENDIENTE", "NO_APLICA"}


@pytest.mark.parametrize(
    "enum_cls",
    [
        Plan,
        FormaPago,
        EstadoCiclo,
        NivelRiesgo,
        EstadoGestion,
        OrigenMembresia,
        EstadoRegistro,
        TipoCarga,
        EstadoMigracion,
        DisparadorReentrenamiento,
        ResultadoReentrenamiento,
        Respuesta,
    ],
)
def test_enum_is_str_enum_with_value_equal_to_name(enum_cls: type[StrEnum]) -> None:
    assert issubclass(enum_cls, StrEnum)
    for member in enum_cls:
        assert member.value == member.name


def test_plan_from_exact_value_returns_same_member() -> None:
    assert Plan("MENSUAL") is Plan.MENSUAL


def test_plan_from_lowercase_value_raises_value_error() -> None:
    with pytest.raises(ValueError, match="mensual"):
        Plan("mensual")


def test_planes_campania_is_plan_without_diario() -> None:
    assert frozenset(Plan) - {Plan.DIARIO} == PLANES_CAMPANIA
    assert Plan.DIARIO not in PLANES_CAMPANIA


def test_respuestas_ofrecimiento_subset() -> None:
    assert frozenset({Respuesta.SI, Respuesta.NO, Respuesta.NO_APLICA}) == RESPUESTAS_OFRECIMIENTO


def test_respuestas_aceptacion_subset() -> None:
    assert (
        frozenset({Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE, Respuesta.NO_APLICA})
        == RESPUESTAS_ACEPTACION
    )


def test_respuestas_renovacion_subset() -> None:
    assert frozenset({Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE}) == RESPUESTAS_RENOVACION


def test_subset_constants_are_immutable() -> None:
    for subset in (
        PLANES_CAMPANIA,
        RESPUESTAS_OFRECIMIENTO,
        RESPUESTAS_ACEPTACION,
        RESPUESTAS_RENOVACION,
    ):
        assert isinstance(subset, frozenset)
