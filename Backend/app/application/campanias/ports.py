"""Puertos del modulo campanias: parametrizacion y sugerencias (CU-06, CU-07).

Unidad de trabajo: la transaccion la gestiona siempre quien llama. Los repositorios reciben
la sesion ya abierta (infraestructura) y **nunca** hacen ``commit`` ni ``rollback``. Una
campana no se borra: se inactiva (RN-06.x), por eso ``CampaniaRepository`` no expone
borrado. Ningun puerto recibe ni devuelve sesiones, engines ni modelos ORM.
"""

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.domain.campanias.campania import DatosCampania
from app.domain.common.enums import NivelRiesgo, Plan


@dataclass(frozen=True, slots=True)
class CampaniaGuardada:
    """Campana no borrada tal como esta guardada."""

    id: int
    nombre: str
    descripcion: str | None
    activa: bool
    niveles_riesgo: tuple[NivelRiesgo, ...]
    planes: tuple[Plan, ...]
    prioridad: int
    es_ejemplo: bool


@runtime_checkable
class CampaniaRepository(Protocol):
    """Campanas dentro de la transaccion de quien llama (sin ``commit``).

    Todas las lecturas y escrituras ignoran las campanas con ``deleted_at``.
    """

    def listar(self) -> list[CampaniaGuardada]:
        """Todas las campanas: ``activa DESC, prioridad, lower(nombre), id``."""
        ...

    def obtener(self, campania_id: int) -> CampaniaGuardada | None:
        """La campana, o ``None`` si no existe o esta borrada."""
        ...

    def crear(self, datos: DatosCampania) -> CampaniaGuardada:
        """Inserta una campana del personal: ``activa = true`` y ``es_ejemplo = false``."""
        ...

    def actualizar(self, campania_id: int, datos: DatosCampania) -> CampaniaGuardada | None:
        """Reemplaza los datos editables; conserva ``activa`` y ``es_ejemplo``.

        Devuelve ``None`` si la campana no existe.
        """
        ...

    def inactivar(self, campania_id: int) -> CampaniaGuardada | None:
        """``activa = false`` (sin ``deleted_at``); ``None`` si la campana no existe."""
        ...

    def compatibles(self, nivel: NivelRiesgo, plan: Plan) -> list[CampaniaGuardada]:
        """Activas cuyo nivel y plan incluyen los dados: ``prioridad, lower(nombre), id``."""
        ...


@runtime_checkable
class PerfilPrediccion(Protocol):
    """Nivel de riesgo de una prediccion y plan de su ciclo de membresia (CU-07)."""

    def obtener(self, prediccion_id: int) -> tuple[NivelRiesgo, Plan] | None:
        """``(predicciones.nivel_riesgo, membresias.plan)``, o ``None`` si no existe."""
        ...


class ContextoCampanias(Protocol):
    """Repositorios que comparten una sola transaccion (unidad de trabajo de retencion).

    Si se sale del contexto sin ``commit()`` (o con una excepcion) todo se revierte.
    """

    @property
    def campanias(self) -> CampaniaRepository: ...

    @property
    def perfiles(self) -> PerfilPrediccion: ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...


class UnidadDeTrabajoCampanias(Protocol):
    """Abre una unidad de trabajo nueva en cada llamada."""

    def __call__(self) -> AbstractContextManager[ContextoCampanias]: ...
