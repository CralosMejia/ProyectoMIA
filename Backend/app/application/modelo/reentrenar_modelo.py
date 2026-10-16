"""Caso de uso ``ReentrenarModelo`` (CU-02, ADR-003; decisiones (d)-(g) de R-011).

Dos disparadores con los mismos criterios:

- ``revisar_programado`` (planificador): con la migracion ``COMPLETADA`` y un modelo vigente,
  compara "hoy" (fecha de negocio) con la proxima fecha programada. Igual -> reentrena;
  pasada -> un intento ``OMITIDO`` por cada fecha perdida y la proxima pasa a 6 meses despues
  de la ultima (si cae hoy, se reentrena a continuacion); futura o nula -> nada.
- ``ejecutar_manual`` (comando): reentrena sin mirar la fecha programada y solo la mueve si
  entrena una version nueva.

Reentrenar: ciclos de todas las membresias etiquetados al **corte de los datos** (R-015 T11,
el mismo criterio que ``adoptar-modelo`` y el notebook): ``corte_de_datos(hoy, corte del
vigente, dia de la ultima carga por plantilla)``. Asi no se marca como "no renovo" un ciclo
cuya renovacion aun no se ha cargado. Los ciclos nuevos (criterios 1 y 3) se miden a ese corte
y el modelo entrenado guarda ese corte como ``fecha_corte``; la cobertura (criterio 2) mira las
membresias registradas despues del ultimo entrenamiento, que ya estan dentro del corte. La
proxima fecha programada sigue contando desde hoy (calendario). Criterios 1 a 4; un
candidato entrenado sin los evaluables de los meses de comparacion ni los que vencen en los 30
dias previos al primer vencimiento de la comparacion (M01, ``ciclos_para_candidato``; esos
ciclos quedan en el historial como pendientes, con sus medianas propias); PR-AUC del candidato y
del vigente sobre ese conjunto; si el candidato no es peor, modelo final con todo el
historial evaluable. El modelo nuevo, su intento y la proxima fecha se guardan en **una**
transaccion. Si algo falla, nada de eso se guarda y un intento ``FALLIDO`` se registra en una
transaccion aparte (el vigente sigue).

Un bloqueo consultivo propio impide dos reentrenamientos a la vez: el segundo termina sin
tocar nada. Los logs y los motivos nunca llevan datos de socios ni el mensaje de una
excepcion ajena (solo su tipo).
"""

import logging
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.application.modelo.entrenar_modelo import EntrenarModeloInicial
from app.application.modelo.mapeo import ciclo_de_membresia, medianas_de
from app.application.modelo.ports import (
    AbrirBloqueoReentrenamiento,
    MembresiaParaEntrenamiento,
    ModeloGuardado,
    NuevoIntento,
    NuevoModelo,
    UnidadDeTrabajoReentrenamiento,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    ResultadoReentrenamiento,
)
from app.domain.common.fechas import hoy_en_negocio, sumar_meses
from app.domain.common.predictor import PredictorModel
from app.domain.modelo.metricas import pr_auc
from app.domain.modelo.reentrenamiento import (
    INTERVALO_MESES,
    AccionProgramada,
    CriteriosReentrenamiento,
    accion_programada,
    ciclos_para_candidato,
    corte_de_datos,
    es_ciclo_nuevo,
    etiquetar_ciclos,
    evaluar_criterios,
    fechas_perdidas,
    proxima_tras_omitido,
)
from app.domain.modelo.umbrales import meses_recientes_con_resultado
from app.domain.modelo.variables import (
    CicloModelo,
    MedianasMonto,
    calcular_medianas,
    construir_variables,
)

logger = logging.getLogger(__name__)

MENSAJE_EN_CURSO = "Ya hay un reentrenamiento en curso."
MENSAJE_NO_LISTO = "El sistema aun no esta listo."
MENSAJE_NO_TOCA = "Hoy no toca el reentrenamiento programado."
CLAVE_FECHA_CORTE = "fecha_corte"


def _por_socio(ciclos: Sequence[CicloModelo]) -> dict[str, list[CicloModelo]]:
    grupos: defaultdict[str, list[CicloModelo]] = defaultdict(list)
    for ciclo in ciclos:
        if not ciclo.excluido:
            grupos[ciclo.clave_socio].append(ciclo)
    return grupos


def corte_de_modelo(vigente: ModeloGuardado) -> date:
    """``fecha_corte`` del vigente; sin ella, la fecha de negocio de su entrenamiento."""
    valor = vigente.metadata_tecnica.get(CLAVE_FECHA_CORTE)
    if isinstance(valor, str) and valor:
        return date.fromisoformat(valor)
    return hoy_en_negocio(vigente.fecha_entrenamiento)


