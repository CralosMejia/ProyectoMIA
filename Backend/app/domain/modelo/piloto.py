"""Indicadores del piloto (M04, R-018): cifras observadas, no causales, del top 25 del mes.

Verificacion T+30 (definicion (c)): con el corte de los datos, un caso con
``T + 30 <= corte`` (``clasificar`` lo da ``EVALUABLE``) esta verificado; renovo si hay otra
membresia no ``DIARIO`` del mismo socio con actividad en ``[T - DIAS_RENOVACION_ANTICIPADA,
T + DIAS_OBSERVACION]`` (la misma regla que ``etiquetar_ciclos``); la membresia de renovacion es
la primera por ``(fecha_actividad, ref)``. ``T + 30 > corte`` (o ``T > corte``) -> pendiente.
Sin vencimiento, sin ciclo o excluido por otra causa -> sin dato (fuera de los ``n``).

Formulas (definicion (e)); proporciones con 8 decimales ``ROUND_HALF_EVEN``, sin minimo de
casos y siempre con su ``n``:

1. ``precision_top25`` = no renovaron / verificados.
2. ``contactados_antes_vencimiento`` = contactados con ``fecha_contacto < T`` / casos con dato.
3. ``dias_anticipacion`` = promedio de ``T - fecha_contacto`` de los contactados con fecha
   (1 decimal; puede ser <= 0).
4. ``tasa_renovacion_contactados`` = renovaron / contactados verificados.
5. ``monto_retenido`` = suma del monto (cobrado, si no facturado) de la membresia de renovacion
   de los contactados verificados que renovaron (2 decimales); sin ningun monto -> se cuenta
   en ``renovaciones_sin_monto``.
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum, unique

from app.domain.common.enums import EstadoCiclo, Plan
from app.domain.historico.ciclos import (
    DIAS_OBSERVACION,
    DIAS_RENOVACION_ANTICIPADA,
    MotivoCiclo,
    clasificar,
)
from app.domain.modelo.variables import CicloModelo

TOP_PILOTO = 25
"""Definicion (b): el top del piloto son las prioridades ``<= 25`` (aunque ``top_k`` sea otro)."""

_OCHO_DECIMALES = Decimal("0.00000001")
_UN_DECIMAL = Decimal("0.1")
_DOS_DECIMALES = Decimal("0.01")


@unique
class EstadoVerificacion(StrEnum):
    RENOVO = "RENOVO"
    NO_RENOVO = "NO_RENOVO"
    PENDIENTE = "PENDIENTE"
    SIN_DATO = "SIN_DATO"


@unique
class EstadoIndicador(StrEnum):
    COMPLETO = "COMPLETO"
    PARCIAL = "PARCIAL"
    PENDIENTE = "PENDIENTE"
    SIN_DATOS = "SIN_DATOS"


_R = EstadoVerificacion
_VERIFICADOS = frozenset({EstadoVerificacion.RENOVO, EstadoVerificacion.NO_RENOVO})


@dataclass(frozen=True, slots=True)
class Verificacion:
    """Resultado T+30 de un caso; ``renovacion`` = ``ref`` de la membresia de renovacion."""

    estado: EstadoVerificacion
    renovacion: Hashable | None = None


@dataclass(frozen=True, slots=True)
class MontoMembresia:
    monto_cobrado: Decimal | None
    monto_facturado: Decimal | None


@dataclass(frozen=True, slots=True)
class CasoPiloto:
    """Un caso del top: ``vencimiento`` = T de su membresia (``None`` si falta o se borro)."""

    ref: Hashable
    vencimiento: date | None
    contactado: bool
    fecha_contacto: date | None


@dataclass(frozen=True, slots=True)
class IndicadorProporcion:
    """``valor = numerador / denominador``; ``n`` = casos considerados (verificados +
    pendientes cuando aplica) y ``pendientes`` = casos aun sin verificar."""

    valor: Decimal | None
    numerador: int
    denominador: int
    n: int
    pendientes: int
    estado: EstadoIndicador


@dataclass(frozen=True, slots=True)
class IndicadorDias:
    valor: Decimal | None
    n: int
    estado: EstadoIndicador


@dataclass(frozen=True, slots=True)
class IndicadorMonto:
    total: Decimal | None
    renovaciones: int
    renovaciones_sin_monto: int
    n: int
    pendientes: int
    estado: EstadoIndicador


@dataclass(frozen=True, slots=True)
class IndicadoresPiloto:
    n_top: int
    sin_dato: int
    precision_top25: IndicadorProporcion
    contactados_antes_vencimiento: IndicadorProporcion
    dias_anticipacion: IndicadorDias
    tasa_renovacion_contactados: IndicadorProporcion
    monto_retenido: IndicadorMonto


def _orden_ref(ref: Hashable) -> int:
    # Las refs del sistema son ids de membresia (int); otra ref desempata por posicion.
    return ref if isinstance(ref, int) else 0


def verificar_renovacion(
    ref: Hashable, ciclos: Sequence[CicloModelo], corte: date | None
) -> Verificacion:
    """Verificacion T+30 del ciclo ``ref`` al ``corte`` de los datos (``None`` = sin datos)."""
    posicion = next((i for i, c in enumerate(ciclos) if c.ref == ref), None)
    if posicion is None:
        return Verificacion(EstadoVerificacion.SIN_DATO)
    ciclo = ciclos[posicion]
    vence = ciclo.fecha_vencimiento
    if vence is None:
        return Verificacion(EstadoVerificacion.SIN_DATO)
    if corte is None:
        return Verificacion(EstadoVerificacion.PENDIENTE)
    estado, motivo = clasificar(ciclo, corte)
    if estado is EstadoCiclo.PENDIENTE or motivo is MotivoCiclo.VENCIMIENTO_POSTERIOR_AL_CORTE:
        return Verificacion(EstadoVerificacion.PENDIENTE)
    if estado is not EstadoCiclo.EVALUABLE:
        return Verificacion(EstadoVerificacion.SIN_DATO)
    inicio = vence - timedelta(days=DIAS_RENOVACION_ANTICIPADA)
    fin = vence + timedelta(days=DIAS_OBSERVACION)
    candidatas = [
        (otra.fecha_actividad, _orden_ref(otra.ref), i, otra.ref)
        for i, otra in enumerate(ciclos)
        if i != posicion
        and otra.clave_socio == ciclo.clave_socio
        and otra.plan is not Plan.DIARIO
        and inicio <= otra.fecha_actividad <= fin
    ]
    if not candidatas:
        return Verificacion(EstadoVerificacion.NO_RENOVO)
    primera = min(candidatas, key=lambda c: (c[0], c[1], c[2]))
    return Verificacion(EstadoVerificacion.RENOVO, renovacion=primera[3])


def _proporcion(numerador: int, denominador: int) -> Decimal:
    return (Decimal(numerador) / Decimal(denominador)).quantize(
        _OCHO_DECIMALES, rounding=ROUND_HALF_EVEN
    )


def _estado_verificable(n: int, verificados: int, pendientes: int) -> EstadoIndicador:
    if n == 0:
        return EstadoIndicador.SIN_DATOS
    if verificados == 0:
        return EstadoIndicador.PENDIENTE
    return EstadoIndicador.COMPLETO if pendientes == 0 else EstadoIndicador.PARCIAL


def _indicador_verificable(
    numerador: int, verificados: int, pendientes: int
) -> IndicadorProporcion:
    n = verificados + pendientes
    return IndicadorProporcion(
        valor=_proporcion(numerador, verificados) if verificados else None,
        numerador=numerador,
        denominador=verificados,
        n=n,
        pendientes=pendientes,
        estado=_estado_verificable(n, verificados, pendientes),
    )


def _monto(monto: MontoMembresia | None) -> Decimal | None:
    if monto is None:
        return None
    return monto.monto_cobrado if monto.monto_cobrado is not None else monto.monto_facturado


def calcular_indicadores(
    casos: Sequence[CasoPiloto],
    resultados: Mapping[Hashable, Verificacion],
    montos: Mapping[Hashable, MontoMembresia],
) -> IndicadoresPiloto:
    """Los cinco indicadores del top. ``resultados`` por ``ref`` del caso (ausente = sin dato);
    ``montos`` por ``ref`` de la membresia de renovacion."""
    sin_dato = _R.SIN_DATO
    con_dato: list[tuple[CasoPiloto, date, EstadoVerificacion, Hashable | None]] = []
    for caso in casos:
        resultado = resultados.get(caso.ref, Verificacion(sin_dato))
        if caso.vencimiento is None or resultado.estado is sin_dato:
            continue
        con_dato.append((caso, caso.vencimiento, resultado.estado, resultado.renovacion))

    verificados = [x for x in con_dato if x[2] in _VERIFICADOS]
    precision = _indicador_verificable(
        numerador=sum(1 for x in verificados if x[2] is _R.NO_RENOVO),
        verificados=len(verificados),
        pendientes=sum(1 for x in con_dato if x[2] is _R.PENDIENTE),
    )

    contactados = [x for x in con_dato if x[0].contactado]
    anticipaciones = [
        (t - caso.fecha_contacto).days
        for caso, t, _, _ in contactados
        if caso.fecha_contacto is not None
    ]
    antes = sum(1 for d in anticipaciones if d > 0)
    total_con_dato = len(con_dato)
    contactados_antes = IndicadorProporcion(
        valor=_proporcion(antes, total_con_dato) if total_con_dato else None,
        numerador=antes,
        denominador=total_con_dato,
        n=total_con_dato,
        pendientes=0,
        estado=EstadoIndicador.COMPLETO if total_con_dato else EstadoIndicador.SIN_DATOS,
    )
    dias = IndicadorDias(
        valor=(
            (Decimal(sum(anticipaciones)) / Decimal(len(anticipaciones))).quantize(
                _UN_DECIMAL, rounding=ROUND_HALF_EVEN
            )
            if anticipaciones
            else None
        ),
        n=len(anticipaciones),
        estado=EstadoIndicador.COMPLETO if anticipaciones else EstadoIndicador.SIN_DATOS,
    )

    contactados_verificados = [x for x in contactados if x[2] in _VERIFICADOS]
    renovados = [x for x in contactados_verificados if x[2] is _R.RENOVO]
    pendientes_contactados = sum(1 for x in contactados if x[2] is _R.PENDIENTE)
    tasa = _indicador_verificable(
        numerador=len(renovados),
        verificados=len(contactados_verificados),
        pendientes=pendientes_contactados,
    )

    importes = [_monto(montos.get(x[3])) if x[3] is not None else None for x in renovados]
    con_monto = [m for m in importes if m is not None]
    monto = IndicadorMonto(
        total=(
            sum(con_monto, Decimal(0)).quantize(_DOS_DECIMALES, rounding=ROUND_HALF_EVEN)
            if contactados_verificados
            else None
        ),
        renovaciones=len(renovados),
        renovaciones_sin_monto=len(importes) - len(con_monto),
        n=len(contactados_verificados),
        pendientes=pendientes_contactados,
        estado=tasa.estado,
    )

    return IndicadoresPiloto(
        n_top=len(casos),
        sin_dato=len(casos) - total_con_dato,
        precision_top25=precision,
        contactados_antes_vencimiento=contactados_antes,
        dias_anticipacion=dias,
        tasa_renovacion_contactados=tasa,
        monto_retenido=monto,
    )
