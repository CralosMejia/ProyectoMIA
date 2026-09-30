"""Repositorio SQLAlchemy de listas priorizadas y predicciones (CU-04, CU-05).

Escribe siempre dentro de la transaccion de la ``Session`` recibida (unit of work): quien
llama la abre y decide si confirma o revierte; aqui no se controla la transaccion. Las
predicciones se insertan en bloque (``insert()`` con lista de parametros, executemany),
nunca fila a fila. ``creada_en``, ``created_at`` y ``updated_at`` salen del ``Clock``.

Lecturas con SQLAlchemy Core (joins con ``modelos``, ``membresias`` y ``socios``). Una lista
es una instantanea inmutable (RN-04.5, RT-07): sus items se leen **sin** filtrar
``deleted_at`` de la membresia o del socio, para que un borrado logico posterior no altere
una lista ya generada. ``listas_priorizadas`` y ``predicciones`` no tienen ``deleted_at``.
"""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import Row, func, insert, select
from sqlalchemy.orm import Session

from app.application.listas.ports import (
    ItemLista,
    ListaDetalle,
    ListaResumen,
    NuevaLista,
    NuevaPrediccion,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import NivelRiesgo, Plan
from app.infrastructure.persistence.models.historial import Carga, Membresia, Socio
from app.infrastructure.persistence.models.modelo import Modelo
from app.infrastructure.persistence.models.retencion import ListaPriorizada, Prediccion


def _vencimiento(valor: date | None) -> date:
    # Solo entran en una lista membresias con vencimiento (cartera en el horizonte).
    if valor is None:
        raise ValueError("una prediccion guardada apunta a una membresia sin vencimiento")
    return valor


def _item(fila: Row[tuple[object, ...]]) -> ItemLista:
    m = fila._mapping
    return ItemLista(
        prediccion_id=m["prediccion_id"],
        membresia_id=m["membresia_id"],
        socio_id=m["socio_id"],
        prioridad=m["prioridad"],
        socio_nombre=m["socio_nombre"],
        celular=m["celular"],
        cedula=m["cedula"],
        plan=Plan(m["plan"]),
        fecha_vencimiento=_vencimiento(m["fecha_vencimiento"]),
        monto_cobrado=m["monto_cobrado"],
        score=m["score"],
        nivel_riesgo=NivelRiesgo(m["nivel_riesgo"]),
        factores_principales=[str(f) for f in m["factores_principales"]],
        dentro_top_k=m["dentro_top_k"],
    )


class SqlAlchemyListaRepository:
    """Implementa ``ListaRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def crear(self, lista: NuevaLista, predicciones: Sequence[NuevaPrediccion]) -> int:
        ahora = self._clock.now()
        marcas = {"created_at": ahora, "updated_at": ahora}
        lista_id = self._session.scalars(
            insert(ListaPriorizada)
            .values(
                modelo_id=lista.modelo_id,
                fecha_generacion=lista.fecha_generacion,
                horizonte_dias=lista.horizonte_dias,
                top_k=lista.top_k,
                creada_en=ahora,
                **marcas,
            )
            .returning(ListaPriorizada.id)
        ).one()
        if predicciones:
            parametros = [
                {
                    "lista_id": lista_id,
                    "membresia_id": p.membresia_id,
                    "socio_id": p.socio_id,
                    "score": p.score,
                    "nivel_riesgo": p.nivel_riesgo,
                    "factores_principales": list(p.factores_principales),
                    "prioridad": p.prioridad,
                    "dentro_top_k": p.dentro_top_k,
                    **marcas,
                }
                for p in predicciones
            ]
            self._session.execute(insert(Prediccion), parametros)
        return lista_id

    def obtener(self, lista_id: int) -> ListaDetalle | None:
        cabecera = self._session.execute(
            select(
                ListaPriorizada.id,
                ListaPriorizada.modelo_id,
                Modelo.version,
                ListaPriorizada.fecha_generacion,
                ListaPriorizada.creada_en,
                ListaPriorizada.horizonte_dias,
                ListaPriorizada.top_k,
                Modelo.umbral_alto,
                Modelo.umbral_medio,
            )
            .join(Modelo, Modelo.id == ListaPriorizada.modelo_id)
            .where(ListaPriorizada.id == lista_id)
        ).one_or_none()
        if cabecera is None:
            return None
        filas = self._session.execute(
            select(
                Prediccion.id.label("prediccion_id"),
                Prediccion.membresia_id,
                Prediccion.socio_id,
                Prediccion.prioridad,
                Socio.nombre.label("socio_nombre"),
                Socio.celular,
                Socio.cedula,
                Membresia.plan,
                Membresia.fecha_vencimiento,
                Membresia.monto_cobrado,
                Prediccion.score,
                Prediccion.nivel_riesgo,
                Prediccion.factores_principales,
                Prediccion.dentro_top_k,
            )
            .join(Membresia, Membresia.id == Prediccion.membresia_id)
            .join(Socio, Socio.id == Membresia.socio_id)
            .where(Prediccion.lista_id == lista_id)
            .order_by(Prediccion.prioridad, Prediccion.id)
        ).all()
        return ListaDetalle(
            id=cabecera.id,
            modelo_id=cabecera.modelo_id,
            modelo_version=cabecera.version,
            fecha_generacion=cabecera.fecha_generacion,
            creada_en=cabecera.creada_en,
            horizonte_dias=cabecera.horizonte_dias,
            top_k=cabecera.top_k,
            umbral_alto=cabecera.umbral_alto,
            umbral_medio=cabecera.umbral_medio,
            items=tuple(_item(fila) for fila in filas),
        )

    def ultima(self) -> ListaDetalle | None:
        lista_id = self._session.scalars(
            select(ListaPriorizada.id)
            .order_by(ListaPriorizada.creada_en.desc(), ListaPriorizada.id.desc())
            .limit(1)
        ).one_or_none()
        return None if lista_id is None else self.obtener(lista_id)

    def listar(self) -> list[ListaResumen]:
        total = func.count(Prediccion.id)
        filas = self._session.execute(
            select(
                ListaPriorizada.id,
                ListaPriorizada.fecha_generacion,
                ListaPriorizada.creada_en,
                Modelo.version,
                ListaPriorizada.horizonte_dias,
                ListaPriorizada.top_k,
                total.label("total_items"),
            )
            .join(Modelo, Modelo.id == ListaPriorizada.modelo_id)
            .outerjoin(Prediccion, Prediccion.lista_id == ListaPriorizada.id)
            .group_by(ListaPriorizada.id, Modelo.version)
            .order_by(ListaPriorizada.creada_en.desc(), ListaPriorizada.id.desc())
        ).all()
        return [
            ListaResumen(
                id=f.id,
                fecha_generacion=f.fecha_generacion,
                creada_en=f.creada_en,
                modelo_version=f.version,
                horizonte_dias=f.horizonte_dias,
                top_k=f.top_k,
                total_items=f.total_items,
            )
            for f in filas
        ]


class SqlAlchemyFechasCarga:
    """Implementa ``FechasCarga`` (advertencia de datos antiguos, CU-04)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ultima_fecha_carga_hasta(self, instante: datetime) -> datetime | None:
        return self._session.scalar(
            select(func.max(Carga.fecha_carga)).where(
                Carga.deleted_at.is_(None), Carga.fecha_carga <= instante
            )
        )
