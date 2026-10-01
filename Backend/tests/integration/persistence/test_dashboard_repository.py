"""Consultas del dashboard contra PostgreSQL real (R-011 T15, decision (c)).

Transaccion externa con rollback (``db_session``): la base queda como estaba. Aislamiento
entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00). Datos 100 % ficticios.
"""

import inspect
import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.application.dashboard.ports import FilaCampania, FilaEmbudo, LectorDashboard
from app.domain.common.enums import Plan
from app.infrastructure.persistence.repositories import dashboard as modulo
from app.infrastructure.persistence.repositories.dashboard import (
    SqlAlchemyDashboardRepository,
    SqlAlchemyLectorDashboard,
)
from tests.integration.persistence.test_migrations import membresia, modelo
from tests.integration.retencion_datos import sembrar_dashboard

pytestmark = pytest.mark.integration

SEPTIEMBRE = (datetime(2026, 9, 1, 5, tzinfo=UTC), datetime(2026, 10, 1, 5, tzinfo=UTC))
OCTUBRE = (datetime(2026, 10, 1, 5, tzinfo=UTC), datetime(2026, 11, 1, 5, tzinfo=UTC))
AGOSTO = (datetime(2026, 8, 1, 5, tzinfo=UTC), datetime(2026, 9, 1, 5, tzinfo=UTC))


@pytest.fixture
def repo(db_session: Session) -> SqlAlchemyDashboardRepository:
    return SqlAlchemyDashboardRepository(db_session)


def test_embudo_septiembre_cuenta_solo_con_campania_y_sin_nulos(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    sembrar_dashboard(db_session.connection())

    assert repo.embudo(*SEPTIEMBRE) == FilaEmbudo(
        asignadas=21, contactadas=17, ofrecidas=11, aceptadas=7, renovaron=7
    )


def test_por_campania_septiembre_ordena_y_deja_sin_campania_al_final(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    datos = sembrar_dashboard(db_session.connection())

    assert repo.por_campania(*SEPTIEMBRE) == [
        FilaCampania(datos.campania_a, "Zeta renovacion", 12, 8, 4, 10),
        FilaCampania(datos.campania_b, "alfa fidelizacion", 9, 9, 3, 9),
        FilaCampania(None, None, 3, 0, 0, 0),
    ]


def test_por_campania_mismo_numero_de_gestiones_ordena_por_nombre_sin_mayusculas(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    datos = sembrar_dashboard(db_session.connection())
    db_session.execute(
        text(
            "UPDATE gestiones_retencion SET deleted_at = now() WHERE id IN ("
            "SELECT id FROM gestiones_retencion WHERE campania_id = :a AND estado = 'PENDIENTE')"
        ),
        {"a": datos.campania_a},
    )
    db_session.execute(
        text(
            "UPDATE gestiones_retencion SET deleted_at = now() WHERE id = ("
            "SELECT min(id) FROM gestiones_retencion WHERE campania_id = :a "
            "AND deleted_at IS NULL AND renovo_declarado = 'NO')"
        ),
        {"a": datos.campania_a},
    )

    filas = repo.por_campania(*SEPTIEMBRE)

    assert [(f.nombre, f.gestiones) for f in filas] == [
        ("alfa fidelizacion", 9),
        ("Zeta renovacion", 9),
        (None, 3),
    ]


def test_frontera_de_mes_usa_la_fecha_de_negocio(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    datos = sembrar_dashboard(db_session.connection())

    octubre = repo.por_campania(*OCTUBRE)

    # Solo la gestion de A del 10 de octubre; la creada el 2026-10-01 03:00Z es de septiembre.
    assert octubre == [FilaCampania(datos.campania_a, "Zeta renovacion", 1, 1, 1, 1)]
    assert repo.embudo(*OCTUBRE).asignadas == 1


def test_mes_sin_gestiones_devuelve_ceros_y_lista_vacia(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    sembrar_dashboard(db_session.connection())

    assert repo.embudo(*AGOSTO) == FilaEmbudo(0, 0, 0, 0, 0)
    assert repo.por_campania(*AGOSTO) == []


def test_por_campania_usa_el_nombre_actual_de_la_campania(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    datos = sembrar_dashboard(db_session.connection())
    db_session.execute(
        text("UPDATE campanias SET nombre = 'Nombre nuevo' WHERE id = :b"), {"b": datos.campania_b}
    )

    nombres = [f.nombre for f in repo.por_campania(*SEPTIEMBRE)]

    assert nombres == ["Zeta renovacion", "Nombre nuevo", None]


def test_modelo_vigente_lee_fecha_corte_de_la_metadata(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    assert repo.modelo_vigente() is None
    conexion = db_session.connection()
    modelo(conexion, version=1, vigente=False, metadata_tecnica="{}")
    modelo(
        conexion,
        version=2,
        vigente=True,
        ciclos_entrenamiento=321,
        metadata_tecnica=json.dumps({"fecha_corte": "2026-08-31"}),
    )

    vigente = repo.modelo_vigente()

    assert vigente is not None
    assert vigente.version == 2
    assert vigente.ciclos_entrenamiento == 321
    assert vigente.fecha_corte == date(2026, 8, 31)


def test_modelo_vigente_sin_fecha_corte_devuelve_none_en_ese_campo(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    modelo(db_session.connection(), version=1, vigente=True, metadata_tecnica="{}")

    vigente = repo.modelo_vigente()

    assert vigente is not None
    assert vigente.fecha_corte is None


def test_proxima_fecha_reentrenamiento_lee_estado_sistema(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    db_session.execute(
        text("UPDATE estado_sistema SET proxima_fecha_reentrenamiento = '2027-03-29' WHERE id = 1")
    )

    assert repo.proxima_fecha_reentrenamiento() == date(2027, 3, 29)


def test_ciclos_excluye_membresias_borradas_y_calcula_duracion(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    conexion = db_session.connection()
    viva = membresia(
        conexion,
        plan="TRIMESTRAL",
        fecha_inicio=date(2026, 6, 1),
        fecha_vencimiento=date(2026, 8, 30),
        fecha_actividad=date(2026, 6, 1),
    )
    membresia(conexion, deleted_at=datetime(2026, 9, 1, tzinfo=UTC))

    ciclos = repo.ciclos()

    assert [c.ref for c in ciclos] == [viva]
    assert ciclos[0].plan is Plan.TRIMESTRAL
    assert ciclos[0].duracion_dias == 90
    assert ciclos[0].excluido is False
    assert ciclos[0].no_renovo is None


def test_lector_sin_datos_cumple_el_puerto(migrated_engine: Engine) -> None:
    lector = SqlAlchemyLectorDashboard(migrated_engine)

    assert isinstance(lector, LectorDashboard)
    assert lector.embudo(*SEPTIEMBRE) == FilaEmbudo(0, 0, 0, 0, 0)
    assert lector.por_campania(*SEPTIEMBRE) == []


def test_modulo_no_confirma_ni_usa_sql_interpolado() -> None:
    fuente = inspect.getsource(modulo)

    assert ".commit(" not in fuente
    assert 'f"' not in fuente
    assert "text(" not in fuente