def _es_evaluable(ciclo: CicloModelo) -> bool:
    return (
        not ciclo.excluido and ciclo.no_renovo is not None and ciclo.fecha_vencimiento is not None
    )


class ReentrenarModelo:
    """Command de CU-02: revision programada y ejecucion manual."""

    def __init__(
        self,
        *,
        unidad_de_trabajo: UnidadDeTrabajoReentrenamiento,
        abrir_bloqueo: AbrirBloqueoReentrenamiento,
        predictor: PredictorModel,
        clock: Clock,
        criterios: CriteriosReentrenamiento | None = None,
    ) -> None:
        self._uow = unidad_de_trabajo
        self._abrir_bloqueo = abrir_bloqueo
        self._predictor = predictor
        self._clock = clock
        self._criterios = criterios if criterios is not None else CriteriosReentrenamiento()

    def revisar_programado(self) -> ResultadoReentrenamientoDTO:
        return self._con_bloqueo(self._programado)

    def ejecutar_manual(self) -> ResultadoReentrenamientoDTO:
        return self._con_bloqueo(self._manual)

    # ------------------------------------------------------------ orquestacion

    def _con_bloqueo(
        self, accion: Callable[[], ResultadoReentrenamientoDTO]
    ) -> ResultadoReentrenamientoDTO:
        with self._abrir_bloqueo() as bloqueo:
            if not bloqueo.intentar_adquirir():
                logger.info("reentrenamiento: otro proceso lo esta ejecutando")
                return ResultadoReentrenamientoDTO(
                    resultado=None, motivo=MENSAJE_EN_CURSO, en_curso=True
                )
            try:
                return accion()
            finally:
                bloqueo.liberar()

    def _sistema_listo(self) -> tuple[ModeloGuardado, date | None] | None:
        with self._uow() as uow:
            estado = uow.estado.obtener()
            vigente = uow.modelos.obtener_vigente()
        if estado.migracion_historica is not EstadoMigracion.COMPLETADA or vigente is None:
            return None
        return vigente, estado.proxima_fecha_reentrenamiento

    def _programado(self) -> ResultadoReentrenamientoDTO:
        hoy = hoy_en_negocio(self._clock.now())
        listo = self._sistema_listo()
        if listo is None:
            return ResultadoReentrenamientoDTO(resultado=None, motivo=MENSAJE_NO_LISTO)
        vigente, programada = listo
        accion = accion_programada(hoy, programada)
        if accion is AccionProgramada.ESPERAR or programada is None:
            return ResultadoReentrenamientoDTO(resultado=None, motivo=MENSAJE_NO_TOCA)
        if accion is AccionProgramada.OMITIR:
            omitido = self._omitir(programada, hoy)
            programada = proxima_tras_omitido(programada, hoy)
            if accion_programada(hoy, programada) is not AccionProgramada.EJECUTAR:
                return omitido
        return self._reentrenar(DisparadorReentrenamiento.PROGRAMADO, programada, hoy, vigente)

    def _manual(self) -> ResultadoReentrenamientoDTO:
        hoy = hoy_en_negocio(self._clock.now())
        listo = self._sistema_listo()
        if listo is None:
            return ResultadoReentrenamientoDTO(resultado=None, motivo=MENSAJE_NO_LISTO)
        vigente, _ = listo
        return self._reentrenar(DisparadorReentrenamiento.MANUAL, None, hoy, vigente)

    def _omitir(self, programada: date, hoy: date) -> ResultadoReentrenamientoDTO:
        ahora = self._clock.now()
        perdidas = fechas_perdidas(programada, hoy)
        proxima = proxima_tras_omitido(programada, hoy)
        with self._uow() as uow:
            for fecha in perdidas:
                uow.intentos.crear(
                    NuevoIntento(
                        fecha=ahora,
                        disparador=DisparadorReentrenamiento.PROGRAMADO,
                        resultado=ResultadoReentrenamiento.OMITIDO,
                        fecha_programada=fecha,
                        motivo=(
                            f"La fecha programada {fecha.isoformat()} paso sin que el sistema "
                            "estuviera encendido; no se recupera."
                        ),
                    )
                )
            uow.estado.fijar_proxima_fecha(proxima)
            uow.commit()
        logger.info(
            "reentrenamiento: %d fecha(s) perdida(s) registrada(s) como OMITIDO; proxima %s",
            len(perdidas),
            proxima.isoformat(),
        )
        return ResultadoReentrenamientoDTO(
            resultado=ResultadoReentrenamiento.OMITIDO,
            motivo=(
                f"Se omitio el reentrenamiento programado ({len(perdidas)} fecha(s) perdida(s)); "
                f"la proxima fecha es {proxima.isoformat()}."
            ),
        )

    # ------------------------------------------------------------ reentrenamiento

    def _reentrenar(
        self,
        disparador: DisparadorReentrenamiento,
        fecha_programada: date | None,
        hoy: date,
        vigente: ModeloGuardado,
    ) -> ResultadoReentrenamientoDTO:
        ahora = self._clock.now()
        proxima_si_no_entrena = (
            sumar_meses(hoy, INTERVALO_MESES)
            if disparador is DisparadorReentrenamiento.PROGRAMADO
            else None
        )
        try:
            return self._evaluar_y_entrenar(
                disparador, fecha_programada, hoy, ahora, vigente, proxima_si_no_entrena
            )
        except Exception as exc:
            # Solo el tipo: el mensaje de una excepcion ajena podria citar datos.
            tipo = type(exc).__name__
            logger.error("reentrenamiento fallido; sigue el modelo vigente (%s)", tipo)
            motivo = (
                f"El entrenamiento fallo ({tipo}); sigue vigente la version v{vigente.version}."
            )
            self._registrar(
                NuevoIntento(
                    fecha=ahora,
                    disparador=disparador,
                    resultado=ResultadoReentrenamiento.FALLIDO,
                    fecha_programada=fecha_programada,
                    motivo=motivo,
                ),
                proxima_si_no_entrena,
            )
            return ResultadoReentrenamientoDTO(
                resultado=ResultadoReentrenamiento.FALLIDO, motivo=motivo
            )

    def _evaluar_y_entrenar(
        self,
        disparador: DisparadorReentrenamiento,
        fecha_programada: date | None,
        hoy: date,
        ahora: datetime,
        vigente: ModeloGuardado,
        proxima_si_no_entrena: date | None,
    ) -> ResultadoReentrenamientoDTO:
        with self._uow() as uow:
            membresias = uow.membresias.listar_para_entrenamiento()
            ultima_carga = uow.cargas.ultima_carga_plantilla_hasta(ahora)

        corte_vigente = corte_de_modelo(vigente)
        corte = corte_de_datos(
            hoy,
            corte_vigente,
            None if ultima_carga is None else hoy_en_negocio(ultima_carga),
        )
        ciclos = etiquetar_ciclos([ciclo_de_membresia(m) for m in membresias], corte)
        nuevos = [c for c in ciclos if es_ciclo_nuevo(c, corte_vigente)]
        evaluables = [c for c in ciclos if _es_evaluable(c)]
        historial = _por_socio(ciclos)

        medianas = calcular_medianas(evaluables)
        motivos = evaluar_criterios(
            nuevos,
            _vencimientos_nuevas(membresias, vigente.fecha_entrenamiento),
            # Criterio 4: variables del conjunto completo de entrenamiento.
            [construir_variables(c, historial[c.clave_socio], medianas) for c in evaluables],
            self._criterios,
        )
        if motivos:
            motivo = " ".join(motivos)
            self._registrar(
                NuevoIntento(
                    fecha=ahora,
                    disparador=disparador,
                    resultado=ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS,
                    fecha_programada=fecha_programada,
                    motivo=motivo,
                    ciclos_nuevos=len(nuevos),
                ),
                proxima_si_no_entrena,
            )
            logger.info("reentrenamiento: criterios no cumplidos (ciclos_nuevos=%d)", len(nuevos))
            return ResultadoReentrenamientoDTO(
                resultado=ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS, motivo=motivo
            )

        comparacion = meses_recientes_con_resultado(evaluables, self._criterios.meses_comparacion)
        entrenador = EntrenarModeloInicial(self._predictor)
        candidato = entrenador.ejecutar_ciclos(_ciclos_del_candidato(ciclos, comparacion), corte)
        etiquetas = [int(bool(c.no_renovo)) for c in comparacion]
        pr_candidato = self._pr_auc(
            candidato.artefacto, comparacion, historial, candidato.medianas, etiquetas
        )
        pr_vigente = self._pr_auc(
            vigente.artefacto,
            comparacion,
            historial,
            medianas_de(vigente.metadata_tecnica),
            etiquetas,
        )
        if pr_candidato < pr_vigente:
            motivo = (
                f"El candidato tiene peor PR-AUC ({pr_candidato}) que el vigente ({pr_vigente}); "
                f"sigue vigente la version v{vigente.version}."
            )
            self._registrar(
                NuevoIntento(
                    fecha=ahora,
                    disparador=disparador,
                    resultado=ResultadoReentrenamiento.NO_SUPERA_VIGENTE,
                    fecha_programada=fecha_programada,
                    motivo=motivo,
                    ciclos_nuevos=len(nuevos),
                    pr_auc_candidato=pr_candidato,
                    pr_auc_vigente=pr_vigente,
                ),
                proxima_si_no_entrena,
            )
            logger.info("reentrenamiento: el candidato no supera al vigente")
            return ResultadoReentrenamientoDTO(
                resultado=ResultadoReentrenamiento.NO_SUPERA_VIGENTE, motivo=motivo
            )

        final = entrenador.ejecutar_ciclos(ciclos, corte)
        version = vigente.version + 1
        metadata: dict[str, object] = dict(final.metadata_tecnica)
        metadata["pr_auc_candidato"] = str(pr_candidato)
        metadata["pr_auc_vigente"] = str(pr_vigente)
        metadata["ciclos_comparacion"] = len(comparacion)
        motivo = (
            f"Se entreno la version v{version}: PR-AUC del candidato {pr_candidato} frente a "
            f"{pr_vigente} del vigente."
        )
        with self._uow() as uow:
            modelo_id = uow.modelos.crear(
                NuevoModelo(
                    version=version,
                    fecha_entrenamiento=ahora,
                    ciclos_entrenamiento=final.ciclos_entrenamiento,
                    periodo_desde=final.periodo_desde,
                    periodo_hasta=final.periodo_hasta,
                    prevalencia=final.prevalencia,
                    umbral_alto=final.umbrales.alto,
                    umbral_medio=final.umbrales.medio,
                    porcentajes_umbral=final.porcentajes_umbral,
                    artefacto=final.artefacto,
                    metadata_tecnica=metadata,
                )
            )
            uow.intentos.crear(
                NuevoIntento(
                    fecha=ahora,
                    disparador=disparador,
                    resultado=ResultadoReentrenamiento.ENTRENADO,
                    fecha_programada=fecha_programada,
                    motivo=motivo,
                    ciclos_nuevos=len(nuevos),
                    pr_auc_candidato=pr_candidato,
                    pr_auc_vigente=pr_vigente,
                    modelo_id=modelo_id,
                )
            )
            uow.estado.fijar_proxima_fecha(sumar_meses(hoy, INTERVALO_MESES))
            uow.commit()
        logger.info(
            "reentrenamiento: version %d entrenada (ciclos=%d)", version, final.ciclos_entrenamiento
        )
        return ResultadoReentrenamientoDTO(
            resultado=ResultadoReentrenamiento.ENTRENADO, motivo=motivo, version=version
        )

    def _pr_auc(
        self,
        artefacto: bytes,
        comparacion: Sequence[CicloModelo],
        historial: Mapping[str, Sequence[CicloModelo]],
        medianas: MedianasMonto,
        etiquetas: Sequence[int],
    ) -> Decimal:
        filas = [construir_variables(c, historial[c.clave_socio], medianas) for c in comparacion]
        scores = [p.score for p in self._predictor.predict(artefacto, filas)]
        return pr_auc(scores, etiquetas)

    def _registrar(self, intento: NuevoIntento, proxima: date | None) -> None:
        with self._uow() as uow:
            uow.intentos.crear(intento)
            if proxima is not None:
                uow.estado.fijar_proxima_fecha(proxima)
            uow.commit()


def _ciclos_del_candidato(
    ciclos: Sequence[CicloModelo], comparacion: Sequence[CicloModelo]
) -> list[CicloModelo]:
    """Todos los ciclos; los evaluables que el candidato no puede ver pasan a pendientes.

    Siguen en el historial (el corte T-30 decide si cuentan como previos), pero no se entrena
    con ellos ni entran en sus medianas.
    """
    evaluables = [c for c in ciclos if _es_evaluable(c)]
    visibles = {id(c) for c in ciclos_para_candidato(evaluables, comparacion)}
    return [
        c if not _es_evaluable(c) or id(c) in visibles else replace(c, no_renovo=None)
        for c in ciclos
    ]


def _vencimientos_nuevas(
    membresias: Sequence[MembresiaParaEntrenamiento], ultimo_entrenamiento: datetime
) -> list[date | None]:
    """Vencimiento de cada membresia registrada despues del ultimo entrenamiento (criterio 2)."""
    return [m.fecha_vencimiento for m in membresias if m.registrada_en > ultimo_entrenamiento]
