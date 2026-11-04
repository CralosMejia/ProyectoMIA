"""Siembra de listas, campanas y gestiones pasadas para grabar el demo en 8081 (R-022/T9).

Parte de una base recien migrada con los libros del perfil ``grabacion`` de
``generar_dataset_demo.py`` (libros hasta el mes 5 anterior a hoy) y usa **solo los casos de
uso de la app** con un reloj fijo por fecha, mes a mes, para los 4 meses cerrados:

1. dia 1 del mes, 10:00 en Ecuador -> ``GenerarLista`` (top 25, horizonte 31);
2. ``CrearGestion`` para el top 25 con una campana sugerida (``SugerirCampanias``);
3. ``RegistrarResultado`` con un reloj posterior al contacto: contactos de 20 dias antes al
   dia siguiente del vencimiento, ofertas, aceptaciones y ``renovo`` segun la plantilla del
   mes siguiente; todas las gestiones quedan cerradas (sin alertas);
4. dia 1 del mes siguiente, 08:00 -> ``ConfirmarCarga`` de la plantilla del mes (CU-01).

Asi cada lista solo ve los datos que existian en su fecha (como en el gimnasio) y el
Dashboard verifica a T+30 con las cargas posteriores. Al final, la lista de hoy con el reloj
del sistema (o el inyectado). No escribe SQL ni salta reglas de dominio.

Guardas: la base debe llamarse ``*_e2e`` (si no, sale 1 sin escribir nada). Idempotente: si
la siembra ya esta completa sale 0 sin duplicar; si la base tiene datos de otra siembra o de
una siembra a medias, sale 1 (vuelva a preparar 8081). La salida son conteos por mes: nunca
nombres, cedulas, celulares, correos ni la URL de la base.

Uso dentro del contenedor ``backend`` de ``mtabolic-e2e`` (lo lanza
``scripts/preparar-8081.*``): ``python - < Backend/scripts/sembrar_grabacion.py``.
"""

import argparse
import hashlib
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.application.campanias.dtos import CampaniaEntradaDTO, PlanCampania
from app.application.campanias.gestionar_campanias import CrearCampania, ListarCampanias
from app.application.campanias.sugerir_campanias import SugerirCampanias
from app.application.cargas.procesar_carga import ConfirmarCarga
from app.application.gestiones.crear_gestion import CrearGestion
from app.application.gestiones.dtos import (
    CrearGestionDTO,
    RegistrarResultadoDTO,
    RespuestaAceptacion,
    RespuestaOfrecimiento,
)
from app.application.gestiones.registrar_resultado import RegistrarResultado
from app.application.listas.consultar_listas import ConsultarListas
from app.application.listas.dtos import GenerarListaDTO, ListaPriorizadaDTO, PrediccionDTO
from app.application.listas.generar_lista import GenerarLista
from app.domain.cargas.validacion import FilaValida, validar_fila
from app.domain.common.clock import Clock
from app.domain.common.enums import NivelRiesgo, Plan, Respuesta
from app.domain.common.exceptions import DomainError
from app.domain.common.fechas import ZONA_NEGOCIO, hoy_en_negocio
from app.domain.gestiones.reglas import fecha_sugerida
from app.infrastructure.cargas.lector_plantilla import LectorPlantillaOpenpyxl
from app.infrastructure.clock.system_clock import SystemClock
from app.infrastructure.exportacion.excel_lista import ExcelListaOpenpyxl
from app.infrastructure.ml.predictor_adoptado import PredictorAdoptado
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.unit_of_work_cargas import SqlAlchemyUnidadDeTrabajoCargas
from app.infrastructure.persistence.unit_of_work_listas import SqlAlchemyUnidadDeTrabajoListas
from app.infrastructure.persistence.unit_of_work_retencion import (
    SqlAlchemyUnidadDeTrabajoRetencion,
)

