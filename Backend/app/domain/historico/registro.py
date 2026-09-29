"""Registro historico: de filas crudas a registros con identidad (notebook MVP, 3.6-4.6, 5.4).

Orden del notebook: filas utiles (3.6) -> conversiones (3.7) -> identidad utilizable
(4.1: nombre normalizado de al menos 5 caracteres) -> cedula e identidad (4.2-4.3) ->
duracion (4.4) -> plan (4.5) -> forma de pago (4.6) -> fecha de actividad (5.4).
Los duplicados exactos se conservan, como en el notebook.

Desviacion documentada del notebook: un monto cobrado negativo se guarda como ``None`` y se
cuenta en ``montos_invalidos`` (la base de datos exige ``monto_cobrado >= 0``).

Ningun ``repr`` expone datos personales (RN-03.5): nombre, cedula, celular, correo e
identidad se excluyen del ``repr``.
"""

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.common.enums import FormaPago, Plan
from app.domain.historico.conversiones import convertir_fecha, convertir_monto
from app.domain.historico.identidad import identidad_de
from app.domain.historico.normalizacion import (
    es_fila_util,
    normalizar_cedula,
    normalizar_forma_pago,
    normalizar_nombre,
    normalizar_plan,
)

LONGITUD_MINIMA_NOMBRE = 5


@dataclass(frozen=True, slots=True)
class FilaCruda:
    """Fila de una hoja mensual tal como la entrega el lector (valores crudos de celda)."""

    anio: int
    hoja: str
    fila: int
    mes_hoja: date
    nombre: object = field(default=None, repr=False)
    cedula: object = field(default=None, repr=False)
    celular: object = field(default=None, repr=False)
    correo: object = field(default=None, repr=False)
    plan: object = None
    fecha_inicio: object = None
    fecha_fin: object = None
    forma_pago: object = None
    monto_cobrado: object = None


@dataclass(frozen=True, slots=True)
class RegistroHistorico:
    identidad: str = field(repr=False)
    cedula: str | None = field(repr=False)
    nombre: str = field(repr=False)
    nombre_normalizado: str = field(repr=False)
    plan: Plan
    plan_original: str | None
    forma_pago: FormaPago
    forma_pago_original: str | None
    fecha_inicio: date | None
    fecha_vencimiento: date | None
    fecha_actividad: date
    inicio_aproximado: bool
    duracion_dias: int | None
    monto_cobrado: Decimal | None
    referencia: tuple[int, str, int]


@dataclass(frozen=True, slots=True)
class ResultadoLimpieza:
    """Registros limpios y conteos de la limpieza; su ``repr`` solo muestra conteos."""

    registros: tuple[RegistroHistorico, ...] = field(repr=False)
    filas_leidas: int
    descartadas_no_utiles: int
    sin_identidad: int
    montos_invalidos: int

    @property
    def utiles(self) -> int:
        return self.filas_leidas - self.descartadas_no_utiles

    @property
    def con_identidad(self) -> int:
        return len(self.registros)

    @property
    def socios_distintos(self) -> int:
        return len({r.identidad for r in self.registros})

    @property
    def por_cedula(self) -> int:
        return sum(1 for r in self.registros if r.cedula is not None)

    @property
    def por_nombre(self) -> int:
        return sum(1 for r in self.registros if r.cedula is None)

    @property
    def inicio_aproximado(self) -> int:
        return sum(1 for r in self.registros if r.inicio_aproximado)


def _texto_original(valor: object) -> str | None:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    texto = str(valor).strip()
    return texto or None


def _registro(fila: FilaCruda, nombre_normalizado: str) -> tuple[RegistroHistorico, bool]:
    """Construye el registro; el booleano indica si el monto era invalido (negativo)."""
    fecha_inicio = convertir_fecha(fila.fecha_inicio)
    fecha_vencimiento = convertir_fecha(fila.fecha_fin)
    duracion = (
        (fecha_vencimiento - fecha_inicio).days
        if fecha_inicio is not None and fecha_vencimiento is not None
        else None
    )
    monto = convertir_monto(fila.monto_cobrado)
    monto_invalido = monto is not None and monto < 0
    cedula = normalizar_cedula(fila.cedula)
    registro = RegistroHistorico(
        identidad=identidad_de(cedula, nombre_normalizado),
        cedula=cedula,
        nombre=str(fila.nombre).strip(),
        nombre_normalizado=nombre_normalizado,
        plan=normalizar_plan(fila.plan, duracion),
        plan_original=_texto_original(fila.plan),
        forma_pago=normalizar_forma_pago(fila.forma_pago),
        forma_pago_original=_texto_original(fila.forma_pago),
        fecha_inicio=fecha_inicio,
        fecha_vencimiento=fecha_vencimiento,
        fecha_actividad=fecha_inicio if fecha_inicio is not None else fila.mes_hoja,
        inicio_aproximado=fecha_inicio is None,
        duracion_dias=duracion,
        monto_cobrado=None if monto_invalido else monto,
        referencia=(fila.anio, fila.hoja, fila.fila),
    )
    return registro, monto_invalido


def limpiar(filas: Iterable[FilaCruda]) -> ResultadoLimpieza:
    """Aplica las reglas de limpieza e identidad del notebook a las filas crudas."""
    registros: list[RegistroHistorico] = []
    leidas = no_utiles = sin_identidad = montos_invalidos = 0
    for fila in filas:
        leidas += 1
        if not es_fila_util(fila.nombre):
            no_utiles += 1
            continue
        nombre_normalizado = normalizar_nombre(fila.nombre)
        if len(nombre_normalizado) < LONGITUD_MINIMA_NOMBRE:
            sin_identidad += 1
            continue
        registro, monto_invalido = _registro(fila, nombre_normalizado)
        registros.append(registro)
        montos_invalidos += int(monto_invalido)
    return ResultadoLimpieza(
        registros=tuple(registros),
        filas_leidas=leidas,
        descartadas_no_utiles=no_utiles,
        sin_identidad=sin_identidad,
        montos_invalidos=montos_invalidos,
    )
