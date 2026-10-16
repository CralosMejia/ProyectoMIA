"""Caso de uso ``AdoptarModelo`` (R-015, decision (e)) con dobles en memoria.

Reutiliza los dobles y los datos sinteticos de ``test_reentrenar_modelo`` (identidades
inventadas, sin datos personales).
"""

import logging
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.modelo.adoptar_modelo import MOTIVO_ADOPCION, AdoptarModelo
from app.application.modelo.ports import EstadoSistema
from app.application.modelo.reentrenar_modelo import MENSAJE_EN_CURSO, MENSAJE_NO_LISTO
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)
from app.domain.common.predictor import FeatureRow, TrainedModel
from app.domain.modelo.variables import (
    CONJUNTO_SIN_FORMA_PAGO_NI_INICIO,
    VARIABLES_CATEGORICAS_MODELO,
    VARIABLES_NUMERICAS_MODELO,
    ConjuntoVariables,
)
from tests.unit.application.modelo.test_reentrenar_modelo import (
    AHORA,
    HOY,
    AbridorDoble,
    Almacen,
    BloqueoDoble,
    PredictorDoble,
    RelojFijo,
    UnidadEnMemoria,
    membresias,
    modelo_vigente,
)

pytestmark = pytest.mark.unit

PROGRAMADA = HOY.replace(month=12, day=15)


class PredictorQueRegistraVariables(PredictorDoble):
    """Ademas de lo del doble, guarda las listas de variables de cada ``train``."""

    def __init__(self) -> None:
        super().__init__()
        self.variables: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        self.variables.append((tuple(numericas), tuple(categoricas)))
        return super().train(features, labels, numericas, categoricas, referencia)


def escenario(
    *,
    migracion: EstadoMigracion = EstadoMigracion.COMPLETADA,
    con_vigente: bool = True,
    version_vigente: int = 1,
    predictor: PredictorDoble | None = None,
    ocupado: bool = False,
    variables: ConjuntoVariables | None = None,
    corte_vigente: str | None = None,
    ultima_carga: datetime | None = AHORA,
) -> tuple[AdoptarModelo, Almacen, BloqueoDoble, PredictorDoble]:
    vigente = modelo_vigente(version_vigente)
    if corte_vigente is not None:
        vigente = replace(
            vigente, metadata_tecnica={**vigente.metadata_tecnica, "fecha_corte": corte_vigente}
        )
    almacen = Almacen(
        estado=EstadoSistema(
            migracion_historica=migracion, proxima_fecha_reentrenamiento=PROGRAMADA
        ),
        # Pocos ciclos nuevos: los criterios de CU-02 no se cumplirian; la adopcion no los mira.
        membresias=membresias(10, 10),
        modelos=[vigente] if con_vigente else [],
        vigente_id=vigente.id if con_vigente else None,
        # Por defecto una carga de plantilla hoy: los datos llegan hasta hoy.
        ultima_carga_plantilla=ultima_carga,
    )
    bloqueo = BloqueoDoble(ocupado=ocupado)
    doble = predictor or PredictorDoble()
    extra = {} if variables is None else {"variables": variables}
    servicio = AdoptarModelo(
        unidad_de_trabajo=UnidadEnMemoria(almacen),
        abrir_bloqueo=AbridorDoble(bloqueo),
        predictor=doble,
        clock=RelojFijo(),
        **extra,
    )
    return servicio, almacen, bloqueo, doble


