"""DTOs del modulo cargas: vista previa y confirmacion de la plantilla (CU-01)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ErrorFilaDTO(BaseModel):
    """Error de validacion de una fila de la hoja ``Registros``."""

    model_config = ConfigDict(frozen=True)

    fila: int = Field(ge=1)
    columna: str | None = None
    motivo: str


class VistaPreviaCargaDTO(BaseModel):
    """Resultado de validar el archivo sin guardar nada."""

    model_config = ConfigDict(frozen=True)

    filas_leidas: int = Field(ge=0)
    filas_validas: int = Field(ge=0)
    filas_con_error: int = Field(ge=0)
    filas_duplicadas: int = Field(ge=0)
    vencimiento_desde: date | None = None
    vencimiento_hasta: date | None = None
    errores: list[ErrorFilaDTO]
    puede_confirmar: bool


class CargaDTO(BaseModel):
    """Carga confirmada y guardada."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    fecha_carga: datetime
    nombre_archivo: str
    filas_leidas: int = Field(ge=0)
    filas_guardadas: int = Field(ge=0)
    filas_duplicadas: int = Field(ge=0)
    socios_enlazados: int = Field(ge=0)
    avisos_enlace: list[str]
