"""Repositorios SQLAlchemy del modelo predictivo y bloqueo consultivo de la migracion.

``SqlAlchemy{Modelo,Intento,EstadoSistema}Repository`` escriben siempre dentro de la
transaccion de la ``Session`` recibida (unit of work): quien llama la abre y decide si
confirma o revierte; aqui no se controla la transaccion. ``created_at``/``updated_at`` salen
del ``Clock`` inyectado.

``PgBloqueoMigracion`` usa ``pg_try_advisory_lock`` a nivel de **sesion** de PostgreSQL
sobre una conexion propia que le entrega quien llama (idealmente en ``AUTOCOMMIT``): el
bloqueo no depende de ninguna transaccion y dura hasta ``liberar()`` o hasta que la
conexion fisica se cierre. Quien llama debe llamar a ``liberar()`` antes de devolver la
conexion al pool. ``PgBloqueoReentrenamiento`` hace lo mismo con otra clave (CU-02): un
reentrenamiento en curso no bloquea la migracion ni al reves.

``SqlAlchemyFechasCargaPlantilla`` lee la fecha de la ultima carga por plantilla (corte de los
datos de ``adoptar-modelo``, R-015 T11).
"""

from collections.abc import Mapping
from datetime import date, datetime

from sqlalchemy import Connection, func, insert, select, text, update
from sqlalchemy.orm import Session

