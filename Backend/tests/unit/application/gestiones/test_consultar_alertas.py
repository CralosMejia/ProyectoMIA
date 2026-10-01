"""CU-09: ConsultarAlertas y ListarGestionesPorAlerta con un lector doble (R-011 T3)."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pytest

from app.application.gestiones.consultar_alertas import ConsultarAlertas, ListarGestionesPorAlerta
from app.application.gestiones.dtos import FiltroGestiones
from app.application.gestiones.ports import (
    ConteoAlertas,
    GestionPendienteResumen,
    LectorSeguimiento,
)
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan
from tests.unit.application.gestiones.dobles import RelojFijo

pytestmark = pytest.mark.unit

TARDE = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
# 2026-09-30 22:00 en Ecuador: sigue siendo el 30 de septiembre.
NOCHE = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

FILA = GestionPendienteResumen(
    id=9,
    prediccion_id=1501,
    socio_nombre="Socio Ficticio",
    celular="0990000000",
    plan=Plan.MENSUAL,
    fecha_vencimiento=date(2026, 10, 5),
    fecha_seguimiento=date(2026, 9, 30),
    nivel_riesgo=NivelRiesgo.ALTO,
    campania_nombre="Campaña congelada",
    responsable="Responsable ficticio",
)


@dataclass
class LectorDoble:
    conteo: ConteoAlertas = field(
        default_factory=lambda: ConteoAlertas(vencidas=2, hoy=1, proximas=5)
    )
    filas: list[GestionPendienteResumen] = field(default_factory=lambda: [FILA])
    dias_contados: list[date] = field(default_factory=list)
    rangos: list[tuple[date | None, date]] = field(default_factory=list)

    def contar(self, hoy: date) -> ConteoAlertas:
        self.dias_contados.append(hoy)
        return self.conteo

    def listar(self, desde: date | None, hasta: date) -> list[GestionPendienteResumen]:
        self.rangos.append((desde, hasta))
        return self.filas


def test_lector_doble_cumple_el_puerto() -> None:
    assert isinstance(LectorDoble(), LectorSeguimiento)


@pytest.mark.parametrize("instante", [TARDE, NOCHE])
def test_ejecutar_alertas_usa_hoy_de_negocio_y_devuelve_conteos(instante: datetime) -> None:
    lector = LectorDoble()

    dto = ConsultarAlertas(lector, RelojFijo(instante)).ejecutar()

    assert lector.dias_contados == [date(2026, 9, 30)]
    assert dto.model_dump() == {"vencidas": 2, "hoy": 1, "proximos_7_dias": 5}


@pytest.mark.parametrize("instante", [TARDE, NOCHE])
def test_ejecutar_lista_hoy_pide_rango_de_hoy_y_mapea_a_resumen(instante: datetime) -> None:
    lector = LectorDoble()

    filas = ListarGestionesPorAlerta(lector, RelojFijo(instante)).ejecutar(FiltroGestiones.HOY)

    assert lector.rangos == [(date(2026, 9, 30), date(2026, 9, 30))]
    assert len(filas) == 1
    fila = filas[0]
    assert fila.id == 9
    assert fila.prediccion_id == 1501
    assert fila.estado is EstadoGestion.PENDIENTE
    assert fila.campania_nombre == "Campaña congelada"
    assert fila.fecha_seguimiento == date(2026, 9, 30)
    assert fila.celular == "0990000000"


@pytest.mark.parametrize(
    ("filtro", "rango"),
    [
        (FiltroGestiones.VENCIDAS, (None, date(2026, 9, 29))),
        (FiltroGestiones.PROXIMAS, (date(2026, 10, 1), date(2026, 10, 7))),
    ],
)
def test_ejecutar_lista_otros_grupos_pide_su_rango(
    filtro: FiltroGestiones, rango: tuple[date | None, date]
) -> None:
    lector = LectorDoble(filas=[])

    assert ListarGestionesPorAlerta(lector, RelojFijo(TARDE)).ejecutar(filtro) == []
    assert lector.rangos == [rango]
