"""Repositorios SQLAlchemy del historial: ``socios``, ``membresias`` y ``cargas``.

Escriben siempre dentro de la transaccion de la ``Session`` recibida (unit of work): quien
llama la abre y decide si confirma o revierte; aqui no se controla la transaccion. Las
inserciones masivas usan ``insert()`` con lista de parametros (executemany /
*insertmanyvalues*), nunca ``session.add`` fila a fila. ``created_at``/``updated_at`` salen
del ``Clock`` inyectado.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.application.historial.ports import (
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    ReferenciaOrigen,
)
from app.domain.common.clock import Clock
from app.infrastructure.persistence.models.historial import Carga, Membresia, Socio


def _marcas(instante: datetime) -> dict[str, datetime]:
    return {"created_at": instante, "updated_at": instante}


def _referencia(referencia: ReferenciaOrigen | None) -> dict[str, object] | None:
    if referencia is None:
        return None
    return {"anio": referencia.anio, "hoja": referencia.hoja, "fila": referencia.fila}


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
