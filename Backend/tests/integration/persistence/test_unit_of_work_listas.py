"""Unidad de trabajo de listas y lectura de la ultima carga contra PostgreSQL real.

Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso por IP, CU-00).
Datos 100 % sinteticos.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.application.historial.ports import NuevaCarga
from app.application.listas.ports import FechasCarga
from app.domain.common.enums import TipoCarga
from app.infrastructure.persistence.repositories.historial import SqlAlchemyCargaRepository
from app.infrastructure.persistence.repositories.listas import SqlAlchemyFechasCarga
from app.infrastructure.persistence.unit_of_work_listas import SqlAlchemyUnidadDeTrabajoListas

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class Reloj:
    def now(self) -> datetime:
        return INSTANTE


def carga(fecha: datetime) -> NuevaCarga:
    return NuevaCarga(
        tipo=TipoCarga.PLANTILLA,
        fecha_carga=fecha,
        nombre_archivo="plantilla sintetica.xlsx",
        filas_leidas=1,
        filas_guardadas=1,
        filas_duplicadas=0,
        socios_enlazados=0,
    )


@pytest.fixture
def sin_cargas(migrated_engine: Engine) -> Iterator[Engine]:
    def limpiar() -> None:
        with migrated_engine.begin() as conexion:
            conexion.execute(text("TRUNCATE cargas RESTART IDENTITY CASCADE"))

    limpiar()
    try:
        yield migrated_engine
    finally:
        limpiar()


def test_ultima_fecha_carga_hasta_ignores_later_and_deleted_loads(db_session: Session) -> None:
    repo = SqlAlchemyCargaRepository(db_session, Reloj())
    repo.crear(carga(datetime(2026, 7, 1, tzinfo=UTC)))
    repo.crear(carga(datetime(2026, 9, 5, tzinfo=UTC)))
    borrada = repo.crear(carga(datetime(2026, 8, 15, tzinfo=UTC)))
    db_session.execute(
        text("UPDATE cargas SET deleted_at = :d WHERE id = :id"), {"d": INSTANTE, "id": borrada}
    )
    fechas = SqlAlchemyFechasCarga(db_session)

    assert isinstance(fechas, FechasCarga)
    assert fechas.ultima_fecha_carga_hasta(INSTANTE) == datetime(2026, 7, 1, tzinfo=UTC)
    assert fechas.ultima_fecha_carga_hasta(datetime(2026, 6, 1, tzinfo=UTC)) is None


def test_unit_of_work_without_commit_rolls_back(sin_cargas: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoListas(sin_cargas, Reloj())
    with uow() as contexto:
        contexto.estado.obtener()
        SqlAlchemyCargaRepository(contexto.listas._session, Reloj()).crear(carga(INSTANTE))  # type: ignore[attr-defined]  # acceso de prueba a la sesion compartida

    with uow() as contexto:
        assert contexto.cargas.ultima_fecha_carga_hasta(INSTANTE) is None


def test_unit_of_work_commit_persists(sin_cargas: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoListas(sin_cargas, Reloj())
    with uow() as contexto:
        SqlAlchemyCargaRepository(contexto.listas._session, Reloj()).crear(carga(INSTANTE))  # type: ignore[attr-defined]  # acceso de prueba a la sesion compartida
        contexto.commit()

    with uow() as contexto:
        assert contexto.cargas.ultima_fecha_carga_hasta(INSTANTE) == INSTANTE