def test_ejecutar_sistema_listo_crea_version_siguiente_vigente_y_conserva_la_anterior() -> None:
    servicio, almacen, bloqueo, doble = escenario()

    resultado = servicio.ejecutar()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert resultado.version == 2
    assert [m.version for m in almacen.modelos] == [1, 2]
    assert almacen.vigente is not None
    assert almacen.vigente.version == 2
    assert almacen.commits == 1  # modelo e intento en una sola transaccion
    (intento,) = almacen.intentos
    assert intento.disparador is DisparadorReentrenamiento.MANUAL
    assert intento.resultado is ResultadoReentrenamiento.ENTRENADO
    assert intento.motivo == MOTIVO_ADOPCION == "Adopción del modelo M01"
    assert intento.modelo_id == almacen.vigente.id
    assert intento.fecha == AHORA
    assert intento.fecha_programada is None
    # Entrena una sola vez con todos los evaluables al corte de los datos (aqui hoy, por la
    # carga de plantilla de hoy), sin candidato.
    assert doble.entrenamientos == [20]
    assert almacen.vigente.ciclos_entrenamiento == 20
    assert almacen.vigente.fecha_entrenamiento == AHORA
    assert almacen.vigente.metadata_tecnica["fecha_corte"] == HOY.isoformat()
    assert "medianas_monto" in almacen.vigente.metadata_tecnica
    assert bloqueo.liberaciones == 1


# ---------------------------------------------------------------- corte de los datos (R-015 T11)
# ``membresias(10, 10)``: 20 ciclos con vencimiento de febrero a agosto de 2026; los de julio
# vencen los dias 10, 17 y 24 y los de agosto los dias 11 y 18.


def test_ejecutar_sin_cargas_etiqueta_y_entrena_al_corte_del_vigente_no_a_hoy() -> None:
    # Como el notebook (fecha de corte de los datos): con hoy = 2026-09-30 y datos solo hasta
    # el 2026-07-31, los ciclos de julio y agosto siguen pendientes (no se etiquetan como
    # "no renovo" por falta de datos posteriores).
    servicio, almacen, _, doble = escenario(corte_vigente="2026-07-31", ultima_carga=None)

    resultado = servicio.ejecutar()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert doble.entrenamientos == [15]
    assert almacen.vigente is not None
    assert almacen.vigente.metadata_tecnica["fecha_corte"] == "2026-07-31"


def test_ejecutar_con_carga_de_plantilla_posterior_el_corte_es_el_dia_de_la_carga() -> None:
    carga = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)  # 10:00 en Ecuador
    servicio, almacen, _, doble = escenario(corte_vigente="2026-07-31", ultima_carga=carga)

    servicio.ejecutar()

    assert doble.entrenamientos == [16]  # entra el ciclo que vence el 2026-07-10
    assert almacen.vigente is not None
    assert almacen.vigente.metadata_tecnica["fecha_corte"] == "2026-08-15"


def test_ejecutar_con_carga_anterior_al_corte_del_vigente_usa_el_corte_del_vigente() -> None:
    carga = datetime(2026, 6, 1, 15, 0, tzinfo=UTC)
    servicio, almacen, _, _ = escenario(corte_vigente="2026-07-31", ultima_carga=carga)

    servicio.ejecutar()

    assert almacen.vigente is not None
    assert almacen.vigente.metadata_tecnica["fecha_corte"] == "2026-07-31"


def test_ejecutar_el_corte_nunca_pasa_de_hoy() -> None:
    servicio, almacen, _, _ = escenario(corte_vigente="2026-12-31", ultima_carga=None)

    servicio.ejecutar()

    assert almacen.vigente is not None
    assert almacen.vigente.metadata_tecnica["fecha_corte"] == HOY.isoformat()


def test_ejecutar_no_cambia_la_proxima_fecha_de_reentrenamiento() -> None:
    servicio, almacen, _, _ = escenario()

    servicio.ejecutar()

    assert almacen.estado.proxima_fecha_reentrenamiento == PROGRAMADA


def test_ejecutar_version_es_la_vigente_mas_uno() -> None:
    servicio, almacen, _, _ = escenario(version_vigente=3)

    resultado = servicio.ejecutar()

    assert resultado.version == 4
    assert almacen.vigente is not None
    assert almacen.vigente.version == 4


def test_ejecutar_entrena_con_el_conjunto_del_modelo_por_defecto() -> None:
    doble = PredictorQueRegistraVariables()
    servicio, _, _, _ = escenario(predictor=doble)

    servicio.ejecutar()

    assert doble.variables == [(VARIABLES_NUMERICAS_MODELO, VARIABLES_CATEGORICAS_MODELO)]


