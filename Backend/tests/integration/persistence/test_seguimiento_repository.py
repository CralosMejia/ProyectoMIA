"""Consultas de alertas de seguimiento contra PostgreSQL real (R-011 T2, decision (a)).

Transaccion externa con rollback (``db_session``): la base queda como estaba. Aislamiento
entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00). Datos 100 % ficticios.
"""

import inspect
from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.application.gestiones.ports import ConteoAlertas, LectorSeguimiento
from app.domain.common.enums import NivelRiesgo, Plan
from app.domain.gestiones.alertas import GrupoAlerta, rango_de
from app.infrastructure.persistence.repositories import seguimiento as modulo
from app.infrastructure.persistence.repositories.seguimiento import (
    SqlAlchemyLectorSeguimiento,
    SqlAlchemySeguimientoRepository,
)
from tests.integration.retencion_datos import HOY, VENCIMIENTO, sembrar_seguimiento

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(db_session: Session) -> SqlAlchemySeguimientoRepository:
    return SqlAlchemySeguimientoRepository(db_session)


def test_contar_datos_conocidos_devuelve_vencidas_hoy_y_proximas(
    db_session: Session, repo: SqlAlchemySeguimientoRepository
) -> None:
    sembrar_seguimiento(db_session.connection())

    assert repo.contar(HOY) == ConteoAlertas(vencidas=2, hoy=1, proximas=2)


def test_contar_sin_gestiones_devuelve_ceros(repo: SqlAlchemySeguimientoRepository) -> None:
    assert repo.contar(HOY) == ConteoAlertas(vencidas=0, hoy=0, proximas=0)


def test_listar_hoy_devuelve_solo_la_pendiente_no_borrada_con_sus_datos(
    db_session: Session, repo: SqlAlchemySeguimientoRepository
) -> None:
    datos = sembrar_seguimiento(db_session.connection())

    filas = repo.listar(*rango_de(GrupoAlerta.HOY, HOY))

    assert len(filas) == 1
    fila = filas[0]
    assert fila.id == datos.hoy
    assert fila.prediccion_id == datos.hoy_prediccion
    assert fila.socio_nombre == "Socio Ficticio"
    assert fila.celular == "0990000000"
    assert fila.plan is Plan.MENSUAL
    assert fila.fecha_vencimiento == VENCIMIENTO
    assert fila.fecha_seguimiento == HOY
    assert fila.nivel_riesgo is NivelRiesgo.ALTO
    assert fila.campania_nombre == "Campaña congelada"
    assert fila.responsable == "Responsable ficticio"


def test_listar_vencidas_sin_limite_inferior_ordena_por_fecha_e_id(
    db_session: Session, repo: SqlAlchemySeguimientoRepository
) -> None:
    datos = sembrar_seguimiento(db_session.connection())

    filas = repo.listar(*rango_de(GrupoAlerta.VENCIDAS, HOY))

    assert [f.id for f in filas] == list(datos.vencidas)
    assert [f.fecha_seguimiento for f in filas] == [date(2026, 9, 20), date(2026, 9, 29)]


def test_listar_proximas_incluye_extremos_y_excluye_fuera_de_ventana(
    db_session: Session, repo: SqlAlchemySeguimientoRepository
) -> None:
    datos = sembrar_seguimiento(db_session.connection())

    filas = repo.listar(*rango_de(GrupoAlerta.PROXIMAS, HOY))

    assert [f.id for f in filas] == list(datos.proximas)
    assert datos.fuera_de_ventana not in [f.id for f in filas]


def test_listar_misma_fecha_ordena_por_id(
    db_session: Session, repo: SqlAlchemySeguimientoRepository
) -> None:
    sembrar_seguimiento(db_session.connection())

    filas = repo.listar(None, date(2026, 12, 31))

    claves = [(f.fecha_seguimiento, f.id) for f in filas]
    assert claves == sorted(claves)
    assert len(filas) == 6


def test_lector_sin_datos_cumple_el_puerto_y_cuenta_ceros(migrated_engine: Engine) -> None:
    lector = SqlAlchemyLectorSeguimiento(migrated_engine)

    assert isinstance(lector, LectorSeguimiento)
    assert lector.contar(HOY) == ConteoAlertas(vencidas=0, hoy=0, proximas=0)
    assert lector.listar(None, HOY) == []


def test_modulo_no_confirma_ni_usa_sql_interpolado() -> None:
    fuente = inspect.getsource(modulo)

    assert ".commit(" not in fuente
    assert 'f"' not in fuente
    assert "text(" not in fuente
