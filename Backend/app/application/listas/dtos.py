"""DTOs del modulo listas: generacion y consulta de la lista priorizada (CU-04, CU-05)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan
from app.domain.listas.nombre import LONGITUD_MAXIMA_NOMBRE

HORIZONTE_DIAS_POR_DEFECTO = 30
HORIZONTE_DIAS_MAXIMO = 31
TOP_K_POR_DEFECTO = 25

NombreLista = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=LONGITUD_MAXIMA_NOMBRE,
        pattern=r"^[^\x00-\x1f\x7f]*$",
    ),
]
"""Nombre de la lista: se recorta; tras recortar 1..80 caracteres y sin caracteres de control."""


class GenerarListaDTO(BaseModel):
    """Parametros de CU-04.

    ``fecha_referencia`` nula = hoy en la zona del negocio (Ecuador); una fecha anterior a hoy
    la rechaza el caso de uso (regla de negocio). ``horizonte_dias`` va de 1 a 31.
    ``nombre`` ausente o nulo = nombre por defecto con la fecha de la lista
    (``"Lista del 29 sep 2026"``); si llega, se recorta y debe quedar con 1..80 caracteres sin
    caracteres de control. Se permiten nombres repetidos.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "nombre": "Campaña octubre",
                    "fecha_referencia": "2026-09-29",
                    "horizonte_dias": 30,
                    "top_k": 25,
                }
            ]
        },
    )

    nombre: NombreLista | None = None
    fecha_referencia: date | None = None
    horizonte_dias: int = Field(default=HORIZONTE_DIAS_POR_DEFECTO, ge=1, le=HORIZONTE_DIAS_MAXIMO)
    top_k: int = Field(default=TOP_K_POR_DEFECTO, ge=1)


class PrediccionDTO(BaseModel):
    """Un socio de la lista. ``score`` es decimal exacto y se serializa como string.

    ``cedula`` es texto (conserva el cero inicial) o ``null`` en listas antiguas guardadas
    antes de excluir a los socios sin cedula. El correo no se expone.
    """

    model_config = ConfigDict(frozen=True)

    prediccion_id: int = Field(ge=1)
    prioridad: int = Field(ge=1)
    socio_nombre: str
    celular: str | None = None
    cedula: str | None = None
    plan: Plan
    fecha_vencimiento: date
    dias_para_vencer: int
    monto_cobrado: Decimal | None = None
    score: Decimal = Field(ge=0, le=1)
    nivel_riesgo: NivelRiesgo
    factores_principales: list[str]
    dentro_top_k: bool
    gestion_id: int | None = Field(default=None, ge=1)
    gestion_estado: EstadoGestion | None = None
    campania_asignada: str | None = None


class ListaPriorizadaDTO(BaseModel):
    """Lista priorizada generada con un modelo concreto (instantanea inmutable).

    ``fecha_generacion`` es la fecha de referencia de la cartera; ``creada_en``, el instante
    (con zona) en que se guardo la lista.
    """

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    nombre: str = Field(min_length=1, max_length=LONGITUD_MAXIMA_NOMBRE)
    modelo_version: str
    fecha_generacion: date
    creada_en: datetime
    horizonte_dias: int = Field(ge=1, le=365)
    top_k: int = Field(ge=1)
    umbral_alto: Decimal = Field(ge=0, le=1)
    umbral_medio: Decimal = Field(ge=0, le=1)
    advertencia_datos_antiguos: bool
    items: list[PrediccionDTO]


class ListaResumenDTO(BaseModel):
    """Resumen de una lista para el historial de listas generadas."""

    model_config = ConfigDict(frozen=True)

    id: int = Field(ge=1)
    nombre: str = Field(min_length=1, max_length=LONGITUD_MAXIMA_NOMBRE)
    fecha_generacion: date
    creada_en: datetime
    modelo_version: str
    horizonte_dias: int = Field(ge=1, le=365)
    top_k: int = Field(ge=1)
    total_items: int = Field(ge=0)
