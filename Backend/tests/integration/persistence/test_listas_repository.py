"""Repositorio de listas priorizadas y predicciones contra PostgreSQL real (``app_db_test``).

El repositorio escribe dentro de la transaccion de quien llama (unit of work) y nunca la
confirma ni la revierte. Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso
restringido por IP, CU-00), por eso no hay pruebas de filtro por propietario.
Datos 100 % sinteticos: ningun nombre, celular ni correo real.
"""

import inspect
import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.gestiones.ports import NuevaGestion
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.application.listas.ports import (
    ListaDetalle,
    ListaRepository,
    NuevaLista,
    NuevaPrediccion,
)
from app.application.modelo.ports import NuevoModelo
from app.domain.common.enums import FormaPago, NivelRiesgo, OrigenMembresia, Plan, TipoCarga
from app.infrastructure.persistence.repositories import listas as modulo_repositorio
from app.infrastructure.persistence.repositories.gestiones import SqlAlchemyGestionRepository
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyCargaRepository,
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from app.infrastructure.persistence.repositories.listas import SqlAlchemyListaRepository
from app.infrastructure.persistence.repositories.modelo import SqlAlchemyModeloRepository

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
TOTAL = 60
TABLAS = ("listas_priorizadas", "predicciones", "membresias", "socios", "cargas", "modelos")


class RelojAjustable:
    def __init__(self) -> None:
        self.instante = INSTANTE

    def now(self) -> datetime:
        return self.instante


@dataclass(frozen=True)
class Escenario:
    modelo_id: int
    membresia_ids: list[int]
    socio_ids: list[int]


def contar(session: Session, tabla: str) -> int:
    assert tabla in TABLAS  # lista blanca: el nombre nunca viene de fuera
    return int(session.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())  # noqa: S608 - tabla de lista blanca


def preparar(session: Session, reloj: RelojAjustable) -> Escenario:
    carga_id = SqlAlchemyCargaRepository(session, reloj).crear(
        NuevaCarga(
            tipo=TipoCarga.MIGRACION_HISTORICA,
            fecha_carga=INSTANTE,
            nombre_archivo="Control Gym 2026 sintetico.xlsx",
            filas_leidas=TOTAL,
            filas_guardadas=TOTAL,
            filas_duplicadas=0,
            socios_enlazados=TOTAL,
        )
    )
    socio_ids = SqlAlchemySocioRepository(session, reloj).insertar_en_bloque(
        [
            NuevoSocio(
                cedula=f"{9100000000 + i:010d}",
                nombre=f"Socio Sintetico {i:02d}",
                nombre_normalizado=f"SOCIO SINTETICO {i:02d}",
                celular=f"09{i:08d}",
                correo=f"socio{i:02d}@ejemplo.test",
            )
            for i in range(TOTAL)
        ]
    )
    SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
        [
            NuevaMembresia(
                socio_id=socio_ids[i],
                carga_id=carga_id,
                plan=Plan.TRIMESTRAL if i % 2 else Plan.MENSUAL,
                forma_pago=FormaPago.EFECTIVO,
                origen=OrigenMembresia.HISTORICO,
                inicio_aproximado=False,
                fecha_actividad=date(2026, 8, 1),
                fecha_inicio=date(2026, 8, 1),
                fecha_vencimiento=date(2026, 9, 1) + timedelta(days=i % 30),
                monto_cobrado=None if i == 0 else Decimal("39.50"),
            )
            for i in range(TOTAL)
        ]
    )
    membresia_ids = [
        int(v)
        for v in session.execute(
            text("SELECT id FROM membresias WHERE carga_id = :c ORDER BY id"), {"c": carga_id}
        ).scalars()
    ]
    modelo_id = SqlAlchemyModeloRepository(session, reloj).crear(
        NuevoModelo(
            version=1,
            fecha_entrenamiento=INSTANTE,
            ciclos_entrenamiento=1000,
            periodo_desde=date(2023, 1, 1),
            periodo_hasta=date(2026, 8, 31),
            prevalencia=Decimal("0.35"),
            umbral_alto=Decimal("0.71234567"),
            umbral_medio=Decimal("0.41234567"),
            porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
            artefacto=b"\x00",
            metadata_tecnica={},
        )
    )
    return Escenario(modelo_id, membresia_ids, socio_ids)


