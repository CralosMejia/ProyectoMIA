"""Repositorio de gestiones y unidad de trabajo de retencion contra PostgreSQL real (R-009 T11).

El repositorio escribe dentro de la transaccion de quien llama y nunca la confirma: las
pruebas del repositorio usan ``db_session`` (transaccion externa con rollback). Las de la
unidad de trabajo confirman datos reales y los borran al terminar. Aislamiento entre
usuarios: no aplica (RT-12, sin login; acceso por IP, CU-00). Datos 100 % ficticios.
"""

import inspect
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Connection, Engine, event, text
from sqlalchemy.orm import Session

from app.application.gestiones.ports import GestionRepository, NuevaGestion, ResultadoGestion
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan, Respuesta
from app.domain.gestiones.errores import GestionDuplicadaError
from app.infrastructure.persistence.repositories import gestiones as modulo_repositorio
from app.infrastructure.persistence.repositories.gestiones import SqlAlchemyGestionRepository
from app.infrastructure.persistence.unit_of_work_retencion import (
    SqlAlchemyUnidadDeTrabajoRetencion,
)
from tests.integration.persistence.test_migrations import insert, membresia, modelo, socio

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
HOY = date(2026, 9, 29)
VENCIMIENTO = date(2026, 10, 5)


class RelojAjustable:
    def __init__(self) -> None:
        self.instante = INSTANTE

    def now(self) -> datetime:
        return self.instante


@dataclass(frozen=True)
class Escenario:
    """Una membresia ficticia en dos listas (dos predicciones del mismo ciclo)."""

    membresia_id: int
    prediccion_1: int
    prediccion_2: int
    campania_id: int
    modelo_version: int


def _lista(conexion: Connection, version: int) -> int:
    return insert(
        conexion,
        "listas_priorizadas",
        {
            "modelo_id": modelo(conexion, version=version),
            "fecha_generacion": HOY,
            "horizonte_dias": 30,
            "top_k": 10,
            "creada_en": INSTANTE,
            "nombre": "Lista ficticia",
        },
    )


def _prediccion(conexion: Connection, lista_id: int, membresia_id: int, score: str) -> int:
    return insert(
        conexion,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "score": score,
            "nivel_riesgo": "ALTO",
            "factores_principales": "[]",
            "prioridad": 3,
            "dentro_top_k": True,
        },
    )


def crear_escenario(conexion: Connection, version: int = 8101) -> Escenario:
    socio_id = socio(conexion, nombre="Socio Ficticio", nombre_normalizado="SOCIO FICTICIO")
    membresia_id = membresia(
        conexion, socio_id=socio_id, plan="MENSUAL", fecha_vencimiento=VENCIMIENTO
    )
    prediccion_1 = _prediccion(conexion, _lista(conexion, version), membresia_id, "0.81000000")
    prediccion_2 = _prediccion(conexion, _lista(conexion, version + 1), membresia_id, "0.70000000")
    campania_id = insert(
        conexion,
        "campanias",
        {
            "nombre": "Campaña ficticia",
            "activa": True,
            "niveles_riesgo": ["ALTO"],
            "planes": ["MENSUAL"],
            "prioridad": 1,
            "es_ejemplo": False,
        },
    )
    return Escenario(membresia_id, prediccion_1, prediccion_2, campania_id, version)


def nueva(
    escenario: Escenario, *, prediccion_id: int | None = None, con_campania: bool = True
) -> NuevaGestion:
    return NuevaGestion(
        prediccion_id=prediccion_id or escenario.prediccion_1,
        membresia_id=escenario.membresia_id,
        campania_id=escenario.campania_id if con_campania else None,
        campania_nombre="Campaña ficticia" if con_campania else None,
        fecha_asignacion=HOY,
        fecha_seguimiento=date(2026, 10, 30),
        responsable="Responsable ficticio",
    )


@pytest.fixture
def reloj() -> RelojAjustable:
    return RelojAjustable()


@pytest.fixture
def repo(db_session: Session, reloj: RelojAjustable) -> SqlAlchemyGestionRepository:
    return SqlAlchemyGestionRepository(db_session, reloj)


