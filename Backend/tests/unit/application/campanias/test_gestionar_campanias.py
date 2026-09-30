"""CU-06: listar, crear, editar e inactivar campanas (R-009 T5), con dobles en memoria."""

import pytest
from pydantic import ValidationError

from app.application.campanias.dtos import CampaniaDTO, CampaniaEntradaDTO
from app.application.campanias.gestionar_campanias import (
    CampaniaNoExisteError,
    CrearCampania,
    EditarCampania,
    InactivarCampania,
    ListarCampanias,
)
from app.application.campanias.ports import CampaniaRepository
from app.domain.campanias.campania import CampaniaInvalidaError, DatosCampania
from app.domain.common.enums import NivelRiesgo, Plan
from tests.unit.application.campanias.dobles import UnidadFalsa, guardada

pytestmark = pytest.mark.unit

ALTO, MEDIO, BAJO = NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO


def entrada(**cambios: object) -> CampaniaEntradaDTO:
    valores: dict[str, object] = {
        "nombre": "  Renovación  ",
        "descripcion": "  ",
        "niveles_riesgo": ["MEDIO", "ALTO", "MEDIO"],
        "planes": ["TRIMESTRAL", "MENSUAL"],
        "prioridad": 1,
        **cambios,
    }
    return CampaniaEntradaDTO.model_validate(valores)


def test_listar_devuelve_dtos_en_orden_del_repositorio() -> None:
    uow = UnidadFalsa()
    repo = uow.contexto.campanias
    repo.campanias = {
        1: guardada(1, nombre="b", prioridad=2),
        2: guardada(2, nombre="Zeta", prioridad=1, activa=False),
        3: guardada(3, nombre="alfa", prioridad=1, es_ejemplo=True),
    }

    resultado = ListarCampanias(uow).ejecutar()

    assert [c.nombre for c in resultado] == ["alfa", "b", "Zeta"]
    assert all(isinstance(c, CampaniaDTO) for c in resultado)
    assert resultado[0].es_ejemplo is True
    assert uow.contexto.commits == 0


def test_crear_normaliza_hace_un_commit_y_devuelve_dto() -> None:
    uow = UnidadFalsa()

    resultado = CrearCampania(uow).ejecutar(entrada())

    assert uow.contexto.campanias.creadas == [
        DatosCampania(
            nombre="Renovación",
            descripcion=None,
            niveles_riesgo=(ALTO, MEDIO),
            planes=(Plan.MENSUAL, Plan.TRIMESTRAL),
            prioridad=1,
        )
    ]
    assert uow.contexto.commits == 1
    assert resultado == CampaniaDTO(
        id=1,
        nombre="Renovación",
        descripcion=None,
        activa=True,
        niveles_riesgo=[ALTO, MEDIO],
        planes=[Plan.MENSUAL, Plan.TRIMESTRAL],
        prioridad=1,
        es_ejemplo=False,
    )


def test_crear_datos_que_pasan_el_dto_pero_no_el_dominio_no_hace_commit() -> None:
    uow = UnidadFalsa()
    # ``model_construct`` salta la validacion del DTO: llega un plan DIARIO al dominio.
    invalida = CampaniaEntradaDTO.model_construct(
        nombre="Renovacion",
        descripcion=None,
        niveles_riesgo=[ALTO],
        planes=[Plan.DIARIO],
        prioridad=1,
    )

    with pytest.raises(CampaniaInvalidaError):
        CrearCampania(uow).ejecutar(invalida)

    assert uow.contexto.campanias.creadas == []
    assert uow.contexto.commits == 0


def test_editar_inexistente_lanza_no_existe_sin_commit() -> None:
    uow = UnidadFalsa()

    with pytest.raises(CampaniaNoExisteError, match=r"La campana no existe\."):
        EditarCampania(uow).ejecutar(99, entrada())

    assert uow.contexto.commits == 0


def test_editar_reemplaza_datos_y_conserva_activa_y_es_ejemplo() -> None:
    uow = UnidadFalsa()
    uow.contexto.campanias.campanias = {7: guardada(7, activa=False, es_ejemplo=True)}

    resultado = EditarCampania(uow).ejecutar(7, entrada(nombre="Nueva", prioridad=5))

    assert resultado.nombre == "Nueva"
    assert resultado.prioridad == 5
    assert resultado.niveles_riesgo == [ALTO, MEDIO]
    assert resultado.activa is False
    assert resultado.es_ejemplo is True
    assert uow.contexto.commits == 1


def test_editar_datos_invalidos_en_dominio_no_hace_commit() -> None:
    uow = UnidadFalsa()
    uow.contexto.campanias.campanias = {7: guardada(7)}
    invalida = CampaniaEntradaDTO.model_construct(
        nombre="   ", descripcion=None, niveles_riesgo=[ALTO], planes=[Plan.MENSUAL], prioridad=1
    )

    with pytest.raises(CampaniaInvalidaError):
        EditarCampania(uow).ejecutar(7, invalida)

    assert uow.contexto.campanias.actualizadas == []
    assert uow.contexto.commits == 0


def test_inactivar_activa_la_deja_inactiva_con_un_commit() -> None:
    uow = UnidadFalsa()
    uow.contexto.campanias.campanias = {7: guardada(7)}

    resultado = InactivarCampania(uow).ejecutar(7)

    assert resultado.activa is False
    assert uow.contexto.campanias.inactivadas == [7]
    assert uow.contexto.commits == 1


def test_inactivar_ya_inactiva_es_idempotente() -> None:
    uow = UnidadFalsa()
    inactiva = guardada(7, activa=False)
    uow.contexto.campanias.campanias = {7: inactiva}

    resultado = InactivarCampania(uow).ejecutar(7)

    assert resultado.activa is False
    assert resultado.id == 7
    assert uow.contexto.campanias.campanias[7] == inactiva


def test_inactivar_inexistente_lanza_no_existe_sin_commit() -> None:
    uow = UnidadFalsa()

    with pytest.raises(CampaniaNoExisteError):
        InactivarCampania(uow).ejecutar(99)

    assert uow.contexto.commits == 0


def test_entrada_dto_prioridad_1000_es_invalida() -> None:
    with pytest.raises(ValidationError):
        entrada(prioridad=1000)


def test_entrada_dto_prioridad_999_es_valida() -> None:
    assert entrada(prioridad=999).prioridad == 999


def test_puerto_no_expone_borrado() -> None:
    metodos = {m for m in dir(CampaniaRepository) if not m.startswith("_")}

    assert metodos == {"listar", "obtener", "crear", "actualizar", "inactivar", "compatibles"}
