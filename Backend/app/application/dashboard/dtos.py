"""DTOs del modulo dashboard: embudo, resultados por campana y estado del modelo (CU-11)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# Mes de consulta ``YYYY-MM`` con mes entre 01 y 12.
MES_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class EmbudoDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    asignadas: int = Field(ge=0)
    contactadas: int = Field(ge=0)
    ofrecidas: int = Field(ge=0)
    aceptadas: int = Field(ge=0)
    renovaron: int = Field(ge=0)


class ResultadoCampaniaDTO(BaseModel):
    """Cifras descriptivas por campana; ``campania_id`` nulo = gestiones sin campana."""

    model_config = ConfigDict(frozen=True)

    campania_id: int | None = None
    nombre: str
    gestiones: int = Field(ge=0)
    contactados: int = Field(ge=0)
    renovaciones: int = Field(ge=0)
    gestiones_cerradas: int = Field(ge=0)
    tasa_renovacion: Decimal | None = Field(default=None, ge=0, le=1)
    casos_insuficientes: bool


class EstadoModeloDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int = Field(ge=0)
    proxima_fecha_reentrenamiento: date | None = None
    ciclos_nuevos_evaluables: int = Field(ge=0)


class DashboardDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    mes: str = Field(pattern=MES_PATTERN)
    embudo: EmbudoDTO
    por_campania: list[ResultadoCampaniaDTO]
    estado_modelo: EstadoModeloDTO | None = None
