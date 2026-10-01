"""Lecturas de las alertas de seguimiento (CU-09, decision (a) de R-011).

Solo lectura con ``select`` parametrizado (sin f-strings ni concatenacion). Cuentan y se
listan solo las gestiones ``estado = 'PENDIENTE'`` con ``deleted_at IS NULL``: una gestion
sin campana nace ``CERRADA`` y queda fuera. Los rangos de cada grupo salen del dominio
(``rango_de``), no se repiten aqui.

``SqlAlchemySeguimientoRepository`` trabaja sobre la ``Session`` recibida y nunca hace
``commit``; ``SqlAlchemyLectorSeguimiento`` abre una ``Session`` corta por llamada (mismo
patron que el lector del estado del sistema) y siempre la revierte.

Los datos de la prediccion (socio, plan, vencimiento, nivel) se leen sin filtrar el borrado
de la membresia o del socio: la prediccion es una instantanea (RT-07), igual que en el
repositorio de gestiones.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from sqlalchemy import ColumnElement, Engine, and_, func, select
from sqlalchemy.orm import Session

from app.application.gestiones.ports import ConteoAlertas, GestionPendienteResumen
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan
from app.domain.gestiones.alertas import GrupoAlerta, rango_de
from app.infrastructure.persistence.models.historial import Membresia, Socio
from app.infrastructure.persistence.models.retencion import GestionRetencion, Prediccion

_PENDIENTE_NO_BORRADA = (
    GestionRetencion.estado == EstadoGestion.PENDIENTE.value,
    GestionRetencion.deleted_at.is_(None),
)


def _en_rango(desde: date | None, hasta: date) -> ColumnElement[bool]:
    condiciones: list[ColumnElement[bool]] = [GestionRetencion.fecha_seguimiento <= hasta]
    if desde is not None:
        condiciones.append(GestionRetencion.fecha_seguimiento >= desde)
    return and_(*condiciones)


def _conteo(grupo: GrupoAlerta, hoy: date) -> ColumnElement[int]:
    desde, hasta = rango_de(grupo, hoy)
    return func.count(GestionRetencion.id).filter(_en_rango(desde, hasta))


def _vencimiento(valor: date | None) -> date:
    # Solo entran en una lista membresias con vencimiento (cartera en el horizonte).
    if valor is None:
        raise ValueError("una gestion apunta a una membresia sin vencimiento")
    return valor


class SqlAlchemySeguimientoRepository:
    """Consultas de seguimiento dentro de la ``Session`` de quien llama (sin ``commit``)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def contar(self, hoy: date) -> ConteoAlertas:
        fila = self._session.execute(
            select(
                _conteo(GrupoAlerta.VENCIDAS, hoy).label("vencidas"),
                _conteo(GrupoAlerta.HOY, hoy).label("hoy"),
                _conteo(GrupoAlerta.PROXIMAS, hoy).label("proximas"),
            ).where(*_PENDIENTE_NO_BORRADA)
        ).one()
        return ConteoAlertas(vencidas=fila.vencidas, hoy=fila.hoy, proximas=fila.proximas)

    def listar(self, desde: date | None, hasta: date) -> list[GestionPendienteResumen]:
        filas = self._session.execute(
            select(
                GestionRetencion.id,
                GestionRetencion.prediccion_id,
                Socio.nombre.label("socio_nombre"),
                Socio.celular,
                Membresia.plan,
                Membresia.fecha_vencimiento,
                GestionRetencion.fecha_seguimiento,
                Prediccion.nivel_riesgo,
                GestionRetencion.campania_nombre,
                GestionRetencion.responsable,
            )
            .join(Prediccion, Prediccion.id == GestionRetencion.prediccion_id)
            .join(Membresia, Membresia.id == GestionRetencion.membresia_id)
            .join(Socio, Socio.id == Membresia.socio_id)
            .where(*_PENDIENTE_NO_BORRADA, _en_rango(desde, hasta))
            .order_by(GestionRetencion.fecha_seguimiento, GestionRetencion.id)
        ).all()
        return [
            GestionPendienteResumen(
                id=fila.id,
                prediccion_id=fila.prediccion_id,
                socio_nombre=fila.socio_nombre,
                celular=fila.celular,
                plan=Plan(fila.plan),
                fecha_vencimiento=_vencimiento(fila.fecha_vencimiento),
                fecha_seguimiento=fila.fecha_seguimiento,
                nivel_riesgo=NivelRiesgo(fila.nivel_riesgo),
                campania_nombre=fila.campania_nombre,
                responsable=fila.responsable,
            )
            for fila in filas
        ]


class SqlAlchemyLectorSeguimiento:
    """Implementa ``LectorSeguimiento`` con una ``Session`` corta de solo lectura."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def _repositorio(self) -> Iterator[SqlAlchemySeguimientoRepository]:
        with Session(self._engine) as session:
            try:
                yield SqlAlchemySeguimientoRepository(session)
            finally:
                session.rollback()

    def contar(self, hoy: date) -> ConteoAlertas:
        with self._repositorio() as repositorio:
            return repositorio.contar(hoy)

    def listar(self, desde: date | None, hasta: date) -> list[GestionPendienteResumen]:
        with self._repositorio() as repositorio:
            return repositorio.listar(desde, hasta)
