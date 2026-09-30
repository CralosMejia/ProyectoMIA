"""Repositorio SQLAlchemy de gestiones de retencion (CU-08, CU-10).

Escribe dentro de la transaccion de la ``Session`` recibida (unit of work): nunca hace
``commit`` ni ``rollback``. ``created_at``/``updated_at`` salen del ``Clock``. Toda lectura
ignora las gestiones con ``deleted_at``; no hay borrado (una gestion solo cambia de estado).
Escrituras con el ORM; lecturas con ``select`` parametrizado.

Los datos de la prediccion (score, nivel, version del modelo, plan, vencimiento y socio) se
leen **sin** filtrar ``deleted_at`` de la membresia o del socio: la prediccion es una
instantanea (RT-07). El nombre de la campana sale de la instantanea
``gestiones_retencion.campania_nombre`` (RN-08.2), no de ``campanias``.
"""

from datetime import date
from typing import Any

from sqlalchemy import Select, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.gestiones.ports import (
    DatosPrediccionGestion,
    GestionDetalle,
    NuevaGestion,
    ResultadoGestion,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan, Respuesta
from app.infrastructure.persistence.models.historial import Membresia, Socio
from app.infrastructure.persistence.models.modelo import Modelo
from app.infrastructure.persistence.models.retencion import (
    GestionRetencion,
    ListaPriorizada,
    Prediccion,
)

INDICE_GESTION_POR_CICLO = "ux_gestiones_retencion_membresia_id"


def es_gestion_duplicada(error: IntegrityError) -> bool:
    """``True`` si el error es la violacion del indice unico de una gestion por ciclo."""
    diagnostico = getattr(error.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None) == INDICE_GESTION_POR_CICLO


def _vencimiento(valor: date | None) -> date:
    # Solo entran en una lista membresias con vencimiento (cartera en el horizonte).
    if valor is None:
        raise ValueError("una prediccion guardada apunta a una membresia sin vencimiento")
    return valor


def _respuesta(valor: str | None) -> Respuesta | None:
    return None if valor is None else Respuesta(valor)


_DATOS_PREDICCION = (
    Prediccion.id.label("prediccion_id"),
    Prediccion.membresia_id,
    Membresia.fecha_vencimiento,
    Prediccion.nivel_riesgo,
    Membresia.plan,
    Prediccion.score,
    Modelo.version.label("modelo_version"),
    Socio.nombre.label("socio_nombre"),
)


def _con_prediccion(consulta: Select[Any]) -> Select[Any]:
    return (
        consulta.join(ListaPriorizada, ListaPriorizada.id == Prediccion.lista_id)
        .join(Modelo, Modelo.id == ListaPriorizada.modelo_id)
        .join(Membresia, Membresia.id == Prediccion.membresia_id)
        .join(Socio, Socio.id == Membresia.socio_id)
    )


def _consulta_detalle(gestion_id: int) -> Select[Any]:
    return _con_prediccion(
        select(
            GestionRetencion,
            Prediccion.nivel_riesgo,
            Prediccion.score,
            Membresia.plan,
            Membresia.fecha_vencimiento,
            Modelo.version.label("modelo_version"),
            Socio.nombre.label("socio_nombre"),
        ).join(Prediccion, Prediccion.id == GestionRetencion.prediccion_id)
    ).where(GestionRetencion.id == gestion_id, GestionRetencion.deleted_at.is_(None))


class SqlAlchemyGestionRepository:
    """Implementa ``GestionRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def datos_prediccion(self, prediccion_id: int) -> DatosPrediccionGestion | None:
        fila = self._session.execute(
            _con_prediccion(select(*_DATOS_PREDICCION)).where(Prediccion.id == prediccion_id)
        ).one_or_none()
        if fila is None:
            return None
        return DatosPrediccionGestion(
            prediccion_id=fila.prediccion_id,
            membresia_id=fila.membresia_id,
            fecha_vencimiento=_vencimiento(fila.fecha_vencimiento),
            nivel_riesgo=NivelRiesgo(fila.nivel_riesgo),
            plan=Plan(fila.plan),
            score=fila.score,
            modelo_version=fila.modelo_version,
            socio_nombre=fila.socio_nombre,
        )

    def existe_para_membresia(self, membresia_id: int) -> bool:
        return bool(
            self._session.scalar(
                select(
                    exists().where(
                        GestionRetencion.membresia_id == membresia_id,
                        GestionRetencion.deleted_at.is_(None),
                    )
                )
            )
        )

    def crear(self, nueva: NuevaGestion) -> int:
        ahora = self._clock.now()
        fila = GestionRetencion(
            prediccion_id=nueva.prediccion_id,
            membresia_id=nueva.membresia_id,
            campania_id=nueva.campania_id,
            campania_nombre=nueva.campania_nombre,
            fecha_asignacion=nueva.fecha_asignacion,
            fecha_seguimiento=nueva.fecha_seguimiento,
            estado=nueva.estado.value,
            responsable=nueva.responsable,
            created_at=ahora,
            updated_at=ahora,
        )
        self._session.add(fila)
        # El INSERT se envia aqui: la unidad de trabajo traduce la violacion del indice unico.
        self._session.flush()
        return fila.id

    def obtener(self, gestion_id: int) -> GestionDetalle | None:
        return self._detalle(_consulta_detalle(gestion_id))

    def obtener_para_actualizar(self, gestion_id: int) -> GestionDetalle | None:
        # Solo se bloquea la fila de la gestion, no las de la prediccion, socio o modelo.
        return self._detalle(_consulta_detalle(gestion_id).with_for_update(of=GestionRetencion))

    def guardar_resultado(self, gestion_id: int, resultado: ResultadoGestion) -> None:
        fila = self._session.scalars(
            select(GestionRetencion).where(
                GestionRetencion.id == gestion_id, GestionRetencion.deleted_at.is_(None)
            )
        ).one()
        fila.contactado = resultado.contactado
        fila.campania_ofrecida = resultado.campania_ofrecida.value
        fila.campania_aceptada = resultado.campania_aceptada.value
        fila.renovo_declarado = resultado.renovo_declarado.value
        fila.fecha_contacto = resultado.fecha_contacto
        fila.observaciones = resultado.observaciones
        fila.responsable = resultado.responsable
        fila.fecha_seguimiento = resultado.fecha_seguimiento
        fila.estado = resultado.estado.value
        fila.cerrada_en = resultado.cerrada_en
        fila.updated_at = self._clock.now()
        self._session.flush()

    def _detalle(self, consulta: Select[Any]) -> GestionDetalle | None:
        fila = self._session.execute(consulta).one_or_none()
        if fila is None:
            return None
        g: GestionRetencion = fila.GestionRetencion
        return GestionDetalle(
            id=g.id,
            prediccion_id=g.prediccion_id,
            membresia_id=g.membresia_id,
            socio_nombre=fila.socio_nombre,
            plan=Plan(fila.plan),
            fecha_vencimiento=_vencimiento(fila.fecha_vencimiento),
            modelo_version=fila.modelo_version,
            score=fila.score,
            nivel_riesgo=NivelRiesgo(fila.nivel_riesgo),
            campania_id=g.campania_id,
            campania_nombre=g.campania_nombre,
            estado=EstadoGestion(g.estado),
            fecha_asignacion=g.fecha_asignacion,
            creada_en=g.created_at,
            fecha_seguimiento=g.fecha_seguimiento,
            responsable=g.responsable,
            contactado=g.contactado,
            campania_ofrecida=_respuesta(g.campania_ofrecida),
            campania_aceptada=_respuesta(g.campania_aceptada),
            renovo_declarado=_respuesta(g.renovo_declarado),
            fecha_contacto=g.fecha_contacto,
            observaciones=g.observaciones,
            cerrada_en=g.cerrada_en,
        )
