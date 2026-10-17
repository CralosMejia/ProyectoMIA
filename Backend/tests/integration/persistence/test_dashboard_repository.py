"""Consultas del dashboard contra PostgreSQL real (R-011 T15, decision (c)).

Transaccion externa con rollback (``db_session``): la base queda como estaba. Aislamiento
entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00). Datos 100 % ficticios.
"""

import inspect
import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import Session

from app.application.dashboard.ports import (
    FilaCampania,
    FilaEmbudo,
    LectorDashboard,
    MontoMembresia,
)
from app.domain.common.enums import Plan
from app.infrastructure.persistence.repositories import dashboard as modulo
from app.infrastructure.persistence.repositories.dashboard import (
    SqlAlchemyDashboardRepository,
    SqlAlchemyLectorDashboard,
)
from tests.integration.persistence.test_migrations import carga, insert, membresia, modelo
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


# ------------------------------------------------------------- indicadores del piloto (R-018)


def _lista(conexion: Connection, fecha: date, creada: datetime, nombre: str) -> int:
    return insert(
        conexion,
        "listas_priorizadas",
        {
            "modelo_id": modelo(conexion, version=9300 + fecha.toordinal() % 1000 + creada.hour),
            "fecha_generacion": fecha,
            "horizonte_dias": 30,
            "top_k": 10,
            "creada_en": creada,
            "nombre": nombre,
        },
    )


def _prediccion(conexion: Connection, lista_id: int, membresia_id: int, prioridad: int) -> int:
    return insert(
        conexion,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "score": "0.80000000",
            "nivel_riesgo": "ALTO",
            "factores_principales": "[]",
            "prioridad": prioridad,
            "dentro_top_k": prioridad <= 10,
        },
    )


def _gestion(
    conexion: Connection,
    prediccion_id: int,
    membresia_id: int,
    *,
    contactado: bool | None,
    fecha_contacto: date | None,
    borrada: bool = False,
) -> int:
    return insert(
        conexion,
        "gestiones_retencion",
        {
            "prediccion_id": prediccion_id,
            "membresia_id": membresia_id,
            "fecha_asignacion": date(2026, 9, 1),
            "fecha_seguimiento": date(2026, 9, 1),
            "estado": "PENDIENTE",
            "contactado": contactado,
            "fecha_contacto": fecha_contacto,
            "deleted_at": datetime(2026, 9, 2, tzinfo=UTC) if borrada else None,
        },
    )


