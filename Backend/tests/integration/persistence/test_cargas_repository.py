"""Repositorio de cargas por plantilla contra PostgreSQL real (``app_db_test``), R-007 T3.

Los repositorios trabajan dentro de la transaccion de quien llama y nunca la confirman ni
la revierten. Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso restringido
por IP, CU-00), por eso no hay pruebas de filtro por propietario.
Datos 100 % sinteticos insertados en cada prueba; la sesion termina siempre en ``rollback``.
"""

import inspect
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, event, select, text
from sqlalchemy.orm import Session

from app.application.cargas.ports import ClaveMembresia, ConsultasCarga, EscrituraCarga
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.domain.cargas.enlace import ClaveMembresia as ClaveDominio
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan, TipoCarga
from app.infrastructure.persistence.models.historial import Socio
from app.infrastructure.persistence.repositories import cargas as modulo_cargas
from app.infrastructure.persistence.repositories.cargas import (
    SqlAlchemyConsultasCarga,
    SqlAlchemyEscrituraCarga,
)

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
DESPUES = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)
NOMBRE = "ANA PEREZ LOPEZ"
INICIO = date(2026, 9, 1)
FIN = date(2026, 10, 1)


class Reloj:
    def __init__(self, instante: datetime) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


@pytest.fixture
def reloj() -> Reloj:
    return Reloj(INSTANTE)


@pytest.fixture
def consultas(db_session: Session, reloj: Reloj) -> SqlAlchemyConsultasCarga:
    return SqlAlchemyConsultasCarga(db_session, reloj)


@pytest.fixture
def escritura(db_session: Session, reloj: Reloj) -> SqlAlchemyEscrituraCarga:
    return SqlAlchemyEscrituraCarga(db_session, reloj)


@pytest.fixture
def sentencias(migrated_engine: Engine) -> Iterator[list[str]]:
    registradas: list[str] = []

    def registrar(*args: object) -> None:
        registradas.append(str(args[2]))

    event.listen(migrated_engine, "before_cursor_execute", registrar)
    try:
        yield registradas
    finally:
        event.remove(migrated_engine, "before_cursor_execute", registrar)


def crear_socio(
    escritura: SqlAlchemyEscrituraCarga,
    cedula: str | None,
    nombre: str = NOMBRE,
    celular: str | None = None,
    correo: str | None = None,
) -> int:
    return escritura.crear_socios([NuevoSocio(cedula, nombre.title(), nombre, celular, correo)])[0]


def borrar(db_session: Session, tabla: str, fila_id: int) -> None:
    assert tabla in {"socios", "membresias"}  # lista blanca: el nombre nunca viene de fuera
    db_session.execute(
        text(f"UPDATE {tabla} SET deleted_at = :t WHERE id = :id"),  # noqa: S608 - lista blanca
        {"t": INSTANTE, "id": fila_id},
    )


def crear_carga(escritura: SqlAlchemyEscrituraCarga) -> int:
    return escritura.crear_carga(
        NuevaCarga(
            tipo=TipoCarga.PLANTILLA,
            fecha_carga=INSTANTE,
            nombre_archivo="plantilla_valida.xlsx",
            filas_leidas=1,
            filas_guardadas=1,
            filas_duplicadas=0,
            socios_enlazados=0,
        )
    )


def nueva_membresia(
    socio_id: int,
    carga_id: int,
    origen: OrigenMembresia = OrigenMembresia.PLANTILLA,
    inicio: date | None = INICIO,
    fin: date | None = FIN,
    plan: Plan = Plan.MENSUAL,
) -> NuevaMembresia:
    return NuevaMembresia(
        socio_id=socio_id,
        carga_id=carga_id,
        plan=plan,
        forma_pago=FormaPago.EFECTIVO,
        origen=origen,
        inicio_aproximado=inicio is None,
        fecha_actividad=inicio or INICIO,
        fecha_inicio=inicio,
        fecha_vencimiento=fin,
    )


