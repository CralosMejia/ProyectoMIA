"""DTOs del modulo gestiones: asignacion, alertas y resultado (CU-08, CU-09, CU-10)."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum, unique
from typing import Annotated, Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan, Respuesta

# Subconjuntos por pregunta; deben coincidir con RESPUESTAS_* del dominio.
RespuestaOfrecimiento = Literal[Respuesta.SI, Respuesta.NO, Respuesta.NO_APLICA]
RespuestaAceptacion = Literal[Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE, Respuesta.NO_APLICA]
RespuestaRenovacion = Literal[Respuesta.SI, Respuesta.NO, Respuesta.PENDIENTE]
RESPUESTAS_OFRECIMIENTO_DTO: tuple[Respuesta, ...] = get_args(RespuestaOfrecimiento)
RESPUESTAS_ACEPTACION_DTO: tuple[Respuesta, ...] = get_args(RespuestaAceptacion)
RESPUESTAS_RENOVACION_DTO: tuple[Respuesta, ...] = get_args(RespuestaRenovacion)

Responsable = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Observaciones = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


@unique
class FiltroGestiones(StrEnum):
    """Lista blanca del filtro de gestiones pendientes (mismos grupos que las alertas)."""

    VENCIDAS = "vencidas"
    HOY = "hoy"
    PROXIMAS = "proximas"


class CrearGestionDTO(BaseModel):
    """CU-08: ``campania_id`` nulo = no asignar campana.

    Con campana, ``fecha_seguimiento`` es obligatoria. Sin campana la gestion nace cerrada:
    ``fecha_seguimiento`` y ``responsable`` son opcionales y, si llegan, se ignoran.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "prediccion_id": 15,
                    "campania_id": 3,
                    "fecha_seguimiento": "2026-10-25",
                    "responsable": "Andrea",
                },
                {"prediccion_id": 15, "campania_id": None},
            ]
        },
    )

    prediccion_id: int = Field(ge=1)
    campania_id: int | None = Field(default=None, ge=1)
    fecha_seguimiento: date | None = None
    responsable: Responsable | None = None

    @model_validator(mode="after")
    def _fecha_obligatoria_con_campania(self) -> Self:
        if self.campania_id is not None and self.fecha_seguimiento is None:
            raise ValueError("fecha_seguimiento es obligatoria cuando se asigna una campana")
        return self


class RegistrarResultadoDTO(BaseModel):
    """CU-10: resultado del seguimiento. ``renovo_declarado`` SI/NO cierra la gestion."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "contactado": True,
                    "campania_ofrecida": "SI",
                    "campania_aceptada": "SI",
                    "renovo_declarado": "PENDIENTE",
                    "fecha_contacto": "2026-10-20",
                    "observaciones": "Acepta el descuento; renovara la proxima semana.",
                    "responsable": "Andrea",
                    "fecha_seguimiento": "2026-10-27",
                }
            ]
        },
    )

    contactado: bool
    campania_ofrecida: RespuestaOfrecimiento
    campania_aceptada: RespuestaAceptacion
    renovo_declarado: RespuestaRenovacion
    fecha_contacto: date | None = None
    observaciones: Observaciones | None = None
    responsable: Responsable | None = None
    fecha_seguimiento: date | None = None


class GestionDTO(BaseModel):
    """Gestion de retencion completa, con el score y el nivel originales de la lista."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    prediccion_id: int = Field(ge=1)
    socio_nombre: str
    plan: Plan
    fecha_vencimiento: date
    modelo_version: str
    score: Decimal = Field(ge=0, le=1)
    nivel_riesgo: NivelRiesgo
    campania_id: int | None = None
    campania_nombre: str | None = None
    estado: EstadoGestion
    fecha_asignacion: datetime
    fecha_seguimiento: date
    responsable: str | None = None
    contactado: bool | None = None
    campania_ofrecida: RespuestaOfrecimiento | None = None
    campania_aceptada: RespuestaAceptacion | None = None
    renovo_declarado: RespuestaRenovacion | None = None
    fecha_contacto: date | None = None
    observaciones: str | None = None
    fecha_cierre: datetime | None = None


class GestionResumenDTO(BaseModel):
    """Fila de la lista de gestiones pendientes de un grupo de alertas."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    socio_nombre: str
    celular: str | None = None
    plan: Plan
    fecha_vencimiento: date
    fecha_seguimiento: date
    nivel_riesgo: NivelRiesgo
    campania_nombre: str | None = None
    responsable: str | None = None
    estado: EstadoGestion


class AlertasDTO(BaseModel):
    """Contadores de gestiones ``PENDIENTE`` por fecha de seguimiento (CU-09)."""

    model_config = ConfigDict(frozen=True)

    vencidas: int = Field(ge=0)
    hoy: int = Field(ge=0)
    proximos_7_dias: int = Field(ge=0)
