"""Fila cruda de la hoja ``Registros`` de la plantilla oficial de carga (CU-01).

El lector entrega los valores de celda de las columnas A..N tal cual (sin convertir ni
validar); la validacion por fila vive en el dominio (``validacion``). Las columnas O y P
(formulas de apoyo) se ignoran siempre.

Ningun ``repr`` expone datos personales: nombre, cedula, celular y correo se excluyen.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

PRIMERA_FILA_DATOS = 2
"""La fila 1 contiene los titulos; los datos empiezan en la fila 2 (numeracion de Excel)."""

COLUMNAS: tuple[tuple[str, str], ...] = (
    ("A", "estado_registro"),
    ("B", "nombre"),
    ("C", "cedula"),
    ("D", "celular"),
    ("E", "correo"),
    ("F", "plan"),
    ("G", "fecha_inicio"),
    ("H", "fecha_vencimiento"),
    ("I", "forma_pago"),
    ("J", "numero_transaccion"),
    ("K", "monto_facturado"),
    ("L", "monto_cobrado"),
    ("M", "asistencias"),
    ("N", "observaciones"),
)
"""Letra de columna y atributo de ``FilaPlantilla``, en orden A..N."""


@dataclass(frozen=True, slots=True)
class FilaPlantilla:
    """Valores crudos de las columnas A..N de una fila; ``fila`` es el numero real en Excel."""

    fila: int
    estado_registro: object = None
    nombre: object = field(default=None, repr=False)
    cedula: object = field(default=None, repr=False)
    celular: object = field(default=None, repr=False)
    correo: object = field(default=None, repr=False)
    plan: object = None
    fecha_inicio: object = None
    fecha_vencimiento: object = None
    forma_pago: object = None
    numero_transaccion: object = None
    monto_facturado: object = None
    monto_cobrado: object = None
    asistencias: object = None
    observaciones: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.fila < PRIMERA_FILA_DATOS:
            raise ValueError("fila debe ser 2 o mayor (la fila 1 son los titulos)")

    @classmethod
    def desde_valores(cls, fila: int, valores: Sequence[object]) -> "FilaPlantilla":
        """Crea la fila desde los valores A..N en orden; faltantes -> ``None``, extra -> error."""
        if len(valores) > len(COLUMNAS):
            raise ValueError("una fila de la plantilla tiene como maximo 14 columnas (A..N)")
        campos = {nombre: valor for (_, nombre), valor in zip(COLUMNAS, valores, strict=False)}
        return cls(fila, **campos)

    def valor(self, columna: str) -> object:
        """Valor crudo de la columna ``columna`` (letra A..N)."""
        for letra, nombre in COLUMNAS:
            if letra == columna:
                return getattr(self, nombre)
        raise ValueError("columna fuera de A..N")


@dataclass(frozen=True, slots=True)
class PlantillaLeida:
    """Filas con algun valor en A..N de la hoja ``Registros``, en orden de fila."""

    filas: tuple[FilaPlantilla, ...]
