"""Casos de uso de la carga por plantilla (CU-01): ``PrevisualizarCarga`` y ``ConfirmarCarga``.

Ambos comparten ``_analizar`` = leer -> validar -> consultar -> planificar, asi la confirmacion
vuelve a validar el archivo completo en el servidor (no hay estado entre vista previa y
confirmacion).

- Vista previa: solo lecturas; nunca escribe ni hace ``commit``.
- Confirmacion (decision (j) de R-007): toma el bloqueo exclusivo de cargas **antes** de
  consultar duplicados y escribe todo (socios nuevos, cedulas asignadas, carga y membresias)
  en **una** transaccion con un solo ``commit`` al final: todo o nada. Dos confirmaciones del
  mismo archivo en paralelo se serializan y la segunda ve todas las filas duplicadas.
- Conteos (decision (a)): ``filas_validas`` incluye las duplicadas; nuevas = validas -
  duplicadas = ``filas_guardadas``; ``puede_confirmar`` = sin errores y al menos una nueva.
- Membresia guardada (decision (i)): ``origen=PLANTILLA``, ``fecha_actividad = fecha_inicio``,
  ``inicio_aproximado=False``; la carga ``tipo=PLANTILLA`` con ``fecha_carga`` del reloj.
- La carga no dispara ningun entrenamiento (RN-01.11).

Los logs solo llevan conteos: nunca nombres, cedulas, celulares ni correos.
"""

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.application.cargas.dtos import CargaDTO, ErrorFilaDTO, VistaPreviaCargaDTO
from app.application.cargas.ports import (
    ConsultasCarga,
    ContextoCargas,
    LectorPlantilla,
    UnidadDeTrabajoCargas,
)
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.domain.cargas.enlace import PlanCarga, planificar
from app.domain.cargas.validacion import ErrorFila, FilaValida, validar_fila
from app.domain.common.clock import Clock
from app.domain.common.enums import EstadoMigracion, OrigenMembresia, TipoCarga
from app.domain.common.exceptions import DomainError

logger = logging.getLogger(__name__)

MENSAJE_CON_ERRORES = "Hay filas con error; corrija el archivo y vuelva a subirlo."
MENSAJE_SIN_FILAS_NUEVAS = "El archivo no tiene filas nuevas para guardar."
MENSAJE_MIGRACION_NO_COMPLETADA = "La migracion del historico aun no se ha completado."

LONGITUD_MAXIMA_NOMBRE_ARCHIVO = 255
NOMBRE_ARCHIVO_POR_DEFECTO = "plantilla.xlsx"
_SEPARADORES_RUTA = re.compile(r"[\\/]")


class CargaConErroresError(DomainError):
    """Se intento confirmar un archivo con al menos una fila con error (-> 422)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_CON_ERRORES)


class CargaSinFilasNuevasError(DomainError):
    """El archivo no tiene filas nuevas (vacio o todo duplicado) (-> 422)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_SIN_FILAS_NUEVAS)


class MigracionNoCompletadaError(DomainError):
    """La migracion historica no esta ``COMPLETADA`` (-> 409)."""

    def __init__(self) -> None:
        super().__init__(MENSAJE_MIGRACION_NO_COMPLETADA)


@dataclass(frozen=True, slots=True)
class _ArchivoValidado:
    """Resultado de leer y validar el archivo (sin tocar la base de datos)."""

    filas_leidas: int
    validas: tuple[FilaValida, ...]
    errores: tuple[ErrorFila, ...]


@dataclass(frozen=True, slots=True)
class _Analisis:
    archivo: _ArchivoValidado
    plan: PlanCarga

    @property
    def filas_nuevas(self) -> int:
        return len(self.plan.filas_nuevas)

    @property
    def puede_confirmar(self) -> bool:
        return not self.archivo.errores and self.filas_nuevas > 0


def nombre_base(nombre_archivo: str | None) -> str:
    """Solo el nombre base del archivo (sin ruta), recortado a 255 caracteres (decision (g))."""
    base = _SEPARADORES_RUTA.split(nombre_archivo or "")[-1].strip()
    return (base or NOMBRE_ARCHIVO_POR_DEFECTO)[:LONGITUD_MAXIMA_NOMBRE_ARCHIVO]


def _validar(lector: LectorPlantilla, contenido: bytes) -> _ArchivoValidado:
    plantilla = lector.leer(contenido)
    validas: list[FilaValida] = []
    errores: list[ErrorFila] = []
    for fila in plantilla.filas:
        resultado = validar_fila(fila)
        if isinstance(resultado, FilaValida):
            validas.append(resultado)
        else:
            errores.extend(resultado)
    return _ArchivoValidado(len(plantilla.filas), tuple(validas), tuple(errores))


def _planificar(consultas: ConsultasCarga, validas: Sequence[FilaValida]) -> PlanCarga:
    """Consulta socios y claves existentes (una consulta por tipo) y planifica."""
    por_cedula = consultas.socios_por_cedulas({f.documento for f in validas})
    nombres = {f.nombre_normalizado for f in validas if f.documento not in por_cedula}
    candidatos = consultas.socios_sin_cedula_por_nombres(nombres)
    socio_ids = set(por_cedula.values())
    for ids in candidatos.values():
        socio_ids.update(ids)
    claves = consultas.claves_existentes(socio_ids)
    return planificar(validas, por_cedula, candidatos, claves)


def _exigir_migracion_completada(contexto: ContextoCargas) -> None:
    if contexto.estado.obtener().migracion_historica is not EstadoMigracion.COMPLETADA:
        raise MigracionNoCompletadaError()


