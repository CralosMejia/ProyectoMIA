"""Puertos del modelo predictivo: modelos versionados, intentos, estado del sistema y bloqueo.

Unidad de trabajo: la transaccion la gestiona siempre quien llama. Los repositorios reciben
la sesion ya abierta en su construccion (infraestructura) y **nunca** hacen ``commit`` ni
``rollback`` ni abren o cierran transacciones; asi el guardado del modelo, el intento y el
cambio de estado de la migracion quedan en una unica transaccion (ADR-004). Ninguno expone
``delete``: los modelos y los intentos son instantaneas inmutables (RT-07, ADR-003); un
modelo nuevo solo desmarca como vigente al anterior, que se conserva.

``BloqueoMigracion`` no forma parte de la transaccion: es un bloqueo de sesion sobre su
propia conexion, para que la migracion historica no corra dos veces a la vez (ADR-004).
``BloqueoReentrenamiento`` es el equivalente de CU-02, con una clave propia: impide dos
reentrenamientos a la vez sin bloquear la migracion.
Ningun puerto recibe ni devuelve sesiones, engines ni modelos ORM: solo los DTOs de aqui.
"""

from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    FormaPago,
    Plan,
    ResultadoReentrenamiento,
)

_CERO = Decimal(0)
_UNO = Decimal(1)


def _exigir_zona(nombre: str, valor: datetime) -> None:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError(f"{nombre} debe tener zona horaria")


def _exigir_probabilidad(nombre: str, valor: Decimal | None) -> None:
    if valor is not None and not _CERO <= valor <= _UNO:
        raise ValueError(f"{nombre} debe estar entre 0 y 1")


@dataclass(frozen=True, slots=True)
class NuevoModelo:
    """Modelo entrenado a guardar como vigente. ``artefacto`` es el binario serializado."""

    version: int
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int
    periodo_desde: date
    periodo_hasta: date
    prevalencia: Decimal
    umbral_alto: Decimal
    umbral_medio: Decimal
    porcentajes_umbral: Mapping[str, int]
    artefacto: bytes
    metadata_tecnica: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version debe ser positiva")
        if self.ciclos_entrenamiento < 0:
            raise ValueError("ciclos_entrenamiento no puede ser negativo")
        _exigir_zona("fecha_entrenamiento", self.fecha_entrenamiento)
        for nombre in ("prevalencia", "umbral_alto", "umbral_medio"):
            _exigir_probabilidad(nombre, getattr(self, nombre))
        if self.umbral_alto < self.umbral_medio:
            raise ValueError("umbral_alto no puede ser menor que umbral_medio")
        if self.periodo_hasta < self.periodo_desde:
            raise ValueError("periodo_hasta no puede ser anterior a periodo_desde")


@dataclass(frozen=True, slots=True)
class ModeloGuardado:
    """Modelo persistido (lectura)."""

    id: int
    version: int
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int
    periodo_desde: date
    periodo_hasta: date
    prevalencia: Decimal
    umbral_alto: Decimal
    umbral_medio: Decimal
    porcentajes_umbral: Mapping[str, int]
    artefacto: bytes
    metadata_tecnica: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class NuevoIntento:
    """Intento de (re)entrenamiento a registrar (auditoria append-only)."""

    fecha: datetime
    disparador: DisparadorReentrenamiento
    resultado: ResultadoReentrenamiento
    fecha_programada: date | None = None
    motivo: str | None = None
    ciclos_nuevos: int | None = None
    pr_auc_candidato: Decimal | None = None
    pr_auc_vigente: Decimal | None = None
    modelo_id: int | None = None

    def __post_init__(self) -> None:
        _exigir_zona("fecha", self.fecha)
        _exigir_probabilidad("pr_auc_candidato", self.pr_auc_candidato)
        _exigir_probabilidad("pr_auc_vigente", self.pr_auc_vigente)
        if self.ciclos_nuevos is not None and self.ciclos_nuevos < 0:
            raise ValueError("ciclos_nuevos no puede ser negativo")


@dataclass(frozen=True, slots=True)
class EstadoSistema:
    """Fila unica de control: estado de la migracion y proxima fecha de reentrenamiento."""

    migracion_historica: EstadoMigracion
    proxima_fecha_reentrenamiento: date | None


