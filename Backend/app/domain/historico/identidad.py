"""Identidad unica del socio en el historico (notebook MVP, seccion 4.3)."""


def identidad_de(cedula_normalizada: str | None, nombre_normalizado: str) -> str:
    """``"C:<cedula>"`` si hay cedula valida; si no, respaldo por nombre ``"N:<nombre>"``."""
    if cedula_normalizada is not None:
        return f"C:{cedula_normalizada}"
    return f"N:{nombre_normalizado}"
