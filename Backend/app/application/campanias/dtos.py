"""DTOs del modulo campanias: parametrizacion y sugerencias (CU-06, CU-07)."""

from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.campanias.campania import (
    LONGITUD_MAXIMA_DESCRIPCION,
    LONGITUD_MAXIMA_NOMBRE,
    PRIORIDAD_MAXIMA,
    PRIORIDAD_MINIMA,
)
from app.domain.common.enums import NivelRiesgo, Plan

# Planes que admite una campana (todos salvo DIARIO); debe coincidir con PLANES_CAMPANIA.
PlanCampania = Literal[Plan.MENSUAL, Plan.TRIMESTRAL, Plan.SEMESTRAL, Plan.ANUAL, Plan.OTRO]
PLANES_CAMPANIA_DTO: tuple[Plan, ...] = get_args(PlanCampania)
# S8 (R-013): tope de elementos de niveles/planes (se admiten repetidos, pero no sin limite).
MAX_ELEMENTOS_FILTRO = 10

NombreCampania = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LONGITUD_MAXIMA_NOMBRE)
]
DescripcionCampania = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=LONGITUD_MAXIMA_DESCRIPCION)
]


class CampaniaDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    nombre: str
    descripcion: str | None = None
    activa: bool
    niveles_riesgo: list[NivelRiesgo]
    planes: list[PlanCampania]
    prioridad: int = Field(ge=1)
    es_ejemplo: bool


class CampaniaEntradaDTO(BaseModel):
    """Datos para crear o editar una campana. ``prioridad`` 1 es la mas prioritaria (1..999).

    Niveles y planes repetidos se aceptan y se guardan sin repetir, en orden canonico.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "nombre": "Ejemplo: Renovación anticipada",
                    "descripcion": "Ofrecer renovar antes del vencimiento con el beneficio "
                    "que Mtabolic defina.",
                    "niveles_riesgo": ["ALTO", "MEDIO"],
                    "planes": ["MENSUAL", "TRIMESTRAL"],
                    "prioridad": 2,
                }
            ]
        },
    )

    nombre: NombreCampania
    descripcion: DescripcionCampania | None = None
    niveles_riesgo: list[NivelRiesgo] = Field(min_length=1, max_length=MAX_ELEMENTOS_FILTRO)
    planes: list[PlanCampania] = Field(min_length=1, max_length=MAX_ELEMENTOS_FILTRO)
    prioridad: int = Field(ge=PRIORIDAD_MINIMA, le=PRIORIDAD_MAXIMA)
