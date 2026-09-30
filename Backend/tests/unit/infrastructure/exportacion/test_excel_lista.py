"""Generador del Excel de la lista priorizada (CU-12, R-008 T1), leyendo el archivo de vuelta.

El Excel muestra lo mismo que la pantalla: hojas "Socios prioritarios a contactar", "Otros
socios por vencer" y "Resumen"; columnas de la tabla (incluidas "Gestión" y "Campaña" desde
R-009 T15), sin celular, score ni monto.
Datos 100 % sinteticos: ningun nombre, celular ni cedula real.
"""

import io
import os
import tempfile
import time
import zipfile
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.application.listas.ports import ExportadorLista, ItemLista, ListaDetalle
from app.domain.common.enums import EstadoGestion, NivelRiesgo, Plan
from app.infrastructure.exportacion.excel_lista import (
    COLUMNAS,
    HOJA_OTROS,
    HOJA_PRIORITARIOS,
    HOJA_RESUMEN,
    SIN_FACTORES,
    ExcelListaOpenpyxl,
)

pytestmark = pytest.mark.unit

CREADA_EN = datetime(2026, 9, 1, 12, 30, 15, tzinfo=UTC)
NIVELES = (NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO)
HOJAS = ["Socios prioritarios a contactar", "Otros socios por vencer", "Resumen"]
ENCABEZADOS = [
    "Prioridad",
    "Nombre",
    "Cédula",
    "Plan",
    "Vence el",
    "Días para vencer",
    "Nivel de riesgo",
    "Motivos principales",
    "Gestión",
    "Campaña",
]
# R-009 (j): "Gestion" y "Campana" dejan de estar prohibidas (sustituye el criterio de R-008 T1).
PROHIBIDOS = (
    "Celular",
    "Score",
    "Monto",
    "Top K",
    "Umbral",
    "Version del modelo",
)
CELULAR = "0987654321"
SCORE = Decimal("0.87654321")
NOMBRE_PELIGROSO = '=HYPERLINK("http://x","y")'