@pytest.fixture
def escenario(db_session: Session) -> Escenario:
    return crear_escenario(db_session.connection())


def marcas(session: Session, gestion_id: int) -> dict[str, object]:
    return dict(
        session.execute(
            text(
                "SELECT created_at, updated_at, deleted_at, estado, campania_nombre "
                "FROM gestiones_retencion WHERE id = :id"
            ),
            {"id": gestion_id},
        )
        .mappings()
        .one()
    )


# ------------------------------------------------------------------ repositorio
def test_implementa_el_puerto(repo: SqlAlchemyGestionRepository) -> None:
    assert isinstance(repo, GestionRepository)


def test_datos_prediccion_devuelve_ciclo_modelo_y_socio(
    repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    datos = repo.datos_prediccion(escenario.prediccion_1)

    assert datos is not None
    assert datos.prediccion_id == escenario.prediccion_1
    assert datos.membresia_id == escenario.membresia_id
    assert datos.fecha_vencimiento == VENCIMIENTO
    assert datos.nivel_riesgo is NivelRiesgo.ALTO
    assert datos.plan is Plan.MENSUAL
    assert datos.score == Decimal("0.81000000")
    assert datos.modelo_version == escenario.modelo_version
    assert datos.socio_nombre == "Socio Ficticio"


def test_datos_prediccion_inexistente_devuelve_none(repo: SqlAlchemyGestionRepository) -> None:
    assert repo.datos_prediccion(999_999) is None


def test_crear_guarda_con_marcas_del_reloj_y_obtener_devuelve_el_detalle(
    db_session: Session, repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario))

    guardada = marcas(db_session, gestion_id)
    assert guardada["created_at"] == INSTANTE
    assert guardada["updated_at"] == INSTANTE
    assert guardada["deleted_at"] is None
    detalle = repo.obtener(gestion_id)
    assert detalle is not None
    assert detalle.id == gestion_id
    assert detalle.prediccion_id == escenario.prediccion_1
    assert detalle.membresia_id == escenario.membresia_id
    assert detalle.socio_nombre == "Socio Ficticio"
    assert detalle.plan is Plan.MENSUAL
    assert detalle.fecha_vencimiento == VENCIMIENTO
    assert detalle.modelo_version == escenario.modelo_version
    assert detalle.score == Decimal("0.81000000")
    assert detalle.nivel_riesgo is NivelRiesgo.ALTO
    assert detalle.campania_id == escenario.campania_id
    assert detalle.campania_nombre == "Campaña ficticia"
    assert detalle.estado is EstadoGestion.PENDIENTE
    assert detalle.fecha_asignacion == HOY
    assert detalle.creada_en == INSTANTE
    assert detalle.fecha_seguimiento == date(2026, 10, 30)
    assert detalle.responsable == "Responsable ficticio"
    assert detalle.contactado is None
    assert detalle.campania_ofrecida is None
    assert detalle.cerrada_en is None
    assert repo.existe_para_membresia(escenario.membresia_id) is True


def test_crear_sin_campania_deja_nombre_nulo(
    repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario, con_campania=False))

    detalle = repo.obtener(gestion_id)
    assert detalle is not None
    assert detalle.campania_id is None
    assert detalle.campania_nombre is None


def test_existe_para_membresia_sin_gestion_es_false(
    repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    assert repo.existe_para_membresia(escenario.membresia_id) is False


def test_obtener_conserva_el_nombre_original_tras_renombrar_e_inactivar_la_campania(
    db_session: Session, repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario))
    db_session.execute(
        text("UPDATE campanias SET nombre = 'Otro nombre', activa = false WHERE id = :id"),
        {"id": escenario.campania_id},
    )

    detalle = repo.obtener(gestion_id)

    assert detalle is not None
    assert detalle.campania_nombre == "Campaña ficticia"
    assert detalle.campania_id == escenario.campania_id


def test_lecturas_ignoran_gestiones_con_deleted_at(
    db_session: Session, repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario))
    db_session.execute(
        text("UPDATE gestiones_retencion SET deleted_at = :t WHERE id = :id"),
        {"t": INSTANTE, "id": gestion_id},
    )

    assert repo.obtener(gestion_id) is None
    assert repo.obtener_para_actualizar(gestion_id) is None
    assert repo.existe_para_membresia(escenario.membresia_id) is False


