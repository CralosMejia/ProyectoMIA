"""Servicio ``EntrenarModeloInicial`` (CU-03 paso 12 y CU-05): ciclos -> variables -> modelo.

Orquesta, sin persistir:

1. Convierte los ciclos etiquetados en ``CicloModelo``.
2. Medianas de ``monto_cobrado`` de los ciclos no excluidos (se guardan con el modelo).
3. Variables en T-30 de cada ciclo ``EVALUABLE``; el historial previo son los ciclos no
   excluidos (evaluables y pendientes) del mismo socio.
4. Entrena con todos los evaluables, etiqueta ``int(no_renovo)``, en el orden del notebook
   (``ordenar_para_entrenamiento``: el bootstrap del bosque depende de el).
5. Referencia de los factores: las filas de entrenamiento cuyo vencimiento cae en
   ``PERIODO_REFERENCIA_FACTORES`` (como ``X_train`` del notebook, 13.3).
6. Umbrales por percentiles con los scores del modelo nuevo sobre los evaluables de los 3
   meses de vencimiento mas recientes (CU-05).

La version del modelo la decide quien llama (la migracion inicial guarda la v1). Si el
predictor falla, la excepcion se propaga: la reversion es responsabilidad de quien llama.
Los mensajes de error nunca incluyen datos personales.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.application.modelo.mapeo import ciclo_modelo_desde
from app.domain.common.exceptions import DomainError
from app.domain.common.predictor import FeatureRow, PredictorModel
from app.domain.historico.ciclos import CicloEtiquetado
from app.domain.modelo.umbrales import Umbrales, calcular_umbrales, meses_recientes_con_resultado
from app.domain.modelo.variables import (
    PERIODO_REFERENCIA_FACTORES,
    VARIABLES_CATEGORICAS,
    VARIABLES_NUMERICAS,
    CicloModelo,
    MedianasMonto,
    calcular_medianas,
    construir_variables,
    ordenar_para_entrenamiento,
)


class DatosInsuficientesError(DomainError):
    """No hay ciclos evaluables suficientes (o de las dos clases) para entrenar."""


@dataclass(frozen=True, slots=True)
class ModeloEntrenado:
    """Modelo entrenado listo para guardarse; sin datos personales."""

    artefacto: bytes = field(repr=False)
    metadata_tecnica: Mapping[str, object]
    ciclos_entrenamiento: int
    periodo_desde: date
    periodo_hasta: date
    prevalencia: Decimal
    umbrales: Umbrales
    medianas: MedianasMonto

    @property
    def porcentajes_umbral(self) -> Mapping[str, int]:
        return self.umbrales.porcentajes


def medianas_como_texto(medianas: MedianasMonto) -> dict[str, object]:
    """Medianas serializables (``Decimal`` como texto) para ``metadata_tecnica``."""
    return {
        "por_plan": {plan.value: str(valor) for plan, valor in medianas.por_plan.items()},
        "general": None if medianas.general is None else str(medianas.general),
    }


def _por_socio(ciclos: Sequence[CicloModelo]) -> dict[str, list[CicloModelo]]:
    grupos: defaultdict[str, list[CicloModelo]] = defaultdict(list)
    for ciclo in ciclos:
        if not ciclo.excluido:
            grupos[ciclo.clave_socio].append(ciclo)
    return grupos


class EntrenarModeloInicial:
    """Entrena el modelo con los ciclos del historico y calcula sus umbrales."""

    def __init__(self, predictor: PredictorModel) -> None:
        self._predictor = predictor

    def ejecutar(
        self, ciclos_etiquetados: Sequence[CicloEtiquetado], fecha_corte: date
    ) -> ModeloEntrenado:
        ciclos = [ciclo_modelo_desde(c) for c in ciclos_etiquetados]
        evaluables = ordenar_para_entrenamiento(
            [
                c
                for c in ciclos
                if not c.excluido and c.no_renovo is not None and c.fecha_vencimiento is not None
            ]
        )
        etiquetas = [int(bool(c.no_renovo)) for c in evaluables]
        if not evaluables:
            raise DatosInsuficientesError("No hay ciclos evaluables para entrenar el modelo.")
        if len(set(etiquetas)) < 2:
            raise DatosInsuficientesError(
                "Los ciclos evaluables no tienen las dos clases (renovo y no renovo)."
            )

        medianas = calcular_medianas(ciclos)
        historial = _por_socio(ciclos)
        filas: list[FeatureRow] = [
            construir_variables(c, historial[c.clave_socio], medianas) for c in evaluables
        ]
        referencia = [
            fila
            for ciclo, fila in zip(evaluables, filas, strict=True)
            if PERIODO_REFERENCIA_FACTORES.contiene(ciclo)
        ]
        entrenado = self._predictor.train(
            filas,
            etiquetas,
            VARIABLES_NUMERICAS,
            VARIABLES_CATEGORICAS,
            referencia=referencia,
        )

        recientes = {id(c) for c in meses_recientes_con_resultado(evaluables)}
        filas_recientes = [
            fila for ciclo, fila in zip(evaluables, filas, strict=True) if id(ciclo) in recientes
        ]
        scores = [p.score for p in self._predictor.predict(entrenado.artefacto, filas_recientes)]
        umbrales = calcular_umbrales(scores)

        vencimientos = [c.fecha_vencimiento for c in evaluables if c.fecha_vencimiento]
        metadata: dict[str, object] = dict(entrenado.metadata_tecnica)
        metadata["medianas_monto"] = medianas_como_texto(medianas)
        metadata["fecha_corte"] = fecha_corte.isoformat()
        metadata["ciclos_referencia_factores"] = len(referencia)
        metadata["ciclos_umbrales"] = len(filas_recientes)
        return ModeloEntrenado(
            artefacto=entrenado.artefacto,
            metadata_tecnica=metadata,
            ciclos_entrenamiento=len(evaluables),
            periodo_desde=min(vencimientos),
            periodo_hasta=max(vencimientos),
            prevalencia=Decimal(sum(etiquetas)) / Decimal(len(etiquetas)),
            umbrales=umbrales,
            medianas=medianas,
        )
