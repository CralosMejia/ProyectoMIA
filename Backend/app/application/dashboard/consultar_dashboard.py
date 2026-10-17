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
5. Indicadores del piloto (M04, R-018): top 25 de la ultima lista generada en el mes,
   verificado a T+30 con el corte de los datos ``corte_de_datos(hoy, corte del vigente, dia de
   la ultima carga por plantilla)`` (sin vigente -> corte nulo y todo pendiente). Sin lista en
   el mes -> ``SIN_DATOS``. Los ciclos se leen **una sola vez** por consulta y se comparten
   con el punto 4.
"""

from collections.abc import Callable, Hashable
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from app.application.dashboard.dtos import (
    DashboardDTO,
    EmbudoDTO,
    EstadoModeloDTO,
    IndicadorDiasDTO,
    IndicadoresPilotoDTO,
    IndicadorMontoDTO,
    IndicadorProporcionDTO,
    ListaPilotoDTO,
    ResultadoCampaniaDTO,
)
from app.application.dashboard.ports import (
    FilaCampania,
    LectorDashboard,
    ListaPiloto,
    ModeloDashboard,
    MontoMembresia,
)
from app.domain.common.clock import Clock
from app.domain.common.fechas import (
    ZONA_NEGOCIO,
    hoy_en_negocio,
    limites_mes_negocio,
    sumar_meses,
)
from app.domain.modelo.piloto import (
    TOP_PILOTO,
    CasoPiloto,
    EstadoIndicador,
    IndicadoresPiloto,
    Verificacion,
    calcular_indicadores,
    verificar_renovacion,
)
from app.domain.modelo.reentrenamiento import corte_de_datos, es_ciclo_nuevo, etiquetar_ciclos
from app.domain.modelo.variables import CicloModelo

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


class _CiclosUnaVez:
    """Lee los ciclos la primera vez que se piden y los reutiliza el resto de la consulta."""

    def __init__(self, leer: Callable[[], list[CicloModelo]]) -> None:
        self._leer = leer
        self._ciclos: list[CicloModelo] | None = None

    def __call__(self) -> list[CicloModelo]:
        if self._ciclos is None:
            self._ciclos = self._leer()
        return self._ciclos


def _piloto_dto(
    indicadores: IndicadoresPiloto, lista: ListaPiloto | None, corte: date | None
) -> IndicadoresPilotoDTO:
    return IndicadoresPilotoDTO(
        estado=(EstadoIndicador.SIN_DATOS if lista is None else indicadores.precision_top25.estado),
        lista=(
            None
            if lista is None
            else ListaPilotoDTO(
                id=lista.id, nombre=lista.nombre, fecha_generacion=lista.fecha_generacion
            )
        ),
        corte_verificacion=corte,
        n_top=indicadores.n_top,
        sin_dato=indicadores.sin_dato,
        precision_top25=IndicadorProporcionDTO.model_validate(
            indicadores.precision_top25, from_attributes=True
        ),
        contactados_antes_vencimiento=IndicadorProporcionDTO.model_validate(
            indicadores.contactados_antes_vencimiento, from_attributes=True
        ),
        dias_anticipacion=IndicadorDiasDTO.model_validate(
            indicadores.dias_anticipacion, from_attributes=True
        ),
        tasa_renovacion_contactados=IndicadorProporcionDTO.model_validate(
            indicadores.tasa_renovacion_contactados, from_attributes=True
        ),
        monto_retenido=IndicadorMontoDTO.model_validate(
            indicadores.monto_retenido, from_attributes=True
        ),
    )


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
        modelo = self._lector.modelo_vigente()
        ciclos = _CiclosUnaVez(self._lector.ciclos)
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
            estado_modelo=self._estado_modelo(hoy, modelo, ciclos),
            piloto=self._piloto(date(anio, numero, 1), hoy, modelo, ciclos),
        )

    def _estado_modelo(
        self, hoy: date, modelo: ModeloDashboard | None, ciclos: _CiclosUnaVez
    ) -> EstadoModeloDTO | None:
        if modelo is None:
            return None
        corte = _corte_vigente(modelo)
        etiquetados = etiquetar_ciclos(ciclos(), hoy)
        nuevos = sum(1 for ciclo in etiquetados if es_ciclo_nuevo(ciclo, corte))
        return EstadoModeloDTO(
            version=_version_publica(modelo.version),
            fecha_entrenamiento=modelo.fecha_entrenamiento,
            ciclos_entrenamiento=modelo.ciclos_entrenamiento,
            proxima_fecha_reentrenamiento=self._lector.proxima_fecha_reentrenamiento(),
            ciclos_nuevos_evaluables=nuevos,
        )

    def _piloto(
        self, inicio_mes: date, hoy: date, modelo: ModeloDashboard | None, ciclos: _CiclosUnaVez
    ) -> IndicadoresPilotoDTO:
        fin_mes = sumar_meses(inicio_mes, 1) - timedelta(days=1)
        lista = self._lector.lista_piloto(inicio_mes, fin_mes)
        if lista is None:
            return _piloto_dto(calcular_indicadores([], {}, {}), None, None)

        corte: date | None = None
        if modelo is not None:
            ultima = self._lector.ultima_carga_plantilla()
            corte = corte_de_datos(
                hoy, _corte_vigente(modelo), None if ultima is None else hoy_en_negocio(ultima)
            )

        filas = [f for f in lista.filas if f.prioridad <= TOP_PILOTO]
        todos = ciclos() if filas else []
        por_ref = {c.ref: c for c in todos}
        casos: list[CasoPiloto] = []
        resultados: dict[Hashable, Verificacion] = {}
        for fila in filas:
            ciclo = por_ref.get(fila.membresia_id)
            casos.append(
                CasoPiloto(
                    ref=fila.membresia_id,
                    vencimiento=None if ciclo is None else ciclo.fecha_vencimiento,
                    contactado=fila.contactado is True,
                    fecha_contacto=fila.fecha_contacto,
                )
            )
            resultados[fila.membresia_id] = verificar_renovacion(fila.membresia_id, todos, corte)

        renovaciones = [r.renovacion for r in resultados.values() if isinstance(r.renovacion, int)]
        montos: dict[Hashable, MontoMembresia] = (
            dict(self._lector.montos(renovaciones).items()) if renovaciones else {}
        )
        return _piloto_dto(calcular_indicadores(casos, resultados, montos), lista, corte)