def item(i: int, **cambios: object) -> ItemLista:
    base = ItemLista(
        prediccion_id=100 + i,
        membresia_id=200 + i,
        socio_id=300 + i,
        prioridad=i,
        socio_nombre=f"Socio Sintetico {i:02d}",
        celular=f"09{i:08d}",
        cedula=f"17123456{i:02d}",
        plan=Plan.MENSUAL,
        fecha_vencimiento=date(2026, 9, 1 + i),
        monto_cobrado=Decimal("39.50"),
        score=Decimal("0.9") - Decimal(i) / 100,
        nivel_riesgo=NIVELES[i % 3],
        factores_principales=["Plan: MENSUAL (+0,10)", "Forma de pago: EFECTIVO (+0,02)"],
        dentro_top_k=i <= 3,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # cambios de prueba


def lista(
    items: tuple[ItemLista, ...] | None = None,
    top_k: int = 3,
    nombre: str = "Lista del 31 ago 2026",
) -> ListaDetalle:
    return ListaDetalle(
        id=42,
        modelo_id=7,
        modelo_version=1,
        fecha_generacion=date(2026, 8, 31),
        creada_en=CREADA_EN,
        horizonte_dias=30,
        top_k=top_k,
        umbral_alto=Decimal("0.70000000"),
        umbral_medio=Decimal("0.50000000"),
        items=items if items is not None else tuple(item(i) for i in range(1, 6)),
        nombre=nombre,
    )


def lista_ficticia(nombre: str = "Campaña octubre") -> ListaDetalle:
    """3 items, ``top_k`` 2: uno con factores, otro sin factores, cedula con cero inicial y
    nombre con formula. Se entregan desordenados para comprobar el orden por prioridad."""
    return lista(
        (
            item(
                3,
                dentro_top_k=False,
                nivel_riesgo=NivelRiesgo.BAJO,
                fecha_vencimiento=date(2026, 9, 20),
            ),
            item(
                1,
                dentro_top_k=True,
                nivel_riesgo=NivelRiesgo.ALTO,
                cedula="0912345678",
                socio_nombre=NOMBRE_PELIGROSO,
                celular=CELULAR,
                score=SCORE,
                factores_principales=["Plan: TRIMESTRAL (+0,09)", "Membresías previas: 1 (-0,02)"],
            ),
            item(
                2,
                dentro_top_k=True,
                nivel_riesgo=NivelRiesgo.MEDIO,
                factores_principales=[],
            ),
        ),
        top_k=2,
        nombre=nombre,
    )


def leer(contenido: bytes):  # type: ignore[no-untyped-def]  # openpyxl sin stubs
    return load_workbook(io.BytesIO(contenido))


def valores(hoja) -> list[object]:  # type: ignore[no-untyped-def]  # openpyxl sin stubs
    return [v for fila in hoja.iter_rows(values_only=True) for v in fila if v is not None]


def resumen(contenido: bytes) -> dict[object, object]:
    hoja = leer(contenido)[HOJA_RESUMEN]
    return {fila[0]: fila[1] for fila in hoja.iter_rows(values_only=True)}


def test_exporter_implements_the_port() -> None:
    assert isinstance(ExcelListaOpenpyxl(), ExportadorLista)


def test_generar_sheet_names_and_rows_split_by_dentro_top_k() -> None:
    libro = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))

    assert libro.sheetnames == HOJAS
    assert [HOJA_PRIORITARIOS, HOJA_OTROS, HOJA_RESUMEN] == HOJAS
    assert len(HOJA_PRIORITARIOS) <= 31
    prioritarios = libro[HOJA_PRIORITARIOS]
    otros = libro[HOJA_OTROS]
    assert prioritarios.max_row == 1 + 2
    assert otros.max_row == 1 + 1
    assert [prioritarios.cell(row=r, column=1).value for r in (2, 3)] == [1, 2]
    assert otros["A2"].value == 3


def test_generar_all_inside_top_leaves_other_sheet_with_only_headers() -> None:
    items = tuple(item(i, dentro_top_k=True) for i in range(1, 4))
    libro = leer(ExcelListaOpenpyxl().generar(lista(items, top_k=25)))

    assert libro[HOJA_PRIORITARIOS].max_row == 1 + 3
    otros = libro[HOJA_OTROS]
    assert otros.max_row == 1
    assert [c.value for c in otros[1]] == ENCABEZADOS


def test_generar_headers_are_exactly_the_screen_columns_in_both_sheets() -> None:
    libro = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))

    assert list(COLUMNAS) == ENCABEZADOS
    for nombre in (HOJA_PRIORITARIOS, HOJA_OTROS):
        assert [c.value for c in libro[nombre][1]] == ENCABEZADOS


def test_generar_no_cell_contains_forbidden_terms_nor_phone_or_score() -> None:
    libro = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))

    for hoja in libro.worksheets:
        for valor in valores(hoja):
            texto = str(valor)
            assert not any(p.lower() in texto.lower() for p in PROHIBIDOS), texto
            assert CELULAR not in texto
            assert str(SCORE) not in texto
            assert valor != SCORE


def test_generar_row_values_match_the_screen() -> None:
    hoja = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))[HOJA_PRIORITARIOS]

    fila = [c.value for c in hoja[2]]
    assert fila[0] == 1
    assert fila[1] == "'" + NOMBRE_PELIGROSO
    assert fila[2] == "0912345678"
    assert fila[3] == "MENSUAL"
    assert fila[4].date() == date(2026, 9, 2)
    assert fila[5] == 2  # vencimiento - fecha_generacion
    assert fila[6] == "Alto"
    assert fila[7] == "Plan: TRIMESTRAL; Membresías previas: 1"
    segunda = [c.value for c in hoja[3]]
    assert segunda[6] == "Medio"
    assert segunda[7] == SIN_FACTORES
    assert SIN_FACTORES == "Sin factores de riesgo destacados"
    otros = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))[HOJA_OTROS]
    assert otros["G2"].value == "Bajo"
    assert otros["F2"].value == 20


