"""Reglas de una gestion de retencion (R-009 T2, decisiones (g) y (h))."""

from datetime import date

import pytest

from app.domain.common.enums import EstadoGestion, Respuesta
from app.domain.common.exceptions import DomainError
from app.domain.gestiones.errores import (
    CampaniaNoAplicableError,
    FechaSeguimientoFueraDeRangoError,
    GestionCerradaError,
    GestionDuplicadaError,
    PlazoSeguimientoTerminadoError,
    ResultadoIncoherenteError,
)
from app.domain.gestiones.reglas import (
    estado_tras_resultado,
    fecha_sugerida,
    rango_seguimiento,
    validar_fecha_seguimiento,
    validar_resultado,
)

pytestmark = pytest.mark.unit

HOY = date(2026, 9, 29)
VENCE = date(2026, 10, 5)
ASIGNADA = date(2026, 9, 20)

SI = Respuesta.SI
NO = Respuesta.NO
PEND = Respuesta.PENDIENTE
NA = Respuesta.NO_APLICA


# --- rango y fecha sugerida (g) ---------------------------------------------------------


def test_rango_seguimiento_vencimiento_futuro_va_de_hoy_a_vencimiento_mas_30() -> None:
    assert rango_seguimiento(HOY, VENCE) == (date(2026, 9, 29), date(2026, 11, 4))


def test_fecha_sugerida_vencimiento_futuro_es_vencimiento_mas_25() -> None:
    assert fecha_sugerida(HOY, VENCE) == date(2026, 10, 30)


def test_rango_seguimiento_vencimiento_pasado_termina_en_vencimiento_mas_30() -> None:
    assert rango_seguimiento(HOY, date(2026, 9, 1)) == (date(2026, 9, 29), date(2026, 10, 1))


def test_fecha_sugerida_vencimiento_mas_25_pasado_es_hoy() -> None:
    assert fecha_sugerida(HOY, date(2026, 9, 1)) == HOY


def test_rango_seguimiento_plazo_terminado_lanza_error() -> None:
    with pytest.raises(PlazoSeguimientoTerminadoError) as error:
        rango_seguimiento(HOY, date(2026, 8, 29))
    assert str(error.value) == "El plazo de seguimiento de este ciclo ya termino."


def test_rango_seguimiento_ultimo_dia_del_plazo_es_hoy_valido() -> None:
    assert rango_seguimiento(HOY, date(2026, 8, 30)) == (HOY, HOY)


def test_fecha_sugerida_plazo_terminado_lanza_error() -> None:
    with pytest.raises(PlazoSeguimientoTerminadoError):
        fecha_sugerida(HOY, date(2026, 8, 29))


@pytest.mark.parametrize("fecha", [date(2026, 9, 28), date(2026, 11, 5)])
def test_validar_fecha_seguimiento_fuera_de_rango_lanza_error_con_el_rango(fecha: date) -> None:
    with pytest.raises(FechaSeguimientoFueraDeRangoError) as error:
        validar_fecha_seguimiento(fecha, HOY, VENCE)
    mensaje = str(error.value)
    assert "2026-09-29" in mensaje
    assert "2026-11-04" in mensaje
    assert mensaje == "La fecha de seguimiento debe estar entre 2026-09-29 y 2026-11-04."


@pytest.mark.parametrize("fecha", [date(2026, 9, 29), date(2026, 10, 30), date(2026, 11, 4)])
def test_validar_fecha_seguimiento_dentro_del_rango_no_lanza(fecha: date) -> None:
    validar_fecha_seguimiento(fecha, HOY, VENCE)


def test_validar_fecha_seguimiento_plazo_terminado_lanza_error() -> None:
    with pytest.raises(PlazoSeguimientoTerminadoError):
        validar_fecha_seguimiento(HOY, HOY, date(2026, 8, 29))


# --- coherencia del resultado (h) --------------------------------------------------------


@pytest.mark.parametrize(
    ("con_campania", "contactado", "ofrecida", "aceptada", "fecha_contacto"),
    [
        pytest.param(True, False, SI, NA, None, id="no-contactado-ofrecida-si"),
        pytest.param(True, False, NA, SI, None, id="no-contactado-aceptada-si"),
        pytest.param(False, True, NO, NA, HOY, id="sin-campania-ofrecida-no"),
        pytest.param(False, True, NA, PEND, HOY, id="sin-campania-aceptada-pendiente"),
        pytest.param(True, True, NO, SI, HOY, id="ofrecida-no-aceptada-si"),
        pytest.param(True, True, SI, NA, HOY, id="ofrecida-si-aceptada-no-aplica"),
        pytest.param(True, True, NA, NA, HOY, id="contactado-con-campania-ofrecida-no-aplica"),
        pytest.param(True, True, SI, SI, None, id="contactado-sin-fecha-contacto"),
        pytest.param(False, True, NA, NA, None, id="contactado-sin-campania-sin-fecha"),
        pytest.param(True, True, SI, SI, date(2026, 9, 30), id="fecha-contacto-futura"),
        pytest.param(True, True, SI, SI, date(2026, 9, 19), id="fecha-contacto-antes-asignacion"),
        pytest.param(True, False, NA, NA, HOY, id="no-contactado-con-fecha-contacto"),
        pytest.param(False, False, NA, NA, HOY, id="no-contactado-sin-campania-con-fecha"),
    ],
)
def test_validar_resultado_incoherente_lanza_error(
    con_campania: bool,
    contactado: bool,
    ofrecida: Respuesta,
    aceptada: Respuesta,
    fecha_contacto: date | None,
) -> None:
    with pytest.raises(ResultadoIncoherenteError) as error:
        validar_resultado(
            con_campania=con_campania,
            contactado=contactado,
            ofrecida=ofrecida,
            aceptada=aceptada,
            fecha_contacto=fecha_contacto,
            fecha_asignacion=ASIGNADA,
            hoy=HOY,
        )
    assert str(error.value)