@runtime_checkable
class ModeloRepository(Protocol):
    """Modelos versionados dentro de la transaccion de quien llama (sin ``commit``)."""

    def crear(self, modelo: NuevoModelo) -> int:
        """Guarda ``modelo`` como vigente, desmarca el vigente anterior y devuelve el id."""
        ...

    def obtener_vigente(self) -> ModeloGuardado | None:
        """Devuelve el modelo vigente o ``None`` si aun no hay ninguno."""
        ...


@runtime_checkable
class IntentoRepository(Protocol):
    """Registro de intentos de entrenamiento (sin ``commit``)."""

    def crear(self, intento: NuevoIntento) -> int:
        """Inserta el intento y devuelve su id."""
        ...


@runtime_checkable
class EstadoSistemaRepository(Protocol):
    """Lectura y cambio de la fila unica de ``estado_sistema`` (sin ``commit``)."""

    def obtener(self) -> EstadoSistema:
        """Devuelve el estado actual."""
        ...

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        """Cambia el estado de la migracion historica."""
        ...

    def fijar_proxima_fecha(self, fecha: date) -> None:
        """Fija la proxima fecha de reentrenamiento."""
        ...


@runtime_checkable
class BloqueoMigracion(Protocol):
    """Bloqueo exclusivo entre procesos para la migracion historica."""

    def intentar_adquirir(self) -> bool:
        """Intenta tomar el bloqueo sin esperar; ``True`` si se obtuvo."""
        ...

    def liberar(self) -> None:
        """Libera el bloqueo tomado con ``intentar_adquirir``."""
        ...


# ---------------------------------------------------------------- reentrenamiento (CU-02)


@dataclass(frozen=True, slots=True)
class MembresiaParaEntrenamiento:
    """Membresia no borrada con lo que necesitan los ciclos del modelo (sin datos personales).

    ``registrada_en`` es su ``created_at``: el criterio 2 de CU-02 cuenta las membresias
    registradas despues del ultimo entrenamiento.
    """

    membresia_id: int
    socio_id: int
    plan: Plan
    forma_pago: FormaPago
    fecha_inicio: date | None
    fecha_vencimiento: date | None
    fecha_actividad: date
    monto_cobrado: Decimal | None
    inicio_aproximado: bool
    registrada_en: datetime


@runtime_checkable
class LectorMembresiasEntrenamiento(Protocol):
    """Lectura de las membresias para reentrenar, dentro de la transaccion de quien llama."""

    def listar_para_entrenamiento(self) -> list[MembresiaParaEntrenamiento]:
        """Todas las membresias no borradas logicamente, ordenadas por id."""
        ...


class ContextoReentrenamiento(Protocol):
    """Repositorios que comparten una sola transaccion (unidad de trabajo de CU-02).

    Si se sale del contexto sin ``commit()`` (o con una excepcion) todo se revierte.
    """

    @property
    def membresias(self) -> LectorMembresiasEntrenamiento: ...

    @property
    def modelos(self) -> ModeloRepository: ...

    @property
    def intentos(self) -> IntentoRepository: ...

    @property
    def estado(self) -> EstadoSistemaRepository: ...

    def commit(self) -> None:
        """Confirma la transaccion."""
        ...


class UnidadDeTrabajoReentrenamiento(Protocol):
    """Abre una unidad de trabajo nueva en cada llamada."""

    def __call__(self) -> AbstractContextManager[ContextoReentrenamiento]: ...


@runtime_checkable
class BloqueoReentrenamiento(Protocol):
    """Bloqueo exclusivo entre procesos para el reentrenamiento (clave propia)."""

    def intentar_adquirir(self) -> bool:
        """Intenta tomar el bloqueo sin esperar; ``True`` si se obtuvo."""
        ...

    def liberar(self) -> None:
        """Libera el bloqueo tomado con ``intentar_adquirir``."""
        ...


class AbrirBloqueoReentrenamiento(Protocol):
    """Entrega un ``BloqueoReentrenamiento`` sobre una conexion propia mientras dura el ``with``."""

    def __call__(self) -> AbstractContextManager[BloqueoReentrenamiento]: ...
