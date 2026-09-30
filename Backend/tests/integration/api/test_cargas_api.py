"""API de cargas (CU-01) contra PostgreSQL real: vista previa y confirmacion (R-007 T10).

Aislamiento entre usuarios: NO APLICA. No hay login (RT-12): el acceso se controla por IP
(CU-00) y no existe un propietario de datos por usuario.

Datos 100 % sinteticos: fixtures de ``tests/fixtures`` y libros construidos en ``tmp_path``
con nombres y cedulas ficticios (``cedula_valida``). Migracion sintetica completada con
``base_migrada`` y reloj fijo con ``fijar_reloj_api``.
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.application.historial.ports import NuevaMembresia, NuevoSocio
from app.domain.common.enums import FormaPago, OrigenMembresia, Plan, TipoCarga
from app.domain.historico.normalizacion import normalizar_nombre
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)
from tests.fixtures.esperado import LIBRO_2025
from tests.fixtures.generar_fixtures import (
    DIR_HISTORICO,
    DIR_PLANTILLAS,
    PLANTILLA_CEDULA_INVALIDA,
    PLANTILLA_VALIDA,
    cedula_valida,
    fila_plantilla,
    generar_plantilla,
)
from tests.integration.api.listas_datos import RELOJ_API, fijar_reloj_api

pytestmark = pytest.mark.integration

VISTA_PREVIA = "/api/v1/cargas/vista-previa"
CARGAS = "/api/v1/cargas"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_BYTES = 5 * 1024 * 1024
_CONTEOS = (
    "SELECT (SELECT count(*) FROM socios), (SELECT count(*) FROM membresias), "
    "(SELECT count(*) FROM cargas)"
)


class Reloj:
    def now(self) -> datetime:
        return datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def cliente(contract_app: FastAPI, base_migrada: Engine) -> Iterator[TestClient]:
    fijar_reloj_api(contract_app)
    with TestClient(contract_app, raise_server_exceptions=False) as test_client:
        yield test_client


def _archivo(contenido: bytes, nombre: str = "plantilla.xlsx") -> dict[str, Any]:
    return {"archivo": (nombre, contenido, XLSX)}


def _fixture(nombre: str) -> bytes:
    return (DIR_PLANTILLAS / nombre).read_bytes()


def _plantilla(tmp_path: Path, filas: list[list[object]]) -> bytes:
    return generar_plantilla(filas, tmp_path / "plantilla.xlsx").read_bytes()


def _conteos(engine: Engine) -> dict[str, int]:
    with engine.connect() as conexion:
        fila = conexion.execute(text(_CONTEOS)).one()
    return {"socios": int(fila[0]), "membresias": int(fila[1]), "cargas": int(fila[2])}


def _fila(indice: int, nombre: str, cedula: str) -> list[object]:
    valores = fila_plantilla(indice)
    valores[1] = nombre
    valores[2] = cedula
    return valores


def _sembrar_socios(engine: Engine, socios: list[NuevoSocio]) -> list[int]:
    with Session(engine) as session, session.begin():
        return SqlAlchemySocioRepository(session, Reloj()).insertar_en_bloque(socios)


def _cedula_de(engine: Engine, socio_id: int) -> str | None:
    with engine.connect() as conexion:
        valor = conexion.execute(
            text("SELECT cedula FROM socios WHERE id = :id"), {"id": socio_id}
        ).scalar_one()
        return None if valor is None else str(valor)


# ---------------------------------------------------------------- vista previa


def test_vista_previa_valid_template_returns_counts_and_saves_nothing(
    cliente: TestClient, base_migrada: Engine
) -> None:
    antes = _conteos(base_migrada)

    response = cliente.post(VISTA_PREVIA, files=_archivo(_fixture(PLANTILLA_VALIDA)))

    assert response.status_code == 200
    body = response.json()
    assert body["filas_leidas"] == 6
    assert body["filas_validas"] == 6
    assert body["filas_con_error"] == 0
    assert body["filas_duplicadas"] == 0
    assert body["errores"] == []
    assert body["puede_confirmar"] is True
    assert body["vencimiento_desde"] is not None
    assert body["vencimiento_hasta"] is not None
    assert _conteos(base_migrada) == antes


def test_invalid_cedula_preview_reports_error_and_confirm_returns_422(
    cliente: TestClient, base_migrada: Engine
) -> None:
    contenido = _fixture(PLANTILLA_CEDULA_INVALIDA)
    antes = _conteos(base_migrada)

    vista = cliente.post(VISTA_PREVIA, files=_archivo(contenido))
    confirmacion = cliente.post(CARGAS, files=_archivo(contenido))

    assert vista.status_code == 200
    body = vista.json()
    assert body["puede_confirmar"] is False
    assert body["filas_con_error"] == 1
    assert [(e["fila"], e["columna"]) for e in body["errores"]] == [(3, "C")]
    assert confirmacion.status_code == 422
    assert confirmacion.json() == {
        "error": {
            "code": "domain_rule_violated",
            "message": "Hay filas con error; corrija el archivo y vuelva a subirlo.",
        }
    }
    assert _conteos(base_migrada) == antes


# ---------------------------------------------------------------- confirmacion


def test_confirm_valid_template_saves_and_second_time_is_all_duplicate(
    cliente: TestClient, base_migrada: Engine
) -> None:
    contenido = _fixture(PLANTILLA_VALIDA)
    antes = _conteos(base_migrada)

    primera = cliente.post(CARGAS, files=_archivo(contenido, "C:\\carpeta\\septiembre.xlsx"))

    assert primera.status_code == 201
    carga = primera.json()
    assert carga["filas_leidas"] == 6
    assert carga["filas_guardadas"] == 6
    assert carga["filas_duplicadas"] == 0
    assert carga["nombre_archivo"] == "septiembre.xlsx"
    assert datetime.fromisoformat(carga["fecha_carga"]) == RELOJ_API
    despues = _conteos(base_migrada)
    assert despues["membresias"] == antes["membresias"] + 6
    assert despues["cargas"] == antes["cargas"] + 1

    vista = cliente.post(VISTA_PREVIA, files=_archivo(contenido))
    segunda = cliente.post(CARGAS, files=_archivo(contenido))

    assert vista.status_code == 200
    assert vista.json()["filas_duplicadas"] == 6
    assert vista.json()["puede_confirmar"] is False
    assert segunda.status_code == 422
    assert segunda.json() == {
        "error": {
            "code": "domain_rule_violated",
            "message": "El archivo no tiene filas nuevas para guardar.",
        }
    }
    assert _conteos(base_migrada) == despues


def test_confirm_links_unique_name_without_cedula_and_assigns_it(
    cliente: TestClient, base_migrada: Engine, tmp_path: Path
) -> None:
    nombre = "Ficticio Enlazable Unico"
    cedula = cedula_valida(801)
    [socio_id] = _sembrar_socios(
        base_migrada, [NuevoSocio(None, nombre, normalizar_nombre(nombre))]
    )

    response = cliente.post(
        CARGAS, files=_archivo(_plantilla(tmp_path, [_fila(0, nombre, cedula)]))
    )

    assert response.status_code == 201
    assert response.json()["socios_enlazados"] >= 1
    assert response.json()["avisos_enlace"] == []
    assert _cedula_de(base_migrada, socio_id) == cedula


def test_confirm_homonyms_create_new_member_with_notice(
    cliente: TestClient, base_migrada: Engine, tmp_path: Path
) -> None:
    nombre = "Ficticio Homonimo Repetido"
    ids = _sembrar_socios(
        base_migrada, [NuevoSocio(None, nombre, normalizar_nombre(nombre)) for _ in range(2)]
    )
    antes = _conteos(base_migrada)

    response = cliente.post(
        CARGAS, files=_archivo(_plantilla(tmp_path, [_fila(0, nombre, cedula_valida(802))]))
    )

    assert response.status_code == 201
    body = response.json()
    assert body["socios_enlazados"] == 0
    assert body["avisos_enlace"] == [
        "Fila 2: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."
    ]
    assert _conteos(base_migrada)["socios"] == antes["socios"] + 1
    assert [_cedula_de(base_migrada, i) for i in ids] == [None, None]


def test_preview_row_equal_to_migrated_membership_is_duplicate(
    cliente: TestClient, base_migrada: Engine, tmp_path: Path
) -> None:
    nombre = "Ficticio Con Historia"
    cedula = cedula_valida(803)
    fila = _fila(0, nombre, cedula)
    inicio, fin, plan = fila[6], fila[7], fila[5]
    assert isinstance(inicio, date)
    assert isinstance(fin, date)
    assert isinstance(plan, str)
    with Session(base_migrada) as session, session.begin():
        reloj = Reloj()
        [socio_id] = SqlAlchemySocioRepository(session, reloj).insertar_en_bloque(
            [NuevoSocio(cedula, nombre, normalizar_nombre(nombre))]
        )
        # La membresia cuelga de la carga de la migracion historica sintetica (unica).
        carga_id = int(
            session.execute(
                text("SELECT id FROM cargas WHERE tipo = :tipo"),
                {"tipo": TipoCarga.MIGRACION_HISTORICA.value},
            ).scalar_one()
        )
        SqlAlchemyMembresiaRepository(session, reloj).insertar_en_bloque(
            [
                NuevaMembresia(
                    socio_id=socio_id,
                    carga_id=carga_id,
                    plan=Plan(plan),
                    forma_pago=FormaPago.EFECTIVO,
                    origen=OrigenMembresia.HISTORICO,
                    inicio_aproximado=False,
                    fecha_actividad=inicio,
                    fecha_inicio=inicio,
                    fecha_vencimiento=fin,
                )
            ]
        )

    otra = _fila(1, "Ficticio Nuevo", cedula_valida(804))
    response = cliente.post(VISTA_PREVIA, files=_archivo(_plantilla(tmp_path, [fila, otra])))

    assert response.status_code == 200
    body = response.json()
    assert body["filas_validas"] == 2
    assert body["filas_duplicadas"] == 1
    assert body["puede_confirmar"] is True


# ---------------------------------------------------------------- errores de archivo


@pytest.mark.parametrize("path", [VISTA_PREVIA, CARGAS])
@pytest.mark.parametrize(
    ("contenido", "nombre", "mensaje"),
    [
        (
            lambda: _fixture("plantilla_501_filas.xlsx"),
            "plantilla_501_filas.xlsx",
            "El archivo tiene más de 500 filas con datos; divídalo en varios archivos.",
        ),
        (
            lambda: (DIR_HISTORICO / LIBRO_2025).read_bytes(),
            LIBRO_2025,
            "El archivo tiene el formato antiguo de hojas mensuales; use la plantilla oficial "
            "de carga.",
        ),
        (
            lambda: b"esto es un texto plano, no un libro de Excel",
            "notas.xlsx",
            "El archivo está dañado o no es un .xlsx válido.",
        ),
    ],
    ids=["501-filas", "formato-antiguo", "txt-renombrado"],
)
def test_invalid_file_returns_400_validation_error(
    cliente: TestClient,
    base_migrada: Engine,
    path: str,
    contenido: Any,
    nombre: str,
    mensaje: str,
) -> None:
    antes = _conteos(base_migrada)

    response = cliente.post(path, files=_archivo(contenido(), nombre))

    assert response.status_code == 400
    assert response.json() == {"error": {"code": "validation_error", "message": mensaje}}
    assert _conteos(base_migrada) == antes


@pytest.mark.parametrize("path", [VISTA_PREVIA, CARGAS])
def test_missing_archivo_field_returns_400(cliente: TestClient, path: str) -> None:
    response = cliente.post(path, files={"otro": ("a.xlsx", b"x", XLSX)})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("path", [VISTA_PREVIA, CARGAS])
def test_file_over_5_mb_returns_413(cliente: TestClient, path: str) -> None:
    response = cliente.post(path, files=_archivo(b"0" * (MAX_BYTES + 1)))

    assert response.status_code == 413
    assert response.json() == {
        "error": {
            "code": "payload_too_large",
            "message": "El archivo supera el tamaño máximo permitido.",
        }
    }


@pytest.mark.parametrize("path", [VISTA_PREVIA, CARGAS])
def test_migration_pending_returns_409(
    contract_app: FastAPI, base_limpia: Engine, path: str
) -> None:
    fijar_reloj_api(contract_app)
    with TestClient(contract_app, raise_server_exceptions=False) as cliente:
        response = cliente.post(path, files=_archivo(_fixture(PLANTILLA_VALIDA)))

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "La migracion del historico aun no se ha completado.",
        }
    }
    assert _conteos(base_limpia) == {"socios": 0, "membresias": 0, "cargas": 0}
