"""Unidad de trabajo de cargas contra PostgreSQL real (R-007 T9).

Aislamiento entre usuarios: no aplica (RT-12, sin login; acceso por IP, CU-00).
Datos 100 % sinteticos. Cada prueba trunca las tablas al empezar y al terminar (la base se
llama ``*_test``, lo garantiza ``test_database_url``).
"""

import threading
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from app.application.cargas.ports import ContextoCargas
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan, TipoCarga
from app.infrastructure.persistence.unit_of_work_cargas import (
    CLAVE_BLOQUEO_CARGAS,
    SqlAlchemyUnidadDeTrabajoCargas,
)
from tests.integration.api.listas_datos import limpiar

pytestmark = pytest.mark.integration

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)


class Reloj:
    def now(self) -> datetime:
        return INSTANTE


@pytest.fixture
def base(migrated_engine: Engine) -> Iterator[Engine]:
    limpiar(migrated_engine)
    try:
        yield migrated_engine
    finally:
        limpiar(migrated_engine)


def _escribir_todo(contexto: ContextoCargas) -> None:
    [socio_id] = contexto.escritura.crear_socios(
        [NuevoSocio("1700000019", "Socio Ficticio", "SOCIO FICTICIO")]
    )
    carga_id = contexto.escritura.crear_carga(
        NuevaCarga(TipoCarga.PLANTILLA, INSTANTE, "plantilla.xlsx", 1, 1, 0, 0)
    )
    contexto.escritura.insertar_membresias(
        [
            NuevaMembresia(
                socio_id=socio_id,
                carga_id=carga_id,
                plan=Plan.MENSUAL,
                forma_pago=FormaPago.EFECTIVO,
                origen=OrigenMembresia.PLANTILLA,
                inicio_aproximado=False,
                fecha_actividad=date(2026, 9, 1),
                fecha_inicio=date(2026, 9, 1),
                fecha_vencimiento=date(2026, 10, 1),
            )
        ]
    )


def _conteos(engine: Engine) -> list[int]:
    with engine.connect() as conexion:
        fila = conexion.execute(
            text(
                "SELECT (SELECT count(*) FROM socios), (SELECT count(*) FROM membresias), "
                "(SELECT count(*) FROM cargas)"
            )
        ).one()
    return [int(valor) for valor in fila]


def test_uow_exit_without_commit_leaves_nothing(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoCargas(base, Reloj())

    with uow() as contexto:
        contexto.bloquear()
        _escribir_todo(contexto)

    assert _conteos(base) == [0, 0, 0]


def test_uow_exception_rolls_back_everything(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoCargas(base, Reloj())

    with pytest.raises(RuntimeError), uow() as contexto:
        _escribir_todo(contexto)
        raise RuntimeError("fallo simulado")

    assert _conteos(base) == [0, 0, 0]


def test_uow_commit_persists_all_writes(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoCargas(base, Reloj())

    with uow() as contexto:
        contexto.bloquear()
        _escribir_todo(contexto)
        contexto.commit()

    assert _conteos(base) == [1, 1, 1]


def test_bloquear_second_session_waits_until_first_commits(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoCargas(base, Reloj())
    adquirido = threading.Event()
    instantes: dict[str, float] = {}

    def segunda() -> None:
        with uow() as contexto:
            contexto.bloquear()
            instantes["segunda"] = time.monotonic()
            adquirido.set()

    with uow() as contexto:
        contexto.bloquear()
        hilo = threading.Thread(target=segunda, daemon=True)
        hilo.start()
        assert not adquirido.wait(0.5), "la segunda sesion tomo el bloqueo a la vez"
        instantes["primera_libera"] = time.monotonic()
        contexto.commit()

    hilo.join(timeout=10)
    assert adquirido.is_set()
    assert instantes["segunda"] >= instantes["primera_libera"]


def test_bloquear_with_short_lock_timeout_expires_while_held(base: Engine) -> None:
    uow = SqlAlchemyUnidadDeTrabajoCargas(base, Reloj())

    with uow() as contexto:
        contexto.bloquear()
        with base.connect() as otra, otra.begin():
            otra.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError):
                otra.execute(
                    text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": CLAVE_BLOQUEO_CARGAS}
                )

    # Sin commit el bloqueo se libera al revertir: otra sesion lo toma sin esperar.
    with base.connect() as otra, otra.begin():
        assert otra.execute(
            text("SELECT pg_try_advisory_xact_lock(:clave)"), {"clave": CLAVE_BLOQUEO_CARGAS}
        ).scalar_one()