def test_lista_piloto_devuelve_la_ultima_del_mes_con_su_top_25(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    c = db_session.connection()
    temprana = _lista(c, date(2026, 9, 5), datetime(2026, 9, 5, 15, tzinfo=UTC), "Sep A")
    mismo_dia_1 = _lista(c, date(2026, 9, 20), datetime(2026, 9, 20, 14, tzinfo=UTC), "Sep B")
    ultima = _lista(c, date(2026, 9, 20), datetime(2026, 9, 20, 16, tzinfo=UTC), "Sep C")
    _lista(c, date(2026, 10, 1), datetime(2026, 10, 1, 15, tzinfo=UTC), "Oct")
    membresias = [membresia(c, fecha_vencimiento=date(2026, 10, 5)) for _ in range(4)]
    for lista_id in (temprana, mismo_dia_1):
        _prediccion(c, lista_id, membresias[0], 1)
    _prediccion(c, ultima, membresias[0], 25)
    _prediccion(c, ultima, membresias[1], 3)
    _prediccion(c, ultima, membresias[2], 26)  # fuera del top 25
    _prediccion(c, ultima, membresias[3], 1)

    resultado = repo.lista_piloto(date(2026, 9, 1), date(2026, 9, 30))

    assert resultado is not None
    assert (resultado.id, resultado.nombre) == (ultima, "Sep C")
    assert resultado.fecha_generacion == date(2026, 9, 20)
    assert [(f.membresia_id, f.prioridad) for f in resultado.filas] == [
        (membresias[3], 1),
        (membresias[1], 3),
        (membresias[0], 25),
    ]
    assert all(f.contactado is None and f.fecha_contacto is None for f in resultado.filas)


def test_lista_piloto_mes_sin_listas_devuelve_none(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    _lista(db_session.connection(), date(2026, 10, 1), datetime(2026, 10, 1, tzinfo=UTC), "Oct")

    assert repo.lista_piloto(date(2026, 9, 1), date(2026, 9, 30)) is None


def test_lista_piloto_toma_el_contacto_de_la_gestion_no_borrada_del_ciclo(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    c = db_session.connection()
    anterior = _lista(c, date(2026, 8, 20), datetime(2026, 8, 20, tzinfo=UTC), "Ago")
    lista_id = _lista(c, date(2026, 9, 20), datetime(2026, 9, 20, tzinfo=UTC), "Sep")
    propia, desde_otra, borrada, sin_gestion = (
        membresia(c, fecha_vencimiento=date(2026, 10, 5)) for _ in range(4)
    )
    p1 = _prediccion(c, lista_id, propia, 1)
    _gestion(c, p1, propia, contactado=True, fecha_contacto=date(2026, 9, 25))
    _prediccion(c, lista_id, desde_otra, 2)
    p_otra = _prediccion(c, anterior, desde_otra, 1)
    _gestion(c, p_otra, desde_otra, contactado=False, fecha_contacto=date(2026, 9, 1))
    p3 = _prediccion(c, lista_id, borrada, 3)
    _gestion(c, p3, borrada, contactado=True, fecha_contacto=date(2026, 9, 1), borrada=True)
    _prediccion(c, lista_id, sin_gestion, 4)

    resultado = repo.lista_piloto(date(2026, 9, 1), date(2026, 9, 30))

    assert resultado is not None
    assert [(f.contactado, f.fecha_contacto) for f in resultado.filas] == [
        (True, date(2026, 9, 25)),
        (False, date(2026, 9, 1)),
        (None, None),
        (None, None),
    ]


def test_montos_devuelve_decimales_exactos_e_ignora_borradas(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    c = db_session.connection()
    cobrada = membresia(c, monto_cobrado="40.1234", monto_facturado="45.0000")
    facturada = membresia(c, monto_facturado="35.5000")
    sin_monto = membresia(c)
    borrada = membresia(c, monto_cobrado="99.0000", deleted_at=datetime(2026, 9, 1, tzinfo=UTC))

    montos = repo.montos([cobrada, facturada, sin_monto, borrada])

    assert montos == {
        cobrada: MontoMembresia(Decimal("40.1234"), Decimal("45.0000")),
        facturada: MontoMembresia(None, Decimal("35.5000")),
        sin_monto: MontoMembresia(None, None),
    }
    assert isinstance(montos[cobrada].monto_cobrado, Decimal)
    assert repo.montos([]) == {}


def test_ultima_carga_plantilla_es_la_no_borrada_mas_reciente(
    db_session: Session, repo: SqlAlchemyDashboardRepository
) -> None:
    db_session.execute(text("UPDATE cargas SET deleted_at = now() WHERE deleted_at IS NULL"))
    assert repo.ultima_carga_plantilla() is None
    c = db_session.connection()
    carga(c, fecha_carga=datetime(2026, 9, 10, tzinfo=UTC))
    carga(c, fecha_carga=datetime(2026, 9, 29, 15, tzinfo=UTC))
    carga(
        c,
        fecha_carga=datetime(2026, 9, 30, tzinfo=UTC),
        deleted_at=datetime(2026, 9, 30, tzinfo=UTC),
    )
    carga(c, tipo="MIGRACION_HISTORICA", fecha_carga=datetime(2026, 10, 1, tzinfo=UTC))

    assert repo.ultima_carga_plantilla() == datetime(2026, 9, 29, 15, tzinfo=UTC)


def test_lector_lee_el_piloto_con_sesion_corta(migrated_engine: Engine) -> None:
    lector = SqlAlchemyLectorDashboard(migrated_engine)

    assert lector.lista_piloto(date(1990, 1, 1), date(1990, 1, 31)) is None
    assert lector.montos([-1]) == {}
    lector.ultima_carga_plantilla()


def test_consultas_del_piloto_no_tocan_socios() -> None:
    fuente = "".join(
        inspect.getsource(getattr(SqlAlchemyDashboardRepository, nombre))
        for nombre in ("lista_piloto", "montos", "ultima_carga_plantilla")
    )

    assert "Socio" not in fuente
    assert "socio_id" not in fuente


def test_modulo_no_confirma_ni_usa_sql_interpolado() -> None:
    fuente = inspect.getsource(modulo)

    assert ".commit(" not in fuente
    assert 'f"' not in fuente
    assert "text(" not in fuente
