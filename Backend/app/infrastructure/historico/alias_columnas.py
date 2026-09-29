"""Meses y equivalencias de columnas copiados del notebook MVP (secciones 2.4 y 3.2).

Los alias ya estan normalizados con ``normalizar_texto_encabezado``; una columna coincide si
su titulo *contiene* alguno de ellos. ``"FECHA INSCRIP"`` no es alias: una hoja con ese
titulo queda sin fecha de inicio (inicio aproximado), igual que en el notebook.
"""

from types import MappingProxyType
from typing import Final

MESES: Final = MappingProxyType(
    {
        "ENERO": 1,
        "FEBRERO": 2,
        "MARZO": 3,
        "ABRIL": 4,
        "MAYO": 5,
        "JUNIO": 6,
        "JULIO": 7,
        "AGOSTO": 8,
        "SEPTIEMBRE": 9,
        "OCTUBRE": 10,
        "NOVIEMBRE": 11,
        "DICIEMBRE": 12,
    }
)

# campo estandar -> nombres posibles en el Excel (ya normalizados), en el orden del notebook.
ALIAS_COLUMNAS: Final = MappingProxyType(
    {
        "status": ("STATUS",),
        "nombre": ("NOMBRES Y APELLIDOS", "NOMBRES Y APELLIDOS DEL SOCIO"),
        "cedula": ("CEDULA",),
        "celular": ("CELULAR",),
        "correo": ("CORREO",),
        "plan": ("TIPO DE PLAN",),
        "fecha_inicio": ("FECHA INSCRIPCION", "FECHA INICIO"),
        "fecha_fin": ("FECHA FIN PLAN", "FECHA FIN"),
        "forma_pago": ("TIPO PAGO",),
        "monto_cobrado": ("MONTO A COBRAR", "MONTO COBRAR"),
    }
)