def test_generar_gestion_and_campania_columns_use_the_screen_texts() -> None:
    items = (
        item(1),
        item(
            2,
            gestion_id=9,
            gestion_estado=EstadoGestion.PENDIENTE,
            campania_asignada="Ejemplo: Renovación anticipada",
        ),
        item(3, gestion_id=10, gestion_estado=EstadoGestion.CERRADA),
        item(4, gestion_id=11, gestion_estado=EstadoGestion.PENDIENTE, dentro_top_k=False),
    )
    libro = leer(ExcelListaOpenpyxl().generar(lista(items)))
    hoja = libro[HOJA_PRIORITARIOS]

    assert [(hoja[f"I{f}"].value, hoja[f"J{f}"].value) for f in (2, 3, 4)] == [
        ("Sin gestión", "—"),
        ("Pendiente", "Ejemplo: Renovación anticipada"),
        ("Cerrada", "Sin campaña"),
    ]
    assert hoja.max_column == 10
    otros = libro[HOJA_OTROS]
    assert (otros["I2"].value, otros["J2"].value) == ("Pendiente", "Sin campaña")


def test_generar_campaign_name_with_formula_is_neutralized_text() -> None:
    items = (
        item(
            1,
            gestion_id=9,
            gestion_estado=EstadoGestion.PENDIENTE,
            campania_asignada="=SUM(1)",
        ),
    )
    hoja = leer(ExcelListaOpenpyxl().generar(lista(items)))[HOJA_PRIORITARIOS]

    assert hoja["J2"].value == "'=SUM(1)"
    assert hoja["J2"].data_type == "s"


def test_generar_vence_el_is_a_date_with_dd_mm_yyyy_format() -> None:
    hoja = leer(ExcelListaOpenpyxl().generar(lista_ficticia()))[HOJA_PRIORITARIOS]

    assert hoja["E2"].is_date
    assert hoja["E2"].number_format == "dd/mm/yyyy"


def test_generar_cedula_is_text_with_leading_zero_and_none_is_empty() -> None:
    items = (item(1, cedula="0912345678"), item(2, cedula=None))
    hoja = leer(ExcelListaOpenpyxl().generar(lista(items)))[HOJA_PRIORITARIOS]

    assert hoja["C2"].value == "0912345678"
    assert hoja["C2"].data_type == "s"
    assert hoja["C3"].value is None


@pytest.mark.parametrize("peligroso", ['=HYPERLINK("x")', "+5+5", "-2+3", "@SUM(A1)"])
def test_generar_neutralizes_formulas_with_quote_prefix(peligroso: str) -> None:
    items = (item(1, socio_nombre=peligroso, cedula=peligroso, factores_principales=[peligroso]),)
    contenido = ExcelListaOpenpyxl().generar(lista(items, nombre=peligroso))

    libro = leer(contenido)
    hoja = libro[HOJA_PRIORITARIOS]
    assert hoja["B2"].value == "'" + peligroso
    assert hoja["B2"].data_type == "s"
    assert hoja["C2"].value == "'" + peligroso
    assert hoja["H2"].value.startswith("'")
    assert libro[HOJA_RESUMEN]["B1"].value == "'" + peligroso
    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
        for nombre in archivo.namelist():
            if nombre.startswith("xl/worksheets/"):
                assert b"<f>" not in archivo.read(nombre)
                assert b"<f " not in archivo.read(nombre)