@pytest.mark.parametrize(
    ("con_campania", "contactado", "ofrecida", "aceptada", "fecha_contacto"),
    [
        pytest.param(False, False, NA, NA, None, id="sin-campania-no-contactado"),
        pytest.param(False, True, NA, NA, HOY, id="sin-campania-contactado"),
        pytest.param(True, False, NA, NA, None, id="con-campania-no-contactado"),
        pytest.param(True, True, NO, NA, HOY, id="ofrecida-no"),
        pytest.param(True, True, SI, SI, HOY, id="ofrecida-si-aceptada-si"),
        pytest.param(True, True, SI, NO, HOY, id="ofrecida-si-aceptada-no"),
        pytest.param(True, True, SI, PEND, HOY, id="ofrecida-si-aceptada-pendiente"),
        pytest.param(True, True, SI, SI, ASIGNADA, id="fecha-contacto-igual-asignacion"),
    ],
)
def test_validar_resultado_coherente_no_lanza(
    con_campania: bool,
    contactado: bool,
    ofrecida: Respuesta,
    aceptada: Respuesta,
    fecha_contacto: date | None,
) -> None:
    validar_resultado(
        con_campania=con_campania,
        contactado=contactado,
        ofrecida=ofrecida,
        aceptada=aceptada,
        fecha_contacto=fecha_contacto,
        fecha_asignacion=ASIGNADA,
        hoy=HOY,
    )


def test_validar_resultado_mensajes_distintos_por_regla() -> None:
    def mensaje(**cambios: object) -> str:
        datos: dict[str, object] = {
            "con_campania": True,
            "contactado": True,
            "ofrecida": SI,
            "aceptada": SI,
            "fecha_contacto": HOY,
            "fecha_asignacion": ASIGNADA,
            "hoy": HOY,
        }
        datos.update(cambios)
        with pytest.raises(ResultadoIncoherenteError) as error:
            validar_resultado(**datos)  # type: ignore[arg-type]  # datos de prueba heterogeneos
        return str(error.value)

    mensajes = {
        mensaje(con_campania=False, ofrecida=NO, aceptada=NA),
        mensaje(contactado=False, ofrecida=SI, aceptada=NA, fecha_contacto=None),
        mensaje(ofrecida=NA, aceptada=NA),
        mensaje(ofrecida=NO, aceptada=SI),
        mensaje(ofrecida=SI, aceptada=NA),
        mensaje(fecha_contacto=None),
        mensaje(fecha_contacto=date(2026, 9, 30)),
        mensaje(contactado=False, ofrecida=NA, aceptada=NA),
    }
    assert len(mensajes) == 8


# --- estado tras el resultado ----------------------------------------------------------


@pytest.mark.parametrize(
    ("renovo", "estado"),
    [(SI, EstadoGestion.CERRADA), (NO, EstadoGestion.CERRADA), (PEND, EstadoGestion.PENDIENTE)],
)
def test_estado_tras_resultado_segun_renovo(renovo: Respuesta, estado: EstadoGestion) -> None:
    assert estado_tras_resultado(renovo) is estado


def test_estado_tras_resultado_no_aplica_lanza_error() -> None:
    with pytest.raises(ResultadoIncoherenteError):
        estado_tras_resultado(NA)


# --- errores ---------------------------------------------------------------------------


def test_errores_de_gestion_son_domain_error_con_mensaje_fijo() -> None:
    assert isinstance(GestionCerradaError(), DomainError)
    assert str(GestionCerradaError()) == "La gestion esta cerrada y no se puede modificar."
    assert isinstance(GestionDuplicadaError(), DomainError)
    assert str(GestionDuplicadaError()) == "El ciclo de membresia ya tiene una gestion."
    assert isinstance(CampaniaNoAplicableError(), DomainError)
    assert str(CampaniaNoAplicableError()) == "La campana no esta activa o no aplica a este socio."
    assert isinstance(PlazoSeguimientoTerminadoError(), DomainError)
    assert isinstance(
        FechaSeguimientoFueraDeRangoError(date(2026, 9, 29), date(2026, 11, 4)), DomainError
    )
    assert isinstance(ResultadoIncoherenteError("x"), DomainError)
