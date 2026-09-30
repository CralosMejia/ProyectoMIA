"""Puertos del modulo sistema: unidad de trabajo, bloqueo, libros y estado de la migracion.

- ``UnidadDeTrabajo``: una transaccion con los repositorios del historial y del modelo. Al
  salir del ``with`` sin ``commit()`` (o por una excepcion) todo se revierte.
- ``AbrirBloqueo``: entrega un ``BloqueoMigracion`` sobre una conexion propia durante el
  ``with``; quien lo usa llama a ``liberar()`` antes de salir.
- ``LocalizadorLibros``: rutas de los libros historicos disponibles.
- ``LectorEstadoSistema``: lecturas ligeras para ``GET /sistema/estado`` (sin el artefacto).
- ``RegistroMigracion``: resultado en memoria de la migracion de este proceso (decision (c)
  de R-004: un fallo deja ``PENDIENTE`` en la base y el motivo solo aqui y en el log).
"""

import threading
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, unique
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from app.application.historial.ports import (
    CargaRepository,
    MembresiaRepository,
    SocioRepository,
)
from app.application.modelo.ports import (
    BloqueoMigracion,
    EstadoSistema,
    EstadoSistemaRepository,
    IntentoRepository,
    ModeloRepository,
)


@runtime_checkable
class UnidadDeTrabajo(Protocol):
    """Transaccion unica con los repositorios; ``commit()`` explicito, si no, ``rollback``."""

    @property
    def socios(self) -> SocioRepository: ...

    @property
    def membresias(self) -> MembresiaRepository: ...

    @property
    def cargas(self) -> CargaRepository: ...

    @property
    def modelos(self) -> ModeloRepository: ...

    @property
    def intentos(self) -> IntentoRepository: ...

    @property
    def estado(self) -> EstadoSistemaRepository: ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


@runtime_checkable
class FabricaUnidadDeTrabajo(Protocol):
    """Crea una unidad de trabajo nueva (una transaccion nueva) en cada llamada."""

    def __call__(self) -> UnidadDeTrabajo: ...


@runtime_checkable
class AbrirBloqueo(Protocol):
    """Abre una conexion propia y entrega el bloqueo de la migracion sobre ella."""

    def __call__(self) -> AbstractContextManager[BloqueoMigracion]: ...


@runtime_checkable
class LocalizadorLibros(Protocol):
    """Localiza los libros historicos disponibles."""

    def rutas(self) -> list[Path]:
        """Rutas de los libros, en orden estable; lista vacia si no hay ninguno."""
        ...


@dataclass(frozen=True, slots=True)
class ResumenModelo:
    """Datos del modelo vigente que muestra el estado del sistema."""

    version: int
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int


@runtime_checkable
class LectorEstadoSistema(Protocol):
    """Lecturas para el estado del sistema; no carga el artefacto del modelo."""

    def estado(self) -> EstadoSistema: ...

    def modelo_vigente(self) -> ResumenModelo | None: ...

    def ultima_carga_en(self) -> datetime | None: ...


@unique
class ResultadoMigracion(StrEnum):
    COMPLETADA = "COMPLETADA"
    YA_MIGRADA = "YA_MIGRADA"
    EN_OTRO_PROCESO = "EN_OTRO_PROCESO"
    FALTAN_DATOS = "FALTAN_DATOS"
    FALLIDA = "FALLIDA"


class RegistroMigracion:
    """Estado en memoria de la migracion de este proceso (seguro entre hilos)."""

    def __init__(self) -> None:
        self._candado = threading.Lock()
        self._en_curso = False
        self._resultado: ResultadoMigracion | None = None

    def iniciar(self) -> None:
        with self._candado:
            self._en_curso = True
            self._resultado = None

    def terminar(self, resultado: ResultadoMigracion) -> None:
        with self._candado:
            self._en_curso = False
            self._resultado = resultado

    @property
    def en_curso(self) -> bool:
        with self._candado:
            return self._en_curso

    @property
    def resultado(self) -> ResultadoMigracion | None:
        with self._candado:
            return self._resultado
