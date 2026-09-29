"""DTOs de salida del modulo health."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthDTO(BaseModel):
    """Estado de salud del servicio expuesto a la capa de presentacion."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "degraded"]
    database: Literal["up", "down"]
    checked_at: datetime