SEMILLA = "mtabolic-siembra-grabacion-1"
SUFIJO_BASE = "_e2e"
MESES_SEMBRADOS = 4
HORIZONTE = 31
TOP = 25
HORA_LISTA = time(10, 0)
HORA_CARGA = time(8, 0)
VENTANA_RENOVACION = 30
RESPONSABLES = ("Andrea", "Luis", "Carolina", "Pablo")
# Dias entre el contacto y el vencimiento (T - contacto): de 20 antes al dia siguiente.
DIAS_ANTES_DEL_VENCIMIENTO = (20, 18, 16, 15, 13, 11, 10, 9, 8, 6, 5, 4, 3, 2, 1, 0, -1)
CONTACTADOS_POR_CIEN = 85
OFRECIDAS_POR_CIEN = 85
ACEPTADAS_POR_CIEN = 50
PENDIENTES_POR_CIEN = 15
TODOS_LOS_PLANES: list[PlanCampania] = [
    Plan.MENSUAL,
    Plan.TRIMESTRAL,
    Plan.SEMESTRAL,
    Plan.ANUAL,
    Plan.OTRO,
]
TODOS_LOS_NIVELES = [NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO]
CAMPANIAS = (
    CampaniaEntradaDTO(
        nombre="Congela 7 días gratis",
        descripcion="Ofrecer congelar la membresía 7 días sin costo al renovar.",
        niveles_riesgo=[NivelRiesgo.ALTO, NivelRiesgo.MEDIO],
        planes=[Plan.MENSUAL, Plan.TRIMESTRAL],
        prioridad=1,
    ),
    CampaniaEntradaDTO(
        nombre="Trimestral con descuento",
        descripcion="Proponer pasar a plan trimestral con un descuento por renovar a tiempo.",
        niveles_riesgo=TODOS_LOS_NIVELES,
        planes=[Plan.MENSUAL],
        prioridad=2,
    ),
    CampaniaEntradaDTO(
        nombre="Clase de prueba con un amigo",
        descripcion="Invitar al socio a traer a un amigo a una clase de prueba.",
        niveles_riesgo=[NivelRiesgo.MEDIO, NivelRiesgo.BAJO],
        planes=TODOS_LOS_PLANES,
        prioridad=3,
    ),
    CampaniaEntradaDTO(
        nombre="Llamada de bienvenida de vuelta",
        descripcion="Llamar para saber cómo le va y recordarle el vencimiento.",
        niveles_riesgo=TODOS_LOS_NIVELES,
        planes=TODOS_LOS_PLANES,
        prioridad=4,
    ),
)
NOMBRES_CAMPANIAS = frozenset(c.nombre for c in CAMPANIAS)


class SiembraError(Exception):
    """La base o los datos no permiten sembrar (mensaje sin datos personales)."""


class RelojFijo:
    """``Clock`` con un instante fijo; la siembra lo mueve fecha a fecha."""

    def __init__(self, instante: datetime) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante

    def en(self, dia: date, hora: time) -> "RelojFijo":
        self.instante = datetime.combine(dia, hora, tzinfo=ZONA_NEGOCIO).astimezone(UTC)
        return self


@dataclass(frozen=True, slots=True)
class Plantilla:
    mes: date
    ruta: Path
    filas: tuple[FilaValida, ...]


@dataclass(frozen=True, slots=True)
class ResumenMes:
    mes: date
    en_lista: int
    gestiones: int
    contactadas: int
    filas_cargadas: int


# ------------------------------------------------------------------ decisiones deterministas


def _sorteo(modulo: int, *clave: object) -> int:
    texto = "|".join(str(parte) for parte in (SEMILLA, *clave))
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], "big") % modulo


def _primer_dia(dia: date) -> date:
    return dia.replace(day=1)


def _mes_anterior(mes: date) -> date:
    return _primer_dia(mes - timedelta(days=1))


def _mes_siguiente(mes: date) -> date:
    return _primer_dia(mes + timedelta(days=32))


# ------------------------------------------------------------------ datos de entrada


def leer_plantillas(carpeta: Path, hoy: date) -> list[Plantilla]:
    """Plantillas ``Carga AAAA-MM.xlsx`` de los 4 meses cerrados anteriores a ``hoy``."""
    meses: list[date] = []
    mes = _primer_dia(hoy)
    for _ in range(MESES_SEMBRADOS):
        mes = _mes_anterior(mes)
        meses.append(mes)
    plantillas: list[Plantilla] = []
    lector = LectorPlantillaOpenpyxl()
    for mes in sorted(meses):
        ruta = carpeta / f"Carga {mes.year:04d}-{mes.month:02d}.xlsx"
        if not ruta.is_file():
            raise SiembraError(
                f"Falta la plantilla de {mes:%Y-%m}: genere datos-grabacion con la fecha de hoy."
            )
        validas = [validar_fila(f) for f in lector.leer(ruta.read_bytes()).filas]
        filas = tuple(f for f in validas if isinstance(f, FilaValida))
        if len(filas) != len(validas):
            raise SiembraError(f"La plantilla de {mes:%Y-%m} tiene filas con errores.")
        plantillas.append(Plantilla(mes, ruta, filas))
    return plantillas


def _renovo(item: PrediccionDTO, inicios: dict[str, list[date]]) -> bool:
    """``True`` si la plantilla tiene una membresia del socio en ``[T, T + 30]``."""
    hasta = item.fecha_vencimiento + timedelta(days=VENTANA_RENOVACION)
    return any(item.fecha_vencimiento <= d <= hasta for d in inicios.get(item.cedula or "", []))


