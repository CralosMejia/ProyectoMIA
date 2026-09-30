"""Repositorio SQLAlchemy de campanas y perfil de una prediccion (CU-06, CU-07).

Escribe dentro de la transaccion de la ``Session`` recibida (unit of work): nunca hace
``commit`` ni ``rollback``. ``created_at``/``updated_at`` salen del ``Clock``. Toda lectura
y escritura ignora las campanas con ``deleted_at``; no hay borrado (una campana se
inactiva). Escrituras con el ORM; lecturas con ``select`` parametrizado (el filtro por nivel
y plan usa ``:valor = ANY(columna)`` con parametros enlazados).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.campanias.ports import CampaniaGuardada
from app.domain.campanias.campania import DatosCampania
from app.domain.common.clock import Clock
from app.domain.common.enums import NivelRiesgo, Plan
from app.infrastructure.persistence.models.historial import Membresia
from app.infrastructure.persistence.models.retencion import Campania, Prediccion

_ORDEN_SUGERENCIAS = (Campania.prioridad, func.lower(Campania.nombre), Campania.id)


def _guardada(fila: Campania) -> CampaniaGuardada:
    return CampaniaGuardada(
        id=fila.id,
        nombre=fila.nombre,
        descripcion=fila.descripcion,
        activa=fila.activa,
        niveles_riesgo=tuple(NivelRiesgo(n) for n in fila.niveles_riesgo),
        planes=tuple(Plan(p) for p in fila.planes),
        prioridad=fila.prioridad,
        es_ejemplo=fila.es_ejemplo,
    )


class SqlAlchemyCampaniaRepository:
    """Implementa ``CampaniaRepository``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def _vigente(self, campania_id: int) -> Campania | None:
        return self._session.scalars(
            select(Campania).where(Campania.id == campania_id, Campania.deleted_at.is_(None))
        ).one_or_none()

    def listar(self) -> list[CampaniaGuardada]:
        filas = self._session.scalars(
            select(Campania)
            .where(Campania.deleted_at.is_(None))
            .order_by(Campania.activa.desc(), *_ORDEN_SUGERENCIAS)
        )
        return [_guardada(f) for f in filas]

    def obtener(self, campania_id: int) -> CampaniaGuardada | None:
        fila = self._vigente(campania_id)
        return None if fila is None else _guardada(fila)

    def crear(self, datos: DatosCampania) -> CampaniaGuardada:
        ahora = self._clock.now()
        fila = Campania(
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activa=True,
            niveles_riesgo=[n.value for n in datos.niveles_riesgo],
            planes=[p.value for p in datos.planes],
            prioridad=datos.prioridad,
            es_ejemplo=False,
            created_at=ahora,
            updated_at=ahora,
        )
        self._session.add(fila)
        self._session.flush()
        return _guardada(fila)

    def actualizar(self, campania_id: int, datos: DatosCampania) -> CampaniaGuardada | None:
        fila = self._vigente(campania_id)
        if fila is None:
            return None
        fila.nombre = datos.nombre
        fila.descripcion = datos.descripcion
        fila.niveles_riesgo = [n.value for n in datos.niveles_riesgo]
        fila.planes = [p.value for p in datos.planes]
        fila.prioridad = datos.prioridad
        fila.updated_at = self._clock.now()
        self._session.flush()
        return _guardada(fila)

    def inactivar(self, campania_id: int) -> CampaniaGuardada | None:
        fila = self._vigente(campania_id)
        if fila is None:
            return None
        if fila.activa:
            fila.activa = False
            fila.updated_at = self._clock.now()
            self._session.flush()
        return _guardada(fila)

    def compatibles(self, nivel: NivelRiesgo, plan: Plan) -> list[CampaniaGuardada]:
        filas = self._session.scalars(
            select(Campania)
            .where(
                Campania.activa.is_(True),
                Campania.deleted_at.is_(None),
                Campania.niveles_riesgo.any_() == nivel.value,
                Campania.planes.any_() == plan.value,
            )
            .order_by(*_ORDEN_SUGERENCIAS)
        )
        return [_guardada(f) for f in filas]


class SqlAlchemyPerfilPrediccion:
    """Implementa ``PerfilPrediccion``: nivel de la prediccion y plan de su membresia.

    Sin filtro de ``deleted_at`` de la membresia: la prediccion es una instantanea (RT-07).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener(self, prediccion_id: int) -> tuple[NivelRiesgo, Plan] | None:
        fila = self._session.execute(
            select(Prediccion.nivel_riesgo, Membresia.plan)
            .join(Membresia, Membresia.id == Prediccion.membresia_id)
            .where(Prediccion.id == prediccion_id)
        ).one_or_none()
        if fila is None:
            return None
        return NivelRiesgo(fila.nivel_riesgo), Plan(fila.plan)
