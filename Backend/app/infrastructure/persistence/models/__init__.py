"""Modelos ORM. Importar este paquete registra las 10 tablas en ``Base.metadata``."""

from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.historial import Carga, Membresia, Socio
from app.infrastructure.persistence.models.modelo import (
    EstadoSistema,
    IntentoReentrenamiento,
    Modelo,
)
from app.infrastructure.persistence.models.retencion import (
    Campania,
    GestionRetencion,
    ListaPriorizada,
    Prediccion,
)

__all__ = [
    "Base",
    "Campania",
    "Carga",
    "EstadoSistema",
    "GestionRetencion",
    "IntentoReentrenamiento",
    "ListaPriorizada",
    "Membresia",
    "Modelo",
    "Prediccion",
    "Socio",
]
