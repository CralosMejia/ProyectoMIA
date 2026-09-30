"""Caso de uso ``MigrarHistorico`` (CU-03 completo, atomico; ADR-004).

Flujo:

1. Toma el bloqueo de la migracion sobre una conexion propia; si otro proceso lo tiene, no
   hace nada. El bloqueo se libera siempre en ``finally``, tambien si la migracion falla.
2. Si ya hay una migracion historica o membresias, o el estado es ``COMPLETADA``, no hace
   nada. Un ``EN_CURSO`` con el bloqueo tomado y la base vacia es un huerfano de una caida
   anterior y se trata como ``PENDIENTE``.
3. Sin libros: no migra, deja ``PENDIENTE`` y el resultado es ``FALTAN_DATOS``.
4. Transaccion corta: ``EN_CURSO`` + ``commit``.
5. ``ProcesarHistorico`` y ``EntrenarModeloInicial`` (fuera de la transaccion).
6. **Una** unidad de trabajo guarda la carga ``MIGRACION_HISTORICA``, los socios (uno por
   identidad, con los datos del registro mas reciente en orden de lectura), las membresias,
   el modelo v1 vigente, el intento ``INICIAL``/``ENTRENADO``, la proxima fecha de
   reentrenamiento (6 meses) y ``COMPLETADA``; despues ``commit``.
7. Si algo falla no hay ``commit`` (todo se revierte) y una transaccion corta vuelve a
   ``PENDIENTE``. El resultado en memoria es ``FALTAN_DATOS`` (libros ilegibles) o ``FALLIDA``.

Los logs solo llevan conteos, nombres de libro y de hoja, y el tipo de la excepcion: nunca
nombres, cedulas, celulares ni correos (RN-03.5), ni el mensaje de una excepcion ajena, que
podria citar valores de las filas.
"""

import logging
import zipfile
from collections.abc import Sequence
from pathlib import Path

from app.application.historial.ports import (
    LectorHistorico,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
    ReferenciaOrigen,
)
from app.application.historial.procesar_historico import (
    ProcesarHistorico,
    ResultadoProcesamiento,
)
from app.application.modelo.entrenar_modelo import EntrenarModeloInicial, ModeloEntrenado
from app.application.modelo.ports import NuevoIntento, NuevoModelo
from app.application.sistema.ports import (
    AbrirBloqueo,
    FabricaUnidadDeTrabajo,
    LocalizadorLibros,
    RegistroMigracion,
    ResultadoMigracion,
    UnidadDeTrabajo,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    OrigenMembresia,
    ResultadoReentrenamiento,
    TipoCarga,
)
from app.domain.common.fechas import sumar_meses
from app.domain.common.predictor import PredictorModel
from app.domain.historico.ciclos import SinMesesDisponiblesError
from app.domain.historico.errores import HojaSinEncabezadoError, LibroSinAnioError
from app.domain.historico.registro import RegistroHistorico

logger = logging.getLogger(__name__)

VERSION_INICIAL = 1
MESES_HASTA_REENTRENAMIENTO = 6