def predicciones(escenario: Escenario, top_k: int = 25) -> list[NuevaPrediccion]:
    # Se entregan en orden inverso de prioridad para comprobar el orden de lectura.
    return [
        NuevaPrediccion(
            membresia_id=escenario.membresia_ids[i],
            socio_id=escenario.socio_ids[i],
            score=Decimal(TOTAL - i) / Decimal(TOTAL + 1),
            nivel_riesgo=NivelRiesgo.ALTO if i < 12 else NivelRiesgo.BAJO,
            factores_principales=() if i else ("Pocos ciclos previos", "Plan mensual"),
            prioridad=i + 1,
            dentro_top_k=i < top_k,
        )
        for i in reversed(range(TOTAL))
    ]


def nueva_lista(
    escenario: Escenario, fecha: date = date(2026, 8, 31), nombre: str = "Lista sintetica"
) -> NuevaLista:
    return NuevaLista(
        modelo_id=escenario.modelo_id,
        fecha_generacion=fecha,
        horizonte_dias=30,
        top_k=25,
        nombre=nombre,
    )


@pytest.fixture
def reloj() -> RelojAjustable:
    return RelojAjustable()


@pytest.fixture
def repo(db_session: Session, reloj: RelojAjustable) -> SqlAlchemyListaRepository:
    return SqlAlchemyListaRepository(db_session, reloj)


@pytest.fixture
def escenario(db_session: Session, reloj: RelojAjustable) -> Escenario:
    return preparar(db_session, reloj)


@pytest.fixture
def sentencias_predicciones(migrated_engine: Engine) -> Iterator[list[bool]]:
    """Registra cada ejecucion de ``INSERT INTO predicciones`` (``True`` si fue executemany)."""
    registradas: list[bool] = []

    def escuchar(
        conn: object, cursor: object, sql: str, params: object, context: object, many: bool
    ) -> None:
        if sql.lstrip().upper().startswith("INSERT INTO PREDICCIONES"):
            registradas.append(many)

    event.listen(migrated_engine, "before_cursor_execute", escuchar)
    try:
        yield registradas
    finally:
        event.remove(migrated_engine, "before_cursor_execute", escuchar)


def test_repository_implements_the_port(repo: SqlAlchemyListaRepository) -> None:
    assert isinstance(repo, ListaRepository)


def test_crear_inserts_list_and_60_predictions_in_bulk_with_clock(
    db_session: Session,
    repo: SqlAlchemyListaRepository,
    escenario: Escenario,
    sentencias_predicciones: list[bool],
) -> None:
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario))

    assert sentencias_predicciones == [True]  # una sola ejecucion, en bloque
    assert contar(db_session, "predicciones") == TOTAL
    creada_en, created_at = db_session.execute(
        text("SELECT creada_en, created_at FROM listas_priorizadas WHERE id = :id"),
        {"id": lista_id},
    ).one()
    assert creada_en == INSTANTE
    assert created_at == INSTANTE


