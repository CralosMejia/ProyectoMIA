"""Repositorios SQLAlchemy del historial: ``socios``, ``membresias`` y ``cargas``.

Escriben siempre dentro de la transaccion de la ``Session`` recibida (unit of work): quien
llama la abre y decide si confirma o revierte; aqui no se controla la transaccion. Las
inserciones masivas usan ``insert()`` con lista de parametros (executemany /
*insertmanyvalues*), nunca ``session.add`` fila a fila. ``created_at``/``updated_at`` salen
del ``Clock`` inyectado.

Las lecturas (``listar_para_prediccion``, ``listar_para_entrenamiento``,
``ultima_fecha_carga``, ``hay_migracion_o_membresias``) usan SQLAlchemy Core en una sola
consulta cada una y filtran siempre ``deleted_at IS NULL``.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import exists, func, insert, or_, select
from sqlalchemy.orm import Session

from app.application.historial.ports import (
    MembresiaParaPrediccion,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    ReferenciaOrigen,
)
from app.application.modelo.ports import MembresiaParaEntrenamiento
from app.domain.common.clock import Clock
from app.domain.common.enums import FormaPago, Plan, TipoCarga
from app.infrastructure.persistence.models.historial import Carga, Membresia, Socio


def _marcas(instante: datetime) -> dict[str, datetime]:
    return {"created_at": instante, "updated_at": instante}


def _referencia(referencia: ReferenciaOrigen | None) -> dict[str, object] | None:
    if referencia is None:
        return None
    return {"anio": referencia.anio, "hoja": referencia.hoja, "fila": referencia.fila}


def listar_membresias_para_entrenamiento(session: Session) -> list[MembresiaParaEntrenamiento]:
    """Membresias no borradas, ordenadas por id, con su ``created_at`` (CU-02 y CU-11)."""
    filas = session.execute(
        select(
            Membresia.id,
            Membresia.socio_id,
            Membresia.plan,
            Membresia.forma_pago,
            Membresia.fecha_inicio,
            Membresia.fecha_vencimiento,
            Membresia.fecha_actividad,
            Membresia.monto_cobrado,
            Membresia.inicio_aproximado,
            Membresia.created_at,
        )
        .where(Membresia.deleted_at.is_(None))
        .order_by(Membresia.id)
    ).all()
    return [
        MembresiaParaEntrenamiento(
            membresia_id=f.id,
            socio_id=f.socio_id,
            plan=Plan(f.plan),
            forma_pago=FormaPago(f.forma_pago),
            fecha_inicio=f.fecha_inicio,
            fecha_vencimiento=f.fecha_vencimiento,
            fecha_actividad=f.fecha_actividad,
            monto_cobrado=f.monto_cobrado,
            inicio_aproximado=f.inicio_aproximado,
            registrada_en=f.created_at,
        )
        for f in filas
    ]


class SqlAlchemySocioRepository:
    """Implementa ``SocioRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def insertar_en_bloque(self, socios: Sequence[NuevoSocio]) -> list[int]:
        if not socios:
            return []
        marcas = _marcas(self._clock.now())
        parametros = [
            {
                "cedula": socio.cedula,
                "nombre": socio.nombre,
                "nombre_normalizado": socio.nombre_normalizado,
                "celular": socio.celular,
                "correo": socio.correo,
                **marcas,
            }
            for socio in socios
        ]
        sentencia = insert(Socio).returning(Socio.id, sort_by_parameter_order=True)
        return list(self._session.scalars(sentencia, parametros))


class SqlAlchemyMembresiaRepository:
    """Implementa ``MembresiaRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def insertar_en_bloque(self, membresias: Sequence[NuevaMembresia]) -> int:
        if not membresias:
            return 0
        marcas = _marcas(self._clock.now())
        parametros = [
            {
                "socio_id": m.socio_id,
                "carga_id": m.carga_id,
                "estado_registro": m.estado_registro,
                "plan": m.plan,
                "fecha_inicio": m.fecha_inicio,
                "fecha_vencimiento": m.fecha_vencimiento,
                "fecha_actividad": m.fecha_actividad,
                "forma_pago": m.forma_pago,
                "monto_facturado": m.monto_facturado,
                "monto_cobrado": m.monto_cobrado,
                "asistencias": m.asistencias,
                "observaciones": m.observaciones,
                "origen": m.origen,
                "referencia_origen": _referencia(m.referencia_origen),
                "plan_original": m.plan_original,
                "forma_pago_original": m.forma_pago_original,
                "inicio_aproximado": m.inicio_aproximado,
                **marcas,
            }
            for m in membresias
        ]
        self._session.execute(insert(Membresia), parametros)
        return len(parametros)

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        filas = self._session.execute(
            select(
                Membresia.id,
                Membresia.socio_id,
                Membresia.plan,
                Membresia.forma_pago,
                Membresia.fecha_inicio,
                Membresia.fecha_vencimiento,
                Membresia.fecha_actividad,
                Membresia.monto_cobrado,
                Membresia.inicio_aproximado,
                Socio.cedula.is_not(None).label("socio_con_cedula"),
            )
            .join(Socio, Socio.id == Membresia.socio_id)
            .where(Membresia.deleted_at.is_(None))
            .order_by(Membresia.id)
        ).all()
        return [
            MembresiaParaPrediccion(
                membresia_id=f.id,
                socio_id=f.socio_id,
                plan=Plan(f.plan),
                forma_pago=FormaPago(f.forma_pago),
                fecha_inicio=f.fecha_inicio,
                fecha_vencimiento=f.fecha_vencimiento,
                fecha_actividad=f.fecha_actividad,
                monto_cobrado=f.monto_cobrado,
                inicio_aproximado=f.inicio_aproximado,
                socio_con_cedula=bool(f.socio_con_cedula),
            )
            for f in filas
        ]

    def listar_para_entrenamiento(self) -> list[MembresiaParaEntrenamiento]:
        return listar_membresias_para_entrenamiento(self._session)


class SqlAlchemyCargaRepository:
    """Implementa ``CargaRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def crear(self, carga: NuevaCarga) -> int:
        sentencia = (
            insert(Carga)
            .values(
                tipo=carga.tipo,
                fecha_carga=carga.fecha_carga,
                nombre_archivo=carga.nombre_archivo,
                filas_leidas=carga.filas_leidas,
                filas_guardadas=carga.filas_guardadas,
                filas_duplicadas=carga.filas_duplicadas,
                socios_enlazados=carga.socios_enlazados,
                **_marcas(self._clock.now()),
            )
            .returning(Carga.id)
        )
        return self._session.scalars(sentencia).one()

    def ultima_fecha_carga(self) -> datetime | None:
        return self._session.scalar(
            select(func.max(Carga.fecha_carga)).where(Carga.deleted_at.is_(None))
        )

    def hay_migracion_o_membresias(self) -> bool:
        migracion = exists().where(
            Carga.tipo == TipoCarga.MIGRACION_HISTORICA, Carga.deleted_at.is_(None)
        )
        membresias = exists().where(Membresia.deleted_at.is_(None))
        return bool(self._session.scalar(select(or_(migracion, membresias))))
