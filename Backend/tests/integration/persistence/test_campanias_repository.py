"""Repositorio de campanas y perfil de prediccion contra PostgreSQL real (R-009 T7).

El repositorio escribe dentro de la transaccion de quien llama y nunca la confirma: cada
prueba usa ``db_session`` (transaccion externa con rollback). La base esta en ``head``, con
las 3 campanas de ejemplo de ``0007``; las pruebas que necesitan un conjunto exacto las
inactivan o las cuentan dentro de su transaccion. Aislamiento entre usuarios: no aplica
(RT-12, sin login; acceso restringido por IP, CU-00). Datos 100 % ficticios.
"""

import inspect
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.application.campanias.ports import CampaniaRepository, PerfilPrediccion
from app.domain.campanias.campania import DatosCampania
from app.domain.common.enums import NivelRiesgo, Plan
from app.infrastructure.persistence.repositories import campanias as modulo_repositorio
from app.infrastructure.persistence.repositories.campanias import (
    SqlAlchemyCampaniaRepository,
    SqlAlchemyPerfilPrediccion,
)
from tests.integration.persistence.test_migrations import insert, membresia, modelo

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
ALTO, MEDIO, BAJO = NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO


class RelojAjustable:
    def __init__(self) -> None:
        self.instante = INSTANTE

    def now(self) -> datetime:
        return self.instante


@pytest.fixture
def reloj() -> RelojAjustable:
    return RelojAjustable()


@pytest.fixture
def repo(db_session: Session, reloj: RelojAjustable) -> SqlAlchemyCampaniaRepository:
    return SqlAlchemyCampaniaRepository(db_session, reloj)


def datos(
    nombre: str,
    *,
    niveles: tuple[NivelRiesgo, ...] = (ALTO,),
    planes: tuple[Plan, ...] = (Plan.MENSUAL,),
    prioridad: int = 1,
    descripcion: str | None = None,
) -> DatosCampania:
    return DatosCampania.crear(
        nombre=nombre, descripcion=descripcion, niveles=niveles, planes=planes, prioridad=prioridad
    )