def test_crear_invalid_prediction_rolls_back_list_and_predictions(
    migrated_engine: Engine, reloj: RelojAjustable
) -> None:
    with migrated_engine.connect() as conexion:
        transaccion = conexion.begin()
        try:
            session = Session(bind=conexion, join_transaction_mode="create_savepoint")
            try:
                escenario = preparar(session, reloj)
                session.commit()  # confirma el savepoint del escenario; la externa sigue abierta
                filas = predicciones(escenario)
                invalida = replace(filas[0])
                # score = 2 salta la validacion del DTO para probar el CHECK de la base.
                object.__setattr__(invalida, "score", Decimal(2))
                with pytest.raises(IntegrityError, match="score"):
                    SqlAlchemyListaRepository(session, reloj).crear(
                        nueva_lista(escenario), [*filas[1:], invalida]
                    )
                session.rollback()

                assert contar(session, "listas_priorizadas") == 0
                assert contar(session, "predicciones") == 0
                assert contar(session, "membresias") == TOTAL
            finally:
                session.close()
        finally:
            transaccion.rollback()


def test_obtener_returns_header_and_items_ordered_by_priority(
    repo: SqlAlchemyListaRepository, escenario: Escenario
) -> None:
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario))

    detalle = repo.obtener(lista_id)

    assert detalle is not None
    assert detalle.id == lista_id
    assert detalle.modelo_id == escenario.modelo_id
    assert detalle.modelo_version == 1
    assert detalle.fecha_generacion == date(2026, 8, 31)
    assert detalle.creada_en == INSTANTE
    assert (detalle.horizonte_dias, detalle.top_k) == (30, 25)
    assert detalle.umbral_alto == Decimal("0.71234567")
    assert detalle.umbral_medio == Decimal("0.41234567")
    assert [i.prioridad for i in detalle.items] == list(range(1, TOTAL + 1))
    assert sum(i.dentro_top_k for i in detalle.items) == 25

    primero = detalle.items[0]
    assert primero.membresia_id == escenario.membresia_ids[0]
    assert primero.socio_id == escenario.socio_ids[0]
    assert primero.socio_nombre == "Socio Sintetico 00"
    assert primero.celular == "0900000000"
    assert primero.cedula == "9100000000"
    assert primero.plan is Plan.MENSUAL
    assert primero.fecha_vencimiento == date(2026, 9, 1)
    assert primero.monto_cobrado is None
    assert isinstance(primero.score, Decimal)
    assert primero.score == (Decimal(TOTAL) / Decimal(TOTAL + 1)).quantize(Decimal("1E-8"))
    assert primero.nivel_riesgo is NivelRiesgo.ALTO
    assert primero.factores_principales == ["Pocos ciclos previos", "Plan mensual"]
    assert primero.dentro_top_k is True

    segundo = detalle.items[1]
    assert segundo.plan is Plan.TRIMESTRAL
    assert segundo.monto_cobrado == Decimal("39.50")
    assert segundo.factores_principales == []
    assert detalle.items[-1].dentro_top_k is False
    assert detalle.items[-1].nivel_riesgo is NivelRiesgo.BAJO


def test_obtener_unknown_id_returns_none(repo: SqlAlchemyListaRepository) -> None:
    assert repo.obtener(999_999_999) is None


def test_ultima_and_listar_without_lists(repo: SqlAlchemyListaRepository) -> None:
    assert repo.ultima() is None
    assert repo.listar() == []


def test_ultima_uses_creada_en_then_id_and_listar_is_newest_first(
    repo: SqlAlchemyListaRepository, escenario: Escenario, reloj: RelojAjustable
) -> None:
    filas = predicciones(escenario)
    reloj.instante = INSTANTE + timedelta(hours=2)
    posterior = repo.crear(nueva_lista(escenario, date(2026, 9, 1)), filas[:10])
    reloj.instante = INSTANTE
    anterior = repo.crear(nueva_lista(escenario, date(2026, 8, 31)), filas)
    reloj.instante = INSTANTE + timedelta(hours=2)
    empate = repo.crear(nueva_lista(escenario, date(2026, 9, 1)), [])

    ultima = repo.ultima()
    assert ultima is not None
    assert ultima.id == empate  # mismo creada_en que ``posterior``: gana el mayor id
    assert ultima.items == ()

    resumen = repo.listar()
    assert [r.id for r in resumen] == [empate, posterior, anterior]
    assert [r.total_items for r in resumen] == [0, 10, TOTAL]
    por_id = {r.id: r for r in resumen}
    assert por_id[anterior].fecha_generacion == date(2026, 8, 31)
    assert por_id[anterior].creada_en == INSTANTE
    assert por_id[anterior].modelo_version == 1
    assert (por_id[anterior].horizonte_dias, por_id[anterior].top_k) == (30, 25)


