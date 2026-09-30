"""CU-06: listar, crear, editar, inactivar y activar campanas de retencion.

Cada caso de uso abre su unidad de trabajo, delega las reglas en ``DatosCampania.crear`` y
confirma **una** vez al final; si el dominio o el repositorio fallan no se confirma nada.
No existe borrado: una campana se inactiva (y se puede volver a activar, R-010 (a)) y las
gestiones que ya la usan la conservan.
"""

from app.application.campanias.dtos import CampaniaDTO, CampaniaEntradaDTO
from app.application.campanias.ports import CampaniaGuardada, UnidadDeTrabajoCampanias
from app.domain.campanias.campania import DatosCampania
from app.domain.common.exceptions import DomainError

MENSAJE_CAMPANIA_NO_EXISTE = "La campana no existe."


class CampaniaNoExisteError(DomainError):
    """La campana no existe o esta borrada."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_CAMPANIA_NO_EXISTE)


def a_dto(campania: CampaniaGuardada) -> CampaniaDTO:
    # ``model_validate`` comprueba tambien que los planes sean de campana (sin DIARIO).
    return CampaniaDTO.model_validate(
        {
            "id": campania.id,
            "nombre": campania.nombre,
            "descripcion": campania.descripcion,
            "activa": campania.activa,
            "niveles_riesgo": list(campania.niveles_riesgo),
            "planes": list(campania.planes),
            "prioridad": campania.prioridad,
            "es_ejemplo": campania.es_ejemplo,
        }
    )


def _datos(entrada: CampaniaEntradaDTO) -> DatosCampania:
    return DatosCampania.crear(
        nombre=entrada.nombre,
        descripcion=entrada.descripcion,
        niveles=entrada.niveles_riesgo,
        planes=entrada.planes,
        prioridad=entrada.prioridad,
    )


class ListarCampanias:
    """Todas las campanas no borradas: activas primero, luego por prioridad y nombre."""

    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self) -> list[CampaniaDTO]:
        with self._uow() as uow:
            return [a_dto(c) for c in uow.campanias.listar()]


class CrearCampania:
    """Crea una campana del personal: nace activa y no es de ejemplo."""

    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self, entrada: CampaniaEntradaDTO) -> CampaniaDTO:
        datos = _datos(entrada)
        with self._uow() as uow:
            creada = uow.campanias.crear(datos)
            uow.commit()
        return a_dto(creada)


class EditarCampania:
    """Reemplaza los datos editables; ``activa`` y ``es_ejemplo`` no cambian."""

    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self, campania_id: int, entrada: CampaniaEntradaDTO) -> CampaniaDTO:
        datos = _datos(entrada)
        with self._uow() as uow:
            editada = uow.campanias.actualizar(campania_id, datos)
            if editada is None:
                raise CampaniaNoExisteError()
            uow.commit()
        return a_dto(editada)


class InactivarCampania:
    """Deja de sugerir la campana; inactivar una ya inactiva no cambia nada (idempotente)."""

    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self, campania_id: int) -> CampaniaDTO:
        with self._uow() as uow:
            actual = uow.campanias.obtener(campania_id)
            if actual is None:
                raise CampaniaNoExisteError()
            if not actual.activa:
                return a_dto(actual)
            inactivada = uow.campanias.inactivar(campania_id)
            if inactivada is None:
                raise CampaniaNoExisteError()
            uow.commit()
        return a_dto(inactivada)


class ActivarCampania:
    """Vuelve a sugerir la campana; activar una ya activa no cambia nada (idempotente)."""

    def __init__(self, unidad_de_trabajo: UnidadDeTrabajoCampanias) -> None:
        self._uow = unidad_de_trabajo

    def ejecutar(self, campania_id: int) -> CampaniaDTO:
        with self._uow() as uow:
            actual = uow.campanias.obtener(campania_id)
            if actual is None:
                raise CampaniaNoExisteError()
            if actual.activa:
                return a_dto(actual)
            activada = uow.campanias.activar(campania_id)
            if activada is None:
                raise CampaniaNoExisteError()
            uow.commit()
        return a_dto(activada)
