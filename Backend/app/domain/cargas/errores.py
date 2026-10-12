"""Errores de la plantilla de carga que invalidan el archivo completo (CU-01).

Los mensajes nunca incluyen valores de celdas (nombres, cedulas, celulares, correos).
"""

from enum import StrEnum, unique

from app.domain.common.exceptions import DomainError


@unique
class MotivoPlantillaInvalida(StrEnum):
    DANADO = "DANADO"
    SIN_REGISTROS = "SIN_REGISTROS"
    TITULOS = "TITULOS"
    FORMATO_ANTIGUO = "FORMATO_ANTIGUO"
    DEMASIADAS_FILAS = "DEMASIADAS_FILAS"
    DEMASIADO_GRANDE = "DEMASIADO_GRANDE"


MENSAJES: dict[MotivoPlantillaInvalida, str] = {
    MotivoPlantillaInvalida.DANADO: "El archivo está dañado o no es un .xlsx válido.",
    MotivoPlantillaInvalida.SIN_REGISTROS: "El archivo no tiene la hoja Registros.",
    MotivoPlantillaInvalida.TITULOS: (
        "Los títulos de la hoja Registros no coinciden con la plantilla oficial."
    ),
    MotivoPlantillaInvalida.FORMATO_ANTIGUO: (
        "El archivo tiene el formato antiguo de hojas mensuales; use la plantilla oficial de carga."
    ),
    MotivoPlantillaInvalida.DEMASIADAS_FILAS: (
        "El archivo tiene más de 500 filas con datos; divídalo en varios archivos."
    ),
    MotivoPlantillaInvalida.DEMASIADO_GRANDE: (
        "El contenido del archivo es demasiado grande para una plantilla de carga; "
        "use la plantilla oficial."
    ),
}


class PlantillaInvalidaError(DomainError):
    """El archivo no se puede procesar como plantilla oficial; se rechaza completo."""

    def __init__(self, motivo: MotivoPlantillaInvalida) -> None:
        self.motivo = motivo
        super().__init__(MENSAJES[motivo])
