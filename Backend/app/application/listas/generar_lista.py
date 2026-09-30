"""Caso de uso GenerarLista: cartera priorizada de no renovacion (CU-04) con niveles (CU-05).

Flujo (todo en **una** unidad de trabajo, con un solo ``commit`` al final):

1. Estado de la migracion distinto de ``COMPLETADA`` o sin modelo vigente ->
   ``SistemaNoListoError``.
2. Fecha de generacion: la pedida o "hoy" en la zona del negocio (``hoy_en_negocio`` sobre
   el reloj). Una fecha anterior a hoy -> ``FechaReferenciaPasadaError``.
3. Membresias -> ``CicloModelo``; ``excluido`` sale de ``clasificar`` con corte = fecha.
4. Cartera, sin los socios que ya renovaron y despues sin los socios sin cedula (antes de
   predecir y priorizar); variables con las medianas del modelo y el historial completo.
5. Score del modelo vigente, priorizacion y nivel con los umbrales del modelo.
6. Se guardan la lista (con el nombre recibido o ``nombre_por_defecto(fecha)``) y sus
   predicciones.

La prediccion cruza el puerto ``PredictorModel``: aqui no se usa scikit-learn ni pandas.
"""

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.application.historial.ports import MembresiaParaPrediccion
from app.application.listas.consultar_listas import a_dto, advertencia_de
from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO
from app.application.listas.ports import NuevaLista, NuevaPrediccion, UnidadDeTrabajoListas
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoCiclo, EstadoMigracion, Plan
from app.domain.common.exceptions import DomainError
from app.domain.common.fechas import hoy_en_negocio
from app.domain.common.predictor import PredictorModel
from app.domain.historico.ciclos import clasificar
from app.domain.listas.nombre import nombre_por_defecto
from app.domain.modelo.cartera import (
    CicloPuntuado,
    FilaPriorizada,
    priorizar,
    seleccionar_cartera,
    ya_renovo,
)
from app.domain.modelo.umbrales import Umbrales, nivel_de
from app.domain.modelo.variables import CicloModelo, MedianasMonto, construir_variables

CLAVE_MEDIANAS = "medianas_monto"
MENSAJE_NO_LISTO = "El sistema se esta inicializando; intente de nuevo en unos minutos."
MENSAJE_FECHA_PASADA = "La fecha de la lista debe ser hoy o posterior."


class SistemaNoListoError(DomainError):
    """La migracion historica no ha terminado o no hay un modelo vigente (-> 409)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_NO_LISTO)


class FechaReferenciaPasadaError(DomainError):
    """La fecha de la lista es anterior a hoy en la zona del negocio (-> 422)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_FECHA_PASADA)


def _decimal(valor: object) -> Decimal | None:
    if valor is None:
        return None
    if not isinstance(valor, str | int | Decimal):
        raise ValueError("Las medianas del modelo deben ser texto decimal.")
    return Decimal(valor)


def medianas_de(metadata: Mapping[str, object]) -> MedianasMonto:
    """Lee ``metadata_tecnica["medianas_monto"]``.

    Formato: ``{"por_plan": {"MENSUAL": "45.00", ...}, "general": "50.00" | null}``, como
    objeto o como texto JSON; los montos son texto ``Decimal``.
    """
    crudo = metadata.get(CLAVE_MEDIANAS)
    if crudo is None:
        raise ValueError("El modelo vigente no tiene las medianas de monto.")
    if isinstance(crudo, str):
        crudo = json.loads(crudo)
    if not isinstance(crudo, Mapping):
        raise ValueError("Las medianas de monto del modelo no tienen el formato esperado.")
    por_plan = crudo.get("por_plan") or {}
    if not isinstance(por_plan, Mapping):
        raise ValueError("Las medianas por plan del modelo no tienen el formato esperado.")
    medianas_plan: dict[Plan, Decimal] = {}
    for plan, valor in por_plan.items():
        mediana = _decimal(valor)
        if mediana is not None:
            medianas_plan[Plan(plan)] = mediana
    return MedianasMonto(por_plan=medianas_plan, general=_decimal(crudo.get("general")))


def _a_ciclo(m: MembresiaParaPrediccion, corte: date) -> CicloModelo:
    """Ciclo del modelo; ``excluido`` segun ``clasificar`` con la fecha de generacion."""
    duracion = (
        (m.fecha_vencimiento - m.fecha_inicio).days
        if m.fecha_inicio is not None and m.fecha_vencimiento is not None
        else None
    )
    base = CicloModelo(
        clave_socio=str(m.socio_id),
        ref=m.membresia_id,
        plan=m.plan,
        forma_pago=m.forma_pago,
        fecha_actividad=m.fecha_actividad,
        fecha_vencimiento=m.fecha_vencimiento,
        duracion_dias=duracion,
        monto_cobrado=m.monto_cobrado,
        inicio_aproximado=m.inicio_aproximado,
        excluido=False,
        no_renovo=None,
    )
    return replace(base, excluido=clasificar(base, corte)[0] is EstadoCiclo.EXCLUIDO)


