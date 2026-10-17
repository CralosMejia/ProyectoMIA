"""CU-11: ConsultarDashboard con un lector doble (R-011 T16, decision (c))."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.dashboard.consultar_dashboard import ConsultarDashboard
from app.application.dashboard.ports import (
    FilaCampania,
    FilaEmbudo,
    FilaPiloto,
    LectorDashboard,
    ListaPiloto,
    ModeloDashboard,
    MontoMembresia,
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
    lista: ListaPiloto | None = None
    tabla_montos: dict[int, MontoMembresia] = field(default_factory=dict)
    ultima_carga: datetime | None = None
    llamadas_ciclos: int = 0
    rangos_lista: list[tuple[date, date]] = field(default_factory=list)
    ids_montos: list[list[int]] = field(default_factory=list)

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
        self.llamadas_ciclos += 1
        return self.lista_ciclos

    def lista_piloto(self, desde: date, hasta: date) -> ListaPiloto | None:
        self.rangos_lista.append((desde, hasta))
        return self.lista

    def montos(self, ids: Sequence[int]) -> dict[int, MontoMembresia]:
        self.ids_montos.append(list(ids))
        return {i: self.tabla_montos[i] for i in ids if i in self.tabla_montos}

    def ultima_carga_plantilla(self) -> datetime | None:
        return self.ultima_carga


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


# ------------------------------------------------------------- indicadores del piloto (R-018)

# hoy 2026-09-30; corte del vigente 2026-08-31; ultima carga 2026-09-29 (Ecuador)
# -> corte de verificacion 2026-09-29: verificado si T + 30 <= 2026-09-29.
CARGA = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
CICLOS_PILOTO = [
    ciclo(101, "p", date(2026, 7, 1), date(2026, 8, 1)),
    ciclo(102, "q", date(2026, 7, 5), date(2026, 8, 5)),
    ciclo(103, "r", date(2026, 7, 10), date(2026, 8, 10)),
    ciclo(104, "s", date(2026, 7, 15), date(2026, 8, 15)),
    ciclo(201, "p", date(2026, 8, 5), date(2026, 9, 5)),  # renovacion de 101
    ciclo(203, "r", date(2026, 8, 20), date(2026, 9, 20)),  # renovacion de 103
    ciclo(301, "t", date(2026, 8, 10), date(2026, 9, 10)),  # T + 30 = 10-10 > corte
    ciclo(302, "u", date(2026, 8, 20), date(2026, 9, 20)),
]
LISTA_AGOSTO = ListaPiloto(
    id=7,
    nombre="Lista agosto",
    fecha_generacion=date(2026, 8, 20),
    filas=(
        FilaPiloto(101, 1, True, date(2026, 7, 25)),
        FilaPiloto(102, 2, True, date(2026, 8, 5)),  # el mismo dia de T: no es "antes"
        FilaPiloto(103, 3, None, None),
        FilaPiloto(104, 4, False, None),
        FilaPiloto(999, 26, True, date(2026, 7, 1)),  # fuera del top 25
    ),
)


def _lector_piloto(lista: ListaPiloto | None = LISTA_AGOSTO) -> LectorDoble:
    return LectorDoble(
        lista_ciclos=list(CICLOS_PILOTO),
        lista=lista,
        ultima_carga=CARGA,
        tabla_montos={201: MontoMembresia(Decimal("40.0000"), Decimal("45.0000"))},
    )


def test_ejecutar_piloto_mes_sin_lista_es_sin_datos() -> None:
    lector = _lector_piloto(lista=None)

    piloto = ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08").piloto

    assert piloto.estado == "SIN_DATOS"
    assert piloto.lista is None
    assert piloto.corte_verificacion is None
    assert (piloto.n_top, piloto.sin_dato) == (0, 0)
    assert piloto.precision_top25.valor is None
    assert piloto.precision_top25.estado == "SIN_DATOS"
    assert piloto.monto_retenido.total is None
    assert lector.rangos_lista == [(date(2026, 8, 1), date(2026, 8, 31))]
    assert lector.ids_montos == []


def test_ejecutar_piloto_caso_completo_calcula_los_cinco_indicadores() -> None:
    lector = _lector_piloto()

    piloto = ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08").piloto

    assert piloto.estado == "COMPLETO"
    assert piloto.lista is not None
    assert (piloto.lista.id, piloto.lista.nombre) == (7, "Lista agosto")
    assert piloto.lista.fecha_generacion == date(2026, 8, 20)
    assert piloto.corte_verificacion == date(2026, 9, 29)
    assert (piloto.n_top, piloto.sin_dato) == (4, 0)
    p = piloto.precision_top25
    assert (p.valor, p.numerador, p.denominador, p.n, p.pendientes, p.estado) == (
        Decimal("0.50000000"),
        2,
        4,
        4,
        0,
        "COMPLETO",
    )
    assert piloto.contactados_antes_vencimiento.valor == Decimal("0.25000000")
    assert piloto.dias_anticipacion.valor == Decimal("3.5")
    assert piloto.dias_anticipacion.n == 2
    t = piloto.tasa_renovacion_contactados
    assert (t.valor, t.n, t.pendientes, t.estado) == (Decimal("0.50000000"), 2, 0, "COMPLETO")
    m = piloto.monto_retenido
    assert (m.total, m.renovaciones, m.renovaciones_sin_monto) == (Decimal("40.00"), 1, 0)
    assert sorted(lector.ids_montos[0]) == [201, 203]


def test_ejecutar_piloto_serializa_decimales_como_string() -> None:
    dto = ConsultarDashboard(_lector_piloto(), RelojFijo()).ejecutar("2026-08")

    piloto = dto.model_dump(mode="json")["piloto"]

    assert piloto["precision_top25"]["valor"] == "0.50000000"
    assert piloto["dias_anticipacion"]["valor"] == "3.5"
    assert piloto["monto_retenido"]["total"] == "40.00"
    assert piloto["corte_verificacion"] == "2026-09-29"


def test_ejecutar_piloto_proporcion_cero_en_notacion_fija() -> None:
    lista = ListaPiloto(7, "L", date(2026, 8, 20), (FilaPiloto(104, 1, False, None),))
    dto = ConsultarDashboard(_lector_piloto(lista), RelojFijo()).ejecutar("2026-08")

    piloto = dto.model_dump(mode="json")["piloto"]

    assert piloto["precision_top25"]["valor"] == "1.00000000"
    assert piloto["contactados_antes_vencimiento"]["valor"] == "0.00000000"


def test_ejecutar_piloto_todos_pendientes() -> None:
    lista = ListaPiloto(
        8,
        "Lista septiembre",
        date(2026, 9, 1),
        (FilaPiloto(301, 1, True, date(2026, 9, 1)), FilaPiloto(302, 2, False, None)),
    )

    piloto = ConsultarDashboard(_lector_piloto(lista), RelojFijo()).ejecutar().piloto

    assert piloto.estado == "PENDIENTE"
    p = piloto.precision_top25
    assert (p.valor, p.estado, p.pendientes, p.n) == (None, "PENDIENTE", 2, 2)
    t = piloto.tasa_renovacion_contactados
    assert (t.valor, t.estado, t.pendientes, t.n) == (None, "PENDIENTE", 1, 1)


def test_ejecutar_piloto_membresia_sin_ciclo_es_sin_dato() -> None:
    filas = (FilaPiloto(101, 1, True, None), FilaPiloto(555, 2, True, None))
    lista = ListaPiloto(7, "L", date(2026, 8, 20), filas)

    piloto = ConsultarDashboard(_lector_piloto(lista), RelojFijo()).ejecutar("2026-08").piloto

    assert (piloto.n_top, piloto.sin_dato) == (2, 1)
    assert piloto.precision_top25.n == 1


def test_ejecutar_piloto_sin_modelo_vigente_deja_corte_nulo_y_pendiente() -> None:
    lector = _lector_piloto()
    lector.modelo = None

    piloto = ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08").piloto

    assert piloto.corte_verificacion is None
    assert piloto.precision_top25.estado == "PENDIENTE"
    assert piloto.precision_top25.pendientes == 4


def test_ejecutar_lee_los_ciclos_una_sola_vez() -> None:
    lector = _lector_piloto()

    ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08")

    assert lector.llamadas_ciclos == 1


def test_ejecutar_sin_lista_ni_modelo_no_lee_ciclos() -> None:
    lector = _lector_piloto(lista=None)
    lector.modelo = None

    ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08")

    assert lector.llamadas_ciclos == 0


def test_ejecutar_piloto_sin_mes_usa_mes_de_negocio() -> None:
    lector = _lector_piloto(lista=None)

    dto = ConsultarDashboard(lector, RelojFijo(NOCHE)).ejecutar()

    assert dto.mes == "2026-09"
    assert lector.rangos_lista == [(date(2026, 9, 1), date(2026, 9, 30))]


def test_ejecutar_piloto_sin_carga_posterior_al_corte_deja_pendientes_no_cuenta_no_renovo() -> None:
    # Riesgo 1 del plan: sin carga posterior al corte del vigente (2026-08-31), los casos con
    # T + 30 > 2026-08-31 quedan pendientes aunque hoy (2026-09-30) ya haya pasado T + 30.
    lector = _lector_piloto()
    lector.ultima_carga = None

    piloto = ConsultarDashboard(lector, RelojFijo()).ejecutar("2026-08").piloto

    assert piloto.corte_verificacion == date(2026, 8, 31)
    p = piloto.precision_top25
    assert (p.numerador, p.denominador, p.pendientes, p.n) == (0, 1, 3, 4)
    assert (p.valor, p.estado) == (Decimal("0.00000000"), "PARCIAL")