class MigrarHistorico:
    """Migra el historico y entrena el modelo v1 en una sola transaccion."""

    def __init__(
        self,
        *,
        abrir_bloqueo: AbrirBloqueo,
        unidad_de_trabajo: FabricaUnidadDeTrabajo,
        localizador: LocalizadorLibros,
        lector: LectorHistorico,
        predictor: PredictorModel,
        clock: Clock,
        registro: RegistroMigracion,
    ) -> None:
        self._abrir_bloqueo = abrir_bloqueo
        self._uow = unidad_de_trabajo
        self._localizador = localizador
        self._lector = lector
        self._predictor = predictor
        self._clock = clock
        self._registro = registro

    def ejecutar(self) -> ResultadoMigracion:
        self._registro.iniciar()
        resultado = ResultadoMigracion.FALLIDA
        try:
            resultado = self._con_bloqueo()
        finally:
            self._registro.terminar(resultado)
        return resultado

    def _con_bloqueo(self) -> ResultadoMigracion:
        with self._abrir_bloqueo() as bloqueo:
            if not bloqueo.intentar_adquirir():
                logger.info("migracion historica: otro proceso la esta ejecutando")
                return ResultadoMigracion.EN_OTRO_PROCESO
            try:
                return self._migrar()
            finally:
                bloqueo.liberar()

    def _migrar(self) -> ResultadoMigracion:
        with self._uow() as uow:
            estado = uow.estado.obtener().migracion_historica
            ya_migrada = estado is EstadoMigracion.COMPLETADA or (
                uow.cargas.hay_migracion_o_membresias()
            )
        if ya_migrada:
            logger.info("migracion historica: la base ya esta migrada; no se hace nada")
            return ResultadoMigracion.YA_MIGRADA

        rutas = self._localizador.rutas()
        if not rutas:
            logger.warning("migracion historica: no hay libros historicos en la carpeta")
            if estado is EstadoMigracion.EN_CURSO:
                self._volver_a_pendiente()
            return ResultadoMigracion.FALTAN_DATOS

        self._fijar_estado(EstadoMigracion.EN_CURSO)
        try:
            procesado = ProcesarHistorico(self._lector).ejecutar(rutas)
            entrenado = EntrenarModeloInicial(self._predictor).ejecutar(
                procesado.ciclos, procesado.fecha_corte
            )
            with self._uow() as uow:
                self._guardar(uow, rutas, procesado, entrenado)
                uow.commit()
        except (LibroSinAnioError, HojaSinEncabezadoError, SinMesesDisponiblesError) as exc:
            # Estos mensajes solo nombran el libro y la hoja (RN-03.5).
            logger.warning("migracion historica: faltan datos historicos: %s", exc)
            self._volver_a_pendiente()
            return ResultadoMigracion.FALTAN_DATOS
        except (OSError, zipfile.BadZipFile) as exc:
            logger.warning(
                "migracion historica: no se pudieron leer los libros (%s)", type(exc).__name__
            )
            self._volver_a_pendiente()
            return ResultadoMigracion.FALTAN_DATOS
        except Exception as exc:
            # Sin traceback ni mensaje: podrian citar valores de las filas (RN-03.5).
            logger.error("migracion historica fallida; se revierte todo (%s)", type(exc).__name__)
            self._volver_a_pendiente()
            return ResultadoMigracion.FALLIDA

        informe = procesado.informe
        logger.info(
            "migracion historica completada: libros=%d filas_leidas=%d membresias=%d "
            "socios=%d evaluables=%d no_renovo=%d fecha_corte=%s",
            informe.libros,
            informe.filas_leidas,
            informe.con_identidad,
            informe.socios_distintos,
            informe.evaluables,
            informe.no_renovo,
            informe.fecha_corte.isoformat(),
        )
        return ResultadoMigracion.COMPLETADA

    def _fijar_estado(self, estado: EstadoMigracion) -> None:
        with self._uow() as uow:
            uow.estado.fijar_migracion(estado)
            uow.commit()

    def _volver_a_pendiente(self) -> None:
        try:
            self._fijar_estado(EstadoMigracion.PENDIENTE)
        except Exception as exc:
            logger.error(
                "migracion historica: no se pudo volver a PENDIENTE (%s)", type(exc).__name__
            )

    def _guardar(
        self,
        uow: UnidadDeTrabajo,
        rutas: Sequence[Path],
        procesado: ResultadoProcesamiento,
        entrenado: ModeloEntrenado,
    ) -> None:
        ahora = self._clock.now()
        registros = procesado.registros
        informe = procesado.informe
        carga_id = uow.cargas.crear(
            NuevaCarga(
                tipo=TipoCarga.MIGRACION_HISTORICA,
                fecha_carga=ahora,
                nombre_archivo=", ".join(ruta.name for ruta in rutas),
                filas_leidas=informe.filas_leidas,
                filas_guardadas=len(registros),
                filas_duplicadas=0,
                socios_enlazados=informe.socios_distintos,
            )
        )
        socio_por_identidad = self._guardar_socios(uow, registros)
        uow.membresias.insertar_en_bloque(
            [_membresia(r, socio_por_identidad[r.identidad], carga_id) for r in registros]
        )
        modelo_id = uow.modelos.crear(
            NuevoModelo(
                version=VERSION_INICIAL,
                fecha_entrenamiento=ahora,
                ciclos_entrenamiento=entrenado.ciclos_entrenamiento,
                periodo_desde=entrenado.periodo_desde,
                periodo_hasta=entrenado.periodo_hasta,
                prevalencia=entrenado.prevalencia,
                umbral_alto=entrenado.umbrales.alto,
                umbral_medio=entrenado.umbrales.medio,
                porcentajes_umbral=entrenado.porcentajes_umbral,
                artefacto=entrenado.artefacto,
                metadata_tecnica=entrenado.metadata_tecnica,
            )
        )
        uow.intentos.crear(
            NuevoIntento(
                fecha=ahora,
                disparador=DisparadorReentrenamiento.INICIAL,
                resultado=ResultadoReentrenamiento.ENTRENADO,
                ciclos_nuevos=entrenado.ciclos_entrenamiento,
                modelo_id=modelo_id,
            )
        )
        uow.estado.fijar_proxima_fecha(sumar_meses(ahora.date(), MESES_HASTA_REENTRENAMIENTO))
        uow.estado.fijar_migracion(EstadoMigracion.COMPLETADA)

    @staticmethod
    def _guardar_socios(
        uow: UnidadDeTrabajo, registros: Sequence[RegistroHistorico]
    ) -> dict[str, int]:
        """Un socio por identidad; sus datos salen del registro mas reciente leido."""
        ultimo: dict[str, RegistroHistorico] = {}
        for registro in registros:
            ultimo[registro.identidad] = registro
        socios = [
            NuevoSocio(
                cedula=r.cedula,
                nombre=r.nombre,
                nombre_normalizado=r.nombre_normalizado,
                celular=r.celular,
                correo=r.correo,
            )
            for r in ultimo.values()
        ]
        ids = uow.socios.insertar_en_bloque(socios)
        return dict(zip(ultimo, ids, strict=True))


def _membresia(registro: RegistroHistorico, socio_id: int, carga_id: int) -> NuevaMembresia:
    anio, hoja, fila = registro.referencia
    return NuevaMembresia(
        socio_id=socio_id,
        carga_id=carga_id,
        plan=registro.plan,
        forma_pago=registro.forma_pago,
        origen=OrigenMembresia.HISTORICO,
        inicio_aproximado=registro.inicio_aproximado,
        fecha_actividad=registro.fecha_actividad,
        fecha_inicio=registro.fecha_inicio,
        fecha_vencimiento=registro.fecha_vencimiento,
        monto_cobrado=registro.monto_cobrado,
        referencia_origen=ReferenciaOrigen(anio=anio, hoja=hoja, fila=fila),
        plan_original=registro.plan_original,
        forma_pago_original=registro.forma_pago_original,
    )
