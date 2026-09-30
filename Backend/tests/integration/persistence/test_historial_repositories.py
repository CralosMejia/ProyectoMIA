"""Repositorios SQLAlchemy del historial contra PostgreSQL real (``app_db_test``).

Los repositorios escriben dentro de la transaccion de quien llama (unit of work) y nunca la
confirman ni la revierten. Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso
restringido por IP, CU-00), por eso no hay pruebas de filtro por propietario.
Datos 100 % sinteticos: ningun nombre ni cedula real.
"""

import inspect
import re
import time
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Connection, Engine, event, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.application.historial.ports import (
    CargaRepository,
    MembresiaParaPrediccion,
    MembresiaRepository,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    ReferenciaOrigen,
    SocioRepository,
)
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan, TipoCarga
from app.infrastructure.persistence.models.historial import Carga, Membresia, Socio
from app.infrastructure.persistence.repositories import historial as modulo_repositorios
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyCargaRepository,
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)

INSTANTE = datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
TABLAS = ("socios", "membresias", "cargas")
LIMITE_SEGUNDOS_3000 = 5.0


class RelojFijo:
    def now(self) -> datetime:
        return INSTANTE


def carga_historica() -> NuevaCarga:
    return NuevaCarga(
        tipo=TipoCarga.MIGRACION_HISTORICA,
        fecha_carga=INSTANTE,
        nombre_archivo="Control Gym 2025 sintetico.xlsx",
        filas_leidas=3000,
        filas_guardadas=3000,
        filas_duplicadas=0,
        socios_enlazados=1000,
    )


def socio_sintetico(i: int) -> NuevoSocio:
    return NuevoSocio(
        cedula=f"{9000000000 + i:010d}",
        nombre=f"Socio Sintetico {i:04d}",
        nombre_normalizado=f"SOCIO SINTETICO {i:04d}",
    )


def membresia(socio_id: int, carga_id: int, fila: int = 7) -> NuevaMembresia:
    return NuevaMembresia(
        socio_id=socio_id,
        carga_id=carga_id,
        plan=Plan.MENSUAL,
        forma_pago=FormaPago.EFECTIVO,
        origen=OrigenMembresia.HISTORICO,
        inicio_aproximado=False,
        fecha_actividad=date(2025, 1, 6),
        fecha_inicio=date(2025, 1, 6),
        fecha_vencimiento=date(2025, 2, 5),
        monto_cobrado=Decimal("39.50"),
        referencia_origen=ReferenciaOrigen(anio=2025, hoja="ENERO", fila=fila),
        plan_original="PROMO MES",
        forma_pago_original="efectivo",
    )


def contar(origen: Session | Connection, tabla: str) -> int:
    assert tabla in TABLAS  # lista blanca: el nombre nunca viene de fuera
    return int(origen.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one())  # noqa: S608 - tabla de lista blanca


@pytest.fixture
def reloj() -> RelojFijo:
    return RelojFijo()


@pytest.fixture
def repos(
    db_session: Session, reloj: RelojFijo
) -> Iterator[
    tuple[SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository]
]:
    yield (
        SqlAlchemyCargaRepository(db_session, reloj),
        SqlAlchemySocioRepository(db_session, reloj),
        SqlAlchemyMembresiaRepository(db_session, reloj),
    )


def test_repositories_implement_the_ports(db_session: Session, reloj: RelojFijo) -> None:
    assert isinstance(SqlAlchemyCargaRepository(db_session, reloj), CargaRepository)
    assert isinstance(SqlAlchemySocioRepository(db_session, reloj), SocioRepository)
    assert isinstance(SqlAlchemyMembresiaRepository(db_session, reloj), MembresiaRepository)


def test_crear_carga_persists_fields_and_clock_timestamps(
    db_session: Session, repos: tuple[SqlAlchemyCargaRepository, object, object]
) -> None:
    carga_id = repos[0].crear(carga_historica())

    carga = db_session.get_one(Carga, carga_id)
    assert carga.tipo == TipoCarga.MIGRACION_HISTORICA
    assert carga.fecha_carga == INSTANTE
    assert carga.filas_leidas == 3000
    assert carga.created_at == INSTANTE
    assert carga.updated_at == INSTANTE
    assert carga.deleted_at is None


def test_insertar_en_bloque_socios_returns_ids_in_input_order(
    db_session: Session,
    repos: tuple[object, SqlAlchemySocioRepository, object],
) -> None:
    socios = [socio_sintetico(i) for i in (5, 1, 9, 3)]
    socios.append(NuevoSocio(cedula=None, nombre="Sin Cedula", nombre_normalizado="SIN CEDULA"))

    ids = repos[1].insertar_en_bloque(socios)

    assert len(ids) == len(socios)
    for socio_id, esperado in zip(ids, socios, strict=True):
        guardado = db_session.get_one(Socio, socio_id)
        assert guardado.cedula == esperado.cedula
        assert guardado.nombre_normalizado == esperado.nombre_normalizado
        assert guardado.created_at == INSTANTE
        assert guardado.updated_at == INSTANTE


