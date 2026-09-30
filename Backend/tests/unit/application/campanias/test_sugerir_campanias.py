"""CU-07: campanas sugeridas para una prediccion de la lista (R-009 T6)."""

import pytest

from app.application.campanias.dtos import CampaniaDTO
from app.application.campanias.sugerir_campanias import PrediccionNoExisteError, SugerirCampanias
from app.domain.common.enums import NivelRiesgo, Plan
from tests.unit.application.campanias.dobles import UnidadFalsa, guardada

pytestmark = pytest.mark.unit

ALTO, MEDIO, BAJO = NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO


def test_ejecutar_pide_compatibles_y_devuelve_en_orden_del_repositorio() -> None:
    uow = UnidadFalsa()
    uow.contexto.perfiles.perfiles = {15: (ALTO, Plan.MENSUAL)}
    uow.contexto.campanias.campanias = {
        1: guardada(1, nombre="b", prioridad=2),
        2: guardada(2, nombre="Solo bajo", niveles_riesgo=(BAJO,)),
        3: guardada(3, nombre="alfa", prioridad=1, niveles_riesgo=(ALTO, MEDIO)),
    }

    resultado = SugerirCampanias(uow).ejecutar(15)

    assert uow.contexto.campanias.consultas_compatibles == [(ALTO, Plan.MENSUAL)]
    assert [c.nombre for c in resultado] == ["alfa", "b"]
    assert all(isinstance(c, CampaniaDTO) for c in resultado)
    assert uow.contexto.commits == 0


def test_ejecutar_sin_compatibles_devuelve_lista_vacia() -> None:
    uow = UnidadFalsa()
    uow.contexto.perfiles.perfiles = {15: (ALTO, Plan.ANUAL)}
    uow.contexto.campanias.campanias = {1: guardada(1)}

    assert SugerirCampanias(uow).ejecutar(15) == []


def test_ejecutar_prediccion_inexistente_lanza_error() -> None:
    uow = UnidadFalsa()

    with pytest.raises(PrediccionNoExisteError, match=r"La prediccion no existe\."):
        SugerirCampanias(uow).ejecutar(404)

    assert uow.contexto.campanias.consultas_compatibles == []


def test_ejecutar_plan_diario_devuelve_vacio_sin_consultar_campanias() -> None:
    uow = UnidadFalsa()
    uow.contexto.perfiles.perfiles = {15: (ALTO, Plan.DIARIO)}
    uow.contexto.campanias.campanias = {1: guardada(1)}

    assert SugerirCampanias(uow).ejecutar(15) == []
    assert uow.contexto.campanias.consultas_compatibles == []
    assert uow.contexto.commits == 0
