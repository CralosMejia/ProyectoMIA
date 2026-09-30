"""Localizador de los libros historicos en la carpeta montada (``HISTORICO_PATH``).

Devuelve los libros ``*Control*Gym*.xlsx`` de la carpeta (sin subcarpetas; sin distinguir
mayusculas), ignorando los temporales de Excel (``~$*``) y cualquier otro ``.xlsx`` (p. ej.
la plantilla de carga), en orden alfabetico. Una carpeta vacia o inexistente devuelve ``[]``.
No lee el contenido ni registra rutas en logs.
"""

from pathlib import Path

EXTENSION = ".xlsx"
PREFIJO_TEMPORAL = "~$"
MARCAS_LIBRO = ("CONTROL", "GYM")


class LocalizadorLibrosCarpeta:
    """Implementa ``LocalizadorLibros`` sobre una carpeta del sistema de archivos."""

    def __init__(self, carpeta: Path) -> None:
        self._carpeta = carpeta

    def rutas(self) -> list[Path]:
        if not self._carpeta.is_dir():
            return []
        return sorted(
            (
                ruta
                for ruta in self._carpeta.iterdir()
                if ruta.is_file()
                and ruta.suffix.lower() == EXTENSION
                and not ruta.name.startswith(PREFIJO_TEMPORAL)
                and _es_libro_historico(ruta.name)
            ),
            key=lambda ruta: ruta.name,
        )


def _es_libro_historico(nombre: str) -> bool:
    mayusculas = nombre.upper()
    return all(marca in mayusculas for marca in MARCAS_LIBRO)