def _vista_previa(analisis: _Analisis) -> VistaPreviaCargaDTO:
    vencimientos = [f.fecha_vencimiento for f in analisis.archivo.validas]
    return VistaPreviaCargaDTO(
        filas_leidas=analisis.archivo.filas_leidas,
        filas_validas=len(analisis.archivo.validas),
        filas_con_error=len({e.fila for e in analisis.archivo.errores}),
        filas_duplicadas=analisis.plan.filas_duplicadas,
        vencimiento_desde=min(vencimientos, default=None),
        vencimiento_hasta=max(vencimientos, default=None),
        errores=[
            ErrorFilaDTO(fila=e.fila, columna=e.columna, motivo=e.motivo)
            for e in analisis.archivo.errores
        ],
        puede_confirmar=analisis.puede_confirmar,
    )


class PrevisualizarCarga:
    """Query de CU-01: valida el archivo y devuelve la vista previa, sin guardar nada."""

    def __init__(self, lector: LectorPlantilla, uow: UnidadDeTrabajoCargas) -> None:
        self._lector = lector
        self._uow = uow

    def ejecutar(self, contenido: bytes) -> VistaPreviaCargaDTO:
        archivo = _validar(self._lector, contenido)
        with self._uow() as contexto:
            _exigir_migracion_completada(contexto)
            analisis = _Analisis(archivo, _planificar(contexto.consultas, archivo.validas))
        return _vista_previa(analisis)


class ConfirmarCarga:
    """Command de CU-01: revalida el archivo y lo guarda completo en una transaccion."""

    def __init__(self, lector: LectorPlantilla, uow: UnidadDeTrabajoCargas, clock: Clock) -> None:
        self._lector = lector
        self._uow = uow
        self._clock = clock

    def ejecutar(self, contenido: bytes, nombre_archivo: str | None) -> CargaDTO:
        archivo = _validar(self._lector, contenido)
        nombre = nombre_base(nombre_archivo)
        with self._uow() as contexto:
            _exigir_migracion_completada(contexto)
            if archivo.errores:
                raise CargaConErroresError()
            contexto.bloquear()
            analisis = _Analisis(archivo, _planificar(contexto.consultas, archivo.validas))
            if not analisis.puede_confirmar:
                raise CargaSinFilasNuevasError()
            resultado = self._guardar(contexto, analisis, nombre)
            contexto.commit()
        logger.info(
            "carga de plantilla guardada: id=%d filas_leidas=%d guardadas=%d duplicadas=%d "
            "socios_enlazados=%d",
            resultado.id,
            resultado.filas_leidas,
            resultado.filas_guardadas,
            resultado.filas_duplicadas,
            resultado.socios_enlazados,
        )
        return resultado

    def _guardar(self, contexto: ContextoCargas, analisis: _Analisis, nombre: str) -> CargaDTO:
        plan = analisis.plan
        escritura = contexto.escritura
        ids_nuevos = escritura.crear_socios(
            [
                NuevoSocio(
                    cedula=s.cedula,
                    nombre=s.nombre,
                    nombre_normalizado=s.nombre_normalizado,
                    celular=s.celular,
                    correo=s.correo,
                )
                for s in plan.socios_nuevos
            ]
        )
        if len(ids_nuevos) != len(plan.socios_nuevos):
            raise RuntimeError("La escritura debe devolver un id por socio nuevo.")
        for asignacion in plan.cedulas_asignadas:
            escritura.asignar_cedula(
                asignacion.socio_id, asignacion.cedula, asignacion.celular, asignacion.correo
            )

        fecha_carga = self._clock.now()
        carga = NuevaCarga(
            tipo=TipoCarga.PLANTILLA,
            fecha_carga=fecha_carga,
            nombre_archivo=nombre,
            filas_leidas=analisis.archivo.filas_leidas,
            filas_guardadas=analisis.filas_nuevas,
            filas_duplicadas=plan.filas_duplicadas,
            socios_enlazados=plan.socios_enlazados,
        )
        carga_id = escritura.crear_carga(carga)

        membresias: list[NuevaMembresia] = []
        for destino in plan.filas_nuevas:
            if destino.socio_id is not None:
                socio_id = destino.socio_id
            elif destino.socio_nuevo is not None:
                socio_id = ids_nuevos[destino.socio_nuevo]
            else:
                raise RuntimeError("Cada fila planificada debe tener un socio.")
            fila = destino.fila
            membresias.append(
                NuevaMembresia(
                    socio_id=socio_id,
                    carga_id=carga_id,
                    plan=fila.plan,
                    forma_pago=fila.forma_pago,
                    origen=OrigenMembresia.PLANTILLA,
                    inicio_aproximado=False,
                    fecha_actividad=fila.fecha_inicio,
                    estado_registro=fila.estado_registro,
                    fecha_inicio=fila.fecha_inicio,
                    fecha_vencimiento=fila.fecha_vencimiento,
                    monto_facturado=fila.monto_facturado,
                    monto_cobrado=fila.monto_cobrado,
                    asistencias=fila.asistencias,
                    observaciones=fila.observaciones,
                    referencia_origen=None,
                    plan_original=fila.plan_original,
                    forma_pago_original=fila.forma_pago_original,
                )
            )
        escritura.insertar_membresias(membresias)

        return CargaDTO(
            id=carga_id,
            fecha_carga=fecha_carga,
            nombre_archivo=nombre,
            filas_leidas=carga.filas_leidas,
            filas_guardadas=carga.filas_guardadas,
            filas_duplicadas=carga.filas_duplicadas,
            socios_enlazados=carga.socios_enlazados,
            avisos_enlace=list(plan.avisos),
        )