# ------------------------------------------------------------------ siembra


class Siembra:
    def __init__(self, engine: Engine, reloj: RelojFijo) -> None:
        self._reloj = reloj
        retencion = SqlAlchemyUnidadDeTrabajoRetencion(engine, reloj)
        listas = SqlAlchemyUnidadDeTrabajoListas(engine, reloj)
        self.generar_lista = GenerarLista(listas, PredictorAdoptado(), reloj)
        self.consultar_listas = ConsultarListas(listas, ExcelListaOpenpyxl())
        self.listar_campanias = ListarCampanias(retencion)
        self.crear_campania = CrearCampania(retencion)
        self.sugerir = SugerirCampanias(retencion)
        self.crear_gestion = CrearGestion(retencion, reloj)
        self.registrar = RegistrarResultado(retencion, reloj)
        self.confirmar_carga = ConfirmarCarga(
            LectorPlantillaOpenpyxl(), SqlAlchemyUnidadDeTrabajoCargas(engine, reloj), reloj
        )

    def ya_sembrada(self, hoy: date) -> bool:
        """``True`` si la siembra esta completa; ``SiembraError`` si hay datos ajenos o a medias."""
        propias = {c.nombre for c in self.listar_campanias.ejecutar()} & NOMBRES_CAMPANIAS
        listas = self.consultar_listas.listar()
        if not propias and not listas:
            return False
        completa = propias == NOMBRES_CAMPANIAS and any(
            lista.fecha_generacion == hoy for lista in listas
        )
        if completa and len(listas) == MESES_SEMBRADOS + 1:
            return True
        raise SiembraError(
            "La base ya tiene listas o campanas que no son de una siembra completa: "
            "vuelva a preparar 8081 (preparar-8081 grabacion)."
        )

    def ejecutar(self, plantillas: Sequence[Plantilla], hoy: date) -> list[ResumenMes]:
        campanias = {c.nombre: self.crear_campania.ejecutar(c).id for c in CAMPANIAS}
        inicios: dict[str, list[date]] = {}
        for plantilla in plantillas:
            for fila in plantilla.filas:
                inicios.setdefault(fila.documento, []).append(fila.fecha_inicio)
        # Hasta donde las plantillas dicen si alguien renovo (fin del ultimo mes cargado).
        ultimo_dato = _mes_siguiente(plantillas[-1].mes) - timedelta(days=1)

        resumen: list[ResumenMes] = []
        for plantilla in plantillas:
            self._reloj.en(plantilla.mes, HORA_LISTA)
            lista = self.generar_lista.ejecutar(
                GenerarListaDTO(fecha_referencia=plantilla.mes, horizonte_dias=HORIZONTE, top_k=TOP)
            )
            gestiones, contactadas = self._gestionar(
                lista, campanias, inicios, ultimo_dato, hoy, plantilla.mes
            )
            self._reloj.en(_mes_siguiente(plantilla.mes), HORA_CARGA)
            carga = self.confirmar_carga.ejecutar(plantilla.ruta.read_bytes(), plantilla.ruta.name)
            resumen.append(
                ResumenMes(
                    plantilla.mes, len(lista.items), gestiones, contactadas, carga.filas_guardadas
                )
            )

        self._reloj.en(hoy, HORA_LISTA)
        actual = self.generar_lista.ejecutar(
            GenerarListaDTO(fecha_referencia=hoy, horizonte_dias=HORIZONTE, top_k=TOP)
        )
        resumen.append(ResumenMes(_primer_dia(hoy), len(actual.items), 0, 0, 0))
        return resumen

    def _gestionar(
        self,
        lista: ListaPriorizadaDTO,
        campanias: dict[str, int],
        inicios: dict[str, list[date]],
        ultimo_dato: date,
        hoy: date,
        asignacion: date,
    ) -> tuple[int, int]:
        propias = set(campanias.values())
        gestiones = contactadas = 0
        for item in sorted(lista.items, key=lambda i: i.prioridad):
            if not item.dentro_top_k:
                continue
            clave = (asignacion.isoformat(), item.prioridad)
            sugeridas = [c.id for c in self.sugerir.ejecutar(item.prediccion_id) if c.id in propias]
            campania_id = sugeridas[_sorteo(min(2, len(sugeridas)), "campania", *clave)]
            responsable = RESPONSABLES[_sorteo(len(RESPONSABLES), "responsable", *clave)]
            self._reloj.en(asignacion, HORA_LISTA)
            gestion = self.crear_gestion.ejecutar(
                CrearGestionDTO(
                    prediccion_id=item.prediccion_id,
                    campania_id=campania_id,
                    fecha_seguimiento=fecha_sugerida(asignacion, item.fecha_vencimiento),
                    responsable=responsable,
                )
            )
            gestiones += 1
            resultado, registro = _resultado(item, clave, inicios, ultimo_dato, hoy, asignacion)
            contactadas += int(resultado.contactado)
            self._reloj.en(registro, HORA_LISTA)
            self.registrar.ejecutar(gestion.id, resultado)
        return gestiones, contactadas


