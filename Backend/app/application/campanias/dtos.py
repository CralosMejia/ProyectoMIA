"""DTOs del modulo campanias: parametrizacion y sugerencias (CU-06, CU-07)."""

from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.common.enums import NivelRiesgo, Plan

# Planes que admite una campana (todos salvo DIARIO); debe coincidir con PLANES_CAMPANIA.
PlanCampania = Literal[Plan.MENSUAL, Plan.TRIMESTRAL, Plan.SEMESTRAL, Plan.ANUAL, Plan.OTRO]
PLANES_CAMPANIA_DTO: tuple[Plan, ...] = get_args(PlanCampania)

NombreCampania = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
DescripcionCampania = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


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
    """Datos para crear o editar una campana. ``prioridad`` 1 es la mas prioritaria."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "nombre": "Renovacion anticipada",
                    "descripcion": "10% de descuento si renueva antes del vencimiento.",
                    "niveles_riesgo": ["ALTO", "MEDIO"],
                    "planes": ["MENSUAL", "TRIMESTRAL"],
                    "prioridad": 1,
                }
            ]
        },
    )

    nombre: NombreCampania
    descripcion: DescripcionCampania | None = None
    niveles_riesgo: list[NivelRiesgo] = Field(min_length=1)
    planes: list[PlanCampania] = Field(min_length=1)
    prioridad: int = Field(ge=1)