def test_insertar_en_bloque_empty_sequences_insert_nothing(
    db_session: Session,
    repos: tuple[object, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository],
) -> None:
    assert repos[1].insertar_en_bloque([]) == []
    assert repos[2].insertar_en_bloque([]) == 0
    assert contar(db_session, "socios") == 0


def test_insertar_en_bloque_membresias_keeps_decimal_reference_and_enums(
    db_session: Session,
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_repo, socio_repo, membresia_repo = repos
    carga_id = carga_repo.crear(carga_historica())
    (socio_id,) = socio_repo.insertar_en_bloque([socio_sintetico(1)])

    insertadas = membresia_repo.insertar_en_bloque([membresia(socio_id, carga_id, fila=12)])

    assert insertadas == 1
    guardada = db_session.scalars(select(Membresia)).one()
    assert guardada.monto_cobrado == Decimal("39.50")
    assert isinstance(guardada.monto_cobrado, Decimal)
    assert guardada.referencia_origen == {"anio": 2025, "hoja": "ENERO", "fila": 12}
    assert guardada.plan == "MENSUAL"
    assert guardada.forma_pago == "EFECTIVO"
    assert guardada.origen == "HISTORICO"
    assert guardada.plan_original == "PROMO MES"
    assert guardada.inicio_aproximado is False
    assert guardada.created_at == INSTANTE
    assert guardada.updated_at == INSTANTE


def test_insert_3000_in_one_transaction_then_rollback_leaves_tables_empty(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    with migrated_engine.connect() as conexion:
        for tabla in TABLAS:
            assert contar(conexion, tabla) == 0

    with migrated_engine.connect() as conexion:
        transaccion = conexion.begin()
        session = Session(bind=conexion, join_transaction_mode="create_savepoint")
        try:
            carga_id = SqlAlchemyCargaRepository(session, reloj).crear(carga_historica())
            socio_ids = SqlAlchemySocioRepository(session, reloj).insertar_en_bloque(
                [socio_sintetico(i) for i in range(1000)]
            )
            membresias = [membresia(socio_ids[i % 1000], carga_id, fila=i + 2) for i in range(3000)]

            inicio = time.perf_counter()
            insertadas = SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
                membresias
            )
            duracion = time.perf_counter() - inicio

            assert insertadas == 3000
            assert duracion < LIMITE_SEGUNDOS_3000
            assert contar(session, "cargas") == 1
            assert contar(session, "socios") == 1000
            assert contar(session, "membresias") == 3000
        finally:
            session.close()
            transaccion.rollback()

    with migrated_engine.connect() as conexion:
        for tabla in TABLAS:
            assert contar(conexion, tabla) == 0


def test_insertar_en_bloque_membresia_unknown_socio_raises_and_stays_revertible(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    with migrated_engine.connect() as conexion:
        transaccion = conexion.begin()
        session = Session(bind=conexion, join_transaction_mode="create_savepoint")
        try:
            carga_id = SqlAlchemyCargaRepository(session, reloj).crear(carga_historica())

            with pytest.raises(IntegrityError):
                SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
                    [membresia(socio_id=999_999_999, carga_id=carga_id)]
                )

            # La transaccion externa sigue utilizable tras volver al savepoint (la carga,
            # escrita en el mismo savepoint, se deshace con el).
            session.rollback()
            assert conexion.execute(select(func.count()).select_from(Carga)).scalar_one() == 0
        finally:
            session.close()
            transaccion.rollback()

    with migrated_engine.connect() as conexion:
        for tabla in TABLAS:
            assert contar(conexion, tabla) == 0


def test_insertar_en_bloque_membresia_unknown_carga_raises_integrity_error(
    db_session: Session,
    repos: tuple[object, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository],
) -> None:
    (socio_id,) = repos[1].insertar_en_bloque([socio_sintetico(1)])

    with pytest.raises(IntegrityError, match="carga_id"):
        repos[2].insertar_en_bloque([membresia(socio_id=socio_id, carga_id=999_999_999)])


def test_insertar_en_bloque_failure_keeps_outer_transaction_prior_writes(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    with migrated_engine.connect() as conexion:
        transaccion = conexion.begin()
        try:
            # Escritura previa de la transaccion externa, fuera de la sesion.
            conexion.execute(
                text(
                    "INSERT INTO socios (nombre, nombre_normalizado, created_at, updated_at) "
                    "VALUES ('Previo', 'PREVIO', :t, :t)"
                ),
                {"t": INSTANTE},
            )
            session = Session(bind=conexion, join_transaction_mode="create_savepoint")
            try:
                carga_id = SqlAlchemyCargaRepository(session, reloj).crear(carga_historica())
                with pytest.raises(IntegrityError):
                    SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
                        [
                            membresia(socio_id=999_999_998, carga_id=carga_id, fila=2),
                            membresia(socio_id=999_999_999, carga_id=carga_id, fila=3),
                        ]
                    )
                session.rollback()
            finally:
                session.close()

            assert contar(conexion, "socios") == 1
            assert contar(conexion, "cargas") == 0
            assert contar(conexion, "membresias") == 0
            # La transaccion externa sigue aceptando escrituras.
            conexion.execute(
                text(
                    "INSERT INTO socios (nombre, nombre_normalizado, created_at, updated_at) "
                    "VALUES ('Despues', 'DESPUES', :t, :t)"
                ),
                {"t": INSTANTE},
            )
            assert contar(conexion, "socios") == 2
        finally:
            transaccion.rollback()

    with migrated_engine.connect() as conexion:
        for tabla in TABLAS:
            assert contar(conexion, tabla) == 0


def test_insertar_en_bloque_membresias_max_precision_decimal_is_exact(
    db_session: Session,
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_id = repos[0].crear(carga_historica())
    (socio_id,) = repos[1].insertar_en_bloque([socio_sintetico(1)])
    base = membresia(socio_id, carga_id)
    limite = Decimal("999999999999999.9999")  # NUMERIC(19,4): 15 enteros + 4 decimales

    repos[2].insertar_en_bloque([replace(base, monto_cobrado=limite, monto_facturado=Decimal("0"))])

    guardada = db_session.scalars(select(Membresia)).one()
    assert guardada.monto_cobrado == limite
    assert guardada.monto_facturado == Decimal("0")


def test_insertar_en_bloque_membresia_negative_amount_is_rejected(
    db_session: Session,
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_id = repos[0].crear(carga_historica())
    (socio_id,) = repos[1].insertar_en_bloque([socio_sintetico(1)])
    base = membresia(socio_id, carga_id)

    with pytest.raises(IntegrityError, match="monto_cobrado"):
        repos[2].insertar_en_bloque([replace(base, monto_cobrado=Decimal("-0.01"))])


def test_crear_second_historical_carga_concurrently_is_blocked(
    migrated_engine: Engine, reloj: RelojFijo
) -> None:
    with migrated_engine.connect() as conexion_a, migrated_engine.connect() as conexion_b:
        transaccion_a = conexion_a.begin()
        transaccion_b = conexion_b.begin()
        session_a = Session(bind=conexion_a, join_transaction_mode="create_savepoint")
        session_b = Session(bind=conexion_b, join_transaction_mode="create_savepoint")
        try:
            SqlAlchemyCargaRepository(session_a, reloj).crear(carga_historica())
            conexion_b.execute(text("SET LOCAL lock_timeout = '1s'"))

            # B espera a A por el indice unico parcial y no llega a insertar una segunda
            # migracion historica mientras A no termine.
            with pytest.raises(OperationalError, match="lock timeout"):
                SqlAlchemyCargaRepository(session_b, reloj).crear(carga_historica())
        finally:
            session_a.close()
            session_b.close()
            transaccion_b.rollback()
            transaccion_a.rollback()

    with migrated_engine.connect() as conexion:
        assert contar(conexion, "cargas") == 0


def test_repositories_module_never_inserts_row_by_row() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    assert re.search(r"\.add(_all)?\s*\(", fuente) is None
    assert "insert(" in fuente


def test_repositories_module_never_controls_the_transaction() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    for metodo in ("commit", "rollback", "begin", "close"):
        assert re.search(rf"\.{metodo}\s*\(", fuente) is None, metodo


def test_repositories_module_never_reads_system_time() -> None:
    fuente = inspect.getsource(modulo_repositorios)

    assert "datetime.now" not in fuente
    assert "utcnow" not in fuente
    assert "date.today" not in fuente


# ------------------------------------------------------------------ R-004 T5: lecturas
def test_insertar_en_bloque_membresia_stores_fecha_actividad(
    db_session: Session,
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_id = repos[0].crear(carga_historica())
    (socio_id,) = repos[1].insertar_en_bloque([socio_sintetico(1)])
    # Sin inicio: la actividad es el mes de la hoja (dominio), distinta de ``fecha_inicio``.
    sin_inicio = replace(
        membresia(socio_id, carga_id),
        fecha_inicio=None,
        fecha_actividad=date(2025, 3, 1),
        inicio_aproximado=True,
    )

    repos[2].insertar_en_bloque([sin_inicio])

    guardada = db_session.scalars(select(Membresia)).one()
    assert guardada.fecha_actividad == date(2025, 3, 1)
    assert guardada.fecha_inicio is None


def test_listar_para_prediccion_returns_active_rows_in_one_query(
    db_session: Session,
    migrated_engine: Engine,
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_id = repos[0].crear(carga_historica())
    socio_ids = repos[1].insertar_en_bloque(
        [socio_sintetico(0), replace(socio_sintetico(1), cedula=None), socio_sintetico(2)]
    )
    base = membresia(socio_ids[0], carga_id)
    repos[2].insertar_en_bloque(
        [
            base,
            replace(
                base,
                socio_id=socio_ids[1],
                plan=Plan.TRIMESTRAL,
                forma_pago=FormaPago.TRANSFERENCIA,
                fecha_inicio=None,
                fecha_vencimiento=None,
                fecha_actividad=date(2025, 2, 1),
                monto_cobrado=None,
                inicio_aproximado=True,
            ),
            replace(base, socio_id=socio_ids[2]),
        ]
    )
    ids = list(db_session.scalars(select(Membresia.id).order_by(Membresia.id)))
    db_session.execute(
        text("UPDATE membresias SET deleted_at = :t WHERE id = :id"),
        {"t": INSTANTE, "id": ids[2]},
    )

    consultas: list[str] = []

    def registrar(*args: object) -> None:
        consultas.append(str(args[2]))

    event.listen(migrated_engine, "before_cursor_execute", registrar)
    try:
        leidas = repos[2].listar_para_prediccion()
    finally:
        event.remove(migrated_engine, "before_cursor_execute", registrar)

    assert len(consultas) == 1  # sin N+1
    assert "deleted_at IS NULL" in consultas[0]
    assert leidas == [
        MembresiaParaPrediccion(
            membresia_id=ids[0],
            socio_id=socio_ids[0],
            plan=Plan.MENSUAL,
            forma_pago=FormaPago.EFECTIVO,
            fecha_inicio=date(2025, 1, 6),
            fecha_vencimiento=date(2025, 2, 5),
            fecha_actividad=date(2025, 1, 6),
            monto_cobrado=Decimal("39.50"),
            inicio_aproximado=False,
            socio_con_cedula=True,
        ),
        MembresiaParaPrediccion(
            membresia_id=ids[1],
            socio_id=socio_ids[1],
            plan=Plan.TRIMESTRAL,
            forma_pago=FormaPago.TRANSFERENCIA,
            fecha_inicio=None,
            fecha_vencimiento=None,
            fecha_actividad=date(2025, 2, 1),
            monto_cobrado=None,
            inicio_aproximado=True,
            socio_con_cedula=False,
        ),
    ]
    assert isinstance(leidas[0].monto_cobrado, Decimal)
    assert leidas[0].plan is Plan.MENSUAL


def test_hay_migracion_o_membresias_empty_database_returns_false(
    repos: tuple[SqlAlchemyCargaRepository, object, object],
) -> None:
    assert repos[0].hay_migracion_o_membresias() is False


def test_hay_migracion_o_membresias_with_historical_migration_returns_true(
    repos: tuple[SqlAlchemyCargaRepository, object, object],
) -> None:
    repos[0].crear(carga_historica())

    assert repos[0].hay_migracion_o_membresias() is True


def test_hay_migracion_o_membresias_with_template_load_only_depends_on_memberships(
    repos: tuple[
        SqlAlchemyCargaRepository, SqlAlchemySocioRepository, SqlAlchemyMembresiaRepository
    ],
) -> None:
    carga_id = repos[0].crear(replace(carga_historica(), tipo=TipoCarga.PLANTILLA))
    assert repos[0].hay_migracion_o_membresias() is False

    (socio_id,) = repos[1].insertar_en_bloque([socio_sintetico(1)])
    repos[2].insertar_en_bloque(
        [replace(membresia(socio_id, carga_id), origen=OrigenMembresia.PLANTILLA)]
    )

    assert repos[0].hay_migracion_o_membresias() is True


def test_ultima_fecha_carga_without_loads_returns_none(
    repos: tuple[SqlAlchemyCargaRepository, object, object],
) -> None:
    assert repos[0].ultima_fecha_carga() is None


def test_ultima_fecha_carga_with_two_loads_returns_the_latest(
    repos: tuple[SqlAlchemyCargaRepository, object, object],
) -> None:
    posterior = INSTANTE + timedelta(days=3)
    repos[0].crear(replace(carga_historica(), tipo=TipoCarga.PLANTILLA, fecha_carga=posterior))
    repos[0].crear(carga_historica())

    assert repos[0].ultima_fecha_carga() == posterior