def _resultado(
    item: PrediccionDTO,
    clave: tuple[object, ...],
    inicios: dict[str, list[date]],
    ultimo_dato: date,
    hoy: date,
    asignacion: date,
) -> tuple[RegistrarResultadoDTO, date]:
    """Resultado coherente (decision (h) de R-009) y la fecha en que se registra."""
    vence = item.fecha_vencimiento
    contactado = _sorteo(100, "contactado", *clave) < CONTACTADOS_POR_CIEN
    ofrecida: RespuestaOfrecimiento = Respuesta.NO_APLICA
    aceptada: RespuestaAceptacion = Respuesta.NO_APLICA
    fecha_contacto: date | None = None
    if contactado:
        dias = DIAS_ANTES_DEL_VENCIMIENTO[
            _sorteo(len(DIAS_ANTES_DEL_VENCIMIENTO), "anticipacion", *clave)
        ]
        tope = hoy - timedelta(days=1)
        fecha_contacto = min(max(vence - timedelta(days=dias), asignacion), tope)
        if _sorteo(100, "ofrecida", *clave) < OFRECIDAS_POR_CIEN:
            ofrecida = Respuesta.SI
            sorteo = _sorteo(100, "aceptada", *clave)
            if sorteo < ACEPTADAS_POR_CIEN:
                aceptada = Respuesta.SI
            elif sorteo < ACEPTADAS_POR_CIEN + PENDIENTES_POR_CIEN:
                aceptada = Respuesta.PENDIENTE
            else:
                aceptada = Respuesta.NO
        else:
            ofrecida = Respuesta.NO
    verificable = vence + timedelta(days=VENTANA_RENOVACION) <= ultimo_dato
    renovo = _renovo(item, inicios) if verificable else aceptada is Respuesta.SI
    base = fecha_contacto if fecha_contacto is not None else vence
    registro = max(min(base + timedelta(days=1), hoy), fecha_contacto or asignacion)
    return (
        RegistrarResultadoDTO(
            contactado=contactado,
            campania_ofrecida=ofrecida,
            campania_aceptada=aceptada,
            renovo_declarado=Respuesta.SI if renovo else Respuesta.NO,
            fecha_contacto=fecha_contacto,
            observaciones=None,
            responsable=None,
            fecha_seguimiento=None,
        ),
        registro,
    )


# ------------------------------------------------------------------ punto de entrada


def base_permitida(url: str) -> bool:
    """Solo bases ``*_e2e`` (el stack aislado de 8081)."""
    try:
        nombre = make_url(url).database or ""
    except ArgumentError:  # una URL invalida se trata como base no permitida
        return False
    return nombre.endswith(SUFIJO_BASE)


def main(argumentos: Sequence[str] | None = None, clock: Clock | None = None) -> int:
    parser = argparse.ArgumentParser(description="Siembra los datos para grabar el demo.")
    parser.add_argument(
        "--datos",
        type=Path,
        default=Path(os.environ.get("HISTORICO_PATH", "/data/historico")),
        help="carpeta con las plantillas Carga AAAA-MM.xlsx",
    )
    opciones = parser.parse_args(argumentos)
    url = os.environ.get("DATABASE_URL", "")
    if not base_permitida(url):
        print("sembrar_grabacion: la base no termina en _e2e; no se escribe nada.")
        return 1
    hoy = hoy_en_negocio((clock or SystemClock()).now())
    engine = create_database_engine(url)
    try:
        siembra = Siembra(engine, RelojFijo(datetime.combine(hoy, HORA_LISTA, tzinfo=UTC)))
        if siembra.ya_sembrada(hoy):
            print("sembrar_grabacion: ya estaba sembrado; sin cambios.")
            return 0
        plantillas = leer_plantillas(opciones.datos, hoy)
        resumen = siembra.ejecutar(plantillas, hoy)
    except (SiembraError, DomainError) as error:
        # Mensajes pensados para el usuario: sin datos personales ni la URL de la base.
        print(f"sembrar_grabacion: {error}")
        return 1
    finally:
        engine.dispose()
    for fila in resumen:
        print(
            f"{fila.mes:%Y-%m}: lista={fila.en_lista} gestiones={fila.gestiones} "
            f"contactadas={fila.contactadas} filas_cargadas={fila.filas_cargadas}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
