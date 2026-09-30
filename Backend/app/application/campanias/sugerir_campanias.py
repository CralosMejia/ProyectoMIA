"""CU-07: campanas sugeridas para un socio de la lista priorizada.

El nivel es el de la prediccion (el de esa lista) y el plan el del ciclo de membresia. Solo
lee: no confirma nada. La opcion "No asignar campana" la ofrece el frontend; aqui solo se
devuelven campanas activas compatibles, por prioridad (RN-07.x).
"""

from app.application.campanias.dtos import CampaniaDTO
from app.application.campanias.gestionar_campanias import a_dto
from app.application.campanias.ports import UnidadDeTrabajoCampanias
from app.domain.common.enums import PLANES_CAMPANIA
from app.domain.common.exceptions import DomainError

MENSAJE_PREDICCION_NO_EXISTE = "La prediccion no existe."


class PrediccionNoExisteError(DomainError):
    """La prediccion pedida no existe."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_PREDICCION_NO_EXISTE)


class SugerirCampanias:
    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self, prediccion_id: int) -> list[CampaniaDTO]:
        with self._uow() as uow:
            perfil = uow.perfiles.obtener(prediccion_id)
            if perfil is None:
                raise PrediccionNoExisteError()
            nivel, plan = perfil
            if plan not in PLANES_CAMPANIA:
                # Un plan DIARIO nunca tiene campanas: ni se consulta.
                return []
            return [a_dto(c) for c in uow.campanias.compatibles(nivel, plan)]
