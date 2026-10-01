"""Conversiones al ciclo que usa el modelo y lectura de las medianas guardadas con el modelo.

- ``ciclo_modelo_desde``: ciclo etiquetado del historico (CU-03). ``clave_socio`` es la
  identidad del socio y ``ref`` la referencia de origen (anio, hoja, fila), unica por
  registro. ``excluido`` sale del estado del ciclo y ``no_renovo`` de su etiqueta (``None`` si
  el ciclo no es evaluable).
- ``ciclo_de_membresia``: membresia guardada (CU-02, CU-04, CU-11) -> ciclo **sin etiquetar**
  (``excluido=False``, ``no_renovo=None``); ``clave_socio`` = id del socio y ``ref`` = id de
  la membresia. Quien llama decide la etiqueta (``clasificar`` o ``etiquetar_ciclos``).
- ``medianas_de``: medianas de ``monto_cobrado`` de ``metadata_tecnica`` de un modelo.
"""

import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.domain.common.enums import EstadoCiclo, FormaPago, Plan
from app.domain.historico.ciclos import CicloEtiquetado
from app.domain.modelo.variables import CicloModelo, MedianasMonto

CLAVE_MEDIANAS = "medianas_monto"


class DatosMembresia(Protocol):
    """Campos de una membresia guardada que necesita el ciclo del modelo."""

    @property
    def membresia_id(self) -> int: ...

    @property
    def socio_id(self) -> int: ...

    @property
    def plan(self) -> Plan: ...

    @property
    def forma_pago(self) -> FormaPago: ...

    @property
    def fecha_inicio(self) -> date | None: ...

    @property
    def fecha_vencimiento(self) -> date | None: ...

    @property
    def fecha_actividad(self) -> date: ...

    @property
    def monto_cobrado(self) -> Decimal | None: ...

    @property
    def inicio_aproximado(self) -> bool: ...


def ciclo_modelo_desde(ciclo: CicloEtiquetado) -> CicloModelo:
    """``CicloEtiquetado`` (registro + estado + etiqueta) -> ``CicloModelo``."""
    registro = ciclo.registro
    return CicloModelo(
        clave_socio=registro.identidad,
        ref=registro.referencia,
        plan=registro.plan,
        forma_pago=registro.forma_pago,
        fecha_actividad=registro.fecha_actividad,
        fecha_vencimiento=registro.fecha_vencimiento,
        duracion_dias=registro.duracion_dias,
        monto_cobrado=registro.monto_cobrado,
        inicio_aproximado=registro.inicio_aproximado,
        excluido=ciclo.estado is EstadoCiclo.EXCLUIDO,
        no_renovo=ciclo.no_renovo if ciclo.estado is EstadoCiclo.EVALUABLE else None,
    )


def ciclo_de_membresia(m: DatosMembresia) -> CicloModelo:
    """Membresia guardada -> ``CicloModelo`` sin etiquetar."""
    duracion = (
        (m.fecha_vencimiento - m.fecha_inicio).days
        if m.fecha_inicio is not None and m.fecha_vencimiento is not None
        else None
    )
    return CicloModelo(
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
