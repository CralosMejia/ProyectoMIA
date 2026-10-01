"""CU-09: alertas de seguimiento y lista de gestiones pendientes por grupo (solo lectura).

"Hoy" es la fecha de negocio (Ecuador): ``hoy_en_negocio(clock.now())``. Los rangos de cada
grupo los decide el dominio (``rango_de``); el lector solo cuenta y lista gestiones
``PENDIENTE`` no borradas (decision (a) de R-011).
"""

from app.application.gestiones.dtos import AlertasDTO, FiltroGestiones, GestionResumenDTO
from app.application.gestiones.ports import GestionPendienteResumen, LectorSeguimiento
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoGestion
from app.domain.common.fechas import hoy_en_negocio
from app.domain.gestiones.alertas import GrupoAlerta, rango_de


def _resumen_a_dto(fila: GestionPendienteResumen) -> GestionResumenDTO:
    return GestionResumenDTO(
        id=fila.id,
        prediccion_id=fila.prediccion_id,
        socio_nombre=fila.socio_nombre,
        celular=fila.celular,
        plan=fila.plan,
        fecha_vencimiento=fila.fecha_vencimiento,
        fecha_seguimiento=fila.fecha_seguimiento,
        nivel_riesgo=fila.nivel_riesgo,
        campania_nombre=fila.campania_nombre,
        responsable=fila.responsable,
        estado=EstadoGestion.PENDIENTE,
    )


class ConsultarAlertas:
    """Query: contadores de gestiones pendientes vencidas, para hoy y de los proximos 7 dias."""

    def __init__(self, lector: LectorSeguimiento, clock: Clock) -> None:
        self._lector = lector
        self._clock = clock

    def ejecutar(self) -> AlertasDTO:
        conteo = self._lector.contar(hoy_en_negocio(self._clock.now()))
        return AlertasDTO(vencidas=conteo.vencidas, hoy=conteo.hoy, proximos_7_dias=conteo.proximas)


class ListarGestionesPorAlerta:
    """Query: gestiones pendientes de un grupo, ordenadas por fecha de seguimiento e id."""

    def __init__(self, lector: LectorSeguimiento, clock: Clock) -> None:
        self._lector = lector
        self._clock = clock

    def ejecutar(self, filtro: FiltroGestiones) -> list[GestionResumenDTO]:
        desde, hasta = rango_de(GrupoAlerta(filtro.value), hoy_en_negocio(self._clock.now()))
        return [_resumen_a_dto(fila) for fila in self._lector.listar(desde, hasta)]
