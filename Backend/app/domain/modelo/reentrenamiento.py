"""Reglas de dominio del reentrenamiento (CU-02, decisiones (d) y (e) de R-011).

- ``etiquetar_ciclos``: la misma regla que ``historico.ciclos.etiquetar`` sobre ``CicloModelo``
  (clasificacion del notebook y renovacion = otra membresia no ``DIARIO`` del mismo socio con
  actividad en ``[T, T+30]``; solo se excluye el propio ciclo por posicion).
- Ciclo nuevo evaluable: evaluable al corte de hoy y con ``vencimiento + 30 > corte`` del
  modelo vigente, es decir, el modelo vigente aun no conocia su resultado.
- Criterios 1 a 4 de CU-02, con umbrales configurables.
- Fecha programada: igual a hoy -> ejecutar; pasada -> omitir (no se recupera); si no, esperar.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum, unique

from app.domain.common.enums import EstadoCiclo, Plan
from app.domain.common.fechas import sumar_meses
from app.domain.historico.ciclos import (
    DIAS_OBSERVACION,
    DIAS_RENOVACION_ANTICIPADA,
    clasificar,
)
from app.domain.modelo.variables import VARIABLES_CATEGORICAS, VARIABLES_NUMERICAS, CicloModelo

INTERVALO_MESES = 6
"""RN-02.1: meses de calendario entre dos reentrenamientos programados."""

_COLUMNAS_REQUERIDAS: frozenset[str] = frozenset(VARIABLES_NUMERICAS + VARIABLES_CATEGORICAS)
_DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CriteriosReentrenamiento:
    """Umbrales de CU-02 (configurables por ``.env``)."""

    min_ciclos_nuevos: int = 150
    min_cobertura_vencimiento: Decimal = Decimal("0.60")
    min_casos_por_clase: int = 20
    meses_comparacion: int = 3

    def __post_init__(self) -> None:
        if self.min_ciclos_nuevos < 0 or self.min_casos_por_clase < 0:
            raise ValueError("Los minimos de ciclos y de casos no pueden ser negativos.")
        if not Decimal(0) <= self.min_cobertura_vencimiento <= Decimal(1):
            raise ValueError("La cobertura minima debe estar entre 0 y 1.")
        if self.meses_comparacion < 1:
            raise ValueError("Se necesita al menos un mes de comparacion.")


@unique
class AccionProgramada(StrEnum):
    EJECUTAR = "EJECUTAR"
    OMITIR = "OMITIR"
    ESPERAR = "ESPERAR"


def etiquetar_ciclos(ciclos: Sequence[CicloModelo], corte: date) -> list[CicloModelo]:
    """Recalcula ``excluido`` y ``no_renovo`` de cada ciclo al ``corte``; conserva el orden.

    ``no_renovo`` solo tiene valor si el ciclo es evaluable; pendiente o excluido -> ``None``.
    """
    actividades: defaultdict[str, list[tuple[int, date]]] = defaultdict(list)
    for posicion, ciclo in enumerate(ciclos):
        if ciclo.plan is not Plan.DIARIO:
            actividades[ciclo.clave_socio].append((posicion, ciclo.fecha_actividad))

    resultado: list[CicloModelo] = []
    for posicion, ciclo in enumerate(ciclos):
        estado, _ = clasificar(ciclo, corte)
        no_renovo: bool | None = None
        vence = ciclo.fecha_vencimiento
        if estado is EstadoCiclo.EVALUABLE and vence is not None:
            inicio = vence - timedelta(days=DIAS_RENOVACION_ANTICIPADA)
            fin = vence + timedelta(days=DIAS_OBSERVACION)
            no_renovo = not any(
                otra != posicion and inicio <= actividad <= fin
                for otra, actividad in actividades.get(ciclo.clave_socio, [])
            )
        resultado.append(
            replace(ciclo, excluido=estado is EstadoCiclo.EXCLUIDO, no_renovo=no_renovo)
        )
    return resultado


def es_ciclo_nuevo(ciclo: CicloModelo, corte_vigente: date) -> bool:
    """Evaluable (ya etiquetado al corte de hoy) cuyo resultado no conocia el modelo vigente."""
    vence = ciclo.fecha_vencimiento
    if ciclo.excluido or ciclo.no_renovo is None or vence is None:
        return False
    return vence + timedelta(days=DIAS_OBSERVACION) > corte_vigente


def _porcentaje(fraccion: Decimal) -> str:
    return f"{(fraccion * 100).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_EVEN)} %"


def evaluar_criterios(
    ciclos_nuevos: Sequence[CicloModelo],
    vencimientos_membresias_nuevas: Sequence[date | None],
    filas_entrenamiento: Iterable[Mapping[str, object]],
    criterios: CriteriosReentrenamiento | None = None,
) -> list[str]:
    """Motivos de los criterios 1 a 4 que no se cumplen (lista vacia = se puede entrenar).

    - ``ciclos_nuevos``: los ciclos para los que ``es_ciclo_nuevo`` es cierto.
    - ``vencimientos_membresias_nuevas``: la fecha de vencimiento (o ``None``) de cada
      membresia registrada despues del ultimo entrenamiento; sin ninguna, no se cumple.
    - ``filas_entrenamiento``: variables del conjunto completo; cada fila debe tener todas las
      columnas del pipeline. Sin filas, tampoco se cumple.
    """
    c = criterios if criterios is not None else CriteriosReentrenamiento()
    motivos: list[str] = []

    if len(ciclos_nuevos) < c.min_ciclos_nuevos:
        motivos.append(
            f"Hay {len(ciclos_nuevos)} ciclos nuevos evaluables; "
            f"se necesitan al menos {c.min_ciclos_nuevos}."
        )

    total = len(vencimientos_membresias_nuevas)
    if total == 0:
        motivos.append("No hay membresias nuevas desde el ultimo entrenamiento.")
    else:
        con_vencimiento = sum(1 for v in vencimientos_membresias_nuevas if v is not None)
        cobertura = Decimal(con_vencimiento) / Decimal(total)
        if cobertura < c.min_cobertura_vencimiento:
            motivos.append(
                f"Solo el {_porcentaje(cobertura)} de las membresias nuevas tiene fecha de "
                f"vencimiento; se necesita al menos el {_porcentaje(c.min_cobertura_vencimiento)}."
            )

    no_renovaron = sum(1 for ciclo in ciclos_nuevos if ciclo.no_renovo is True)
    renovaron = sum(1 for ciclo in ciclos_nuevos if ciclo.no_renovo is False)
    if min(renovaron, no_renovaron) < c.min_casos_por_clase:
        motivos.append(
            f"Entre los ciclos nuevos hay {renovaron} que renovaron y {no_renovaron} que no "
            f"renovaron; se necesitan al menos {c.min_casos_por_clase} de cada clase."
        )

    filas = list(filas_entrenamiento)
    if not filas or any(not fila.keys() >= _COLUMNAS_REQUERIDAS for fila in filas):
        motivos.append("El conjunto de entrenamiento no tiene las columnas que exige el modelo.")

    return motivos


def accion_programada(hoy: date, programada: date | None) -> AccionProgramada:
    """Que hacer hoy con la fecha programada (RN-02.2: una fecha perdida no se recupera)."""
    if programada is None or programada > hoy:
        return AccionProgramada.ESPERAR
    if programada == hoy:
        return AccionProgramada.EJECUTAR
    return AccionProgramada.OMITIR


def proxima_tras_omitido(programada: date, hoy: date) -> date:
    """Primera fecha ``programada + k * 6 meses`` (k >= 1) que no queda antes de ``hoy``.

    Se suma siempre desde la fecha perdida para no arrastrar el recorte de fin de mes.
    """
    k = 1
    proxima = sumar_meses(programada, INTERVALO_MESES)
    while proxima < hoy:
        k += 1
        proxima = sumar_meses(programada, INTERVALO_MESES * k)
    return proxima


def fechas_perdidas(programada: date, hoy: date) -> list[date]:
    """Fechas ``programada + k * 6 meses`` (k >= 0) anteriores a ``hoy``: un ``OMITIDO`` cada una.

    La siguiente a la ultima es ``proxima_tras_omitido(programada, hoy)``.
    """
    perdidas: list[date] = []
    fecha = programada
    while fecha < hoy:
        perdidas.append(fecha)
        fecha = sumar_meses(programada, INTERVALO_MESES * len(perdidas))
    return perdidas
