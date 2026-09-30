"""Dobles en memoria de los puertos de cargas para probar los casos de uso sin BD.

Un ``Almacen`` compartido por todas las unidades de trabajo de una prueba conserva lo
escrito (socios, cedulas, membresias, cargas) para que una segunda confirmacion lo vea.
``eventos`` registra el orden de ``bloquear``, consultas, escrituras y ``commit``.
Datos 100 % ficticios.
"""

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.application.cargas.ports import (
    ClaveMembresia,
    ContextoCargas,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
)
from app.application.modelo.ports import EstadoSistema
from app.domain.cargas.fila import PlantillaLeida
from app.domain.common.enums import EstadoMigracion

INSTANTE = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)


class RelojFijo:
    def now(self) -> datetime:
        return INSTANTE


@dataclass
class SocioGuardado:
    cedula: str | None
    nombre_normalizado: str
    celular: str | None = None
    correo: str | None = None


@dataclass
class Almacen:
    """Estado compartido por las unidades de trabajo de una prueba."""

    socios: dict[int, SocioGuardado] = field(default_factory=dict)
    membresias: list[NuevaMembresia] = field(default_factory=list)
    cargas: list[NuevaCarga] = field(default_factory=list)
    estado: EstadoMigracion = EstadoMigracion.COMPLETADA
    eventos: list[str] = field(default_factory=list)
    commits: int = 0
    fallar_en_membresias: bool = False

    def agregar_socio(self, socio: SocioGuardado) -> int:
        socio_id = len(self.socios) + 1
        self.socios[socio_id] = socio
        return socio_id

    @property
    def escrituras(self) -> list[str]:
        return [e for e in self.eventos if e.startswith("escritura.")]


class LectorEnMemoria:
    def __init__(self, plantilla: PlantillaLeida) -> None:
        self.plantilla = plantilla

    def leer(self, contenido: bytes) -> PlantillaLeida:
        return self.plantilla


class ConsultasEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def socios_por_cedulas(self, cedulas: Iterable[str]) -> dict[str, int]:
        self._a.eventos.append("consultas.socios_por_cedulas")
        pedidas = set(cedulas)
        return {s.cedula: i for i, s in self._a.socios.items() if s.cedula in pedidas}

    def socios_sin_cedula_por_nombres(self, nombres: Iterable[str]) -> dict[str, list[int]]:
        self._a.eventos.append("consultas.socios_sin_cedula_por_nombres")
        buscados = set(nombres)
        resultado: dict[str, list[int]] = {}
        for socio_id, socio in sorted(self._a.socios.items()):
            if socio.cedula is None and socio.nombre_normalizado in buscados:
                resultado.setdefault(socio.nombre_normalizado, []).append(socio_id)
        return resultado

    def claves_existentes(self, socio_ids: Iterable[int]) -> set[ClaveMembresia]:
        self._a.eventos.append("consultas.claves_existentes")
        ids = set(socio_ids)
        return {
            ClaveMembresia(m.socio_id, m.fecha_inicio, m.fecha_vencimiento, m.plan)
            for m in self._a.membresias
            if m.socio_id in ids and m.fecha_inicio is not None and m.fecha_vencimiento is not None
        }


class EscrituraEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def crear_socios(self, socios: Sequence[NuevoSocio]) -> list[int]:
        self._a.eventos.append("escritura.crear_socios")
        return [
            self._a.agregar_socio(
                SocioGuardado(s.cedula, s.nombre_normalizado, s.celular, s.correo)
            )
            for s in socios
        ]

    def asignar_cedula(
        self, socio_id: int, cedula: str, celular: str | None, correo: str | None
    ) -> None:
        self._a.eventos.append("escritura.asignar_cedula")
        socio = self._a.socios[socio_id]
        socio.cedula = cedula
        socio.celular = socio.celular or celular
        socio.correo = socio.correo or correo

    def insertar_membresias(self, membresias: Sequence[NuevaMembresia]) -> int:
        self._a.eventos.append("escritura.insertar_membresias")
        if self._a.fallar_en_membresias:
            raise RuntimeError("fallo simulado de escritura")
        self._a.membresias.extend(membresias)
        return len(membresias)

    def crear_carga(self, carga: NuevaCarga) -> int:
        self._a.eventos.append("escritura.crear_carga")
        self._a.cargas.append(carga)
        return len(self._a.cargas)


class EstadoEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def obtener(self) -> EstadoSistema:
        return EstadoSistema(self._a.estado, None)

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        raise AssertionError("las cargas no cambian el estado de la migracion")

    def fijar_proxima_fecha(self, fecha: date) -> None:
        raise AssertionError("las cargas no cambian la fecha de reentrenamiento (RN-01.11)")


class ContextoEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen
        self._consultas = ConsultasEnMemoria(almacen)
        self._escritura = EscrituraEnMemoria(almacen)
        self._estado = EstadoEnMemoria(almacen)

    @property
    def consultas(self) -> ConsultasEnMemoria:
        return self._consultas

    @property
    def escritura(self) -> EscrituraEnMemoria:
        return self._escritura

    @property
    def estado(self) -> EstadoEnMemoria:
        return self._estado

    def bloquear(self) -> None:
        self._a.eventos.append("bloquear")

    def commit(self) -> None:
        self._a.eventos.append("commit")
        self._a.commits += 1


class UnidadDeTrabajoEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    @contextmanager
    def __call__(self) -> Iterator[ContextoCargas]:
        yield ContextoEnMemoria(self._a)
