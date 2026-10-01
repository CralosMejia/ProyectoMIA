"""ConsultarEstadoSistema con un lector doble (sin BD)."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import pytest

from app.application.modelo.ports import EstadoSistema
from app.application.sistema.consultar_estado import ConsultarEstadoSistema
from app.application.sistema.ports import (
    LectorEstadoSistema,
    RegistroMigracion,
    ResultadoMigracion,
    ResumenModelo,
)
from app.domain.common.enums import EstadoMigracion

pytestmark = pytest.mark.unit

ENTRENADO = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
CARGA = datetime(2026, 9, 29, 10, 0, 5, tzinfo=UTC)
TARDE = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
# 2026-09-30 22:00 en Ecuador: sigue siendo septiembre.
NOCHE = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
SEPTIEMBRE = (datetime(2026, 9, 1, 5, tzinfo=UTC), datetime(2026, 10, 1, 5, tzinfo=UTC))


class RelojFijo:
    def __init__(self, instante: datetime = TARDE) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


@dataclass
class LectorDoble:
    migracion: EstadoMigracion
    proxima: date | None = None
    modelo: ResumenModelo | None = None
    carga: datetime | None = None
    hay_plantilla: bool = False
    rangos_consultados: list[tuple[datetime, datetime]] = field(default_factory=list)

    def estado(self) -> EstadoSistema:
        return EstadoSistema(self.migracion, self.proxima)

    def modelo_vigente(self) -> ResumenModelo | None:
        return self.modelo

    def ultima_carga_en(self) -> datetime | None:
        return self.carga

    def hay_carga_plantilla_entre(self, desde: datetime, hasta: datetime) -> bool:
        self.rangos_consultados.append((desde, hasta))
        return self.hay_plantilla


def registro_con(
    resultado: ResultadoMigracion | None = None, en_curso: bool = False
) -> RegistroMigracion:
    registro = RegistroMigracion()
    if en_curso:
        registro.iniciar()
    elif resultado is not None:
        registro.iniciar()
        registro.terminar(resultado)
    return registro


def test_lector_doble_cumple_el_puerto() -> None:
    assert isinstance(LectorDoble(EstadoMigracion.PENDIENTE), LectorEstadoSistema)


def test_ejecutar_en_curso_en_base_devuelve_inicializando() -> None:
    dto = ConsultarEstadoSistema(
        LectorDoble(EstadoMigracion.EN_CURSO), RegistroMigracion(), RelojFijo()
    ).ejecutar()

    assert dto.estado == "INICIALIZANDO"
    assert dto.migracion_historica is EstadoMigracion.EN_CURSO
    assert dto.modelo_vigente is None


def test_ejecutar_hilo_en_curso_devuelve_inicializando() -> None:
    dto = ConsultarEstadoSistema(
        LectorDoble(EstadoMigracion.PENDIENTE), registro_con(en_curso=True), RelojFijo()
    ).ejecutar()

    assert dto.estado == "INICIALIZANDO"


@pytest.mark.parametrize("resultado", [ResultadoMigracion.FALTAN_DATOS, ResultadoMigracion.FALLIDA])
def test_ejecutar_pendiente_con_fallo_devuelve_faltan_datos(resultado: ResultadoMigracion) -> None:
    dto = ConsultarEstadoSistema(
        LectorDoble(EstadoMigracion.PENDIENTE), registro_con(resultado), RelojFijo()
    ).ejecutar()

    assert dto.estado == "FALTAN_DATOS_HISTORICOS"
    assert dto.migracion_historica is EstadoMigracion.PENDIENTE


@pytest.mark.parametrize(
    "resultado", [None, ResultadoMigracion.EN_OTRO_PROCESO, ResultadoMigracion.YA_MIGRADA]
)
def test_ejecutar_pendiente_sin_resultado_de_fallo_devuelve_inicializando(
    resultado: ResultadoMigracion | None,
) -> None:
    dto = ConsultarEstadoSistema(
        LectorDoble(EstadoMigracion.PENDIENTE), registro_con(resultado), RelojFijo()
    ).ejecutar()

    assert dto.estado == "INICIALIZANDO"


def test_ejecutar_completada_devuelve_listo_con_modelo_y_fechas() -> None:
    lector = LectorDoble(
        EstadoMigracion.COMPLETADA,
        proxima=date(2027, 3, 29),
        modelo=ResumenModelo(version=1, fecha_entrenamiento=ENTRENADO, ciclos_entrenamiento=15),
        carga=CARGA,
    )

    dto = ConsultarEstadoSistema(
        lector, registro_con(ResultadoMigracion.FALLIDA), RelojFijo()
    ).ejecutar()

    assert dto.estado == "LISTO"
    assert dto.migracion_historica is EstadoMigracion.COMPLETADA
    assert dto.modelo_vigente is not None
    assert dto.modelo_vigente.version == "v1"
    assert dto.modelo_vigente.fecha_entrenamiento == ENTRENADO
    assert dto.modelo_vigente.ciclos_entrenamiento == 15
    assert dto.ultima_carga_en == CARGA
    assert dto.proxima_fecha_reentrenamiento == date(2027, 3, 29)


@pytest.mark.parametrize("instante", [TARDE, NOCHE])
@pytest.mark.parametrize("hay_plantilla", [True, False])
def test_ejecutar_listo_consulta_carga_plantilla_del_mes_de_negocio(
    instante: datetime, hay_plantilla: bool
) -> None:
    lector = LectorDoble(EstadoMigracion.COMPLETADA, hay_plantilla=hay_plantilla)

    dto = ConsultarEstadoSistema(lector, RegistroMigracion(), RelojFijo(instante)).ejecutar()

    assert dto.datos_mes_cargados is hay_plantilla
    assert lector.rangos_consultados == [SEPTIEMBRE]


@pytest.mark.parametrize(
    ("migracion", "registro"),
    [
        (EstadoMigracion.EN_CURSO, RegistroMigracion()),
        (EstadoMigracion.PENDIENTE, registro_con(ResultadoMigracion.FALTAN_DATOS)),
    ],
)
def test_ejecutar_no_listo_devuelve_datos_mes_nulo_sin_consultar(
    migracion: EstadoMigracion, registro: RegistroMigracion
) -> None:
    lector = LectorDoble(migracion, hay_plantilla=True)

    dto = ConsultarEstadoSistema(lector, registro, RelojFijo()).ejecutar()

    assert dto.estado in ("INICIALIZANDO", "FALTAN_DATOS_HISTORICOS")
    assert dto.datos_mes_cargados is None
    assert lector.rangos_consultados == []
