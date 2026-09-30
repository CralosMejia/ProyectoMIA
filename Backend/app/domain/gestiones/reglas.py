"""Reglas de una gestion de retencion (CU-08, CU-10; (g) y (h) de R-009, (c) de R-010).

Sin reloj: ``hoy`` (fecha de negocio en Ecuador) la calcula quien llama con
``hoy_en_negocio(clock.now())``.
"""

from datetime import date, timedelta

from app.domain.common.enums import EstadoGestion, Respuesta
from app.domain.gestiones.errores import (
    FechaSeguimientoFueraDeRangoError,
    PlazoSeguimientoTerminadoError,
    ResultadoIncoherenteError,
)

DIAS_PLAZO_SEGUIMIENTO = 30
"""Ultimo dia permitido para el seguimiento: vencimiento + 30 (regla T a T+30)."""
DIAS_SUGERIDOS = 25
"""Fecha propuesta: vencimiento + 25 (CU-08 paso 3)."""

MENSAJE_SIN_CAMPANIA = "Sin campana asignada, ¿Se ofrecio? y ¿Acepto? deben ser No aplica."
MENSAJE_NO_CONTACTADO = "Si no se contacto al socio, ¿Se ofrecio? y ¿Acepto? deben ser No aplica."
MENSAJE_OFRECIDA_REQUERIDA = "Si se contacto al socio, indique si se ofrecio la campana (Si o No)."
MENSAJE_NO_OFRECIDA = "Si no se ofrecio la campana, ¿Acepto? debe ser No aplica."
MENSAJE_ACEPTADA_REQUERIDA = "Si se ofrecio la campana, indique si la acepto (Si, No o Pendiente)."
MENSAJE_FECHA_CONTACTO_REQUERIDA = "Si se contacto al socio, indique la fecha del contacto."
MENSAJE_FECHA_CONTACTO_RANGO = (
    "La fecha del contacto debe estar entre la fecha de asignacion y hoy."
)
MENSAJE_FECHA_CONTACTO_SOBRANTE = "Si no se contacto al socio, no indique fecha del contacto."
MENSAJE_RENOVO_INVALIDO = "¿Renovo? debe ser Si, No o Pendiente."

_RESPUESTAS_ACEPTADA_OFRECIDA = frozenset({Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE})


def rango_seguimiento(hoy: date, vencimiento: date) -> tuple[date, date]:
    """Rango permitido ``[hoy, vencimiento + 30]`` para la fecha de seguimiento.

    Lanza ``PlazoSeguimientoTerminadoError`` si ``vencimiento + 30`` es anterior a hoy.
    """
    hasta = vencimiento + timedelta(days=DIAS_PLAZO_SEGUIMIENTO)
    if hasta < hoy:
        raise PlazoSeguimientoTerminadoError()
    return hoy, hasta


def fecha_sugerida(hoy: date, vencimiento: date) -> date:
    """``max(vencimiento + 25, hoy)``; siempre dentro de ``rango_seguimiento``."""
    rango_seguimiento(hoy, vencimiento)
    return max(vencimiento + timedelta(days=DIAS_SUGERIDOS), hoy)


def validar_fecha_seguimiento(fecha: date, hoy: date, vencimiento: date) -> None:
    """Rechaza una fecha fuera de ``rango_seguimiento`` (los extremos son validos)."""
    desde, hasta = rango_seguimiento(hoy, vencimiento)
    if not desde <= fecha <= hasta:
        raise FechaSeguimientoFueraDeRangoError(desde, hasta)


def validar_resultado(
    *,
    con_campania: bool,
    contactado: bool,
    ofrecida: Respuesta,
    aceptada: Respuesta,
    fecha_contacto: date | None,
    fecha_asignacion: date,
    hoy: date,
) -> None:
    """Coherencia del resultado (decision (h)); cada regla con su propio mensaje."""
    if not con_campania:
        if ofrecida is not Respuesta.NO_APLICA or aceptada is not Respuesta.NO_APLICA:
            raise ResultadoIncoherenteError(MENSAJE_SIN_CAMPANIA)
    elif not contactado:
        if ofrecida is not Respuesta.NO_APLICA or aceptada is not Respuesta.NO_APLICA:
            raise ResultadoIncoherenteError(MENSAJE_NO_CONTACTADO)
    elif ofrecida is Respuesta.NO:
        if aceptada is not Respuesta.NO_APLICA:
            raise ResultadoIncoherenteError(MENSAJE_NO_OFRECIDA)
    elif ofrecida is Respuesta.SI:
        if aceptada not in _RESPUESTAS_ACEPTADA_OFRECIDA:
            raise ResultadoIncoherenteError(MENSAJE_ACEPTADA_REQUERIDA)
    else:
        raise ResultadoIncoherenteError(MENSAJE_OFRECIDA_REQUERIDA)

    if contactado:
        if fecha_contacto is None:
            raise ResultadoIncoherenteError(MENSAJE_FECHA_CONTACTO_REQUERIDA)
        if not fecha_asignacion <= fecha_contacto <= hoy:
            raise ResultadoIncoherenteError(MENSAJE_FECHA_CONTACTO_RANGO)
    elif fecha_contacto is not None:
        raise ResultadoIncoherenteError(MENSAJE_FECHA_CONTACTO_SOBRANTE)


def estado_inicial(con_campania: bool) -> EstadoGestion:
    """Con campana la gestion nace ``PENDIENTE``; sin campana nace ``CERRADA`` (R-010 (c)).

    Sin campana no hay seguimiento ni resultado que registrar.
    """
    return EstadoGestion.PENDIENTE if con_campania else EstadoGestion.CERRADA


def estado_tras_resultado(renovo: Respuesta) -> EstadoGestion:
    """``SI``/``NO`` cierran la gestion; ``PENDIENTE`` la deja pendiente."""
    if renovo in (Respuesta.SI, Respuesta.NO):
        return EstadoGestion.CERRADA
    if renovo is Respuesta.PENDIENTE:
        return EstadoGestion.PENDIENTE
    raise ResultadoIncoherenteError(MENSAJE_RENOVO_INVALIDO)
