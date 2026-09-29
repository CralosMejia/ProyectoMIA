"""DTOs del modulo sistema: estado general mostrado en la pantalla de inicio (CU-03)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.common.enums import EstadoMigracion

EstadoGeneral = Literal["INICIALIZANDO", "FALTAN_DATOS_HISTORICOS", "LISTO"]


class ModeloVigenteDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int = Field(ge=0)


class EstadoSistemaDTO(BaseModel):
    """Estado del sistema: migracion historica, modelo vigente y proximo reentrenamiento."""

    model_config = ConfigDict(frozen=True)

    estado: EstadoGeneral
    migracion_historica: EstadoMigracion
    modelo_vigente: ModeloVigenteDTO | None = None
    ultima_carga_en: datetime | None = None
    proxima_fecha_reentrenamiento: date | None = None
