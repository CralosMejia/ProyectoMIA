"""CU-11: ConsultarDashboard con un lector doble (R-011 T16, decision (c))."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.dashboard.consultar_dashboard import ConsultarDashboard
from app.application.dashboard.ports import (
    FilaCampania,
    FilaEmbudo,
    LectorDashboard,
    ModeloDashboard,
)
from app.domain.common.enums import FormaPago, Plan
from app.domain.modelo.variables import CicloModelo

pytestmark = pytest.mark.unit

TARDE = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
NOCHE = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
SEPTIEMBRE = (datetime(2026, 9, 1, 5, tzinfo=UTC), datetime(2026, 10, 1, 5, tzinfo=UTC))
ENTRENADO = datetime(2026, 9, 1, 14, 30, tzinfo=UTC)


class RelojFijo:
    def __init__(self, instante: datetime = TARDE) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


def ciclo(ref: int, socio: str, actividad: date, vence: date) -> CicloModelo:
    return CicloModelo(
        clave_socio=socio,
        ref=ref,
        plan=Plan.MENSUAL,
        forma_pago=FormaPago.EFECTIVO,
        fecha_actividad=actividad,
        fecha_vencimiento=vence,
        duracion_dias=(vence - actividad).days,
        monto_cobrado=Decimal("40.00"),
        inicio_aproximado=False,
        excluido=False,
        no_renovo=None,
    )


# Corte del vigente 2026-08-31; hoy 2026-09-30 (evaluable si vence + 30 <= hoy).
CICLOS = [
    ciclo(
        1, "a", date(2026, 7, 2), date(2026, 8, 1)
    ),  # no nuevo: vence + 30 = 08-31, igual al corte
    ciclo(2, "b", date(2026, 7, 3), date(2026, 8, 2)),  # nuevo (09-01 > 08-31), evaluable
    ciclo(3, "c", date(2026, 7, 10), date(2026, 8, 25)),  # nuevo, evaluable (09-24 <= 09-30)
    ciclo(4, "d", date(2026, 6, 1), date(2026, 7, 1)),  # ya conocido por el vigente
    ciclo(5, "e", date(2026, 8, 20), date(2026, 9, 20)),  # aun pendiente (10-20 > hoy)
]


@dataclass
class LectorDoble:
    embudo_fila: FilaEmbudo = field(default_factory=lambda: FilaEmbudo(21, 17, 11, 7, 7))
    filas: list[FilaCampania] = field(default_factory=list)
    modelo: ModeloDashboard | None = field(
        default_factory=lambda: ModeloDashboard(1, ENTRENADO, 1843, date(2026, 8, 31))
    )
    proxima: date | None = date(2027, 3, 1)
    lista_ciclos: list[CicloModelo] = field(default_factory=lambda: list(CICLOS))
    rangos: list[tuple[datetime, datetime]] = field(default_factory=list)

    def embudo(self, desde: datetime, hasta: datetime) -> FilaEmbudo:
        self.rangos.append((desde, hasta))
        return self.embudo_fila

    def por_campania(self, desde: datetime, hasta: datetime) -> list[FilaCampania]:
        self.rangos.append((desde, hasta))
        return self.filas

    def modelo_vigente(self) -> ModeloDashboard | None:
        return self.modelo

    def proxima_fecha_reentrenamiento(self) -> date | None:
        return self.proxima

    def ciclos(self) -> list[CicloModelo]:
        return self.lista_ciclos


def test_lector_doble_cumple_el_puerto() -> None:
    assert isinstance(LectorDoble(), LectorDashboard)


@pytest.mark.parametrize("instante", [TARDE, NOCHE])
def test_ejecutar_sin_mes_usa_mes_de_negocio_y_su_rango(instante: datetime) -> None:
    lector = LectorDoble()

    dto = ConsultarDashboard(lector, RelojFijo(instante)).ejecutar()

    assert dto.mes == "2026-09"
    assert lector.rangos == [SEPTIEMBRE, SEPTIEMBRE]
    assert dto.embudo.model_dump() == {
        "asignadas": 21,
        "contactadas": 17,
        "ofrecidas": 11,
        "aceptadas": 7,
        "renovaron": 7,
    }


def test_ejecutar_con_mes_pide_ese_rango() -> None:
    lector = LectorDoble()

    dto = ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-12")

    assert dto.mes == "2026-12"
    assert lector.rangos[0] == (
        datetime(2026, 12, 1, 5, tzinfo=UTC),
        datetime(2027, 1, 1, 5, tzinfo=UTC),
    )


def test_ejecutar_tasa_con_diez_cerradas_y_nula_con_nueve() -> None:
    lector = LectorDoble(
        filas=[
            FilaCampania(3, "Campaña A", 12, 8, 4, 10),
            FilaCampania(4, "Campaña B", 9, 9, 3, 9),
            FilaCampania(None, None, 3, 0, 0, 0),
        ]
    )

    filas = ConsultarDashboard(lector, RelojFijo()).ejecutar().por_campania

    a, b, sin = filas
    assert a.tasa_renovacion == Decimal("0.40000000")
    assert isinstance(a.tasa_renovacion, Decimal)
    assert a.casos_insuficientes is False
    assert a.model_dump(mode="json")["tasa_renovacion"] == "0.40000000"
    assert (b.tasa_renovacion, b.casos_insuficientes) == (None, True)
    assert sin.campania_id is None
    assert sin.nombre == "Sin campaña"
    assert (sin.tasa_renovacion, sin.casos_insuficientes) == (None, True)


def test_ejecutar_tasa_periodica_se_redondea_a_ocho_decimales() -> None:
    lector = LectorDoble(filas=[FilaCampania(3, "A", 12, 12, 1, 12)])

    fila = ConsultarDashboard(lector, RelojFijo()).ejecutar().por_campania[0]

    assert fila.tasa_renovacion == Decimal("0.08333333")


def test_ejecutar_estado_modelo_cuenta_ciclos_nuevos_evaluables() -> None:
    dto = ConsultarDashboard(LectorDoble(), RelojFijo()).ejecutar()

    assert dto.estado_modelo is not None
    assert dto.estado_modelo.version == "v1"
    assert dto.estado_modelo.fecha_entrenamiento == ENTRENADO
    assert dto.estado_modelo.ciclos_entrenamiento == 1843
    assert dto.estado_modelo.proxima_fecha_reentrenamiento == date(2027, 3, 1)
    assert dto.estado_modelo.ciclos_nuevos_evaluables == 2


def test_ejecutar_modelo_sin_fecha_corte_usa_dia_de_entrenamiento() -> None:
    # Entrenado el 2026-09-01 (Ecuador): solo el ciclo 3 (vence 08-25 -> 09-24) es nuevo.
    lector = LectorDoble(modelo=ModeloDashboard(1, ENTRENADO, 1843, None))

    dto = ConsultarDashboard(lector, RelojFijo()).ejecutar()

    assert dto.estado_modelo is not None
    assert dto.estado_modelo.ciclos_nuevos_evaluables == 1


def test_ejecutar_sin_modelo_vigente_devuelve_estado_modelo_nulo() -> None:
    dto = ConsultarDashboard(LectorDoble(modelo=None), RelojFijo()).ejecutar()

    assert dto.estado_modelo is None
