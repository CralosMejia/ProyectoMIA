"""Plan de carga: enlace de cada fila con su socio y deteccion de duplicados (CU-01).

Reglas (RN-01.8, RN-01.9, D-03, D-04; decisiones (b) y (c) de R-007):

- Enlace, por fila y en orden de fila: 1) la cedula ya existe -> ese socio; 2) si no, un unico
  socio historico **sin cedula** con el mismo ``nombre_normalizado`` -> se enlaza y se le
  asigna la cedula; 3) con dos o mas homonimos -> socio nuevo y un aviso sin el nombre. Todas
  las filas con la misma cedula van al mismo socio. Un candidato por nombre ya enlazado con
  una cedula del archivo no esta disponible para otra cedula distinta.
- Duplicado: identidad resuelta + fecha de inicio + fecha de vencimiento + plan, contra las
  membresias existentes (``claves_existentes``) y contra las filas anteriores del archivo.

Funcion pura: el resultado solo depende de los argumentos y es el mismo para cualquier orden
de entrada (se procesa por numero de fila).
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from app.domain.cargas.validacion import FilaValida
from app.domain.common.enums import Plan

AVISO_HOMONIMOS = (
    "Fila {fila}: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."
)


@dataclass(frozen=True, slots=True)
class ClaveMembresia:
    """Clave de duplicado de una membresia existente (RN-01.8 / D-04)."""

    socio_id: int
    fecha_inicio: date
    fecha_vencimiento: date
    plan: Plan


@dataclass(frozen=True, slots=True)
class SocioNuevo:
    """Socio a crear, con los datos de la primera fila de su cedula."""

    cedula: str = field(repr=False)
    nombre: str = field(repr=False)
    nombre_normalizado: str = field(repr=False)
    celular: str | None = field(repr=False)
    correo: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class AsignacionCedula:
    """Cedula (y celular/correo si estaban vacios) para un socio historico enlazado por nombre."""

    socio_id: int
    cedula: str = field(repr=False)
    celular: str | None = field(repr=False)
    correo: str | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class FilaPlanificada:
    """Destino de una fila: ``socio_id`` existente o ``socio_nuevo`` (indice en el plan)."""

    fila: FilaValida
    socio_id: int | None
    socio_nuevo: int | None
    duplicada: bool
    enlazado_por_nombre: bool


@dataclass(frozen=True, slots=True)
class PlanCarga:
    """Resultado de ``planificar``: filas en orden, socios a crear, cedulas a asignar y avisos."""

    filas: tuple[FilaPlanificada, ...]
    socios_nuevos: tuple[SocioNuevo, ...]
    cedulas_asignadas: tuple[AsignacionCedula, ...]
    avisos: tuple[str, ...]

    @property
    def filas_nuevas(self) -> tuple[FilaPlanificada, ...]:
        return tuple(destino for destino in self.filas if not destino.duplicada)

    @property
    def filas_duplicadas(self) -> int:
        return sum(1 for destino in self.filas if destino.duplicada)

    @property
    def socios_enlazados(self) -> int:
        """Socios existentes distintos con al menos una fila **nueva** asociada."""
        return len({d.socio_id for d in self.filas_nuevas if d.socio_id is not None})


# Identidad resuelta de una fila: ("E", socio_id) existente o ("N", indice) nuevo.
type _Identidad = tuple[str, int]


def planificar(
    filas_validas: Sequence[FilaValida],
    socios_por_cedula: Mapping[str, int],
    candidatos_por_nombre: Mapping[str, Sequence[int]],
    claves_existentes: Collection[ClaveMembresia],
) -> PlanCarga:
    """Resuelve el socio de cada fila valida y marca las duplicadas (ver docstring del modulo)."""
    por_cedula: dict[str, tuple[_Identidad, bool]] = {}
    candidatos_tomados: set[int] = set()
    claves_vistas: set[tuple[_Identidad, date, date, Plan]] = set()
    socios_nuevos: list[SocioNuevo] = []
    asignaciones: list[AsignacionCedula] = []
    avisos: list[str] = []
    destinos: list[FilaPlanificada] = []

    for fila in sorted(filas_validas, key=lambda f: f.fila):
        if fila.documento not in por_cedula:
            por_cedula[fila.documento] = _resolver(
                fila,
                socios_por_cedula,
                candidatos_por_nombre,
                candidatos_tomados,
                socios_nuevos,
                asignaciones,
                avisos,
            )
        identidad, por_nombre = por_cedula[fila.documento]
        tipo, numero = identidad

        clave = (identidad, fila.fecha_inicio, fila.fecha_vencimiento, fila.plan)
        duplicada = clave in claves_vistas or (
            tipo == "E"
            and ClaveMembresia(numero, fila.fecha_inicio, fila.fecha_vencimiento, fila.plan)
            in claves_existentes
        )
        claves_vistas.add(clave)
        destinos.append(
            FilaPlanificada(
                fila=fila,
                socio_id=numero if tipo == "E" else None,
                socio_nuevo=numero if tipo == "N" else None,
                duplicada=duplicada,
                enlazado_por_nombre=por_nombre,
            )
        )

    return PlanCarga(
        filas=tuple(destinos),
        socios_nuevos=tuple(socios_nuevos),
        cedulas_asignadas=tuple(asignaciones),
        avisos=tuple(avisos),
    )


def _resolver(
    fila: FilaValida,
    socios_por_cedula: Mapping[str, int],
    candidatos_por_nombre: Mapping[str, Sequence[int]],
    candidatos_tomados: set[int],
    socios_nuevos: list[SocioNuevo],
    asignaciones: list[AsignacionCedula],
    avisos: list[str],
) -> tuple[_Identidad, bool]:
    """Identidad de la primera fila de una cedula y si se enlazo por nombre."""
    existente = socios_por_cedula.get(fila.documento)
    if existente is not None:
        return ("E", existente), False

    candidatos = candidatos_por_nombre.get(fila.nombre_normalizado, ())
    if len(candidatos) == 1 and candidatos[0] not in candidatos_tomados:
        socio_id = candidatos[0]
        candidatos_tomados.add(socio_id)
        asignaciones.append(AsignacionCedula(socio_id, fila.documento, fila.celular, fila.correo))
        return ("E", socio_id), True

    if len(candidatos) > 1:
        avisos.append(AVISO_HOMONIMOS.format(fila=fila.fila))
    socios_nuevos.append(
        SocioNuevo(
            cedula=fila.documento,
            nombre=fila.nombre,
            nombre_normalizado=fila.nombre_normalizado,
            celular=fila.celular,
            correo=fila.correo,
        )
    )
    return ("N", len(socios_nuevos) - 1), False
