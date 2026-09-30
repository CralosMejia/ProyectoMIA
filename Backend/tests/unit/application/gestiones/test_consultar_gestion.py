"""Consulta de una gestion (R-009 T10)."""

from decimal import Decimal

import pytest

from app.application.gestiones.consultar_gestion import ConsultarGestion
from app.application.gestiones.registrar_resultado import GestionNoExisteError
from app.domain.common.enums import EstadoGestion, NivelRiesgo
from tests.unit.application.gestiones.dobles import INSTANTE, entorno, gestion_pendiente

pytestmark = pytest.mark.unit


def test_ejecutar_devuelve_instantanea_y_datos_originales_sin_bloquear() -> None:
    uow, gestiones, _ = entorno()
    gestion_id = gestion_pendiente(gestiones, campania_nombre="Nombre al asignar")

    resultado = ConsultarGestion(uow).ejecutar(gestion_id)

    assert resultado.id == gestion_id
    assert resultado.campania_id == 3
    assert resultado.campania_nombre == "Nombre al asignar"
    assert resultado.score == Decimal("0.8123")
    assert resultado.nivel_riesgo is NivelRiesgo.ALTO
    assert resultado.modelo_version == "v3"
    assert resultado.estado is EstadoGestion.PENDIENTE
    assert resultado.fecha_asignacion == INSTANTE
    assert gestiones.bloqueos == []
    assert uow.commits == 0


def test_ejecutar_gestion_inexistente_lanza_error() -> None:
    uow, _, _ = entorno()

    with pytest.raises(GestionNoExisteError):
        ConsultarGestion(uow).ejecutar(99)