def test_obtener_inexistente_devuelve_none(repo: SqlAlchemyGestionRepository) -> None:
    assert repo.obtener(999_999) is None
    assert repo.obtener_para_actualizar(999_999) is None


def test_obtener_para_actualizar_emite_for_update(
    db_session: Session, repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario))
    sentencias: list[str] = []

    def capturar(_conn: object, _cur: object, sql: str, *_: object) -> None:
        sentencias.append(sql)

    conexion = db_session.connection()
    event.listen(conexion, "before_cursor_execute", capturar)
    try:
        detalle = repo.obtener_para_actualizar(gestion_id)
    finally:
        event.remove(conexion, "before_cursor_execute", capturar)

    assert detalle == repo.obtener(gestion_id)
    assert any("FOR UPDATE" in s for s in sentencias)


def test_obtener_no_bloquea(
    db_session: Session, repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario))
    sentencias: list[str] = []

    def capturar(_conn: object, _cur: object, sql: str, *_: object) -> None:
        sentencias.append(sql)

    conexion = db_session.connection()
    event.listen(conexion, "before_cursor_execute", capturar)
    try:
        repo.obtener(gestion_id)
    finally:
        event.remove(conexion, "before_cursor_execute", capturar)

    assert sentencias
    assert not any("FOR UPDATE" in s for s in sentencias)


def test_guardar_resultado_reemplaza_campos_estado_cierre_y_updated_at(
    db_session: Session,
    repo: SqlAlchemyGestionRepository,
    escenario: Escenario,
    reloj: RelojAjustable,
) -> None:
    gestion_id = repo.crear(nueva(escenario))
    reloj.instante = INSTANTE + timedelta(hours=2)

    repo.guardar_resultado(
        gestion_id,
        ResultadoGestion(
            contactado=True,
            campania_ofrecida=Respuesta.SI,
            campania_aceptada=Respuesta.NO,
            renovo_declarado=Respuesta.NO,
            fecha_contacto=HOY,
            observaciones="Observacion ficticia",
            responsable="Otro responsable",
            fecha_seguimiento=date(2026, 10, 30),
            estado=EstadoGestion.CERRADA,
            cerrada_en=reloj.instante,
        ),
    )

    detalle = repo.obtener(gestion_id)
    assert detalle is not None
    assert detalle.contactado is True
    assert detalle.campania_ofrecida is Respuesta.SI
    assert detalle.campania_aceptada is Respuesta.NO
    assert detalle.renovo_declarado is Respuesta.NO
    assert detalle.fecha_contacto == HOY
    assert detalle.observaciones == "Observacion ficticia"
    assert detalle.responsable == "Otro responsable"
    assert detalle.estado is EstadoGestion.CERRADA
    assert detalle.cerrada_en == INSTANTE + timedelta(hours=2)
    guardada = marcas(db_session, gestion_id)
    assert guardada["created_at"] == INSTANTE
    assert guardada["updated_at"] == INSTANTE + timedelta(hours=2)
    assert guardada["campania_nombre"] == "Campaña ficticia"


def test_guardar_resultado_pendiente_cambia_fecha_de_seguimiento(
    repo: SqlAlchemyGestionRepository, escenario: Escenario
) -> None:
    gestion_id = repo.crear(nueva(escenario, con_campania=False))

    repo.guardar_resultado(
        gestion_id,
        ResultadoGestion(
            contactado=False,
            campania_ofrecida=Respuesta.NO_APLICA,
            campania_aceptada=Respuesta.NO_APLICA,
            renovo_declarado=Respuesta.PENDIENTE,
            fecha_contacto=None,
            observaciones=None,
            responsable=None,
            fecha_seguimiento=date(2026, 10, 27),
            estado=EstadoGestion.PENDIENTE,
            cerrada_en=None,
        ),
    )

    detalle = repo.obtener(gestion_id)
    assert detalle is not None
    assert detalle.estado is EstadoGestion.PENDIENTE
    assert detalle.fecha_seguimiento == date(2026, 10, 27)
    assert detalle.responsable is None
    assert detalle.cerrada_en is None