def test_second_list_does_not_modify_the_first(
    repo: SqlAlchemyListaRepository, escenario: Escenario, reloj: RelojAjustable
) -> None:
    primera_id = repo.crear(nueva_lista(escenario), predicciones(escenario))
    antes = repo.obtener(primera_id)

    reloj.instante = INSTANTE + timedelta(days=1)
    otras = [
        replace(p, score=Decimal("0.5"), nivel_riesgo=NivelRiesgo.MEDIO)
        for p in predicciones(escenario, top_k=5)
    ]
    segunda_id = repo.crear(nueva_lista(escenario, date(2026, 9, 1)), otras)

    assert segunda_id != primera_id
    assert repo.obtener(primera_id) == antes
    segunda = repo.obtener(segunda_id)
    assert segunda is not None
    assert {i.score for i in segunda.items} == {Decimal("0.5")}


def test_obtener_after_logical_delete_of_membership_and_socio_keeps_historical_items(
    db_session: Session, repo: SqlAlchemyListaRepository, escenario: Escenario
) -> None:
    # Decision aceptada (RN-04.5): una lista generada es inmutable; un borrado logico
    # posterior de la membresia o del socio no la altera.
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario))
    antes = repo.obtener(lista_id)
    db_session.execute(
        text("UPDATE membresias SET deleted_at = :t WHERE id = :id"),
        {"t": INSTANTE, "id": escenario.membresia_ids[0]},
    )
    db_session.execute(
        text("UPDATE socios SET deleted_at = :t WHERE id = :id"),
        {"t": INSTANTE, "id": escenario.socio_ids[1]},
    )

    despues = repo.obtener(lista_id)

    assert despues == antes
    assert despues is not None
    assert len(despues.items) == TOTAL
    assert despues.items[0].socio_nombre == "Socio Sintetico 00"


def test_listar_counts_items_per_list_without_mixing_lists(
    repo: SqlAlchemyListaRepository, escenario: Escenario, reloj: RelojAjustable
) -> None:
    filas = predicciones(escenario)
    primera = repo.crear(nueva_lista(escenario), filas[:7])
    reloj.instante = INSTANTE + timedelta(minutes=1)
    segunda = repo.crear(nueva_lista(escenario, date(2026, 9, 1)), filas[7:])

    totales = {r.id: r.total_items for r in repo.listar()}

    assert totales == {primera: 7, segunda: TOTAL - 7}


def test_repository_module_never_controls_the_transaction_nor_reads_system_time() -> None:
    fuente = inspect.getsource(modulo_repositorio)

    for metodo in ("commit", "rollback", "begin", "close"):
        assert re.search(rf"\.{metodo}\s*\(", fuente) is None, metodo
    assert re.search(r"\.add(_all)?\s*\(", fuente) is None
    assert "datetime.now" not in fuente
    assert "date.today" not in fuente


def test_obtener_returns_cedula_as_text_and_none_for_old_list_without_cedula(
    db_session: Session, repo: SqlAlchemyListaRepository, escenario: Escenario
) -> None:
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario))
    db_session.execute(
        text("UPDATE socios SET cedula = :c WHERE id = :id"),
        {"c": "0912345678", "id": escenario.socio_ids[0]},
    )
    db_session.execute(
        text("UPDATE socios SET cedula = NULL WHERE id = :id"), {"id": escenario.socio_ids[1]}
    )

    detalle = repo.obtener(lista_id)

    assert detalle is not None
    assert detalle.items[0].cedula == "0912345678"
    assert detalle.items[1].cedula is None
    assert len(detalle.items) == TOTAL  # la lista antigua sigue igual (inmutable)
    assert all(not hasattr(i, "correo") for i in detalle.items)


