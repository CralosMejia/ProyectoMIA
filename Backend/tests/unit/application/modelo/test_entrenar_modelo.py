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
from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.common.exceptions import DomainError
from app.domain.common.predictor import FeatureRow, Prediction, PredictorModel, TrainedModel
from app.domain.historico.ciclos import CicloEtiquetado, MotivoCiclo
from app.domain.historico.registro import RegistroHistorico
from app.domain.modelo.umbrales import calcular_umbrales
from app.domain.modelo.variables import VARIABLES_CATEGORICAS, VARIABLES_NUMERICAS

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
    assert llamada["numericas"] == VARIABLES_NUMERICAS
    assert llamada["categoricas"] == VARIABLES_CATEGORICAS


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


def test_ejecutar_umbrales_con_scores_de_los_tres_meses_recientes() -> None:
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
    esperado = calcular_umbrales(scores)
    assert resultado.umbrales == esperado
    assert dict(resultado.porcentajes_umbral) == {"ALTO": 20, "MEDIO": 30, "BAJO": 50}


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
