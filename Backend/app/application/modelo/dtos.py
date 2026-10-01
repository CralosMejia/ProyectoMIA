"""DTOs del reentrenamiento del modelo (CU-02)."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.common.enums import ResultadoReentrenamiento


class ResultadoReentrenamientoDTO(BaseModel):
    """Desenlace de una revision programada o de una ejecucion manual.

    ``resultado`` es ``None`` cuando no se registro ningun intento: no tocaba (programado),
    el sistema no estaba listo o habia otro reentrenamiento en curso (``en_curso``).
    ``version`` solo tiene valor si se entreno una version nueva. ``motivo`` nunca incluye
    datos de socios.
    """

    model_config = ConfigDict(frozen=True)

    resultado: ResultadoReentrenamiento | None
    motivo: str
    version: int | None = Field(default=None, ge=1)
    en_curso: bool = False
