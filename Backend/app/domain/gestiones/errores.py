"""Errores de dominio de una gestion de retencion (CU-08, CU-10).

Los mensajes son para el usuario final y nunca incluyen datos personales del socio.
"""

from datetime import date

from app.domain.common.exceptions import DomainError

MENSAJE_PLAZO_TERMINADO = "El plazo de seguimiento de este ciclo ya termino."
MENSAJE_GESTION_CERRADA = "La gestion esta cerrada y no se puede modificar."
MENSAJE_GESTION_DUPLICADA = "El ciclo de membresia ya tiene una gestion."
MENSAJE_CAMPANIA_NO_APLICABLE = "La campana no esta activa o no aplica a este socio."


class FechaSeguimientoFueraDeRangoError(DomainError):
    """La fecha de seguimiento esta fuera de ``[hoy, vencimiento + 30]`` (-> 422)."""

    def __init__(self, desde: date, hasta: date) -> None:
        self.desde = desde
        self.hasta = hasta
        super().__init__(
            f"La fecha de seguimiento debe estar entre {desde.isoformat()} y {hasta.isoformat()}."
        )


class PlazoSeguimientoTerminadoError(DomainError):
    """``vencimiento + 30`` ya es anterior a hoy: no queda fecha valida (-> 422)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_PLAZO_TERMINADO)


class ResultadoIncoherenteError(DomainError):
    """Las respuestas del resultado se contradicen (-> 422, un mensaje por regla)."""


class GestionCerradaError(DomainError):
    """Una gestion ``CERRADA`` no se puede editar (RN-10.3, -> 409)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_GESTION_CERRADA)


class GestionDuplicadaError(DomainError):
    """El ciclo de membresia ya tiene una gestion (RN-08.1, -> 409)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_GESTION_DUPLICADA)


class CampaniaNoAplicableError(DomainError):
    """La campana esta inactiva o no es compatible con el nivel o el plan (-> 422)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_CAMPANIA_NO_APLICABLE)