def _membresia_id(ciclo: CicloModelo) -> int:
    if not isinstance(ciclo.ref, int):
        raise TypeError("El ciclo de la cartera debe referirse al id de su membresia.")
    return ciclo.ref


class GenerarLista:
    """Command de CU-04: genera y guarda una lista priorizada nueva."""

    def __init__(self, uow: UnidadDeTrabajoListas, predictor: PredictorModel, clock: Clock) -> None:
        self._uow = uow
        self._predictor = predictor
        self._clock = clock

    def ejecutar(self, parametros: GenerarListaDTO) -> ListaPriorizadaDTO:
        with self._uow() as uow:
            estado = uow.estado.obtener()
            modelo = uow.modelos.obtener_vigente()
            if estado.migracion_historica is not EstadoMigracion.COMPLETADA or modelo is None:
                raise SistemaNoListoError()

            hoy = hoy_en_negocio(self._clock.now())
            fecha = parametros.fecha_referencia or hoy
            if fecha < hoy:
                raise FechaReferenciaPasadaError()
            membresias = uow.membresias.listar_para_prediccion()
            ciclos = [_a_ciclo(m, fecha) for m in membresias]
            por_socio: defaultdict[str, list[CicloModelo]] = defaultdict(list)
            for ciclo in ciclos:
                por_socio[ciclo.clave_socio].append(ciclo)

            cartera = [
                c
                for c in seleccionar_cartera(ciclos, fecha, parametros.horizonte_dias)
                if not ya_renovo(c, por_socio[c.clave_socio])
            ]
            con_cedula = {m.membresia_id for m in membresias if m.socio_con_cedula}
            cartera = [c for c in cartera if _membresia_id(c) in con_cedula]
            medianas = medianas_de(modelo.metadata_tecnica)
            variables = [
                construir_variables(c, por_socio[c.clave_socio], medianas) for c in cartera
            ]
            predicciones = self._predictor.predict(modelo.artefacto, variables) if cartera else []
            if len(predicciones) != len(cartera):
                raise ValueError("El modelo debe devolver una prediccion por ciclo de la cartera.")

            filas = priorizar(
                [
                    CicloPuntuado(
                        membresia_id=_membresia_id(c),
                        clave_socio=c.clave_socio,
                        fecha_vencimiento=_vencimiento(c),
                        score=p.score,
                        factores_principales=p.factores_principales,
                    )
                    for c, p in zip(cartera, predicciones, strict=True)
                ],
                parametros.top_k,
                fecha,
            )
            umbrales = Umbrales(
                alto=modelo.umbral_alto,
                medio=modelo.umbral_medio,
                porcentajes=modelo.porcentajes_umbral,
            )
            socio_de = {m.membresia_id: m.socio_id for m in membresias}
            lista_id = uow.listas.crear(
                NuevaLista(
                    modelo_id=modelo.id,
                    fecha_generacion=fecha,
                    horizonte_dias=parametros.horizonte_dias,
                    top_k=parametros.top_k,
                    nombre=parametros.nombre or nombre_por_defecto(fecha),
                ),
                _nuevas_predicciones(filas, umbrales, socio_de),
            )
            guardada = uow.listas.obtener(lista_id)
            if guardada is None:
                raise RuntimeError("La lista recien guardada no se pudo leer.")
            resultado = a_dto(guardada, advertencia_de(uow, guardada))
            uow.commit()
        return resultado


def _vencimiento(ciclo: CicloModelo) -> date:
    if ciclo.fecha_vencimiento is None:  # la cartera solo contiene ciclos con vencimiento
        raise ValueError("Un ciclo de la cartera no tiene vencimiento.")
    return ciclo.fecha_vencimiento


def _nuevas_predicciones(
    filas: Sequence[FilaPriorizada], umbrales: Umbrales, socio_de: Mapping[int, int]
) -> list[NuevaPrediccion]:
    return [
        NuevaPrediccion(
            membresia_id=f.ciclo.membresia_id,
            socio_id=socio_de[f.ciclo.membresia_id],
            score=f.ciclo.score,
            nivel_riesgo=nivel_de(f.ciclo.score, umbrales),
            factores_principales=f.ciclo.factores_principales,
            prioridad=f.prioridad,
            dentro_top_k=f.dentro_top_k,
        )
        for f in filas
    ]
