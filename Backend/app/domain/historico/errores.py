"""Errores de lectura de los libros historicos.

Los mensajes solo nombran el libro y la hoja; nunca incluyen datos de celdas (RN-03.5).
"""

from app.domain.common.exceptions import DomainError


class LibroSinAnioError(DomainError):
    """El nombre del libro no contiene el anio de sus hojas mensuales."""

    def __init__(self, libro: str) -> None:
        self.libro = libro
        super().__init__(f"No se encontro el anio en el nombre del libro '{libro}'.")


class HojaSinEncabezadoError(DomainError):
    """Una hoja mensual no tiene en sus primeras filas un encabezado con CEDULA y NOMBRE."""

    def __init__(self, libro: str, hoja: str) -> None:
        self.libro = libro
        self.hoja = hoja
        super().__init__(f"No se encontro encabezado en la hoja '{hoja}' del libro '{libro}'.")