def test_ejecutar_con_conjunto_explicito_entrena_con_esas_variables() -> None:
    doble = PredictorQueRegistraVariables()
    servicio, _, _, _ = escenario(predictor=doble, variables=CONJUNTO_SIN_FORMA_PAGO_NI_INICIO)

    servicio.ejecutar()

    assert doble.variables == [
        (CONJUNTO_SIN_FORMA_PAGO_NI_INICIO.numericas, CONJUNTO_SIN_FORMA_PAGO_NI_INICIO.categoricas)
    ]


@pytest.mark.parametrize(
    ("migracion", "con_vigente"),
    [
        (EstadoMigracion.EN_CURSO, True),
        (EstadoMigracion.COMPLETADA, False),
    ],
)
def test_ejecutar_sistema_no_listo_o_sin_vigente_no_guarda_nada(
    migracion: EstadoMigracion, con_vigente: bool
) -> None:
    servicio, almacen, bloqueo, doble = escenario(migracion=migracion, con_vigente=con_vigente)

    resultado = servicio.ejecutar()

    assert resultado.resultado is None
    assert resultado.motivo == MENSAJE_NO_LISTO
    assert not resultado.en_curso
    assert almacen.commits == 0
    assert doble.entrenamientos == []
    assert bloqueo.liberaciones == 1


def test_ejecutar_con_el_bloqueo_ocupado_no_toca_nada() -> None:
    servicio, almacen, bloqueo, doble = escenario(ocupado=True)

    resultado = servicio.ejecutar()

    assert resultado.en_curso is True
    assert resultado.motivo == MENSAJE_EN_CURSO
    assert almacen.commits == 0
    assert almacen.aperturas == 0
    assert doble.entrenamientos == []
    assert bloqueo.liberaciones == 0


def test_ejecutar_si_el_entrenamiento_falla_no_guarda_nada_y_sigue_el_vigente(
    caplog: pytest.LogCaptureFixture,
) -> None:
    servicio, almacen, bloqueo, _ = escenario(predictor=PredictorDoble(fallar=True))

    with caplog.at_level(logging.INFO):
        resultado = servicio.ejecutar()

    assert resultado.resultado is None
    assert "RuntimeError" in resultado.motivo
    assert "v1" in resultado.motivo
    assert "fallo del entrenamiento" not in resultado.motivo  # solo el tipo
    assert almacen.commits == 0
    assert almacen.intentos == []
    assert [m.version for m in almacen.modelos] == [1]
    assert almacen.vigente_id == 1
    assert bloqueo.liberaciones == 1
    assert "fallo del entrenamiento" not in caplog.text


def test_ejecutar_si_falla_al_guardar_el_intento_no_queda_el_modelo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    servicio, almacen, _, _ = escenario()
    from tests.unit.application.modelo import test_reentrenar_modelo as dobles

    def fallar(self: object, intento: object) -> int:
        raise RuntimeError("fallo al guardar")

    monkeypatch.setattr(dobles._Intentos, "crear", fallar)

    with pytest.raises(RuntimeError):
        servicio.ejecutar()

    assert almacen.commits == 0
    assert [m.version for m in almacen.modelos] == [1]


def test_ejecutar_logs_y_resultado_solo_con_cifras_del_modelo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    servicio, _, _, _ = escenario()

    with caplog.at_level(logging.INFO):
        resultado = servicio.ejecutar()

    assert caplog.messages == ["adopcion: version 2 en uso (ciclos=20); la version 1 se conserva"]
    assert resultado.motivo == "v2 en uso (Adopción del modelo M01)."


def test_ejecutar_no_modifica_al_vigente_anterior() -> None:
    servicio, almacen, _, _ = escenario()
    anterior = replace(almacen.modelos[0])

    servicio.ejecutar()

    assert almacen.modelos[0] == anterior