def test_repository_module_never_reads_socio_correo() -> None:
    fuente = inspect.getsource(modulo_repositorio)

    assert re.search(r"correo", fuente) is None


# ------------------------------------------------------------------ R-008 T9: nombre de la lista
def test_crear_saves_nombre_and_obtener_ultima_listar_return_it(
    repo: SqlAlchemyListaRepository, escenario: Escenario, reloj: RelojAjustable
) -> None:
    primera = repo.crear(nueva_lista(escenario, nombre="Lista del 31 ago 2026"), [])
    reloj.instante = INSTANTE + timedelta(minutes=1)
    segunda = repo.crear(
        nueva_lista(escenario, date(2026, 9, 1), nombre="Campaña octubre"),
        predicciones(escenario)[:3],
    )

    detalle = repo.obtener(segunda)
    ultima = repo.ultima()
    assert detalle is not None
    assert ultima is not None
    assert detalle.nombre == "Campaña octubre"
    assert ultima.nombre == "Campaña octubre"
    assert {r.id: r.nombre for r in repo.listar()} == {
        segunda: "Campaña octubre",
        primera: "Lista del 31 ago 2026",
    }


def test_repeated_names_are_allowed(repo: SqlAlchemyListaRepository, escenario: Escenario) -> None:
    repo.crear(nueva_lista(escenario, nombre="Campaña octubre"), [])
    repo.crear(nueva_lista(escenario, nombre="Campaña octubre"), [])

    assert [r.nombre for r in repo.listar()] == ["Campaña octubre", "Campaña octubre"]


def test_listar_with_names_is_a_single_query(
    repo: SqlAlchemyListaRepository,
    escenario: Escenario,
    migrated_engine: Engine,
) -> None:
    for i in range(3):
        repo.crear(nueva_lista(escenario, nombre=f"Lista {i}"), predicciones(escenario)[:2])
    consultas: list[str] = []

    def escuchar(
        conn: object, cursor: object, sql: str, params: object, context: object, many: bool
    ) -> None:
        if sql.lstrip().upper().startswith("SELECT"):
            consultas.append(sql)

    event.listen(migrated_engine, "before_cursor_execute", escuchar)
    try:
        resumen = repo.listar()
    finally:
        event.remove(migrated_engine, "before_cursor_execute", escuchar)

    assert len(resumen) == 3
    assert len(consultas) == 1


# ------------------------------------------------------------------ R-009 T14: gestion del ciclo
def _gestion(
    session: Session,
    reloj: RelojAjustable,
    prediccion_id: int,
    membresia_id: int,
    campania: str | None = None,
) -> int:
    campania_id = None
    if campania is not None:
        campania_id = session.execute(
            text(
                "INSERT INTO campanias (nombre, activa, niveles_riesgo, planes, prioridad, "
                "es_ejemplo, created_at, updated_at) VALUES (:n, true, :niveles, :planes, 1, "
                "false, :t, :t) RETURNING id"
            ),
            {"n": campania, "niveles": ["ALTO"], "planes": ["MENSUAL"], "t": INSTANTE},
        ).scalar_one()
    return SqlAlchemyGestionRepository(session, reloj).crear(
        NuevaGestion(
            prediccion_id=prediccion_id,
            membresia_id=membresia_id,
            campania_id=campania_id,
            campania_nombre=campania,
            fecha_asignacion=date(2026, 9, 1),
            fecha_seguimiento=date(2026, 9, 20),
            responsable=None,
        )
    )


def _gestiones(detalle: ListaDetalle | None) -> list[tuple[int | None, str | None, str | None]]:
    assert detalle is not None
    return [
        (
            i.gestion_id,
            None if i.gestion_estado is None else i.gestion_estado.value,
            i.campania_asignada,
        )
        for i in detalle.items
    ]


