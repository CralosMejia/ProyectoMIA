"""Caso de uso CrearGestion (CU-08): asignar campana y programar el seguimiento.

Flujo (todo en **una** unidad de trabajo, con un solo ``commit`` al final):

1. "Hoy" = ``hoy_en_negocio(clock.now())`` (Ecuador).
2. Prediccion inexistente -> ``PrediccionNoExisteError``; su ciclo ya con gestion ->
   ``GestionDuplicadaError`` (RN-08.1).
3. Con campana: fecha de seguimiento dentro de ``[hoy, vencimiento + 30]`` (decision (g));
   campana inexistente o borrada -> ``CampaniaNoExisteError``; inactiva o incompatible con el
   nivel y el plan de la prediccion -> ``CampaniaNoAplicableError``. Se guarda ``PENDIENTE``
   con la instantanea del nombre de la campana (RN-08.2).
4. Sin campana (R-010 (c), (d)): la gestion nace ``CERRADA`` (``estado_inicial``) con
   ``cerrada_en`` = ahora; no hay seguimiento, asi que la fecha y el responsable enviados se
   ignoran (se guarda hoy y nulo) y no se valida el rango ni el plazo.
"""

from datetime import date

from app.application.campanias.gestionar_campanias import CampaniaNoExisteError
from app.application.campanias.sugerir_campanias import PrediccionNoExisteError
from app.application.gestiones.dtos import CrearGestionDTO, GestionDTO
from app.application.gestiones.ports import (
    ContextoGestiones,
    DatosPrediccionGestion,
    GestionDetalle,
    NuevaGestion,
    UnidadDeTrabajoGestiones,
)
from app.application.listas.consultar_listas import version_texto
from app.domain.campanias.campania import es_compatible
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoGestion
from app.domain.common.fechas import hoy_en_negocio
from app.domain.gestiones.errores import CampaniaNoAplicableError, GestionDuplicadaError
from app.domain.gestiones.reglas import estado_inicial, validar_fecha_seguimiento


def gestion_a_dto(detalle: GestionDetalle) -> GestionDTO:
    """``fecha_asignacion`` del contrato = instante de creacion (decision (b)).

    Se valida con ``model_validate``: las respuestas guardadas se comprueban contra el
    subconjunto de cada pregunta en lugar de suponerlo.
    """
    return GestionDTO.model_validate(
        {
            "id": detalle.id,
            "prediccion_id": detalle.prediccion_id,
            "socio_nombre": detalle.socio_nombre,
            "plan": detalle.plan,
            "fecha_vencimiento": detalle.fecha_vencimiento,
            "modelo_version": version_texto(detalle.modelo_version),
            "score": detalle.score,
            "nivel_riesgo": detalle.nivel_riesgo,
            "campania_id": detalle.campania_id,
            "campania_nombre": detalle.campania_nombre,
            "estado": detalle.estado,
            "fecha_asignacion": detalle.creada_en,
            "fecha_seguimiento": detalle.fecha_seguimiento,
            "responsable": detalle.responsable,
            "contactado": detalle.contactado,
            "campania_ofrecida": detalle.campania_ofrecida,
            "campania_aceptada": detalle.campania_aceptada,
            "renovo_declarado": detalle.renovo_declarado,
            "fecha_contacto": detalle.fecha_contacto,
            "observaciones": detalle.observaciones,
            "fecha_cierre": detalle.cerrada_en,
        }
    )


class CrearGestion:
    """Command: crea la gestion de retencion de un socio de la lista."""

    def __init__(self, uow: UnidadDeTrabajoGestiones, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def ejecutar(self, datos: CrearGestionDTO) -> GestionDTO:
        ahora = self._clock.now()
        hoy = hoy_en_negocio(ahora)
        estado = estado_inicial(datos.campania_id is not None)
        with self._uow() as ctx:
            prediccion = ctx.gestiones.datos_prediccion(datos.prediccion_id)
            if prediccion is None:
                raise PrediccionNoExisteError()
            if ctx.gestiones.existe_para_membresia(prediccion.membresia_id):
                raise GestionDuplicadaError()
            fecha_seguimiento, responsable = _seguimiento(datos, hoy, prediccion)
            campania_nombre = _nombre_campania(ctx, datos.campania_id, prediccion)
            gestion_id = ctx.gestiones.crear(
                NuevaGestion(
                    prediccion_id=prediccion.prediccion_id,
                    membresia_id=prediccion.membresia_id,
                    campania_id=datos.campania_id,
                    campania_nombre=campania_nombre,
                    fecha_asignacion=hoy,
                    fecha_seguimiento=fecha_seguimiento,
                    responsable=responsable,
                    estado=estado,
                    cerrada_en=ahora if estado is EstadoGestion.CERRADA else None,
                )
            )
            detalle = ctx.gestiones.obtener(gestion_id)
            if detalle is None:  # pragma: no cover - la fila se acaba de insertar
                raise RuntimeError("La gestion recien creada no se encontro.")
            ctx.commit()
        return gestion_a_dto(detalle)


def _seguimiento(
    datos: CrearGestionDTO, hoy: date, prediccion: DatosPrediccionGestion
) -> tuple[date, str | None]:
    """Fecha de seguimiento y responsable a guardar.

    Sin campana no hay seguimiento: lo enviado se ignora y la fecha (columna obligatoria)
    queda en hoy, sin validar el rango ni el plazo.
    """
    if datos.campania_id is None:
        return hoy, None
    if datos.fecha_seguimiento is None:  # pragma: no cover - lo impide ``CrearGestionDTO``
        raise ValueError("fecha_seguimiento es obligatoria cuando se asigna una campana")
    validar_fecha_seguimiento(datos.fecha_seguimiento, hoy, prediccion.fecha_vencimiento)
    return datos.fecha_seguimiento, datos.responsable


def _nombre_campania(
    ctx: ContextoGestiones, campania_id: int | None, prediccion: DatosPrediccionGestion
) -> str | None:
    """Nombre actual de la campana (instantanea) tras comprobar que aplica al socio."""
    if campania_id is None:
        return None
    campania = ctx.campanias.obtener(campania_id)
    if campania is None:
        raise CampaniaNoExisteError()
    if not es_compatible(
        campania.activa,
        campania.niveles_riesgo,
        campania.planes,
        prediccion.nivel_riesgo,
        prediccion.plan,
    ):
        raise CampaniaNoAplicableError()
    return campania.nombre
