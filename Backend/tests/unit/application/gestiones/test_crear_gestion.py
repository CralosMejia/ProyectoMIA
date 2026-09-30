"""CU-08: crear la gestion (R-009 T9, decisiones (b), (c) y (g); R-010 T5, (c) y (d))."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

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


AHORA_30_SEP = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)


def nueva_gestion(*, estado: EstadoGestion, cerrada_en: datetime | None) -> NuevaGestion:
    return NuevaGestion(
        prediccion_id=15,
        membresia_id=70,
        campania_id=None,
        campania_nombre=None,
        fecha_asignacion=date(2026, 9, 30),
        fecha_seguimiento=date(2026, 9, 30),
        responsable=None,
        estado=estado,
        cerrada_en=cerrada_en,
    )


def dto(
    *,
    campania_id: int | None = 3,
    fecha: date | None = date(2026, 10, 30),
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
            cerrada_en=None,
        )
    ]
    assert uow.commits == 1
    assert resultado.fecha_cierre is None
    assert resultado.score == Decimal("0.8123")
    assert resultado.nivel_riesgo is NivelRiesgo.ALTO
    assert resultado.modelo_version == "v3"
    assert resultado.campania_nombre == "Renovacion anticipada"
    assert resultado.estado is EstadoGestion.PENDIENTE
    assert resultado.fecha_asignacion == INSTANTE
    assert resultado.fecha_seguimiento == date(2026, 10, 30)
    assert resultado.prediccion_id == 15


def test_ejecutar_sin_campania_guarda_gestion_cerrada_sin_seguimiento_ni_resultado() -> None:
    reloj = RelojFijo(AHORA_30_SEP)
    uow, gestiones, _ = entorno(reloj=reloj, campanias=CAMPANIAS)

    resultado = CrearGestion(uow, reloj).ejecutar(
        CrearGestionDTO(prediccion_id=15, campania_id=None)
    )

    assert gestiones.creadas == [
        NuevaGestion(
            prediccion_id=15,
            membresia_id=70,
            campania_id=None,
            campania_nombre=None,
            fecha_asignacion=date(2026, 9, 30),
            fecha_seguimiento=date(2026, 9, 30),
            responsable=None,
            estado=EstadoGestion.CERRADA,
            cerrada_en=AHORA_30_SEP,
        )
    ]
    assert uow.commits == 1
    assert resultado.estado is EstadoGestion.CERRADA
    assert resultado.fecha_cierre == AHORA_30_SEP
    assert resultado.fecha_asignacion == AHORA_30_SEP
    assert resultado.campania_id is None
    assert resultado.campania_nombre is None
    assert resultado.responsable is None
    assert resultado.contactado is None
    assert resultado.campania_ofrecida is None
    assert resultado.campania_aceptada is None
    assert resultado.renovo_declarado is None
    assert resultado.fecha_contacto is None
    assert resultado.observaciones is None


def test_ejecutar_sin_campania_ignora_fecha_y_responsable_enviados() -> None:
    reloj = RelojFijo(AHORA_30_SEP)
    uow, gestiones, _ = entorno(reloj=reloj, campanias=CAMPANIAS)

    resultado = CrearGestion(uow, reloj).ejecutar(
        dto(campania_id=None, fecha=date(2027, 1, 1), responsable="Andrea")
    )

    assert gestiones.creadas[0].fecha_seguimiento == date(2026, 9, 30)
    assert gestiones.creadas[0].responsable is None
    assert gestiones.creadas[0].estado is EstadoGestion.CERRADA
    assert resultado.fecha_seguimiento == date(2026, 9, 30)
    assert resultado.responsable is None
    assert uow.commits == 1


def test_ejecutar_sin_campania_con_plazo_terminado_se_crea_igual() -> None:
    reloj = RelojFijo(AHORA_30_SEP)
    uow, gestiones, _ = entorno(
        reloj=reloj, predicciones=[prediccion(vencimiento=date(2026, 8, 29))], campanias=CAMPANIAS
    )

    resultado = CrearGestion(uow, reloj).ejecutar(dto(campania_id=None, fecha=None))

    assert resultado.estado is EstadoGestion.CERRADA
    assert len(gestiones.creadas) == 1
    assert uow.commits == 1


def test_ejecutar_sin_campania_con_gestion_en_el_ciclo_lanza_duplicada_sin_commit() -> None:
    uow, gestiones, reloj = entorno(
        predicciones=[prediccion(15), prediccion(16, membresia_id=70)], campanias=CAMPANIAS
    )
    gestion_pendiente(gestiones)
    creadas_antes = len(gestiones.creadas)

    with pytest.raises(GestionDuplicadaError):
        CrearGestion(uow, reloj).ejecutar(dto(prediccion_id=16, campania_id=None, fecha=None))

    assert len(gestiones.creadas) == creadas_antes
    assert uow.commits == 0


def test_ejecutar_sin_campania_prediccion_inexistente_lanza_error_sin_commit() -> None:
    uow, gestiones, reloj = entorno(campanias=CAMPANIAS)

    with pytest.raises(PrediccionNoExisteError):
        CrearGestion(uow, reloj).ejecutar(dto(prediccion_id=999, campania_id=None, fecha=None))

    assert gestiones.creadas == []
    assert uow.commits == 0


def test_dto_con_campania_y_sin_fecha_de_seguimiento_es_invalido() -> None:
    with pytest.raises(ValidationError):
        CrearGestionDTO(prediccion_id=1, campania_id=3)


def test_dto_sin_campania_no_exige_fecha_de_seguimiento() -> None:
    datos = CrearGestionDTO(prediccion_id=1)

    assert datos.campania_id is None
    assert datos.fecha_seguimiento is None
    assert datos.responsable is None


def test_nueva_gestion_cerrada_sin_instante_de_cierre_es_invalida() -> None:
    with pytest.raises(ValueError, match="cerrada_en"):
        nueva_gestion(estado=EstadoGestion.CERRADA, cerrada_en=None)


def test_nueva_gestion_pendiente_con_instante_de_cierre_es_invalida() -> None:
    with pytest.raises(ValueError, match="cerrada_en"):
        nueva_gestion(estado=EstadoGestion.PENDIENTE, cerrada_en=INSTANTE)


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