def test_repositories_implement_the_ports(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    assert isinstance(consultas, ConsultasCarga)
    assert isinstance(escritura, EscrituraCarga)


# ------------------------------------------------------------------ socios_por_cedulas
def test_socios_por_cedulas_finds_exact_cedula(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    socio_id = crear_socio(escritura, "0912345678")

    assert consultas.socios_por_cedulas({"0912345678"}) == {"0912345678": socio_id}


def test_socios_por_cedulas_finds_historic_cedula_without_leading_zero(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    socio_id = crear_socio(escritura, "912345678")

    assert consultas.socios_por_cedulas({"0912345678"}) == {"0912345678": socio_id}


def test_socios_por_cedulas_prefers_exact_match_over_variant(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    crear_socio(escritura, "912345678", nombre="SOCIO HISTORICO UNO")
    exacto = crear_socio(escritura, "0912345678")

    assert consultas.socios_por_cedulas(["0912345678"]) == {"0912345678": exacto}


def test_socios_por_cedulas_excludes_soft_deleted_and_unknown(
    db_session: Session,
    consultas: SqlAlchemyConsultasCarga,
    escritura: SqlAlchemyEscrituraCarga,
) -> None:
    borrado = crear_socio(escritura, "0912345678")
    borrar(db_session, "socios", borrado)

    assert consultas.socios_por_cedulas({"0912345678", "1700000019"}) == {}
    assert consultas.socios_por_cedulas([]) == {}


def test_socios_por_cedulas_single_parametrized_query(
    consultas: SqlAlchemyConsultasCarga,
    escritura: SqlAlchemyEscrituraCarga,
    sentencias: list[str],
) -> None:
    crear_socio(escritura, "1700000019")
    sentencias.clear()

    consultas.socios_por_cedulas({"1700000019", "0912345678"})

    assert len(sentencias) == 1
    assert "1700000019" not in sentencias[0]
    assert "deleted_at IS NULL" in sentencias[0]


# ------------------------------------------------------------------ socios sin cedula por nombre
def test_socios_sin_cedula_por_nombres_single_candidate(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    socio_id = crear_socio(escritura, None)

    assert consultas.socios_sin_cedula_por_nombres({NOMBRE}) == {NOMBRE: [socio_id]}


def test_socios_sin_cedula_por_nombres_homonyms_return_all_ids_in_order(
    consultas: SqlAlchemyConsultasCarga, escritura: SqlAlchemyEscrituraCarga
) -> None:
    primero = crear_socio(escritura, None)
    segundo = crear_socio(escritura, None)

    assert consultas.socios_sin_cedula_por_nombres([NOMBRE]) == {NOMBRE: [primero, segundo]}


def test_socios_sin_cedula_por_nombres_skips_with_cedula_or_deleted(
    db_session: Session,
    consultas: SqlAlchemyConsultasCarga,
    escritura: SqlAlchemyEscrituraCarga,
) -> None:
    crear_socio(escritura, "1700000019")
    borrado = crear_socio(escritura, None)
    borrar(db_session, "socios", borrado)

    assert consultas.socios_sin_cedula_por_nombres({NOMBRE}) == {}
    assert consultas.socios_sin_cedula_por_nombres(set()) == {}


def test_socios_sin_cedula_por_nombres_uses_partial_index(
    db_session: Session, migrated_engine: Engine, escritura: SqlAlchemyEscrituraCarga
) -> None:
    crear_socio(escritura, None)
    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    consultas = SqlAlchemyConsultasCarga(db_session, Reloj(INSTANTE))
    capturadas: list[tuple[str, Any]] = []

    def capturar(*args: Any) -> None:
        capturadas.append((str(args[2]), args[3]))

    event.listen(migrated_engine, "before_cursor_execute", capturar)
    try:
        consultas.socios_sin_cedula_por_nombres({NOMBRE})
    finally:
        event.remove(migrated_engine, "before_cursor_execute", capturar)

    assert len(capturadas) == 1
    sentencia, parametros = capturadas[0]
    assert NOMBRE not in sentencia  # parametrizada
    plan = db_session.connection().exec_driver_sql(f"EXPLAIN {sentencia}", parametros).all()
    texto = " | ".join(str(fila[0]) for fila in plan)
    assert "ix_socios_nombre_normalizado_sin_cedula" in texto


# ------------------------------------------------------------------ claves_existentes
def test_claves_existentes_returns_non_deleted_keys_of_historic_and_template(
    db_session: Session,
    consultas: SqlAlchemyConsultasCarga,
    escritura: SqlAlchemyEscrituraCarga,
    sentencias: list[str],
) -> None:
    socio_id = crear_socio(escritura, "1700000019")
    otro = crear_socio(escritura, "1700000027", nombre="OTRO SOCIO FICTICIO")
    carga_id = crear_carga(escritura)
    escritura.insertar_membresias(
        [
            nueva_membresia(socio_id, carga_id, OrigenMembresia.HISTORICO),
            nueva_membresia(socio_id, carga_id, fin=date(2026, 12, 1), plan=Plan.TRIMESTRAL),
            nueva_membresia(socio_id, carga_id, inicio=None),
            nueva_membresia(socio_id, carga_id, inicio=date(2025, 1, 1), fin=date(2025, 2, 1)),
            nueva_membresia(otro, carga_id),
        ]
    )
    borrada = db_session.execute(
        text("SELECT id FROM membresias WHERE socio_id = :s AND fecha_inicio = :i"),
        {"s": socio_id, "i": date(2025, 1, 1)},
    ).scalar_one()
    borrar(db_session, "membresias", int(borrada))
    sentencias.clear()

    claves = consultas.claves_existentes([socio_id])

    assert claves == {
        ClaveMembresia(socio_id, INICIO, FIN, Plan.MENSUAL),
        ClaveMembresia(socio_id, INICIO, date(2026, 12, 1), Plan.TRIMESTRAL),
    }
    assert all(type(clave) is ClaveDominio for clave in claves)
    assert len(sentencias) == 1
    assert "deleted_at IS NULL" in sentencias[0]
    assert consultas.claves_existentes([]) == set()


# ------------------------------------------------------------------ escritura
def test_asignar_cedula_sets_cedula_and_clock_updated_at_and_fills_only_empty_contacts(
    db_session: Session, reloj: Reloj, escritura: SqlAlchemyEscrituraCarga
) -> None:
    vacio = crear_socio(escritura, None)
    con_contacto = crear_socio(
        escritura, None, nombre="BEATRIZ FICTICIA", celular="0980000001", correo="b@example.com"
    )
    reloj.instante = DESPUES

    escritura.asignar_cedula(vacio, "1700000019", "0980000002", "a@example.com")
    escritura.asignar_cedula(con_contacto, "1700000027", "0980000003", "otro@example.com")

    filas = {
        f.id: f
        for f in db_session.execute(
            select(Socio.id, Socio.cedula, Socio.celular, Socio.correo, Socio.updated_at)
        ).all()
    }
    assert (filas[vacio].cedula, filas[vacio].celular, filas[vacio].correo) == (
        "1700000019",
        "0980000002",
        "a@example.com",
    )
    assert (
        filas[con_contacto].cedula,
        filas[con_contacto].celular,
        filas[con_contacto].correo,
    ) == ("1700000027", "0980000001", "b@example.com")
    assert filas[vacio].updated_at == DESPUES


def test_asignar_cedula_without_new_contact_keeps_existing(
    db_session: Session, escritura: SqlAlchemyEscrituraCarga
) -> None:
    socio_id = crear_socio(escritura, None, celular="0980000001")

    escritura.asignar_cedula(socio_id, "1700000019", None, None)

    fila = db_session.execute(
        select(Socio.cedula, Socio.celular, Socio.correo).where(Socio.id == socio_id)
    ).one()
    assert tuple(fila) == ("1700000019", "0980000001", None)


def test_escritura_inserts_socios_membresias_and_carga_in_callers_transaction(
    db_session: Session, escritura: SqlAlchemyEscrituraCarga
) -> None:
    ids = escritura.crear_socios(
        [
            NuevoSocio("1700000019", "Socio Uno", "SOCIO UNO"),
            NuevoSocio("1700000027", "Socio Dos", "SOCIO DOS"),
        ]
    )
    carga_id = crear_carga(escritura)

    insertadas = escritura.insertar_membresias([nueva_membresia(i, carga_id) for i in ids])

    assert len(ids) == 2
    assert ids[0] < ids[1]
    assert insertadas == 2
    assert db_session.in_transaction()
    total = db_session.execute(
        text("SELECT count(*) FROM membresias WHERE carga_id = :c"), {"c": carga_id}
    ).scalar_one()
    assert total == 2


def test_repository_module_never_controls_the_transaction_nor_reads_system_time() -> None:
    fuente = inspect.getsource(modulo_cargas)

    for metodo in ("commit", "rollback", "begin", "close", "delete"):
        assert re.search(rf"\.{metodo}\s*\(", fuente) is None, metodo
    assert re.search(r"\.add(_all)?\s*\(", fuente) is None
    assert "datetime.now" not in fuente
    assert "date.today" not in fuente
