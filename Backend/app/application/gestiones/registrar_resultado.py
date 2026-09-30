"""Caso de uso RegistrarResultado (CU-10): resultado del seguimiento de una gestion.

Flujo (todo en **una** unidad de trabajo, con la fila bloqueada y un solo ``commit``):

1. Gestion inexistente -> ``GestionNoExisteError``; ``CERRADA`` -> ``GestionCerradaError``
   (RN-10.3), comprobado sobre la fila bloqueada (``obtener_para_actualizar``).
2. Coherencia del resultado (decision (h)).
3. ``renovo_declarado`` ``SI``/``NO`` -> ``CERRADA`` con ``cerrada_en = clock.now()`` y se
   ignora la fecha de seguimiento recibida; ``PENDIENTE`` -> sigue ``PENDIENTE`` y, si llega
   ``fecha_seguimiento``, se valida con el rango de CU-08 (si no llega, se conserva).
4. Se reemplazan los campos del resultado. No toca membresias ni etiquetas (RN-10.2).
"""

from app.application.gestiones.crear_gestion import gestion_a_dto
from app.application.gestiones.dtos import GestionDTO, RegistrarResultadoDTO
from app.application.gestiones.ports import ResultadoGestion, UnidadDeTrabajoGestiones
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoGestion
from app.domain.common.exceptions import DomainError
from app.domain.common.fechas import hoy_en_negocio
from app.domain.gestiones.errores import GestionCerradaError
from app.domain.gestiones.reglas import (
    estado_tras_resultado,
    validar_fecha_seguimiento,
    validar_resultado,
)

MENSAJE_GESTION_NO_EXISTE = "La gestion no existe."


class GestionNoExisteError(DomainError):
    """No hay una gestion no borrada con ese id (-> 404)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_GESTION_NO_EXISTE)


class RegistrarResultado:
    """Command: registra (reemplaza) el resultado de una gestion pendiente."""

    def __init__(self, uow: UnidadDeTrabajoGestiones, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def ejecutar(self, gestion_id: int, datos: RegistrarResultadoDTO) -> GestionDTO:
        ahora = self._clock.now()
        hoy = hoy_en_negocio(ahora)
        with self._uow() as ctx:
            gestion = ctx.gestiones.obtener_para_actualizar(gestion_id)
            if gestion is None:
                raise GestionNoExisteError()
            if gestion.estado is EstadoGestion.CERRADA:
                raise GestionCerradaError()
            validar_resultado(
                con_campania=gestion.campania_id is not None,
                contactado=datos.contactado,
                ofrecida=datos.campania_ofrecida,
                aceptada=datos.campania_aceptada,
                fecha_contacto=datos.fecha_contacto,
                fecha_asignacion=gestion.fecha_asignacion,
                hoy=hoy,
            )
            estado = estado_tras_resultado(datos.renovo_declarado)
            fecha_seguimiento = gestion.fecha_seguimiento
            if estado is EstadoGestion.PENDIENTE and datos.fecha_seguimiento is not None:
                validar_fecha_seguimiento(datos.fecha_seguimiento, hoy, gestion.fecha_vencimiento)
                fecha_seguimiento = datos.fecha_seguimiento
            ctx.gestiones.guardar_resultado(
                gestion_id,
                ResultadoGestion(
                    contactado=datos.contactado,
                    campania_ofrecida=datos.campania_ofrecida,
                    campania_aceptada=datos.campania_aceptada,
                    renovo_declarado=datos.renovo_declarado,
                    fecha_contacto=datos.fecha_contacto,
                    observaciones=datos.observaciones,
                    responsable=datos.responsable,
                    fecha_seguimiento=fecha_seguimiento,
                    estado=estado,
                    cerrada_en=ahora if estado is EstadoGestion.CERRADA else None,
                ),
            )
            detalle = ctx.gestiones.obtener(gestion_id)
            if detalle is None:  # pragma: no cover - la fila esta bloqueada por esta transaccion
                raise GestionNoExisteError()
            ctx.commit()
        return gestion_a_dto(detalle)
