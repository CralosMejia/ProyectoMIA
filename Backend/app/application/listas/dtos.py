"""DTOs del modulo listas: generacion y consulta de la lista priorizada (CU-04, CU-05)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan

HORIZONTE_DIAS_POR_DEFECTO = 30
TOP_K_POR_DEFECTO = 25


class GenerarListaDTO(BaseModel):
    """Parametros de CU-04. ``fecha_referencia`` nula = hoy segun el reloj del sistema."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [{"fecha_referencia": "2026-09-28", "horizonte_dias": 30, "top_k": 25}]
        },
    )

    fecha_referencia: date | None = None
    horizonte_dias: int = Field(default=HORIZONTE_DIAS_POR_DEFECTO, ge=1, le=365)
    top_k: int = Field(default=TOP_K_POR_DEFECTO, ge=1)


class PrediccionDTO(BaseModel):
    """Un socio de la lista. ``score`` es decimal exacto y se serializa como string."""

    model_config = ConfigDict(frozen=True)

    prediccion_id: int = Field(ge=1)
    prioridad: int = Field(ge=1)
    socio_nombre: str
    celular: str | None = None
    correo: str | None = None
    plan: Plan
    fecha_vencimiento: date
    dias_para_vencer: int
    score: Decimal = Field(ge=0, le=1)
    nivel_riesgo: NivelRiesgo
    factores_principales: list[str]
    dentro_top_k: bool
    gestion_estado: EstadoGestion | None = None
    campania_asignada: str | None = None


class ListaPriorizadaDTO(BaseModel):
    """Lista priorizada generada con un modelo concreto (instantanea inmutable)."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    modelo_version: str
    fecha_generacion: datetime
    horizonte_dias: int = Field(ge=1, le=365)
    top_k: int = Field(ge=1)
    umbral_alto: Decimal = Field(ge=0, le=1)
    umbral_medio: Decimal = Field(ge=0, le=1)
    advertencia_datos_antiguos: bool
    items: list[PrediccionDTO]
