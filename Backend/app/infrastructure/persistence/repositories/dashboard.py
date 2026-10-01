"""Lecturas del dashboard de retencion (CU-11, decision (c) de R-011).

Solo lectura con ``select`` parametrizado (sin f-strings ni concatenacion). El mes llega como
rango de instantes ``[desde, hasta)`` y se aplica sobre ``gestiones_retencion.created_at``
(instante de asignacion); las gestiones con ``deleted_at`` no cuentan. Los conteos usan
``count(*) FILTER (WHERE ...)``: un nulo nunca cumple la condicion, asi que nunca cuenta.

``SqlAlchemyDashboardRepository`` trabaja sobre la ``Session`` recibida y nunca hace
``commit``; ``SqlAlchemyLectorDashboard`` abre una ``Session`` corta por llamada y siempre la
revierte (mismo patron que el lector del estado del sistema).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime

from sqlalchemy import ColumnElement, Engine, func, select
from sqlalchemy.orm import Session

from app.application.dashboard.ports import FilaCampania, FilaEmbudo, ModeloDashboard
from app.application.modelo.mapeo import ciclo_de_membresia
from app.domain.common.enums import Respuesta
from app.domain.modelo.variables import CicloModelo
from app.infrastructure.persistence.models.modelo import EstadoSistema, Modelo
from app.infrastructure.persistence.models.retencion import Campania, GestionRetencion
from app.infrastructure.persistence.repositories.historial import (
    listar_membresias_para_entrenamiento,
)

_G = GestionRetencion
_CON_RESULTADO = (Respuesta.SI.value, Respuesta.NO.value)


def _del_mes(desde: datetime, hasta: datetime) -> tuple[ColumnElement[bool], ...]:
    return (_G.deleted_at.is_(None), _G.created_at >= desde, _G.created_at < hasta)


def _contar(condicion: ColumnElement[bool]) -> ColumnElement[int]:
    return func.count().filter(condicion)


def _fecha(valor: object) -> date | None:
    return date.fromisoformat(valor) if isinstance(valor, str) and valor else None


class SqlAlchemyDashboardRepository:
    """Consultas del dashboard dentro de la ``Session`` de quien llama (sin ``commit``)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def embudo(self, desde: datetime, hasta: datetime) -> FilaEmbudo:
        fila = self._session.execute(
            select(
                func.count().label("asignadas"),
                _contar(_G.contactado.is_(True)).label("contactadas"),
                _contar(_G.campania_ofrecida == Respuesta.SI.value).label("ofrecidas"),
                _contar(_G.campania_aceptada == Respuesta.SI.value).label("aceptadas"),
                _contar(_G.renovo_declarado == Respuesta.SI.value).label("renovaron"),
            ).where(*_del_mes(desde, hasta), _G.campania_id.is_not(None))
        ).one()
        return FilaEmbudo(
            asignadas=fila.asignadas,
            contactadas=fila.contactadas,
            ofrecidas=fila.ofrecidas,
            aceptadas=fila.aceptadas,
            renovaron=fila.renovaron,
        )

    def por_campania(self, desde: datetime, hasta: datetime) -> list[FilaCampania]:
        gestiones = func.count().label("gestiones")
        filas = self._session.execute(
            select(
                _G.campania_id,
                Campania.nombre,
                gestiones,
                _contar(_G.contactado.is_(True)).label("contactados"),
                _contar(_G.renovo_declarado == Respuesta.SI.value).label("renovaciones"),
                _contar(_G.renovo_declarado.in_(_CON_RESULTADO)).label("gestiones_cerradas"),
            )
            .outerjoin(Campania, Campania.id == _G.campania_id)
            .where(*_del_mes(desde, hasta))
            .group_by(_G.campania_id, Campania.nombre)
            .order_by(
                _G.campania_id.is_(None),
                gestiones.desc(),
                func.lower(Campania.nombre),
                _G.campania_id,
            )
        ).all()
        return [
            FilaCampania(
                campania_id=f.campania_id,
                nombre=f.nombre,
                gestiones=f.gestiones,
                contactados=f.contactados,
                renovaciones=f.renovaciones,
                gestiones_cerradas=f.gestiones_cerradas,
            )
            for f in filas
        ]

    def modelo_vigente(self) -> ModeloDashboard | None:
        # Solo columnas ligeras: el artefacto puede pesar varios MB.
        fila = self._session.execute(
            select(
                Modelo.version,
                Modelo.fecha_entrenamiento,
                Modelo.ciclos_entrenamiento,
                Modelo.metadata_tecnica["fecha_corte"].astext.label("fecha_corte"),
            ).where(Modelo.vigente.is_(True))
        ).one_or_none()
        if fila is None:
            return None
        return ModeloDashboard(
            version=fila.version,
            fecha_entrenamiento=fila.fecha_entrenamiento,
            ciclos_entrenamiento=fila.ciclos_entrenamiento,
            fecha_corte=_fecha(fila.fecha_corte),
        )

    def proxima_fecha_reentrenamiento(self) -> date | None:
        return self._session.scalar(select(EstadoSistema.proxima_fecha_reentrenamiento))

    def ciclos(self) -> list[CicloModelo]:
        # Misma lectura y conversion que el reentrenamiento (CU-02): un solo criterio.
        return [ciclo_de_membresia(m) for m in listar_membresias_para_entrenamiento(self._session)]


class SqlAlchemyLectorDashboard:
    """Implementa ``LectorDashboard`` con una ``Session`` corta de solo lectura por llamada."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def _repositorio(self) -> Iterator[SqlAlchemyDashboardRepository]:
        with Session(self._engine) as session:
            try:
                yield SqlAlchemyDashboardRepository(session)
            finally:
                session.rollback()

    def embudo(self, desde: datetime, hasta: datetime) -> FilaEmbudo:
        with self._repositorio() as repositorio:
            return repositorio.embudo(desde, hasta)

    def por_campania(self, desde: datetime, hasta: datetime) -> list[FilaCampania]:
        with self._repositorio() as repositorio:
            return repositorio.por_campania(desde, hasta)

    def modelo_vigente(self) -> ModeloDashboard | None:
        with self._repositorio() as repositorio:
            return repositorio.modelo_vigente()

    def proxima_fecha_reentrenamiento(self) -> date | None:
        with self._repositorio() as repositorio:
            return repositorio.proxima_fecha_reentrenamiento()

    def ciclos(self) -> list[CicloModelo]:
        with self._repositorio() as repositorio:
            return repositorio.ciclos()
