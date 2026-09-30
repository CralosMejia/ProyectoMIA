"""Consultas de listas (obtener, ultima, listar, advertencia y Excel) con dobles en memoria.

Aislamiento entre usuarios: NO APLICA (RT-12, sin login; acceso por IP, CU-00).
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.listas.consultar_listas import ConsultarListas, a_dto, datos_antiguos
from app.application.listas.dtos import GenerarListaDTO, PrediccionDTO
from app.application.listas.generar_lista import GenerarLista
from app.application.listas.ports import ListaDetalle
from app.domain.common.enums import EstadoGestion, NivelRiesgo
from tests.unit.application.listas.dobles import (
    Almacen,
    PredictorPorMonto,
    RelojFijo,
    membresia,
    modelo,
    unidad_de_trabajo,
)

pytestmark = pytest.mark.unit

FECHA = date(2026, 8, 31)


class ExportadorFalso:
    def __init__(self) -> None:
        self.listas: list[ListaDetalle] = []

    def generar(self, lista: ListaDetalle) -> bytes:
        self.listas.append(lista)
        return f"xlsx-{lista.id}-v{lista.modelo_version}".encode()


def almacen_con_socios() -> Almacen:
    return Almacen(
        membresias=[
            membresia(1, 1, date(2026, 8, 10), date(2026, 9, 10), monto=Decimal("80")),
            membresia(2, 2, date(2026, 8, 20), date(2026, 9, 20), monto=Decimal("60")),
            membresia(3, 3, date(2026, 8, 25), date(2026, 9, 25), monto=Decimal("30")),
        ],
        modelos=[modelo(11, 1)],
        cargas=[datetime(2026, 7, 1, 10, 0, tzinfo=UTC)],
    )


def generar(almacen: Almacen, fecha: date = FECHA, top_k: int = 2) -> int:
    caso = GenerarLista(unidad_de_trabajo(almacen), PredictorPorMonto(), almacen.reloj)
    return caso.ejecutar(GenerarListaDTO(fecha_referencia=fecha, top_k=top_k)).id


def consultas(almacen: Almacen, exportador: ExportadorFalso | None = None) -> ConsultarListas:
    return ConsultarListas(unidad_de_trabajo(almacen), exportador or ExportadorFalso())


def test_obtener_after_new_model_keeps_original_levels_and_version() -> None:
    almacen = almacen_con_socios()
    lista_id = generar(almacen)
    almacen.modelos.append(modelo(12, 2, alto="0.10000000", medio="0.05000000"))

    lista = consultas(almacen).obtener(lista_id)

    assert lista is not None
    assert lista.modelo_version == "v1"
    assert lista.umbral_alto == Decimal("0.70000000")
    assert [i.nivel_riesgo for i in lista.items] == [
        NivelRiesgo.ALTO,
        NivelRiesgo.MEDIO,
        NivelRiesgo.BAJO,
    ]


def test_obtener_maps_every_field_of_the_contract() -> None:
    almacen = almacen_con_socios()
    lista_id = generar(almacen)

    lista = consultas(almacen).obtener(lista_id)

    assert lista is not None
    assert lista.id == lista_id
    assert lista.fecha_generacion == FECHA
    assert lista.creada_en == almacen.reloj.now()
    assert (lista.horizonte_dias, lista.top_k) == (30, 2)
    item = lista.items[0]
    assert item.prediccion_id >= 1
    assert item.dias_para_vencer == 10
    assert item.monto_cobrado == Decimal("80")
    assert item.gestion_estado is None
    assert item.campania_asignada is None


def test_obtener_unknown_id_returns_none() -> None:
    assert consultas(almacen_con_socios()).obtener(999) is None


def test_ultima_without_lists_returns_none_and_with_lists_returns_latest() -> None:
    almacen = almacen_con_socios()
    assert consultas(almacen).ultima() is None

    generar(almacen)
    segunda = generar(almacen, fecha=date(2026, 9, 1))

    ultima = consultas(almacen).ultima()
    assert ultima is not None
    assert ultima.id == segunda


def test_listar_returns_summaries_most_recent_first() -> None:
    almacen = almacen_con_socios()
    primera = generar(almacen)
    segunda = generar(almacen, top_k=1)

    resumenes = consultas(almacen).listar()

    assert [r.id for r in resumenes] == [segunda, primera]
    assert resumenes[0].modelo_version == "v1"
    assert resumenes[0].top_k == 1
    assert resumenes[0].total_items == 3
    assert resumenes[0].fecha_generacion == FECHA


def test_obtener_warning_uses_last_load_not_after_creada_en() -> None:
    almacen = almacen_con_socios()  # ultima carga 2026-07-01, 61 dias antes de la fecha
    almacen.reloj = RelojFijo(datetime(2026, 8, 31, 20, 0, tzinfo=UTC))
    lista_id = generar(almacen)
    # Una carga posterior a la creacion de la lista no cambia la advertencia guardada.
    almacen.cargas.append(datetime(2026, 9, 5, 12, 0, tzinfo=UTC))

    lista = consultas(almacen).obtener(lista_id)

    assert lista is not None
    assert lista.advertencia_datos_antiguos is True


@pytest.mark.parametrize(
    ("carga", "esperado"),
    [
        (datetime(2026, 7, 1, 10, 0, tzinfo=UTC), True),  # 61 dias
        (datetime(2026, 8, 1, 10, 0, tzinfo=UTC), False),  # 30 dias exactos
        (datetime(2026, 7, 31, 23, 59, tzinfo=UTC), True),  # 31 dias
        (None, False),
    ],
)
def test_datos_antiguos_more_than_30_days_is_true(carga: datetime | None, esperado: bool) -> None:
    assert datos_antiguos(carga, FECHA) is esperado


def test_descargar_excel_uses_saved_list_without_running_the_model() -> None:
    almacen = almacen_con_socios()
    lista_id = generar(almacen)
    exportador = ExportadorFalso()
    caso = consultas(almacen, exportador)

    primera = caso.descargar_excel(lista_id)
    almacen.modelos.append(modelo(12, 2))
    segunda = caso.descargar_excel(lista_id)

    assert primera is not None
    assert segunda is not None
    assert primera.contenido == segunda.contenido == f"xlsx-{lista_id}-v1".encode()
    assert primera.nombre_archivo == f"lista_{lista_id}_2026-08-31.xlsx"
    assert almacen.commits == 1  # solo la generacion escribio


def test_descargar_excel_unknown_id_returns_none() -> None:
    exportador = ExportadorFalso()

    assert consultas(almacen_con_socios(), exportador).descargar_excel(5) is None
    assert exportador.listas == []


def test_obtener_copies_cedula_as_text_and_none_as_null() -> None:
    almacen = almacen_con_socios()
    almacen.membresias.append(
        membresia(4, 4, date(2026, 8, 26), date(2026, 9, 26), monto=Decimal("20"))
    )
    lista_id = generar(almacen, top_k=5)
    detalle = unidad_de_trabajo(almacen)
    with detalle() as uow:
        guardada = uow.listas.obtener(lista_id)
    assert guardada is not None
    sin_cedula = replace(guardada.items[-1], cedula=None)
    con_cero = replace(guardada.items[0], cedula="0912345678")

    dto = a_dto(replace(guardada, items=(con_cero, sin_cedula)), advertencia=False)

    assert dto.items[0].cedula == "0912345678"
    assert dto.items[1].cedula is None
    datos = dto.model_dump(mode="json")
    assert datos["items"][0]["cedula"] == "0912345678"
    assert datos["items"][1]["cedula"] is None
    assert all("correo" not in item for item in datos["items"])


def test_prediccion_dto_schema_has_cedula_and_no_correo() -> None:
    propiedades = PrediccionDTO.model_json_schema()["properties"]

    assert "correo" not in propiedades
    assert {t.get("type") for t in propiedades["cedula"]["anyOf"]} == {"string", "null"}


def test_a_dto_maps_gestion_of_each_item() -> None:
    """R-009 T13: gestion pendiente con campana, item sin gestion y gestion sin campana."""
    almacen = almacen_con_socios()
    lista_id = generar(almacen, top_k=5)
    with unidad_de_trabajo(almacen)() as uow:
        guardada = uow.listas.obtener(lista_id)
    assert guardada is not None
    assert len(guardada.items) >= 3
    pendiente = replace(
        guardada.items[0],
        gestion_id=9,
        gestion_estado=EstadoGestion.PENDIENTE,
        campania_asignada="Ejemplo: Renovación anticipada",
    )
    sin_gestion = guardada.items[1]
    sin_campania = replace(guardada.items[2], gestion_id=10, gestion_estado=EstadoGestion.CERRADA)

    dto = a_dto(replace(guardada, items=(pendiente, sin_gestion, sin_campania)), advertencia=False)

    items = dto.model_dump(mode="json")["items"]
    assert [(i["gestion_id"], i["gestion_estado"], i["campania_asignada"]) for i in items] == [
        (9, "PENDIENTE", "Ejemplo: Renovación anticipada"),
        (None, None, None),
        (10, "CERRADA", None),
    ]


def test_prediccion_dto_schema_has_nullable_gestion_id() -> None:
    propiedades = PrediccionDTO.model_json_schema()["properties"]

    assert {t.get("type") for t in propiedades["gestion_id"]["anyOf"]} == {"integer", "null"}
