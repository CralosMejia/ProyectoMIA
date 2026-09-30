"""CU-10: registrar el resultado de una gestion (R-009 T10, decision (h))."""

from datetime import date
from typing import Any

import pytest

from app.application.gestiones.dtos import RegistrarResultadoDTO
from app.application.gestiones.registrar_resultado import GestionNoExisteError, RegistrarResultado
from app.domain.common.enums import EstadoGestion, Respuesta
from app.domain.gestiones.errores import (
    FechaSeguimientoFueraDeRangoError,
    GestionCerradaError,
    ResultadoIncoherenteError,
)
from tests.unit.application.gestiones.dobles import INSTANTE, entorno, gestion_pendiente

pytestmark = pytest.mark.unit


def dto(**cambios: Any) -> RegistrarResultadoDTO:
    datos: dict[str, Any] = {
        "contactado": True,
        "campania_ofrecida": "SI",
        "campania_aceptada": "SI",
        "renovo_declarado": "PENDIENTE",
        "fecha_contacto": date(2026, 9, 29),
        "observaciones": "Acepta la campana.",
        "responsable": "Andrea",
        "fecha_seguimiento": date(2026, 10, 27),
    }
    datos.update(cambios)
    return RegistrarResultadoDTO.model_validate(datos)


def test_ejecutar_renovo_pendiente_sigue_pendiente_y_actualiza_seguimiento() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)

    resultado = RegistrarResultado(uow, reloj).ejecutar(gestion_id, dto())

    assert resultado.estado is EstadoGestion.PENDIENTE
    assert resultado.fecha_seguimiento == date(2026, 10, 27)
    assert resultado.contactado is True
    assert resultado.campania_ofrecida is Respuesta.SI
    assert resultado.campania_aceptada is Respuesta.SI
    assert resultado.renovo_declarado is Respuesta.PENDIENTE
    assert resultado.fecha_cierre is None
    assert gestiones.bloqueos == [gestion_id]
    assert uow.commits == 1


def test_ejecutar_renovo_pendiente_sin_fecha_conserva_la_anterior() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)

    resultado = RegistrarResultado(uow, reloj).ejecutar(gestion_id, dto(fecha_seguimiento=None))

    assert resultado.fecha_seguimiento == date(2026, 10, 30)
    assert uow.commits == 1


def test_ejecutar_renovo_no_cierra_con_cerrada_en_del_reloj_e_ignora_fecha() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)

    resultado = RegistrarResultado(uow, reloj).ejecutar(
        gestion_id, dto(renovo_declarado="NO", fecha_seguimiento=date(2027, 1, 1))
    )

    assert resultado.estado is EstadoGestion.CERRADA
    assert resultado.fecha_cierre == INSTANTE
    assert resultado.fecha_seguimiento == date(2026, 10, 30)
    assert gestiones.resultados[0][1].cerrada_en == INSTANTE
    assert uow.commits == 1


def test_ejecutar_gestion_cerrada_lanza_error_sin_commit() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)
    RegistrarResultado(uow, reloj).ejecutar(gestion_id, dto(renovo_declarado="SI"))
    commits = uow.commits
    resultados = len(gestiones.resultados)

    with pytest.raises(GestionCerradaError):
        RegistrarResultado(uow, reloj).ejecutar(gestion_id, dto())

    assert uow.commits == commits
    assert len(gestiones.resultados) == resultados


def test_ejecutar_no_contactado_y_ofrecida_si_lanza_incoherente_sin_commit() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)

    with pytest.raises(ResultadoIncoherenteError):
        RegistrarResultado(uow, reloj).ejecutar(
            gestion_id,
            dto(contactado=False, campania_aceptada="NO_APLICA", fecha_contacto=None),
        )

    assert gestiones.resultados == []
    assert uow.commits == 0


def test_ejecutar_sin_campania_y_ofrecida_no_lanza_incoherente_sin_commit() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones, campania_id=None, campania_nombre=None)

    with pytest.raises(ResultadoIncoherenteError):
        RegistrarResultado(uow, reloj).ejecutar(
            gestion_id, dto(campania_ofrecida="NO", campania_aceptada="NO_APLICA")
        )

    assert gestiones.resultados == []
    assert uow.commits == 0


def test_ejecutar_fecha_seguimiento_fuera_de_rango_con_pendiente_lanza_error() -> None:
    uow, gestiones, reloj = entorno()
    gestion_id = gestion_pendiente(gestiones)

    with pytest.raises(FechaSeguimientoFueraDeRangoError):
        RegistrarResultado(uow, reloj).ejecutar(
            gestion_id, dto(fecha_seguimiento=date(2026, 11, 5))
        )

    assert gestiones.resultados == []
    assert uow.commits == 0


def test_ejecutar_gestion_inexistente_lanza_error_sin_commit() -> None:
    uow, _, reloj = entorno()

    with pytest.raises(GestionNoExisteError):
        RegistrarResultado(uow, reloj).ejecutar(99, dto())

    assert uow.commits == 0