def test_no_existe_metodo_de_borrado() -> None:
    publicos = {n for n in dir(SqlAlchemyGestionRepository) if not n.startswith("_")}
    assert publicos == {
        "datos_prediccion",
        "existe_para_membresia",
        "crear",
        "obtener",
        "obtener_para_actualizar",
        "guardar_resultado",
    }


def test_repositorio_no_confirma_la_transaccion() -> None:
    fuente = inspect.getsource(modulo_repositorio)
    assert ".commit(" not in fuente
    assert ".rollback(" not in fuente


# ------------------------------------------------------------------ unidad de trabajo
@pytest.fixture
def escenario_confirmado(migrated_engine: Engine) -> Iterator[Escenario]:
    """Escenario confirmado en la base; al terminar se borra todo lo que creo la prueba."""
    with migrated_engine.begin() as conexion:
        datos = crear_escenario(conexion, version=8201)
    try:
        yield datos
    finally:
        with migrated_engine.begin() as conexion:
            ids = {"m": datos.membresia_id, "c": datos.campania_id}
            fila = conexion.execute(
                text("SELECT socio_id, carga_id FROM membresias WHERE id = :m"), ids
            ).one()
            listas = conexion.execute(
                text("SELECT lista_id FROM predicciones WHERE membresia_id = :m"), ids
            ).scalars()
            listas_ids = list(listas)
            conexion.execute(text("DELETE FROM gestiones_retencion WHERE membresia_id = :m"), ids)
            conexion.execute(text("DELETE FROM predicciones WHERE membresia_id = :m"), ids)
            modelos = conexion.execute(
                text("SELECT modelo_id FROM listas_priorizadas WHERE id = ANY(:l)"),
                {"l": listas_ids},
            ).scalars()
            modelos_ids = list(modelos)
            conexion.execute(
                text("DELETE FROM listas_priorizadas WHERE id = ANY(:l)"), {"l": listas_ids}
            )
            conexion.execute(text("DELETE FROM modelos WHERE id = ANY(:i)"), {"i": modelos_ids})
            conexion.execute(text("DELETE FROM campanias WHERE id = :c"), ids)
            conexion.execute(text("DELETE FROM membresias WHERE id = :m"), ids)
            conexion.execute(text("DELETE FROM socios WHERE id = :s"), {"s": fila.socio_id})
            conexion.execute(text("DELETE FROM cargas WHERE id = :k"), {"k": fila.carga_id})


def _gestiones_de(engine: Engine, membresia_id: int) -> list[int]:
    with engine.connect() as conexion:
        return list(
            conexion.execute(
                text("SELECT prediccion_id FROM gestiones_retencion WHERE membresia_id = :m"),
                {"m": membresia_id},
            ).scalars()
        )


def test_uow_segunda_gestion_del_mismo_ciclo_desde_otra_lista_es_duplicada(
    escenario_confirmado: Escenario, migrated_engine: Engine
) -> None:
    uow = SqlAlchemyUnidadDeTrabajoRetencion(migrated_engine, RelojAjustable())
    with uow() as ctx:
        ctx.gestiones.crear(nueva(escenario_confirmado))
        ctx.commit()

    with pytest.raises(GestionDuplicadaError), uow() as ctx:
        ctx.gestiones.crear(
            nueva(escenario_confirmado, prediccion_id=escenario_confirmado.prediccion_2)
        )
        ctx.commit()

    assert _gestiones_de(migrated_engine, escenario_confirmado.membresia_id) == [
        escenario_confirmado.prediccion_1
    ]


def test_uow_sin_commit_no_guarda_la_gestion(
    escenario_confirmado: Escenario, migrated_engine: Engine
) -> None:
    uow = SqlAlchemyUnidadDeTrabajoRetencion(migrated_engine, RelojAjustable())
    with uow() as ctx:
        ctx.gestiones.crear(nueva(escenario_confirmado))
        assert ctx.campanias.obtener(escenario_confirmado.campania_id) is not None

    assert _gestiones_de(migrated_engine, escenario_confirmado.membresia_id) == []
