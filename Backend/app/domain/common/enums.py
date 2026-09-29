"""Catalogos cerrados del dominio comun.

Cada valor coincide con su nombre y es la fuente unica de los ``CHECK ... IN (...)`` de la
base de datos y de los enums de los DTOs. La conversion es estricta (``Plan("mensual")``
lanza ``ValueError``): la normalizacion de textos de origen ocurre antes, en quien lee.
"""

from enum import StrEnum, unique


@unique
class Plan(StrEnum):
    MENSUAL = "MENSUAL"
    TRIMESTRAL = "TRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"
    DIARIO = "DIARIO"
    OTRO = "OTRO"


@unique
class FormaPago(StrEnum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"
    TARJETA_DATAFAST = "TARJETA_DATAFAST"
    OTRO = "OTRO"
    SIN_DATO = "SIN_DATO"


@unique
class EstadoCiclo(StrEnum):
    EVALUABLE = "EVALUABLE"
    PENDIENTE = "PENDIENTE"
    EXCLUIDO = "EXCLUIDO"


@unique
class NivelRiesgo(StrEnum):
    ALTO = "ALTO"
    MEDIO = "MEDIO"
    BAJO = "BAJO"


@unique
class EstadoGestion(StrEnum):
    PENDIENTE = "PENDIENTE"
    CERRADA = "CERRADA"


@unique
class OrigenMembresia(StrEnum):
    HISTORICO = "HISTORICO"
    PLANTILLA = "PLANTILLA"


@unique
class EstadoRegistro(StrEnum):
    NUEVO = "NUEVO"
    RENOVACION = "RENOVACION"
    CONGELAMIENTO = "CONGELAMIENTO"
    REINGRESO = "REINGRESO"
    BAJA = "BAJA"


@unique
class TipoCarga(StrEnum):
    MIGRACION_HISTORICA = "MIGRACION_HISTORICA"
    PLANTILLA = "PLANTILLA"


@unique
class EstadoMigracion(StrEnum):
    PENDIENTE = "PENDIENTE"
    EN_CURSO = "EN_CURSO"
    COMPLETADA = "COMPLETADA"


@unique
class DisparadorReentrenamiento(StrEnum):
    PROGRAMADO = "PROGRAMADO"
    MANUAL = "MANUAL"
    INICIAL = "INICIAL"


@unique
class ResultadoReentrenamiento(StrEnum):
    ENTRENADO = "ENTRENADO"
    CRITERIOS_NO_CUMPLIDOS = "CRITERIOS_NO_CUMPLIDOS"
    NO_SUPERA_VIGENTE = "NO_SUPERA_VIGENTE"
    OMITIDO = "OMITIDO"
    FALLIDO = "FALLIDO"


@unique
class Respuesta(StrEnum):
    SI = "SI"
    NO = "NO"
    PENDIENTE = "PENDIENTE"
    NO_APLICA = "NO_APLICA"


# Subconjuntos validos por contexto.
PLANES_CAMPANIA: frozenset[Plan] = frozenset(Plan) - {Plan.DIARIO}
RESPUESTAS_OFRECIMIENTO: frozenset[Respuesta] = frozenset(
    {Respuesta.SI, Respuesta.NO, Respuesta.NO_APLICA}
)
RESPUESTAS_ACEPTACION: frozenset[Respuesta] = frozenset(
    {Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE, Respuesta.NO_APLICA}
)
RESPUESTAS_RENOVACION: frozenset[Respuesta] = frozenset(
    {Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE}
)