def test_obtener_shows_the_cycle_gestion_in_every_list_that_contains_the_membership(
    db_session: Session,
    repo: SqlAlchemyListaRepository,
    escenario: Escenario,
    reloj: RelojAjustable,
) -> None:
    lista_1 = repo.crear(nueva_lista(escenario), predicciones(escenario)[-3:])
    lista_2 = repo.crear(nueva_lista(escenario), predicciones(escenario)[-3:])
    primera = repo.obtener(lista_1)
    assert primera is not None
    item_1, item_2, _ = primera.items
    con_campania = _gestion(
        db_session, reloj, item_1.prediccion_id, item_1.membresia_id, "Campaña sintetica"
    )
    sin_campania = _gestion(db_session, reloj, item_2.prediccion_id, item_2.membresia_id)
    db_session.execute(
        text("UPDATE gestiones_retencion SET estado = 'CERRADA', cerrada_en = :t WHERE id = :g"),
        {"t": INSTANTE, "g": sin_campania},
    )
    esperado = [
        (con_campania, "PENDIENTE", "Campaña sintetica"),
        (sin_campania, "CERRADA", None),
        (None, None, None),
    ]

    assert _gestiones(repo.obtener(lista_1)) == esperado
    assert _gestiones(repo.obtener(lista_2)) == esperado
    assert _gestiones(repo.ultima()) == esperado


def test_obtener_ignores_gestion_with_deleted_at_and_keeps_campaign_snapshot(
    db_session: Session,
    repo: SqlAlchemyListaRepository,
    escenario: Escenario,
    reloj: RelojAjustable,
) -> None:
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario)[-2:])
    detalle = repo.obtener(lista_id)
    assert detalle is not None
    item_1, item_2 = detalle.items
    borrada = _gestion(db_session, reloj, item_1.prediccion_id, item_1.membresia_id)
    viva = _gestion(db_session, reloj, item_2.prediccion_id, item_2.membresia_id, "Original")
    db_session.execute(
        text("UPDATE gestiones_retencion SET deleted_at = :t WHERE id = :g"),
        {"t": INSTANTE, "g": borrada},
    )
    db_session.execute(text("UPDATE campanias SET nombre = 'Renombrada' WHERE nombre = 'Original'"))

    assert _gestiones(repo.obtener(lista_id)) == [
        (None, None, None),
        (viva, "PENDIENTE", "Original"),
    ]
    assert len(detalle.items) == 2


def test_obtener_with_gestiones_reads_items_in_a_single_query(
    db_session: Session,
    repo: SqlAlchemyListaRepository,
    escenario: Escenario,
    reloj: RelojAjustable,
    migrated_engine: Engine,
) -> None:
    lista_id = repo.crear(nueva_lista(escenario), predicciones(escenario))
    detalle = repo.obtener(lista_id)
    assert detalle is not None
    for item in detalle.items[:5]:
        _gestion(db_session, reloj, item.prediccion_id, item.membresia_id)
    consultas: list[str] = []

    def escuchar(
        conn: object, cursor: object, sql: str, params: object, context: object, many: bool
    ) -> None:
        if sql.lstrip().upper().startswith("SELECT"):
            consultas.append(sql)

    event.listen(migrated_engine, "before_cursor_execute", escuchar)
    try:
        con_gestiones = repo.obtener(lista_id)
    finally:
        event.remove(migrated_engine, "before_cursor_execute", escuchar)

    assert con_gestiones is not None
    assert len(con_gestiones.items) == TOTAL
    assert sum(i.gestion_id is not None for i in con_gestiones.items) == 5
    # Cabecera + items: la gestion llega en la consulta de items (LEFT JOIN), sin N+1.
    assert len(consultas) == 2
    assert sum("gestiones_retencion" in c for c in consultas) == 1