def contar(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM campanias")).scalar_one())


def fila(session: Session, campania_id: int) -> dict[str, object]:
    return dict(
        session.execute(
            text(
                "SELECT activa, es_ejemplo, created_at, updated_at, deleted_at, niveles_riesgo, "
                "planes FROM campanias WHERE id = :id"
            ),
            {"id": campania_id},
        )
        .mappings()
        .one()
    )


def inactivar_ejemplos(session: Session) -> None:
    session.execute(text("UPDATE campanias SET activa = false WHERE es_ejemplo"))


def borrar_logicamente(session: Session, campania_id: int) -> None:
    session.execute(
        text("UPDATE campanias SET deleted_at = :t WHERE id = :id"),
        {"t": INSTANTE, "id": campania_id},
    )


def test_implementa_los_puertos(db_session: Session, repo: SqlAlchemyCampaniaRepository) -> None:
    assert isinstance(repo, CampaniaRepository)
    assert isinstance(SqlAlchemyPerfilPrediccion(db_session), PerfilPrediccion)


def test_crear_guarda_activa_no_ejemplo_con_marcas_del_reloj(
    db_session: Session, repo: SqlAlchemyCampaniaRepository
) -> None:
    creada = repo.crear(
        datos("Renovacion", niveles=(ALTO, MEDIO), planes=(Plan.MENSUAL, Plan.TRIMESTRAL))
    )

    guardada = fila(db_session, creada.id)
    assert creada.activa is True
    assert creada.es_ejemplo is False
    assert creada.niveles_riesgo == (ALTO, MEDIO)
    assert creada.planes == (Plan.MENSUAL, Plan.TRIMESTRAL)
    assert guardada["created_at"] == INSTANTE
    assert guardada["updated_at"] == INSTANTE
    assert guardada["deleted_at"] is None
    assert guardada["niveles_riesgo"] == ["ALTO", "MEDIO"]
    assert repo.obtener(creada.id) == creada


def test_actualizar_cambia_datos_y_updated_at_y_conserva_activa_y_es_ejemplo(
    db_session: Session, repo: SqlAlchemyCampaniaRepository, reloj: RelojAjustable
) -> None:
    creada = repo.crear(datos("Antes"))
    repo.inactivar(creada.id)
    reloj.instante = INSTANTE + timedelta(hours=1)

    editada = repo.actualizar(creada.id, datos("Despues", niveles=(BAJO,), prioridad=7))

    assert editada is not None
    assert editada.nombre == "Despues"
    assert editada.niveles_riesgo == (BAJO,)
    assert editada.prioridad == 7
    assert editada.activa is False
    assert editada.es_ejemplo is False
    guardada = fila(db_session, creada.id)
    assert guardada["created_at"] == INSTANTE
    assert guardada["updated_at"] == INSTANTE + timedelta(hours=1)


def test_actualizar_inexistente_o_borrada_devuelve_none(
    db_session: Session, repo: SqlAlchemyCampaniaRepository
) -> None:
    creada = repo.crear(datos("Borrada"))
    borrar_logicamente(db_session, creada.id)

    assert repo.actualizar(creada.id, datos("Otra")) is None
    assert repo.actualizar(999_999, datos("Otra")) is None
    assert repo.obtener(creada.id) is None


def test_inactivar_pone_activa_false_sin_deleted_at_y_sin_perder_filas(
    db_session: Session, repo: SqlAlchemyCampaniaRepository, reloj: RelojAjustable
) -> None:
    creada = repo.crear(datos("Inactivar"))
    antes = contar(db_session)
    reloj.instante = INSTANTE + timedelta(hours=2)

    inactivada = repo.inactivar(creada.id)

    assert inactivada is not None
    assert inactivada.activa is False
    guardada = fila(db_session, creada.id)
    assert guardada["activa"] is False
    assert guardada["deleted_at"] is None
    assert guardada["updated_at"] == INSTANTE + timedelta(hours=2)
    assert contar(db_session) == antes


def test_inactivar_ya_inactiva_no_cambia_updated_at(
    db_session: Session, repo: SqlAlchemyCampaniaRepository, reloj: RelojAjustable
) -> None:
    creada = repo.crear(datos("Dos veces"))
    repo.inactivar(creada.id)
    reloj.instante = INSTANTE + timedelta(days=1)

    repo.inactivar(creada.id)

    assert fila(db_session, creada.id)["updated_at"] == INSTANTE


def test_inactivar_inexistente_devuelve_none(repo: SqlAlchemyCampaniaRepository) -> None:
    assert repo.inactivar(999_999) is None


def test_no_existe_metodo_de_borrado() -> None:
    metodos = {n for n, _ in inspect.getmembers(SqlAlchemyCampaniaRepository, inspect.isfunction)}

    assert not {m for m in metodos if "borr" in m or "delete" in m or "elimin" in m}


def test_listar_excluye_borradas_y_ordena_activa_prioridad_nombre_id(
    db_session: Session, repo: SqlAlchemyCampaniaRepository
) -> None:
    db_session.execute(text("UPDATE campanias SET deleted_at = :t"), {"t": INSTANTE})
    inactiva = repo.crear(datos("aaa inactiva", prioridad=1))
    repo.inactivar(inactiva.id)
    borrada = repo.crear(datos("Borrada", prioridad=1))
    borrar_logicamente(db_session, borrada.id)
    b = repo.crear(datos("b", prioridad=2))
    zeta = repo.crear(datos("Zeta", prioridad=1))
    alfa = repo.crear(datos("alfa", prioridad=1))
    alfa_bis = repo.crear(datos("Alfa", prioridad=1))

    ids = [c.id for c in repo.listar()]

    assert ids == [alfa.id, alfa_bis.id, zeta.id, b.id, inactiva.id]


def test_listar_incluye_las_tres_de_ejemplo(repo: SqlAlchemyCampaniaRepository) -> None:
    ejemplos = [c for c in repo.listar() if c.es_ejemplo]

    assert [c.prioridad for c in ejemplos] == [1, 2, 3]


def test_compatibles_alto_mensual_devuelve_solo_activas_no_borradas_en_orden(
    db_session: Session, repo: SqlAlchemyCampaniaRepository
) -> None:
    inactivar_ejemplos(db_session)
    repo.crear(datos("Solo bajo", niveles=(BAJO,)))
    repo.crear(datos("Solo anual", planes=(Plan.ANUAL,)))
    inactiva = repo.crear(datos("Inactiva compatible"))
    repo.inactivar(inactiva.id)
    borrada = repo.crear(datos("Borrada compatible"))
    borrar_logicamente(db_session, borrada.id)
    repo.crear(datos("Prioridad dos", niveles=(ALTO, MEDIO), prioridad=2))
    repo.crear(datos("beta", planes=(Plan.MENSUAL, Plan.OTRO)))
    repo.crear(datos("Alfa", niveles=(MEDIO, ALTO)))

    nombres = [c.nombre for c in repo.compatibles(ALTO, Plan.MENSUAL)]

    assert nombres == ["Alfa", "beta", "Prioridad dos"]


def test_compatibles_usa_parametros_enlazados(
    db_session: Session, repo: SqlAlchemyCampaniaRepository
) -> None:
    sentencias: list[tuple[str, object]] = []

    def capturar(_conn: object, _cur: object, sql: str, params: object, *_: object) -> None:
        sentencias.append((sql, params))

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", capturar)
    try:
        repo.compatibles(ALTO, Plan.MENSUAL)
    finally:
        event.remove(engine, "before_cursor_execute", capturar)

    sql, params = sentencias[-1]
    assert "ANY" in sql.upper()
    assert "'ALTO'" not in sql
    assert "'MENSUAL'" not in sql
    assert "ALTO" in str(params)


def test_repositorio_no_confirma_la_transaccion() -> None:
    fuente = inspect.getsource(modulo_repositorio)

    assert ".commit(" not in fuente
    assert ".rollback(" not in fuente


def test_perfil_obtener_devuelve_nivel_de_la_prediccion_y_plan_de_la_membresia(
    db_session: Session,
) -> None:
    conexion = db_session.connection()
    membresia_id = membresia(conexion, plan="TRIMESTRAL")
    lista_id = insert(
        conexion,
        "listas_priorizadas",
        {
            "modelo_id": modelo(conexion, version=7001),
            "fecha_generacion": INSTANTE.date(),
            "horizonte_dias": 30,
            "top_k": 10,
            "creada_en": INSTANTE,
            "nombre": "Lista ficticia",
        },
    )
    prediccion_id = insert(
        conexion,
        "predicciones",
        {
            "lista_id": lista_id,
            "membresia_id": membresia_id,
            "score": "0.4",
            "nivel_riesgo": "MEDIO",
            "factores_principales": "[]",
            "prioridad": 1,
            "dentro_top_k": True,
        },
    )

    perfil = SqlAlchemyPerfilPrediccion(db_session).obtener(prediccion_id)

    assert perfil == (MEDIO, Plan.TRIMESTRAL)


def test_perfil_obtener_inexistente_devuelve_none(db_session: Session) -> None:
    assert SqlAlchemyPerfilPrediccion(db_session).obtener(999_999) is None
