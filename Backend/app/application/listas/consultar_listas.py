"""Consultas de listas priorizadas y descarga del Excel (CU-04, CU-05, CU-12).

Solo leen: una lista guardada es una instantanea inmutable con el modelo y los umbrales con
que se genero (RN-04.3, RT-07). La descarga usa la lista guardada y nunca vuelve a ejecutar
el modelo (RN-12.3).
"""

from dataclasses import dataclass
from datetime import date, datetime

from app.application.listas.dtos import ListaPriorizadaDTO, ListaResumenDTO, PrediccionDTO
from app.application.listas.ports import (
    ContextoListas,
    ExportadorLista,
    ListaDetalle,
    ListaResumen,
    UnidadDeTrabajoListas,
)

DIAS_DATOS_ANTIGUOS = 30


@dataclass(frozen=True, slots=True)
class ArchivoLista:
    """Excel generado en memoria y su nombre de descarga (sin datos personales)."""

    contenido: bytes
    nombre_archivo: str


def datos_antiguos(ultima_carga: datetime | None, fecha_generacion: date) -> bool:
    """``True`` si la ultima carga tiene mas de 30 dias respecto a la fecha de generacion."""
    if ultima_carga is None:
        return False
    return (fecha_generacion - ultima_carga.date()).days > DIAS_DATOS_ANTIGUOS


def version_texto(version: int) -> str:
    return f"v{version}"


def advertencia_de(uow: ContextoListas, lista: ListaDetalle) -> bool:
    """Evalua la advertencia con la ultima carga cuya ``fecha_carga <= creada_en``."""
    ultima = uow.cargas.ultima_fecha_carga_hasta(lista.creada_en)
    return datos_antiguos(ultima, lista.fecha_generacion)


def a_dto(lista: ListaDetalle, advertencia: bool) -> ListaPriorizadaDTO:
    return ListaPriorizadaDTO(
        id=lista.id,
        nombre=lista.nombre,
        modelo_version=version_texto(lista.modelo_version),
        fecha_generacion=lista.fecha_generacion,
        creada_en=lista.creada_en,
        horizonte_dias=lista.horizonte_dias,
        top_k=lista.top_k,
        umbral_alto=lista.umbral_alto,
        umbral_medio=lista.umbral_medio,
        advertencia_datos_antiguos=advertencia,
        items=[
            PrediccionDTO(
                prediccion_id=item.prediccion_id,
                prioridad=item.prioridad,
                socio_nombre=item.socio_nombre,
                celular=item.celular,
                cedula=item.cedula,
                plan=item.plan,
                fecha_vencimiento=item.fecha_vencimiento,
                dias_para_vencer=(item.fecha_vencimiento - lista.fecha_generacion).days,
                monto_cobrado=item.monto_cobrado,
                score=item.score,
                nivel_riesgo=item.nivel_riesgo,
                factores_principales=list(item.factores_principales),
                dentro_top_k=item.dentro_top_k,
                gestion_id=item.gestion_id,
                gestion_estado=item.gestion_estado,
                campania_asignada=item.campania_asignada,
            )
            for item in lista.items
        ],
    )


def _a_resumen(resumen: ListaResumen) -> ListaResumenDTO:
    return ListaResumenDTO(
        id=resumen.id,
        nombre=resumen.nombre,
        fecha_generacion=resumen.fecha_generacion,
        creada_en=resumen.creada_en,
        modelo_version=version_texto(resumen.modelo_version),
        horizonte_dias=resumen.horizonte_dias,
        top_k=resumen.top_k,
        total_items=resumen.total_items,
    )


class ConsultarListas:
    """Queries de listas: ``obtener``, ``ultima``, ``listar`` y ``descargar_excel``."""

    def __init__(self, uow: UnidadDeTrabajoListas, exportador: ExportadorLista) -> None:
        self._uow = uow
        self._exportador = exportador

    def obtener(self, lista_id: int) -> ListaPriorizadaDTO | None:
        with self._uow() as uow:
            lista = uow.listas.obtener(lista_id)
            return None if lista is None else a_dto(lista, advertencia_de(uow, lista))

    def ultima(self) -> ListaPriorizadaDTO | None:
        with self._uow() as uow:
            lista = uow.listas.ultima()
            return None if lista is None else a_dto(lista, advertencia_de(uow, lista))

    def listar(self) -> list[ListaResumenDTO]:
        with self._uow() as uow:
            return [_a_resumen(r) for r in uow.listas.listar()]

    def descargar_excel(self, lista_id: int) -> ArchivoLista | None:
        with self._uow() as uow:
            lista = uow.listas.obtener(lista_id)
        if lista is None:
            return None
        return ArchivoLista(
            contenido=self._exportador.generar(lista),
            nombre_archivo=f"lista_{lista.id}_{lista.fecha_generacion.isoformat()}.xlsx",
        )