from app.application.modelo.ports import (
    EstadoSistema,
    ModeloGuardado,
    NuevoIntento,
    NuevoModelo,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoMigracion, TipoCarga
from app.infrastructure.persistence.models.historial import Carga
from app.infrastructure.persistence.models.modelo import EstadoSistema as EstadoSistemaOrm
from app.infrastructure.persistence.models.modelo import IntentoReentrenamiento, Modelo

ESTADO_SISTEMA_ID = 1
# Clave fija del bloqueo consultivo de la migracion historica (CU-03, ADR-004).
CLAVE_BLOQUEO_MIGRACION = 7_310_003
# Clave fija del bloqueo consultivo del reentrenamiento (CU-02); distinta de la de migracion.
CLAVE_BLOQUEO_REENTRENAMIENTO = 7_310_002


def _marcas(instante: datetime) -> dict[str, datetime]:
    return {"created_at": instante, "updated_at": instante}


def _porcentajes(valor: Mapping[str, object]) -> dict[str, int]:
    porcentajes: dict[str, int] = {}
    for clave, porcentaje in valor.items():
        if not isinstance(porcentaje, int):
            raise TypeError("porcentajes_umbral debe contener enteros")
        porcentajes[clave] = porcentaje
    return porcentajes


class SqlAlchemyModeloRepository:
    """Implementa ``ModeloRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def crear(self, modelo: NuevoModelo) -> int:
        ahora = self._clock.now()
        # Primero se desmarca el vigente anterior: el indice unico parcial exige uno solo.
        self._session.execute(
            update(Modelo).where(Modelo.vigente.is_(True)).values(vigente=False, updated_at=ahora)
        )
        sentencia = (
            insert(Modelo)
            .values(
                version=modelo.version,
                vigente=True,
                fecha_entrenamiento=modelo.fecha_entrenamiento,
                ciclos_entrenamiento=modelo.ciclos_entrenamiento,
                periodo_desde=modelo.periodo_desde,
                periodo_hasta=modelo.periodo_hasta,
                prevalencia=modelo.prevalencia,
                umbral_alto=modelo.umbral_alto,
                umbral_medio=modelo.umbral_medio,
                porcentajes_umbral=dict(modelo.porcentajes_umbral),
                artefacto=modelo.artefacto,
                metadata_tecnica=dict(modelo.metadata_tecnica),
                **_marcas(ahora),
            )
            .returning(Modelo.id)
        )
        return self._session.scalars(sentencia).one()

    def obtener_vigente(self) -> ModeloGuardado | None:
        fila = self._session.scalars(select(Modelo).where(Modelo.vigente.is_(True))).one_or_none()
        if fila is None:
            return None
        return ModeloGuardado(
            id=fila.id,
            version=fila.version,
            fecha_entrenamiento=fila.fecha_entrenamiento,
            ciclos_entrenamiento=fila.ciclos_entrenamiento,
            periodo_desde=fila.periodo_desde,
            periodo_hasta=fila.periodo_hasta,
            prevalencia=fila.prevalencia,
            umbral_alto=fila.umbral_alto,
            umbral_medio=fila.umbral_medio,
            porcentajes_umbral=_porcentajes(fila.porcentajes_umbral),
            artefacto=bytes(fila.artefacto),
            metadata_tecnica=dict(fila.metadata_tecnica),
        )


class SqlAlchemyIntentoRepository:
    """Implementa ``IntentoRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def crear(self, intento: NuevoIntento) -> int:
        sentencia = (
            insert(IntentoReentrenamiento)
            .values(
                fecha=intento.fecha,
                fecha_programada=intento.fecha_programada,
                disparador=intento.disparador,
                resultado=intento.resultado,
                motivo=intento.motivo,
                ciclos_nuevos=intento.ciclos_nuevos,
                pr_auc_candidato=intento.pr_auc_candidato,
                pr_auc_vigente=intento.pr_auc_vigente,
                modelo_id=intento.modelo_id,
                **_marcas(self._clock.now()),
            )
            .returning(IntentoReentrenamiento.id)
        )
        return self._session.scalars(sentencia).one()


class SqlAlchemyEstadoSistemaRepository:
    """Implementa ``EstadoSistemaRepository`` sobre la fila unica ``id = 1``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def obtener(self) -> EstadoSistema:
        fila = self._session.execute(
            select(
                EstadoSistemaOrm.migracion_historica,
                EstadoSistemaOrm.proxima_fecha_reentrenamiento,
            ).where(EstadoSistemaOrm.id == ESTADO_SISTEMA_ID)
        ).one()
        return EstadoSistema(
            migracion_historica=EstadoMigracion(fila.migracion_historica),
            proxima_fecha_reentrenamiento=fila.proxima_fecha_reentrenamiento,
        )

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        self._actualizar(migracion_historica=estado)

    def fijar_proxima_fecha(self, fecha: date) -> None:
        self._actualizar(proxima_fecha_reentrenamiento=fecha)

    def _actualizar(self, **valores: object) -> None:
        self._session.execute(
            update(EstadoSistemaOrm)
            .where(EstadoSistemaOrm.id == ESTADO_SISTEMA_ID)
            .values(**valores, updated_at=self._clock.now())
        )


class SqlAlchemyFechasCargaPlantilla:
    """Implementa ``FechasCargaPlantilla`` (una consulta parametrizada, solo lectura)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ultima_carga_plantilla_hasta(self, instante: datetime) -> datetime | None:
        return self._session.scalar(
            select(func.max(Carga.fecha_carga)).where(
                Carga.tipo == TipoCarga.PLANTILLA.value,
                Carga.deleted_at.is_(None),
                Carga.fecha_carga <= instante,
            )
        )


class _PgBloqueoConsultivo:
    """``pg_try_advisory_lock`` de sesion con una clave fija."""

    _clave: int

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def intentar_adquirir(self) -> bool:
        obtenido = self._connection.execute(
            text("SELECT pg_try_advisory_lock(:clave)"), {"clave": self._clave}
        ).scalar_one()
        return bool(obtenido)

    def liberar(self) -> None:
        self._connection.execute(text("SELECT pg_advisory_unlock(:clave)"), {"clave": self._clave})


class PgBloqueoMigracion(_PgBloqueoConsultivo):
    """Implementa ``BloqueoMigracion`` con un bloqueo consultivo de sesion de PostgreSQL."""

    _clave = CLAVE_BLOQUEO_MIGRACION


class PgBloqueoReentrenamiento(_PgBloqueoConsultivo):
    """Implementa ``BloqueoReentrenamiento`` (clave propia, distinta de la migracion)."""

    _clave = CLAVE_BLOQUEO_REENTRENAMIENTO
