"""Dobles en memoria de los puertos de campanias (sin base de datos).

Datos 100 % ficticios.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from app.application.campanias.ports import CampaniaGuardada, ContextoCampanias
from app.domain.campanias.campania import DatosCampania, clave_orden, es_compatible
from app.domain.common.enums import NivelRiesgo, Plan


def guardada(campania_id: int, **cambios: object) -> CampaniaGuardada:
    base = CampaniaGuardada(
        id=campania_id,
        nombre=f"Campana {campania_id}",
        descripcion=None,
        activa=True,
        niveles_riesgo=(NivelRiesgo.ALTO,),
        planes=(Plan.MENSUAL,),
        prioridad=1,
        es_ejemplo=False,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # cambios de prueba


@dataclass
class RepositorioCampaniasEnMemoria:
    campanias: dict[int, CampaniaGuardada] = field(default_factory=dict)
    creadas: list[DatosCampania] = field(default_factory=list)
    actualizadas: list[tuple[int, DatosCampania]] = field(default_factory=list)
    inactivadas: list[int] = field(default_factory=list)
    consultas_compatibles: list[tuple[NivelRiesgo, Plan]] = field(default_factory=list)

    def listar(self) -> list[CampaniaGuardada]:
        return sorted(
            self.campanias.values(),
            key=lambda c: (not c.activa, clave_orden(c.prioridad, c.nombre, c.id)),
        )

    def obtener(self, campania_id: int) -> CampaniaGuardada | None:
        return self.campanias.get(campania_id)

    def crear(self, datos: DatosCampania) -> CampaniaGuardada:
        self.creadas.append(datos)
        nueva = CampaniaGuardada(
            id=max(self.campanias, default=0) + 1,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activa=True,
            niveles_riesgo=datos.niveles_riesgo,
            planes=datos.planes,
            prioridad=datos.prioridad,
            es_ejemplo=False,
        )
        self.campanias[nueva.id] = nueva
        return nueva

    def actualizar(self, campania_id: int, datos: DatosCampania) -> CampaniaGuardada | None:
        actual = self.campanias.get(campania_id)
        if actual is None:
            return None
        self.actualizadas.append((campania_id, datos))
        nueva = replace(
            actual,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            niveles_riesgo=datos.niveles_riesgo,
            planes=datos.planes,
            prioridad=datos.prioridad,
        )
        self.campanias[campania_id] = nueva
        return nueva

    def inactivar(self, campania_id: int) -> CampaniaGuardada | None:
        actual = self.campanias.get(campania_id)
        if actual is None:
            return None
        self.inactivadas.append(campania_id)
        nueva = replace(actual, activa=False)
        self.campanias[campania_id] = nueva
        return nueva

    def compatibles(self, nivel: NivelRiesgo, plan: Plan) -> list[CampaniaGuardada]:
        self.consultas_compatibles.append((nivel, plan))
        return [
            c
            for c in self.listar()
            if es_compatible(c.activa, c.niveles_riesgo, c.planes, nivel, plan)
        ]


@dataclass
class PerfilesEnMemoria:
    perfiles: dict[int, tuple[NivelRiesgo, Plan]] = field(default_factory=dict)

    def obtener(self, prediccion_id: int) -> tuple[NivelRiesgo, Plan] | None:
        return self.perfiles.get(prediccion_id)


@dataclass
class ContextoFalso:
    campanias: RepositorioCampaniasEnMemoria = field(default_factory=RepositorioCampaniasEnMemoria)
    perfiles: PerfilesEnMemoria = field(default_factory=PerfilesEnMemoria)
    commits: int = 0

    def commit(self) -> None:
        self.commits += 1


@dataclass
class UnidadFalsa:
    contexto: ContextoFalso = field(default_factory=ContextoFalso)
    aperturas: int = 0

    @contextmanager
    def __call__(self) -> Iterator[ContextoCampanias]:
        self.aperturas += 1
        yield self.contexto
