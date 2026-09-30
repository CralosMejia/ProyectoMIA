"""Puertos de la carga por plantilla (CU-01): lector, consultas, escritura y unidad de trabajo.

Unidad de trabajo: la transaccion la gestiona siempre quien llama. Los repositorios reciben
la sesion ya abierta en su construccion (infraestructura) y **nunca** hacen ``commit`` ni
``rollback`` ni abren o cierran transacciones; asi los socios nuevos, las cedulas asignadas,
las membresias y la carga se escriben de forma atomica (todo o nada). Ningun repositorio
expone ``delete``: nada del negocio se borra fisicamente. Ningun puerto recibe ni devuelve
sesiones, engines ni modelos ORM: solo los DTOs de aqui y de ``historial.ports``.
"""

from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.application.modelo.ports import EstadoSistemaRepository
from app.domain.cargas.enlace import ClaveMembresia
from app.domain.cargas.fila import PlantillaLeida

__all__ = [
    "ClaveMembresia",
    "ConsultasCarga",
    "ContextoCargas",
    "EscrituraCarga",
    "LectorPlantilla",
    "NuevaCarga",
    "NuevaMembresia",
    "NuevoSocio",
    "UnidadDeTrabajoCargas",
]


@runtime_checkable
class LectorPlantilla(Protocol):
    """Lee la hoja ``Registros`` de la plantilla oficial y entrega valores crudos A..N."""

    def leer(self, contenido: bytes) -> PlantillaLeida:
        """Lee ``contenido`` (un ``.xlsx``); lanza ``PlantillaInvalidaError`` si no sirve."""
        ...


@runtime_checkable
class ConsultasCarga(Protocol):
    """Lecturas para enlazar socios y detectar duplicados (solo filas no borradas)."""

    def socios_por_cedulas(self, cedulas: Iterable[str]) -> dict[str, int]:
        """Id del socio de cada cedula encontrada, indexado por la cedula pedida.

        Una cedula ``0XXXXXXXXX`` tambien se busca como ``XXXXXXXXX`` (el historico perdio
        el cero inicial). Las cedulas no encontradas no aparecen en el resultado.
        """
        ...

    def socios_sin_cedula_por_nombres(self, nombres: Iterable[str]) -> dict[str, list[int]]:
        """Ids de los socios sin cedula por ``nombre_normalizado`` (ordenados por id)."""
        ...

    def claves_existentes(self, socio_ids: Iterable[int]) -> set[ClaveMembresia]:
        """Claves de las membresias de ``socio_ids`` con ambas fechas registradas."""
        ...


@runtime_checkable
class EscrituraCarga(Protocol):
    """Escritura de la carga dentro de la transaccion de quien llama (sin ``commit``)."""

    def crear_socios(self, socios: Sequence[NuevoSocio]) -> list[int]:
        """Inserta ``socios`` y devuelve sus ids en el mismo orden de entrada."""
        ...

    def asignar_cedula(
        self, socio_id: int, cedula: str, celular: str | None, correo: str | None
    ) -> None:
        """Asigna la cedula al socio; celular y correo solo se rellenan si estaban vacios."""
        ...

    def insertar_membresias(self, membresias: Sequence[NuevaMembresia]) -> int:
        """Inserta ``membresias`` y devuelve cuantas se insertaron."""
        ...

    def crear_carga(self, carga: NuevaCarga) -> int:
        """Inserta la carga y devuelve su id."""
        ...


@runtime_checkable
class ContextoCargas(Protocol):
    """Repositorios que comparten una sola transaccion (unidad de trabajo de cargas).

    Si se sale del contexto sin ``commit()`` (o con una excepcion) todo se revierte.
    """

    @property
    def consultas(self) -> ConsultasCarga: ...

    @property
    def escritura(self) -> EscrituraCarga: ...

    @property
    def estado(self) -> EstadoSistemaRepository: ...

    def bloquear(self) -> None:
        """Toma el bloqueo exclusivo de cargas hasta el fin de la transaccion."""
        ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...


@runtime_checkable
class UnidadDeTrabajoCargas(Protocol):
    """Abre una unidad de trabajo nueva en cada llamada."""

    def __call__(self) -> AbstractContextManager[ContextoCargas]: ...
