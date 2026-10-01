"""Consulta ``ConsultarEstadoSistema`` (CU-03, flujos alternativos; decision (c) de R-004).

Estado general:

- ``COMPLETADA`` en la base -> ``LISTO``, con el modelo vigente, la ultima carga, la proxima
  fecha de reentrenamiento y si ya se cargaron los datos del mes de negocio actual
  (``datos_mes_cargados``, D6-BE-06; mes segun ``hoy_en_negocio(clock.now())``). En los demas
  estados ``datos_mes_cargados`` es ``None`` y no se consulta.
- ``EN_CURSO`` en la base, o la migracion de este proceso en curso -> ``INICIALIZANDO``.
- ``PENDIENTE`` y la ultima migracion de este proceso termino en ``FALTAN_DATOS`` o
  ``FALLIDA`` -> ``FALTAN_DATOS_HISTORICOS`` (el detalle queda solo en el log tecnico).
- ``PENDIENTE`` sin resultado todavia -> ``INICIALIZANDO``.
"""

from app.application.sistema.dtos import EstadoGeneral, EstadoSistemaDTO, ModeloVigenteDTO
from app.application.sistema.ports import (
    LectorEstadoSistema,
    RegistroMigracion,
    ResultadoMigracion,
)
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoMigracion
from app.domain.common.fechas import hoy_en_negocio, limites_mes_negocio

RESULTADOS_SIN_DATOS = frozenset({ResultadoMigracion.FALTAN_DATOS, ResultadoMigracion.FALLIDA})


def version_publica(version: int) -> str:
    """Version del modelo tal como se muestra: ``1`` -> ``"v1"``."""
    return f"v{version}"


class ConsultarEstadoSistema:
    """Devuelve el estado general del sistema para la pantalla de inicio."""

    def __init__(
        self, lector: LectorEstadoSistema, registro: RegistroMigracion, clock: Clock
    ) -> None:
        self._lector = lector
        self._registro = registro
        self._clock = clock

    def _datos_mes_cargados(self) -> bool:
        hoy = hoy_en_negocio(self._clock.now())
        return self._lector.hay_carga_plantilla_entre(*limites_mes_negocio(hoy.year, hoy.month))

    def ejecutar(self) -> EstadoSistemaDTO:
        estado = self._lector.estado()
        migracion = estado.migracion_historica
        if migracion is EstadoMigracion.COMPLETADA:
            modelo = self._lector.modelo_vigente()
            return EstadoSistemaDTO(
                estado="LISTO",
                migracion_historica=migracion,
                modelo_vigente=None
                if modelo is None
                else ModeloVigenteDTO(
                    version=version_publica(modelo.version),
                    fecha_entrenamiento=modelo.fecha_entrenamiento,
                    ciclos_entrenamiento=modelo.ciclos_entrenamiento,
                ),
                ultima_carga_en=self._lector.ultima_carga_en(),
                proxima_fecha_reentrenamiento=estado.proxima_fecha_reentrenamiento,
                datos_mes_cargados=self._datos_mes_cargados(),
            )

        general: EstadoGeneral = "INICIALIZANDO"
        if (
            migracion is EstadoMigracion.PENDIENTE
            and not self._registro.en_curso
            and self._registro.resultado in RESULTADOS_SIN_DATOS
        ):
            general = "FALTAN_DATOS_HISTORICOS"
        return EstadoSistemaDTO(
            estado=general,
            migracion_historica=migracion,
            proxima_fecha_reentrenamiento=estado.proxima_fecha_reentrenamiento,
        )
