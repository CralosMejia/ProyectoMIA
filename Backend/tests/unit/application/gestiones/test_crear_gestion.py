"""CU-08: crear la gestion (R-009 T9, decisiones (b), (c) y (g))."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.campanias.gestionar_campanias import CampaniaNoExisteError
from app.application.campanias.sugerir_campanias import PrediccionNoExisteError
from app.application.gestiones.crear_gestion import CrearGestion
from app.application.gestiones.dtos import CrearGestionDTO
from app.application.gestiones.ports import NuevaGestion
from app.domain.common.enums import EstadoGestion, NivelRiesgo
from app.domain.gestiones.errores import (
    CampaniaNoAplicableError,
    FechaSeguimientoFueraDeRangoError,
    GestionDuplicadaError,
    PlazoSeguimientoTerminadoError,
)
from tests.unit.application.gestiones.dobles import (
    INSTANTE,
    RelojFijo,
    campania,
    entorno,
    gestion_pendiente,
    prediccion,
)

pytestmark = pytest.mark.unit

COMPATIBLE = campania(3, "Renovacion anticipada")
INACTIVA = campania(4, "Inactiva", activa=False)
SOLO_BAJO = campania(5, "Solo bajo", niveles_riesgo=(NivelRiesgo.BAJO,))
CAMPANIAS = [COMPATIBLE, INACTIVA, SOLO_BAJO]


def dto(
    *,
    campania_id: int | None = 3,
    fecha: date = date(2026, 10, 30),
    responsable: str | None = None,
    prediccion_id: int = 15,
) -> CrearGestionDTO:
    return CrearGestionDTO(
        prediccion_id=prediccion_id,
        campania_id=campania_id,
        fecha_seguimiento=fecha,
        responsable=responsable,
    )


def test_ejecutar_campania_compatible_guarda_gestion_pendiente_con_instantanea() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    resultado = CrearGestion(uow, reloj).ejecutar(dto())

    assert gestiones.creadas == [
        NuevaGestion(
            prediccion_id=15,
            membresia_id=70,
            campania_id=3,
            campania_nombre="Renovacion anticipada",
            fecha_asignacion=date(2026, 9, 29),
            fecha_seguimiento=date(2026, 10, 30),
            responsable=None,
            estado=EstadoGestion.PENDIENTE,
        )
    ]
    assert uow.commits == 1
    assert resultado.score == Decimal("0.8123")
    assert resultado.nivel_riesgo is NivelRiesgo.ALTO
    assert resultado.modelo_version == "v3"
    assert resultado.campania_nombre == "Renovacion anticipada"
    assert resultado.estado is EstadoGestion.PENDIENTE
    assert resultado.fecha_asignacion == INSTANTE
    assert resultado.fecha_seguimiento == date(2026, 10, 30)
    assert resultado.prediccion_id == 15


def test_ejecutar_sin_campania_guarda_nombre_nulo() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    resultado = CrearGestion(uow, reloj).ejecutar(dto(campania_id=None))

    assert gestiones.creadas[0].campania_id is None
    assert gestiones.creadas[0].campania_nombre is None
    assert resultado.campania_nombre is None
    assert uow.commits == 1


def test_ejecutar_responsable_llega_recortado_por_el_dto() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    resultado = CrearGestion(uow, reloj).ejecutar(dto(responsable="  Andrea "))

    assert gestiones.creadas[0].responsable == "Andrea"
    assert resultado.responsable == "Andrea"


@pytest.mark.parametrize("fecha", [date(2026, 9, 28), date(2026, 11, 5)])
def test_ejecutar_fecha_fuera_de_rango_lanza_error_sin_commit(fecha: date) -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    with pytest.raises(FechaSeguimientoFueraDeRangoError):
        CrearGestion(uow, reloj).ejecutar(dto(fecha=fecha))

    assert gestiones.creadas == []
    assert uow.commits == 0


def test_ejecutar_plazo_terminado_lanza_error_sin_commit() -> None:
    uow, gestiones, reloj = entorno(
        predicciones=[prediccion(vencimiento=date(2026, 8, 29))], campanias=CAMPANIAS
    )

    with pytest.raises(PlazoSeguimientoTerminadoError):
        CrearGestion(uow, reloj).ejecutar(dto(fecha=date(2026, 9, 29)))

    assert gestiones.creadas == []
    assert uow.commits == 0


@pytest.mark.parametrize("campania_id", [4, 5], ids=["inactiva", "solo-bajo"])
def test_ejecutar_campania_no_aplicable_lanza_error_sin_commit(campania_id: int) -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    with pytest.raises(CampaniaNoAplicableError):
        CrearGestion(uow, reloj).ejecutar(dto(campania_id=campania_id))

    assert gestiones.creadas == []
    assert uow.commits == 0


def test_ejecutar_campania_inexistente_lanza_error_sin_commit() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    with pytest.raises(CampaniaNoExisteError):
        CrearGestion(uow, reloj).ejecutar(dto(campania_id=99))

    assert gestiones.creadas == []
    assert uow.commits == 0


def test_ejecutar_prediccion_inexistente_lanza_error_sin_commit() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    with pytest.raises(PrediccionNoExisteError):
        CrearGestion(uow, reloj).ejecutar(dto(prediccion_id=999))

    assert gestiones.creadas == []
    assert uow.commits == 0


def test_ejecutar_membresia_con_gestion_lanza_duplicada_sin_commit() -> None:
    uow, gestiones, reloj = entorno(
        predicciones=[prediccion(15), prediccion(16, membresia_id=70)], campanias=CAMPANIAS
    )
    gestion_pendiente(gestiones)
    creadas_antes = len(gestiones.creadas)

    with pytest.raises(GestionDuplicadaError):
        CrearGestion(uow, reloj).ejecutar(dto(prediccion_id=16))

    assert len(gestiones.creadas) == creadas_antes
    assert uow.commits == 0


def test_ejecutar_madrugada_utc_usa_hoy_de_ecuador() -> None:
    reloj = RelojFijo(datetime(2026, 9, 30, 3, 0, tzinfo=UTC))
    uow, gestiones, _ = entorno(reloj=reloj, campanias=CAMPANIAS)

    CrearGestion(uow, reloj).ejecutar(dto(fecha=date(2026, 9, 29)))

    assert gestiones.creadas[0].fecha_asignacion == date(2026, 9, 29)
    assert gestiones.creadas[0].fecha_seguimiento == date(2026, 9, 29)
    assert uow.commits == 1
