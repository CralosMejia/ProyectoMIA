"""Conversion de los ciclos etiquetados del historico al ciclo que usa el modelo.

``clave_socio`` es la identidad del socio y ``ref`` la referencia de origen (anio, hoja,
fila), unica por registro. ``excluido`` sale del estado del ciclo y ``no_renovo`` de su
etiqueta (``None`` si el ciclo no es evaluable).
"""

from app.domain.common.enums import EstadoCiclo
from app.domain.historico.ciclos import CicloEtiquetado
from app.domain.modelo.variables import CicloModelo


def ciclo_modelo_desde(ciclo: CicloEtiquetado) -> CicloModelo:
    """``CicloEtiquetado`` (registro + estado + etiqueta) -> ``CicloModelo``."""
    registro = ciclo.registro
    return CicloModelo(
        clave_socio=registro.identidad,
        ref=registro.referencia,
        plan=registro.plan,
        forma_pago=registro.forma_pago,
        fecha_actividad=registro.fecha_actividad,
        fecha_vencimiento=registro.fecha_vencimiento,
        duracion_dias=registro.duracion_dias,
        monto_cobrado=registro.monto_cobrado,
        inicio_aproximado=registro.inicio_aproximado,
        excluido=ciclo.estado is EstadoCiclo.EXCLUIDO,
        no_renovo=ciclo.no_renovo if ciclo.estado is EstadoCiclo.EVALUABLE else None,
    )
