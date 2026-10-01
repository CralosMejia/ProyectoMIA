"""CU-11: dashboard de retencion del mes (solo lectura; decision (c) de R-011).

1. Mes: el pedido (``YYYY-MM``) o el mes actual en fecha de negocio
   (``hoy_en_negocio(clock.now())``). Se consulta como rango de instantes
   ``[dia 1 05:00Z, dia 1 del mes siguiente 05:00Z)`` (Ecuador, UTC-5).
2. Embudo y resultados por campana del lector; la fila sin campana se llama "Sin campaña".
3. ``tasa_renovacion`` = ``renovaciones / gestiones_cerradas`` con 8 decimales (``Decimal``,
   nunca ``float``) solo si hay al menos ``MIN_CASOS_TASA`` gestiones cerradas con resultado;
   si no, ``None`` y ``casos_insuficientes``.
4. Estado del modelo vigente: version, fecha, ciclos, proxima fecha de reentrenamiento y
   ciclos nuevos evaluables (la misma regla que CU-02: ``etiquetar_ciclos`` al corte de hoy y
   ``es_ciclo_nuevo`` frente a la ``fecha_corte`` del vigente). Sin vigente -> ``None``.
"""

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from app.application.dashboard.dtos import (
    DashboardDTO,
    EmbudoDTO,
    EstadoModeloDTO,
    ResultadoCampaniaDTO,
)
from app.application.dashboard.ports import FilaCampania, LectorDashboard, ModeloDashboard
from app.domain.common.clock import Clock
from app.domain.common.fechas import ZONA_NEGOCIO, hoy_en_negocio, limites_mes_negocio
from app.domain.modelo.reentrenamiento import es_ciclo_nuevo, etiquetar_ciclos

MIN_CASOS_TASA = 10
"""RN-11.1: minimo de gestiones cerradas con resultado para mostrar la tasa."""
NOMBRE_SIN_CAMPANIA = "Sin campaña"
_OCHO_DECIMALES = Decimal("0.00000001")


def _version_publica(version: int) -> str:
    return f"v{version}"


def _tasa(renovaciones: int, cerradas: int) -> Decimal | None:
    if cerradas < MIN_CASOS_TASA:
        return None
    return (Decimal(renovaciones) / Decimal(cerradas)).quantize(
        _OCHO_DECIMALES, rounding=ROUND_HALF_EVEN
    )


def _resultado(fila: FilaCampania) -> ResultadoCampaniaDTO:
    tasa = _tasa(fila.renovaciones, fila.gestiones_cerradas)
    return ResultadoCampaniaDTO(
        campania_id=fila.campania_id,
        nombre=NOMBRE_SIN_CAMPANIA if fila.campania_id is None else (fila.nombre or ""),
        gestiones=fila.gestiones,
        contactados=fila.contactados,
        renovaciones=fila.renovaciones,
        gestiones_cerradas=fila.gestiones_cerradas,
        tasa_renovacion=tasa,
        casos_insuficientes=tasa is None,
    )


def _corte_vigente(modelo: ModeloDashboard) -> date:
    # Un modelo sin ``fecha_corte`` en su metadata usa el dia (Ecuador) en que se entreno.
    if modelo.fecha_corte is not None:
        return modelo.fecha_corte
    return modelo.fecha_entrenamiento.astimezone(ZONA_NEGOCIO).date()


class ConsultarDashboard:
    """Query de CU-11."""

    def __init__(self, lector: LectorDashboard, clock: Clock) -> None:
        self._lector = lector
        self._clock = clock

    def ejecutar(self, mes: str | None = None) -> DashboardDTO:
        hoy = hoy_en_negocio(self._clock.now())
        anio, numero = hoy.year, hoy.month
        if mes is not None:
            anio, numero = int(mes[:4]), int(mes[5:7])
        desde, hasta = limites_mes_negocio(anio, numero)
        embudo = self._lector.embudo(desde, hasta)
        return DashboardDTO(
            mes=f"{anio:04d}-{numero:02d}",
            embudo=EmbudoDTO(
                asignadas=embudo.asignadas,
                contactadas=embudo.contactadas,
                ofrecidas=embudo.ofrecidas,
                aceptadas=embudo.aceptadas,
                renovaron=embudo.renovaron,
            ),
            por_campania=[_resultado(fila) for fila in self._lector.por_campania(desde, hasta)],
            estado_modelo=self._estado_modelo(hoy),
        )

    def _estado_modelo(self, hoy: date) -> EstadoModeloDTO | None:
        modelo = self._lector.modelo_vigente()
        if modelo is None:
            return None
        corte = _corte_vigente(modelo)
        etiquetados = etiquetar_ciclos(self._lector.ciclos(), hoy)
        nuevos = sum(1 for ciclo in etiquetados if es_ciclo_nuevo(ciclo, corte))
        return EstadoModeloDTO(
            version=_version_publica(modelo.version),
            fecha_entrenamiento=modelo.fecha_entrenamiento,
            ciclos_entrenamiento=modelo.ciclos_entrenamiento,
            proxima_fecha_reentrenamiento=self._lector.proxima_fecha_reentrenamiento(),
            ciclos_nuevos_evaluables=nuevos,
        )
