"""Servicio EntrenarModeloInicial con un doble de PredictorModel (sin scikit-learn ni BD).

Los nombres y cedulas son inventados.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.application.modelo.entrenar_modelo import (
    DatosInsuficientesError,
    EntrenarModeloInicial,
    ModeloEntrenado,
)
from app.application.modelo.mapeo import ciclo_modelo_desde
from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.common.exceptions import DomainError
from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel, TrainedModel
from app.domain.historico.ciclos import CicloEtiquetado, MotivoCiclo
from app.domain.historico.registro import RegistroHistorico
from app.domain.modelo.umbrales import UMBRAL_ALTO, UMBRAL_MEDIO, umbrales_fijos
from app.domain.modelo.variables import (
    CONJUNTO_SIN_FORMA_PAGO_NI_INICIO,
    VARIABLES_CATEGORICAS,
    VARIABLES_CATEGORICAS_MODELO,
    VARIABLES_NUMERICAS,
    VARIABLES_NUMERICAS_MODELO,
)

pytestmark = pytest.mark.unit

CORTE = date(2026, 8, 31)
NOMBRE_SECRETO = "Nombre Ficticio Secreto"
CEDULA_SECRETA = "1799999999"


@dataclass
class PredictorDoble:
    """Registra lo que recibe; el score es ``ciclos_previos / 10 + 0.05`` (determinista)."""

    fallar: bool = False
    train_llamadas: list[dict[str, object]] = field(default_factory=list)
    predict_llamadas: list[list[FeatureRow]] = field(default_factory=list)

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        if self.fallar:
            raise RuntimeError("fallo del entrenamiento")
        self.train_llamadas.append(
            {
                "features": list(features),
                "labels": list(labels),
                "numericas": tuple(numericas),
                "categoricas": tuple(categoricas),
                "referencia": list(referencia or []),
            }
        )
        return TrainedModel(artefacto=b"artefacto", metadata_tecnica={"algoritmo": "doble"})

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        self.predict_llamadas.append(list(features))
        return [
            Prediction(
                score=Decimal(str(f["ciclos_previos"])) / 10 + Decimal("0.05"),
                factores_principales=(),
            )
            for f in features
        ]


def ciclo(
    fila: int,
    *,
    socio: str = "A",
    actividad: date,
    vence: date | None = None,
    estado: EstadoCiclo = EstadoCiclo.EVALUABLE,
    no_renovo: bool | None = None,
    plan: Plan = Plan.MENSUAL,
    monto: Decimal | None = Decimal("30"),
) -> CicloEtiquetado:
    vencimiento = vence if vence is not None else actividad + timedelta(days=30)
    registro = RegistroHistorico(
        identidad=f"socio-{socio}",
        cedula=None,
        nombre=NOMBRE_SECRETO,
        nombre_normalizado=NOMBRE_SECRETO.upper(),
        plan=plan,
        plan_original=plan.value,
        forma_pago=FormaPago.EFECTIVO,
        forma_pago_original="EFECTIVO",
        fecha_inicio=actividad,
        fecha_vencimiento=vencimiento,
        fecha_actividad=actividad,
        inicio_aproximado=False,
        duracion_dias=(vencimiento - actividad).days,
        monto_cobrado=monto,
        referencia=(actividad.year, "HOJA", fila),
    )
    if estado is EstadoCiclo.EVALUABLE and no_renovo is None:
        no_renovo = True
    motivo = {
        EstadoCiclo.EVALUABLE: MotivoCiclo.EVALUABLE,
        EstadoCiclo.PENDIENTE: MotivoCiclo.VENTANA_INCOMPLETA,
        EstadoCiclo.EXCLUIDO: MotivoCiclo.DURACION_IMPLAUSIBLE,
    }[estado]
    return CicloEtiquetado(
        registro=registro,
        estado=estado,
        motivo=motivo,
        no_renovo=no_renovo if estado is EstadoCiclo.EVALUABLE else None,
        fecha_renovacion=None,
    )


def seis_evaluables() -> list[CicloEtiquetado]:
    """6 evaluables (4 no renovo), 1 pendiente y 1 excluido; vencimientos 2025-02 .. 2026-07."""
    return [
        ciclo(1, socio="B", actividad=date(2026, 6, 10), no_renovo=False),
        ciclo(2, socio="A", actividad=date(2025, 1, 5), no_renovo=True),
        ciclo(3, socio="A", actividad=date(2025, 2, 5), no_renovo=False),
        ciclo(4, socio="C", actividad=date(2026, 5, 1), no_renovo=True),
        ciclo(5, socio="C", actividad=date(2026, 4, 1), estado=EstadoCiclo.PENDIENTE),
        ciclo(6, socio="C", actividad=date(2026, 3, 1), estado=EstadoCiclo.EXCLUIDO),
        ciclo(7, socio="D", actividad=date(2026, 6, 1), no_renovo=True),
        ciclo(8, socio="B", actividad=date(2025, 11, 1), no_renovo=True),
    ]


def entrenar(
    ciclos: Sequence[CicloEtiquetado], predictor: PredictorDoble | None = None
) -> tuple[PredictorDoble, ModeloEntrenado]:
    doble = predictor or PredictorDoble()
    assert isinstance(doble, PredictorModel)
    resultado = EntrenarModeloInicial(doble).ejecutar(ciclos, CORTE)
    return doble, resultado


def test_ejecutar_entrena_solo_evaluables_en_orden_del_notebook() -> None:
    doble, _ = entrenar(seis_evaluables())

    llamada = doble.train_llamadas[0]
    features = llamada["features"]
    assert isinstance(features, list)
    # Orden: (socio, actividad, vencimiento) -> A(2025-01), A(2025-02), B(2025-11), B(2026-06),
    # C(2026-05), D(2026-06).
    assert [f["mes_vencimiento"] for f in features] == [
        "2025-02",
        "2025-03",
        "2025-12",
        "2026-07",
        "2026-05",
        "2026-07",
    ]
    assert llamada["labels"] == [1, 0, 1, 0, 1, 1]
    assert llamada["numericas"] == VARIABLES_NUMERICAS_MODELO
    assert llamada["categoricas"] == VARIABLES_CATEGORICAS_MODELO


def test_ejecutar_historial_usa_no_excluidos_incluidos_pendientes() -> None:
    doble, _ = entrenar(seis_evaluables())

    features = doble.train_llamadas[0]["features"]
    assert isinstance(features, list)
    socio_c = features[4]  # C 2026-05-01: previos = pendiente 2026-04-01 (el excluido no cuenta)
    assert socio_c["ciclos_previos"] == 1
    assert socio_c["dias_desde_ultima_membresia"] == 30
    socio_a_segundo = features[1]
    assert socio_a_segundo["ciclos_previos"] == 1
    assert socio_a_segundo["monto_historico"] == Decimal("30")


def test_ejecutar_con_seis_evaluables_calcula_conteos_prevalencia_y_periodo() -> None:
    _, resultado = entrenar(seis_evaluables())

    assert resultado.ciclos_entrenamiento == 6
    assert resultado.prevalencia == Decimal(4) / 6
    assert resultado.periodo_desde == date(2025, 2, 4)
    assert resultado.periodo_hasta == date(2026, 7, 10)


def test_ejecutar_referencia_son_evaluables_con_vencimiento_en_2025() -> None:
    ciclos = [
        *seis_evaluables(),
        # Pendiente y excluido con vencimiento en 2025: no entran en la referencia.
        ciclo(9, socio="E", actividad=date(2025, 3, 1), estado=EstadoCiclo.PENDIENTE),
        ciclo(10, socio="F", actividad=date(2025, 4, 1), estado=EstadoCiclo.EXCLUIDO),
    ]
    doble, resultado = entrenar(ciclos)

    referencia = doble.train_llamadas[0]["referencia"]
    assert isinstance(referencia, list)
    assert [f["mes_vencimiento"] for f in referencia] == ["2025-02", "2025-03", "2025-12"]
    assert resultado.metadata_tecnica["ciclos_referencia_factores"] == 3


def test_ejecutar_umbrales_fijos_y_reparticion_de_los_tres_meses_recientes() -> None:
    doble, resultado = entrenar(seis_evaluables())

    # Meses con resultado: 2025-02, 2025-03, 2025-12, 2026-05, 2026-07 -> recientes 12, 05, 07.
    filas = doble.predict_llamadas[0]
    assert sorted(str(f["mes_vencimiento"]) for f in filas) == [
        "2025-12",
        "2026-05",
        "2026-07",
        "2026-07",
    ]
    scores = [Decimal(str(f["ciclos_previos"])) / 10 + Decimal("0.05") for f in filas]
    # R-015 T11: cortes fijos del notebook (0,70 / 0,50); los porcentajes son la reparticion
    # observada de esos scores (todos < 0,50 -> BAJO).
    assert (resultado.umbrales.alto, resultado.umbrales.medio) == (UMBRAL_ALTO, UMBRAL_MEDIO)
    assert resultado.umbrales == umbrales_fijos(scores)
    assert dict(resultado.porcentajes_umbral) == {"ALTO": 0, "MEDIO": 0, "BAJO": 100}


def test_ejecutar_referencia_completa_montos_con_las_medianas_de_la_referencia() -> None:
    # Notebook 13.3: X_train lleva monto_actual completado con las medianas de la particion de
    # entrenamiento, no con las del modelo operativo (todos los evaluables).
    ciclos = [
        ciclo(1, socio="A", actividad=date(2025, 1, 5), monto=Decimal("30"), no_renovo=True),
        ciclo(2, socio="B", actividad=date(2025, 3, 1), monto=None, no_renovo=False),
        ciclo(3, socio="C", actividad=date(2026, 5, 1), monto=Decimal("100"), no_renovo=True),
        ciclo(4, socio="D", actividad=date(2026, 6, 1), monto=Decimal("100"), no_renovo=False),
        ciclo(5, socio="E", actividad=date(2026, 6, 5), monto=Decimal("100"), no_renovo=True),
    ]
    doble, resultado = entrenar(ciclos)

    llamada = doble.train_llamadas[0]
    features = llamada["features"]
    referencia = llamada["referencia"]
    assert isinstance(features, list) and isinstance(referencia, list)
    entrenamiento_b = next(f for f in features if f["mes_vencimiento"] == "2025-03")
    referencia_b = next(f for f in referencia if f["mes_vencimiento"] == "2025-03")
    assert entrenamiento_b["monto_actual"] == Decimal("100")  # mediana operativa (30,100,100,100)
    assert referencia_b["monto_actual"] == Decimal("30")  # mediana de la referencia (30)
    assert resultado.metadata_tecnica["medianas_monto"] == {
        "por_plan": {"MENSUAL": "100"},
        "general": "100",
    }


def test_ejecutar_guarda_medianas_como_texto_decimal() -> None:
    ciclos = [
        *seis_evaluables(),
        ciclo(11, socio="G", actividad=date(2025, 5, 1), monto=Decimal("10"), no_renovo=False),
        ciclo(
            12,
            socio="H",
            actividad=date(2025, 6, 1),
            plan=Plan.TRIMESTRAL,
            vence=date(2025, 8, 30),
            monto=Decimal("80.50"),
            no_renovo=True,
        ),
    ]
    _, resultado = entrenar(ciclos)

    medianas = resultado.metadata_tecnica["medianas_monto"]
    assert medianas == {"por_plan": {"MENSUAL": "30", "TRIMESTRAL": "80.50"}, "general": "30"}
    assert resultado.metadata_tecnica["algoritmo"] == "doble"
    assert resultado.metadata_tecnica["fecha_corte"] == "2026-08-31"


def test_ejecutar_sin_evaluables_lanza_domain_error_sin_datos_personales() -> None:
    ciclos = [ciclo(1, actividad=date(2026, 8, 1), estado=EstadoCiclo.PENDIENTE)]

    with pytest.raises(DomainError) as error:
        entrenar(ciclos)

    assert isinstance(error.value, DatosInsuficientesError)
    assert NOMBRE_SECRETO not in str(error.value)
    assert CEDULA_SECRETA not in str(error.value)


def test_ejecutar_con_una_sola_clase_lanza_domain_error() -> None:
    ciclos = [
        ciclo(1, socio="A", actividad=date(2025, 1, 5), no_renovo=True),
        ciclo(2, socio="B", actividad=date(2025, 2, 5), no_renovo=True),
    ]
    doble = PredictorDoble()

    with pytest.raises(DatosInsuficientesError) as error:
        entrenar(ciclos, doble)

    assert NOMBRE_SECRETO not in str(error.value)
    assert doble.train_llamadas == []


def test_ejecutar_si_el_predictor_falla_propaga_la_excepcion() -> None:
    with pytest.raises(RuntimeError, match="fallo del entrenamiento"):
        entrenar(seis_evaluables(), PredictorDoble(fallar=True))


def test_modelo_entrenado_repr_no_incluye_el_artefacto() -> None:
    _, resultado = entrenar(seis_evaluables())

    assert "artefacto=" not in repr(resultado)


def test_ejecutar_ciclos_produce_el_mismo_modelo_que_ejecutar() -> None:
    ciclos = seis_evaluables()
    _, por_historico = entrenar(ciclos)

    por_ciclos = EntrenarModeloInicial(PredictorDoble()).ejecutar_ciclos(
        [ciclo_modelo_desde(c) for c in ciclos], CORTE
    )

    assert por_ciclos == por_historico
    assert por_ciclos.metadata_tecnica["fecha_corte"] == "2026-08-31"


# ---------------------------------------------------------------- M01: medianas y conjunto


def test_ejecutar_medianas_solo_de_evaluables_pendientes_con_monto_no_las_cambian() -> None:
    base = seis_evaluables()
    con_pendientes = [
        *base,
        ciclo(
            13,
            socio="I",
            actividad=date(2026, 7, 1),
            estado=EstadoCiclo.PENDIENTE,
            monto=Decimal("900"),
        ),
        ciclo(
            14,
            socio="J",
            actividad=date(2026, 7, 5),
            estado=EstadoCiclo.PENDIENTE,
            plan=Plan.TRIMESTRAL,
            vence=date(2026, 10, 3),
            monto=Decimal("500"),
        ),
    ]

    _, sin = entrenar(base)
    _, con = entrenar(con_pendientes)

    assert con.medianas == sin.medianas
    assert con.metadata_tecnica["medianas_monto"] == {
        "por_plan": {"MENSUAL": "30"},
        "general": "30",
    }


def test_ejecutar_medianas_se_aplican_a_evaluables_sin_monto() -> None:
    ciclos = [
        *seis_evaluables(),
        ciclo(15, socio="K", actividad=date(2025, 7, 1), monto=None, no_renovo=False),
        ciclo(
            16,
            socio="L",
            actividad=date(2026, 7, 10),
            estado=EstadoCiclo.PENDIENTE,
            monto=Decimal("999"),
        ),
    ]
    doble, _ = entrenar(ciclos)

    features = doble.train_llamadas[0]["features"]
    assert isinstance(features, list)
    sin_monto = [f for f in features if f["mes_vencimiento"] == "2025-07"]
    assert [f["monto_actual"] for f in sin_monto] == [Decimal("30")]


def test_ejecutar_entrena_con_el_conjunto_del_modelo_por_defecto() -> None:
    doble, _ = entrenar(seis_evaluables())

    llamada = doble.train_llamadas[0]
    assert llamada["numericas"] == VARIABLES_NUMERICAS_MODELO
    assert llamada["categoricas"] == VARIABLES_CATEGORICAS_MODELO


def test_ejecutar_con_conjunto_sin_forma_pago_ni_inicio_entrena_solo_con_esas() -> None:
    doble = PredictorDoble()

    EntrenarModeloInicial(doble, variables=CONJUNTO_SIN_FORMA_PAGO_NI_INICIO).ejecutar(
        seis_evaluables(), CORTE
    )

    llamada = doble.train_llamadas[0]
    assert llamada["numericas"] == VARIABLES_NUMERICAS
    assert llamada["categoricas"] == ("plan", "mes_vencimiento")
    # Las filas siguen con las 10 columnas: el artefacto selecciona las suyas.
    features = llamada["features"]
    assert isinstance(features, list)
    assert all(set(f) == set(VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS) for f in features)
