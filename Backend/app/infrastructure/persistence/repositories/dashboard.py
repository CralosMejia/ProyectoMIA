"""Lecturas del dashboard de retencion (CU-11, decision (c) de R-011).

Solo lectura con ``select`` parametrizado (sin f-strings ni concatenacion). El mes llega como
rango de instantes ``[desde, hasta)`` y se aplica sobre ``gestiones_retencion.created_at``
(instante de asignacion); las gestiones con ``deleted_at`` no cuentan. Los conteos usan
``count(*) FILTER (WHERE ...)``: un nulo nunca cumple la condicion, asi que nunca cuenta.

``SqlAlchemyDashboardRepository`` trabaja sobre la ``Session`` recibida y nunca hace
``commit``; ``SqlAlchemyLectorDashboard`` abre una ``Session`` corta por llamada y siempre la
revierte (mismo patron que el lector del estado del sistema).

Indicadores del piloto (M04, R-018): la lista del mes, sus filas del top 25 con el contacto de
la gestion no borrada del mismo ciclo, los montos exactos de las membresias de renovacion y la
ultima carga por plantilla. Ninguna consulta toca ``socios`` ni devuelve datos personales.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime

from sqlalchemy import ColumnElement, Engine, and_, func, select
from sqlalchemy.orm import Session

from app.application.dashboard.ports import (
    FilaCampania,
    FilaEmbudo,
    FilaPiloto,
    ListaPiloto,
    ModeloDashboard,
    MontoMembresia,
)
from app.application.modelo.mapeo import ciclo_de_membresia
from app.domain.common.enums import Respuesta, TipoCarga
from app.domain.modelo.piloto import TOP_PILOTO
from app.domain.modelo.variables import CicloModelo
from app.infrastructure.persistence.models.historial import Carga, Membresia
from app.infrastructure.persistence.models.modelo import EstadoSistema, Modelo
from app.infrastructure.persistence.models.retencion import (
    Campania,
    GestionRetencion,
    ListaPriorizada,
    Prediccion,
)
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

    def lista_piloto(self, desde: date, hasta: date) -> ListaPiloto | None:
        lista = self._session.execute(
            select(ListaPriorizada.id, ListaPriorizada.nombre, ListaPriorizada.fecha_generacion)
            .where(
                ListaPriorizada.fecha_generacion >= desde,
                ListaPriorizada.fecha_generacion <= hasta,
            )
            .order_by(
                ListaPriorizada.fecha_generacion.desc(),
                ListaPriorizada.creada_en.desc(),
                ListaPriorizada.id.desc(),
            )
            .limit(1)
        ).one_or_none()
        if lista is None:
            return None
        # Una gestion no borrada por ciclo (RN-08.1): el contacto cuenta venga de la lista que
        # venga.
        filas = self._session.execute(
            select(Prediccion.membresia_id, Prediccion.prioridad, _G.contactado, _G.fecha_contacto)
            .outerjoin(
                _G, and_(_G.membresia_id == Prediccion.membresia_id, _G.deleted_at.is_(None))
            )
            .where(Prediccion.lista_id == lista.id, Prediccion.prioridad <= TOP_PILOTO)
            .order_by(Prediccion.prioridad, Prediccion.id)
        ).all()
        return ListaPiloto(
            id=lista.id,
            nombre=lista.nombre,
            fecha_generacion=lista.fecha_generacion,
            filas=tuple(
                FilaPiloto(
                    membresia_id=f.membresia_id,
                    prioridad=f.prioridad,
                    contactado=f.contactado,
                    fecha_contacto=f.fecha_contacto,
                )
                for f in filas
            ),
        )

    def montos(self, ids: Sequence[int]) -> dict[int, MontoMembresia]:
        if not ids:
            return {}
        filas = self._session.execute(
            select(Membresia.id, Membresia.monto_cobrado, Membresia.monto_facturado).where(
                Membresia.id.in_(list(ids)), Membresia.deleted_at.is_(None)
            )
        ).all()
        return {
            f.id: MontoMembresia(monto_cobrado=f.monto_cobrado, monto_facturado=f.monto_facturado)
            for f in filas
        }

    def ultima_carga_plantilla(self) -> datetime | None:
        return self._session.scalar(
            select(func.max(Carga.fecha_carga)).where(
                Carga.tipo == TipoCarga.PLANTILLA.value, Carga.deleted_at.is_(None)
            )
        )


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

    def lista_piloto(self, desde: date, hasta: date) -> ListaPiloto | None:
        with self._repositorio() as repositorio:
            return repositorio.lista_piloto(desde, hasta)

    def montos(self, ids: Sequence[int]) -> dict[int, MontoMembresia]:
        with self._repositorio() as repositorio:
            return repositorio.montos(ids)

    def ultima_carga_plantilla(self) -> datetime | None:
        with self._repositorio() as repositorio:
            return repositorio.ultima_carga_plantilla()
