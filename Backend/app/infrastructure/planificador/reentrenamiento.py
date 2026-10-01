"""Planificador del reentrenamiento programado (CU-02, ADR-003; decision (f) de R-011).

Un hilo daemon del backend revisa al arrancar y despues cada hora; solo llama a
``revisar_programado`` cuando cambia el dia de negocio (Ecuador) respecto de la ultima
revision completada. El servicio decide que hacer (ejecutar, omitir o esperar) y toma su
propio bloqueo consultivo. Si la revision falla o hay otro reentrenamiento en curso, el dia no
se da por revisado y se reintenta en la siguiente vuelta.

Las excepciones se registran solo por su tipo: el mensaje podria citar datos. Este modulo no
crea tablas ni migra nada.
"""

import logging
import threading
from datetime import date
from typing import Protocol

from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.domain.common.clock import Clock
from app.domain.common.fechas import hoy_en_negocio

logger = logging.getLogger(__name__)

NOMBRE_HILO = "planificador-reentrenamiento"
INTERVALO_SEGUNDOS = 3600.0
ESPERA_AL_DETENER_SEGUNDOS = 60.0


class RevisionProgramada(Protocol):
    def revisar_programado(self) -> ResultadoReentrenamientoDTO: ...


class PlanificadorReentrenamiento:
    """Hilo que revisa el reentrenamiento programado una vez por dia de negocio."""

    def __init__(
        self,
        servicio: RevisionProgramada,
        clock: Clock,
        *,
        intervalo_segundos: float = INTERVALO_SEGUNDOS,
    ) -> None:
        self._servicio = servicio
        self._clock = clock
        self._intervalo = intervalo_segundos
        self._detener = threading.Event()
        self._hilo: threading.Thread | None = None
        self._ultimo_dia: date | None = None

    @property
    def hilo(self) -> threading.Thread | None:
        return self._hilo

    def iniciar(self) -> None:
        if self._hilo is not None:
            raise RuntimeError("El planificador ya esta iniciado.")
        self._hilo = threading.Thread(target=self._bucle, name=NOMBRE_HILO, daemon=True)
        self._hilo.start()

    def detener(self, espera_segundos: float = ESPERA_AL_DETENER_SEGUNDOS) -> None:
        """Pide al hilo que termine y espera a que acabe la revision en curso."""
        self._detener.set()
        if self._hilo is not None:
            self._hilo.join(espera_segundos)
            if self._hilo.is_alive():
                logger.warning("planificador de reentrenamiento: sigue ocupado al detenerse")

    def revisar_si_cambio_el_dia(self) -> None:
        """Una vuelta del planificador (publica para las pruebas)."""
        hoy = hoy_en_negocio(self._clock.now())
        if hoy == self._ultimo_dia:
            return
        try:
            resultado = self._servicio.revisar_programado()
        except Exception as exc:
            logger.error(
                "planificador de reentrenamiento: error inesperado (%s)", type(exc).__name__
            )
            return
        if resultado.en_curso:
            return
        self._ultimo_dia = hoy
        if resultado.resultado is not None:
            logger.info("planificador de reentrenamiento: resultado %s", resultado.resultado.value)

    def _bucle(self) -> None:
        while True:
            self.revisar_si_cambio_el_dia()
            if self._detener.wait(self._intervalo):
                return
