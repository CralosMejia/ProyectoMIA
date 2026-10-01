"""DTOs del modulo dashboard: embudo, resultados por campana y estado del modelo (CU-11)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# Mes de consulta ``YYYY-MM`` con mes entre 01 y 12.
MES_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class EmbudoDTO(BaseModel):
    """Embudo del mes sobre las gestiones **con campana** (``asignadas``).

    ``contactadas``: contactado si; ``ofrecidas``/``aceptadas``/``renovaron``: respuesta ``SI``.
    Un valor nulo (sin resultado) nunca cuenta.
    """

    model_config = ConfigDict(frozen=True)

    asignadas: int = Field(ge=0)
    contactadas: int = Field(ge=0)
    ofrecidas: int = Field(ge=0)
    aceptadas: int = Field(ge=0)
    renovaron: int = Field(ge=0)


class ResultadoCampaniaDTO(BaseModel):
    """Cifras descriptivas por campana; ``campania_id`` nulo = gestiones sin campana.

    ``gestiones_cerradas`` = gestiones cerradas **con resultado** (``renovo_declarado`` SI o
    NO). ``tasa_renovacion`` = ``renovaciones / gestiones_cerradas`` con 8 decimales, solo si
    hay al menos 10 cerradas con resultado; si no, nula y ``casos_insuficientes``.
    """

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
    """Modelo vigente; ``ciclos_nuevos_evaluables`` con la misma regla que CU-02."""

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
