"""Caso de uso ConsultarGestion: detalle de una gestion (solo lectura, sin bloqueo)."""

from app.application.gestiones.crear_gestion import gestion_a_dto
from app.application.gestiones.dtos import GestionDTO
from app.application.gestiones.ports import UnidadDeTrabajoGestiones
from app.application.gestiones.registrar_resultado import GestionNoExisteError


class ConsultarGestion:
    """Query: la gestion con la instantanea de la campana y los datos originales del modelo."""

    def __init__(self, uow: UnidadDeTrabajoGestiones) -> None:
        self._uow = uow

    def ejecutar(self, gestion_id: int) -> GestionDTO:
        with self._uow() as ctx:
            detalle = ctx.gestiones.obtener(gestion_id)
        if detalle is None:
            raise GestionNoExisteError()
        return gestion_a_dto(detalle)
