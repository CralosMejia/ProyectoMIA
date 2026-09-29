"""Caso de uso ``ProcesarHistorico`` (CU-03, pasos 4-11 y 15; logica sin persistencia).

Orquesta: lector -> limpieza e identidad (``limpiar``) -> fecha de corte -> ciclos y etiqueta
(``etiquetar``). No usa repositorios: el guardado atomico es de otro caso de uso (D3-BE-04).
El ``InformeHistorico`` solo lleva conteos, fechas y claves fijas; nunca nombres, cedulas,
celulares ni correos (RN-03.5, RT-13).
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.application.historial.ports import LectorHistorico
from app.domain.common.enums import EstadoCiclo
from app.domain.historico.ciclos import CicloEtiquetado, MotivoCiclo, etiquetar, fecha_corte
from app.domain.historico.registro import RegistroHistorico, limpiar

ValorInforme = int | Decimal | date | None | dict[str, int] | dict[str, date]


@dataclass(frozen=True, slots=True)
class InformeHistorico:
    """Conteos del procesamiento del historico; sin datos personales."""

    libros: int
    hojas_incluidas: int
    hojas_omitidas: int
    filas_leidas: int
    descartadas_no_utiles: int
    utiles: int
    sin_identidad: int
    con_identidad: int
    socios_distintos: int
    socios_por_cedula: int
    socios_por_nombre: int
    registros_por_cedula: int
    registros_por_nombre: int
    inicio_aproximado: int
    montos_invalidos: int
    fecha_corte: date
    ciclos_por_estado: dict[str, int]
    ciclos_por_motivo: dict[str, int]
    evaluables: int
    no_renovo: int
    renovo: int
    prevalencia: Decimal | None
    rango_vencimientos: tuple[date, date] | None
    rango_vencimientos_evaluables: tuple[date, date] | None

    def a_dict(self) -> dict[str, ValorInforme]:
        """Diccionario con claves fijas y valores numericos o fechas (los rangos como dict)."""
        datos: dict[str, ValorInforme] = {}
        for nombre in self.__slots__:
            valor = getattr(self, nombre)
            if isinstance(valor, dict):
                valor = dict(valor)
            elif isinstance(valor, tuple):
                valor = {"desde": valor[0], "hasta": valor[1]}
            datos[nombre] = valor
        return datos


@dataclass(frozen=True, slots=True)
class ResultadoProcesamiento:
    """Registros limpios, ciclos etiquetados, fecha de corte e informe; ``repr`` sin datos."""

    registros: tuple[RegistroHistorico, ...] = field(repr=False)
    ciclos: tuple[CicloEtiquetado, ...] = field(repr=False)
    fecha_corte: date
    informe: InformeHistorico


def _rango(fechas: Iterable[date | None]) -> tuple[date, date] | None:
    presentes = [f for f in fechas if f is not None]
    return (min(presentes), max(presentes)) if presentes else None


class ProcesarHistorico:
    """Procesa los libros historicos hasta la etiqueta de no renovacion, sin persistir."""

    def __init__(self, lector: LectorHistorico) -> None:
        self._lector = lector

    def ejecutar(self, rutas: Sequence[Path]) -> ResultadoProcesamiento:
        leidos = self._lector.leer(rutas)
        limpieza = limpiar(leidos.filas)
        corte = fecha_corte(fila.mes_hoja for fila in leidos.filas)
        registros = limpieza.registros
        ciclos = tuple(etiquetar(registros, corte))

        por_estado = Counter(c.estado for c in ciclos)
        por_motivo = Counter(c.motivo for c in ciclos)
        evaluables = [c for c in ciclos if c.estado is EstadoCiclo.EVALUABLE]
        no_renovo = sum(1 for c in evaluables if c.no_renovo is True)
        identidades_cedula = {r.identidad for r in registros if r.cedula is not None}
        identidades_nombre = {r.identidad for r in registros if r.cedula is None}

        informe = InformeHistorico(
            libros=len(leidos.libros),
            hojas_incluidas=sum(len(libro.hojas_incluidas) for libro in leidos.libros),
            hojas_omitidas=sum(len(libro.hojas_omitidas) for libro in leidos.libros),
            filas_leidas=limpieza.filas_leidas,
            descartadas_no_utiles=limpieza.descartadas_no_utiles,
            utiles=limpieza.utiles,
            sin_identidad=limpieza.sin_identidad,
            con_identidad=limpieza.con_identidad,
            socios_distintos=limpieza.socios_distintos,
            socios_por_cedula=len(identidades_cedula),
            socios_por_nombre=len(identidades_nombre),
            registros_por_cedula=limpieza.por_cedula,
            registros_por_nombre=limpieza.por_nombre,
            inicio_aproximado=limpieza.inicio_aproximado,
            montos_invalidos=limpieza.montos_invalidos,
            fecha_corte=corte,
            ciclos_por_estado={e.value: por_estado[e] for e in EstadoCiclo},
            ciclos_por_motivo={m.value: por_motivo[m] for m in MotivoCiclo},
            evaluables=len(evaluables),
            no_renovo=no_renovo,
            renovo=len(evaluables) - no_renovo,
            prevalencia=Decimal(no_renovo) / Decimal(len(evaluables)) if evaluables else None,
            rango_vencimientos=_rango(r.fecha_vencimiento for r in registros),
            rango_vencimientos_evaluables=_rango(c.registro.fecha_vencimiento for c in evaluables),
        )
        return ResultadoProcesamiento(
            registros=registros, ciclos=ciclos, fecha_corte=corte, informe=informe
        )
