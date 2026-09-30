"""Dobles en memoria de los puertos de gestiones (sin base de datos).

Datos 100 % sinteticos: ningun nombre, celular ni cedula real.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.campanias.ports import CampaniaGuardada
from app.application.gestiones.ports import (
    DatosPrediccionGestion,
    GestionDetalle,
    NuevaGestion,
    ResultadoGestion,
)
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
VENCIMIENTO = date(2026, 10, 5)


class RelojFijo:
    def __init__(self, instante: datetime = INSTANTE) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


def campania(
    campania_id: int,
    nombre: str,
    *,
    activa: bool = True,
    niveles_riesgo: tuple[NivelRiesgo, ...] = (NivelRiesgo.ALTO, NivelRiesgo.MEDIO),
    planes: tuple[Plan, ...] = (Plan.MENSUAL, Plan.TRIMESTRAL),
) -> CampaniaGuardada:
    return CampaniaGuardada(
        id=campania_id,
        nombre=nombre,
        descripcion=None,
        activa=activa,
        niveles_riesgo=niveles_riesgo,
        planes=planes,
        prioridad=1,
        es_ejemplo=False,
    )


def prediccion(
    prediccion_id: int = 15,
    *,
    membresia_id: int = 70,
    vencimiento: date = VENCIMIENTO,
    nivel: NivelRiesgo = NivelRiesgo.ALTO,
    plan: Plan = Plan.MENSUAL,
) -> DatosPrediccionGestion:
    return DatosPrediccionGestion(
        prediccion_id=prediccion_id,
        membresia_id=membresia_id,
        fecha_vencimiento=vencimiento,
        nivel_riesgo=nivel,
        plan=plan,
        score=Decimal("0.8123"),
        modelo_version=3,
        socio_nombre="Socio Ficticio Uno",
    )


class CampaniasEnMemoria:
    def __init__(self, campanias: list[CampaniaGuardada] | None = None) -> None:
        self._por_id = {c.id: c for c in campanias or []}

    def obtener(self, campania_id: int) -> CampaniaGuardada | None:
        return self._por_id.get(campania_id)


@dataclass
class GestionesEnMemoria:
    reloj: RelojFijo
    predicciones: dict[int, DatosPrediccionGestion] = field(default_factory=dict)
    filas: dict[int, GestionDetalle] = field(default_factory=dict)
    creadas: list[NuevaGestion] = field(default_factory=list)
    resultados: list[tuple[int, ResultadoGestion]] = field(default_factory=list)
    bloqueos: list[int] = field(default_factory=list)
    lecturas: list[int] = field(default_factory=list)

    def datos_prediccion(self, prediccion_id: int) -> DatosPrediccionGestion | None:
        return self.predicciones.get(prediccion_id)

    def existe_para_membresia(self, membresia_id: int) -> bool:
        return any(g.membresia_id == membresia_id for g in self.filas.values())

    def crear(self, nueva: NuevaGestion) -> int:
        self.creadas.append(nueva)
        datos = self.predicciones[nueva.prediccion_id]
        gestion_id = max(self.filas, default=0) + 1
        self.filas[gestion_id] = GestionDetalle(
            id=gestion_id,
            prediccion_id=nueva.prediccion_id,
            membresia_id=nueva.membresia_id,
            socio_nombre=datos.socio_nombre,
            plan=datos.plan,
            fecha_vencimiento=datos.fecha_vencimiento,
            modelo_version=datos.modelo_version,
            score=datos.score,
            nivel_riesgo=datos.nivel_riesgo,
            campania_id=nueva.campania_id,
            campania_nombre=nueva.campania_nombre,
            estado=nueva.estado,
            fecha_asignacion=nueva.fecha_asignacion,
            creada_en=self.reloj.now(),
            fecha_seguimiento=nueva.fecha_seguimiento,
            responsable=nueva.responsable,
            contactado=None,
            campania_ofrecida=None,
            campania_aceptada=None,
            renovo_declarado=None,
            fecha_contacto=None,
            observaciones=None,
            cerrada_en=nueva.cerrada_en,
        )
        return gestion_id

    def obtener(self, gestion_id: int) -> GestionDetalle | None:
        self.lecturas.append(gestion_id)
        return self.filas.get(gestion_id)

    def obtener_para_actualizar(self, gestion_id: int) -> GestionDetalle | None:
        self.bloqueos.append(gestion_id)
        return self.filas.get(gestion_id)

    def guardar_resultado(self, gestion_id: int, resultado: ResultadoGestion) -> None:
        self.resultados.append((gestion_id, resultado))
        self.filas[gestion_id] = replace(
            self.filas[gestion_id],
            contactado=resultado.contactado,
            campania_ofrecida=resultado.campania_ofrecida,
            campania_aceptada=resultado.campania_aceptada,
            renovo_declarado=resultado.renovo_declarado,
            fecha_contacto=resultado.fecha_contacto,
            observaciones=resultado.observaciones,
            responsable=resultado.responsable,
            fecha_seguimiento=resultado.fecha_seguimiento,
            estado=resultado.estado,
            cerrada_en=resultado.cerrada_en,
        )


class ContextoEnMemoria:
    def __init__(self, gestiones: GestionesEnMemoria, campanias: CampaniasEnMemoria) -> None:
        self.gestiones = gestiones
        self.campanias = campanias
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class UnidadDeTrabajoEnMemoria:
    """Cuenta los ``commit``; ``commits`` es el total de todas las unidades abiertas."""

    def __init__(self, contexto: ContextoEnMemoria) -> None:
        self.contexto = contexto

    @contextmanager
    def __call__(self) -> Iterator[ContextoEnMemoria]:
        yield self.contexto

    @property
    def commits(self) -> int:
        return self.contexto.commits


def entorno(
    *,
    reloj: RelojFijo | None = None,
    predicciones: list[DatosPrediccionGestion] | None = None,
    campanias: list[CampaniaGuardada] | None = None,
) -> tuple[UnidadDeTrabajoEnMemoria, GestionesEnMemoria, RelojFijo]:
    reloj = reloj or RelojFijo()
    gestiones = GestionesEnMemoria(
        reloj=reloj, predicciones={p.prediccion_id: p for p in predicciones or [prediccion()]}
    )
    uow = UnidadDeTrabajoEnMemoria(ContextoEnMemoria(gestiones, CampaniasEnMemoria(campanias)))
    return uow, gestiones, reloj


def gestion_pendiente(
    gestiones: GestionesEnMemoria,
    *,
    campania_id: int | None = 3,
    campania_nombre: str | None = "Renovacion anticipada",
    fecha_asignacion: date = date(2026, 9, 29),
    fecha_seguimiento: date = date(2026, 10, 30),
) -> int:
    """Crea en el doble una gestion pendiente de la prediccion 15 y devuelve su id."""
    return gestiones.crear(
        NuevaGestion(
            prediccion_id=15,
            membresia_id=70,
            campania_id=campania_id,
            campania_nombre=campania_nombre,
            fecha_asignacion=fecha_asignacion,
            fecha_seguimiento=fecha_seguimiento,
            responsable="Andrea",
            estado=EstadoGestion.PENDIENTE,
        )
    )
