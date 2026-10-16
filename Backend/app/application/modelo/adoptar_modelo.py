"""Caso de uso ``AdoptarModelo`` (R-015, decision (e)): pone en uso el modelo M01.

Comando manual ``python -m app.cli adoptar-modelo``. Con el sistema listo (migracion
``COMPLETADA`` y un modelo vigente):

1. Etiqueta los ciclos de todas las membresias al **corte de los datos** (R-015 T11):
   ``corte_de_datos(hoy, corte del vigente, dia de la ultima carga por plantilla)``, con hoy
   del reloj inyectado. Como el notebook, que etiqueta a la fecha de corte de los datos: con
   los libros historicos hasta el 31-08-2026 y sin cargas posteriores, el corte es ese dia
   aunque el comando se ejecute despues, y el modelo y la lista coinciden con el notebook.
2. Entrena **una vez** con todos los evaluables y el ``ConjuntoVariables`` configurado (por
   defecto ``CONJUNTO_MODELO``), sin candidato ni criterios de CU-02.
3. En **una** transaccion guarda la version ``vigente + 1`` como vigente (la anterior se
   conserva como historia, no vigente) y un intento ``MANUAL``/``ENTRENADO`` con el motivo
   ``MOTIVO_ADOPCION``. No cambia la proxima fecha de reentrenamiento programado.

Si el entrenamiento falla no se guarda nada (ni intento ``FALLIDO``): sigue el vigente. Comparte
el bloqueo del reentrenamiento: con otro en curso termina sin tocar nada. Los logs y los
mensajes nunca llevan datos de socios ni el mensaje de una excepcion ajena (solo su tipo).
"""

import logging
from datetime import datetime

from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.application.modelo.entrenar_modelo import EntrenarModeloInicial, ModeloEntrenado
from app.application.modelo.mapeo import ciclo_de_membresia
from app.application.modelo.ports import (
    AbrirBloqueoReentrenamiento,
    NuevoIntento,
    NuevoModelo,
    UnidadDeTrabajoReentrenamiento,
)
from app.application.modelo.reentrenar_modelo import (
    MENSAJE_EN_CURSO,
    MENSAJE_NO_LISTO,
    corte_de_modelo,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)
from app.domain.common.fechas import hoy_en_negocio
from app.domain.common.predictor import PredictorModel
from app.domain.modelo.reentrenamiento import corte_de_datos, etiquetar_ciclos
from app.domain.modelo.variables import CONJUNTO_MODELO, ConjuntoVariables

logger = logging.getLogger(__name__)

MOTIVO_ADOPCION = "Adopción del modelo M01"


class AdoptarModelo:
    """Command: entrena y pone en uso un modelo nuevo (version vigente + 1)."""

    def __init__(
        self,
        *,
        unidad_de_trabajo: UnidadDeTrabajoReentrenamiento,
        abrir_bloqueo: AbrirBloqueoReentrenamiento,
        predictor: PredictorModel,
        clock: Clock,
        variables: ConjuntoVariables = CONJUNTO_MODELO,
    ) -> None:
        self._uow = unidad_de_trabajo
        self._abrir_bloqueo = abrir_bloqueo
        self._predictor = predictor
        self._clock = clock
        self._variables = variables

    def ejecutar(self) -> ResultadoReentrenamientoDTO:
        with self._abrir_bloqueo() as bloqueo:
            if not bloqueo.intentar_adquirir():
                logger.info("adopcion: otro proceso esta reentrenando")
                return ResultadoReentrenamientoDTO(
                    resultado=None, motivo=MENSAJE_EN_CURSO, en_curso=True
                )
            try:
                return self._adoptar()
            finally:
                bloqueo.liberar()

    def _adoptar(self) -> ResultadoReentrenamientoDTO:
        ahora = self._clock.now()
        hoy = hoy_en_negocio(ahora)
        with self._uow() as uow:
            estado = uow.estado.obtener()
            vigente = uow.modelos.obtener_vigente()
            if estado.migracion_historica is not EstadoMigracion.COMPLETADA or vigente is None:
                return ResultadoReentrenamientoDTO(resultado=None, motivo=MENSAJE_NO_LISTO)
            membresias = uow.membresias.listar_para_entrenamiento()
            ultima_carga = uow.cargas.ultima_carga_plantilla_hasta(ahora)

        corte = corte_de_datos(
            hoy,
            corte_de_modelo(vigente),
            None if ultima_carga is None else hoy_en_negocio(ultima_carga),
        )
        ciclos = etiquetar_ciclos([ciclo_de_membresia(m) for m in membresias], corte)
        try:
            modelo = EntrenarModeloInicial(self._predictor, self._variables).ejecutar_ciclos(
                ciclos, corte
            )
        except Exception as exc:
            # Solo el tipo: el mensaje de una excepcion ajena podria citar datos.
            tipo = type(exc).__name__
            logger.error("adopcion fallida; sigue el modelo vigente (%s)", tipo)
            return ResultadoReentrenamientoDTO(
                resultado=None,
                motivo=(
                    f"El entrenamiento fallo ({tipo}); sigue vigente la version "
                    f"v{vigente.version}; no se guardo nada."
                ),
            )

        version = vigente.version + 1
        with self._uow() as uow:
            modelo_id = uow.modelos.crear(self._nuevo_modelo(modelo, version, ahora))
            uow.intentos.crear(
                NuevoIntento(
                    fecha=ahora,
                    disparador=DisparadorReentrenamiento.MANUAL,
                    resultado=ResultadoReentrenamiento.ENTRENADO,
                    motivo=MOTIVO_ADOPCION,
                    modelo_id=modelo_id,
                )
            )
            uow.commit()
        logger.info(
            "adopcion: version %d en uso (ciclos=%d); la version %d se conserva",
            version,
            modelo.ciclos_entrenamiento,
            vigente.version,
        )
        return ResultadoReentrenamientoDTO(
            resultado=ResultadoReentrenamiento.ENTRENADO,
            motivo=f"v{version} en uso ({MOTIVO_ADOPCION}).",
            version=version,
        )

    @staticmethod
    def _nuevo_modelo(modelo: ModeloEntrenado, version: int, ahora: datetime) -> NuevoModelo:
        metadata: dict[str, object] = dict(modelo.metadata_tecnica)
        metadata["adopcion"] = MOTIVO_ADOPCION
        return NuevoModelo(
            version=version,
            fecha_entrenamiento=ahora,
            ciclos_entrenamiento=modelo.ciclos_entrenamiento,
            periodo_desde=modelo.periodo_desde,
            periodo_hasta=modelo.periodo_hasta,
            prevalencia=modelo.prevalencia,
            umbral_alto=modelo.umbrales.alto,
            umbral_medio=modelo.umbrales.medio,
            porcentajes_umbral=modelo.porcentajes_umbral,
            artefacto=modelo.artefacto,
            metadata_tecnica=metadata,
        )