def test_generar_summary_has_friendly_labels_and_values() -> None:
    contenido = ExcelListaOpenpyxl().generar(lista_ficticia())
    hoja = leer(contenido)[HOJA_RESUMEN]

    etiquetas = [fila[0] for fila in hoja.iter_rows(values_only=True)]
    assert etiquetas == [
        "Nombre de la lista",
        "Fecha de la lista",
        "Vencen hasta",
        "Socios prioritarios a contactar",
        "Otros socios por vencer",
        "Total de socios por vencer",
        "Riesgo alto",
        "Riesgo medio",
        "Riesgo bajo",
    ]
    datos = resumen(contenido)
    assert datos["Nombre de la lista"] == "Campaña octubre"
    assert datos["Fecha de la lista"].date() == date(2026, 8, 31)
    assert datos["Vencen hasta"].date() == date(2026, 9, 30)
    assert hoja["B2"].number_format == "dd/mm/yyyy"
    assert hoja["B3"].number_format == "dd/mm/yyyy"
    assert datos["Socios prioritarios a contactar"] == 2
    assert datos["Otros socios por vencer"] == 1
    assert datos["Total de socios por vencer"] == 3
    assert (datos["Riesgo alto"], datos["Riesgo medio"], datos["Riesgo bajo"]) == (1, 1, 1)


def test_generar_summary_name_with_formula_is_neutralized_text() -> None:
    contenido = ExcelListaOpenpyxl().generar(lista_ficticia(nombre="=SUM(1)"))
    celda = leer(contenido)[HOJA_RESUMEN]["B1"]

    assert celda.value == "'=SUM(1)"
    assert celda.data_type == "s"


def test_generar_same_list_produces_identical_bytes_with_properties_from_creada_en(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exportador = ExcelListaOpenpyxl()
    primero = exportador.generar(lista_ficticia())
    # Otra hora del sistema: ni el zip ni openpyxl pueden colarla en el resultado.
    monkeypatch.setattr(time, "time", lambda: 1_000_000_000.0)
    segundo = exportador.generar(lista_ficticia())

    assert primero == segundo
    libro = leer(primero)
    assert libro.properties.created == datetime(2026, 9, 1, 12, 30, 15)  # noqa: DTZ001 - openpyxl devuelve UTC sin zona
    assert libro.properties.modified == datetime(2026, 9, 1, 12, 30, 15)  # noqa: DTZ001 - openpyxl devuelve UTC sin zona
    with zipfile.ZipFile(io.BytesIO(primero)) as archivo:
        assert {i.date_time for i in archivo.infolist()} == {(2026, 9, 1, 12, 30, 14)}


def test_generar_different_creada_en_changes_the_bytes() -> None:
    exportador = ExcelListaOpenpyxl()
    otra = replace(lista(), creada_en=datetime(2026, 9, 2, 8, 0, tzinfo=UTC))

    assert exportador.generar(lista()) != exportador.generar(otra)


def test_generar_in_memory_without_temporary_files(monkeypatch: pytest.MonkeyPatch) -> None:
    import openpyxl.worksheet._writer as escritor

    def prohibido(*_: object, **__: object) -> str:
        raise AssertionError("no se deben crear archivos temporales")

    monkeypatch.setattr(escritor, "create_temporary_file", prohibido)
    directorio = Path(tempfile.gettempdir())
    antes = set(os.listdir(directorio))

    contenido = ExcelListaOpenpyxl().generar(lista())

    assert contenido.startswith(b"PK")
    assert set(os.listdir(directorio)) - antes == set()


def test_generar_empty_list_is_valid() -> None:
    contenido = ExcelListaOpenpyxl().generar(lista(()))
    libro = leer(contenido)

    assert libro[HOJA_PRIORITARIOS].max_row == 1
    assert libro[HOJA_OTROS].max_row == 1
    assert resumen(contenido)["Total de socios por vencer"] == 0


def test_generar_never_exports_correo() -> None:
    libro = leer(ExcelListaOpenpyxl().generar(lista()))

    for hoja in libro.worksheets:
        assert not any("correo" in str(v).lower() or "@" in str(v) for v in valores(hoja))
