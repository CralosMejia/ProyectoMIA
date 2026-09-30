"""Excel de la lista priorizada con openpyxl, generado en memoria (CU-12).

- Tres hojas: ``top_{K}`` (como maximo K filas), ``cartera_completa`` y ``resumen``.
- RN-12.1: todo ocurre en ``BytesIO``. openpyxl escribe cada hoja en un archivo temporal;
  aqui se sustituye ese paso por un buffer en memoria, asi que no se toca el disco.
- RN-12.2: un texto que empieza por ``=``, ``+``, ``-`` o ``@`` se guarda como texto con el
  prefijo ``'``; ninguna celda es una formula.
- La cedula se guarda siempre como texto (conserva el cero inicial); el correo no se exporta.
- RN-12.3: solo usa la lista guardada (``ListaDetalle``); no ejecuta el modelo.
- Determinista: las propiedades del libro y las fechas de las entradas del zip salen de
  ``creada_en``, asi que la misma lista produce siempre los mismos bytes.
"""

import io
import zipfile
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from openpyxl import Workbook  # type: ignore[import-untyped]  # openpyxl no publica stubs
from openpyxl.cell.cell import (  # type: ignore[import-untyped]  # openpyxl no publica stubs
    ILLEGAL_CHARACTERS_RE,
)
from openpyxl.drawing.spreadsheet_drawing import (  # type: ignore[import-untyped]  # sin stubs
    SpreadsheetDrawing,
)
from openpyxl.worksheet._writer import (  # type: ignore[import-untyped]  # sin stubs
    WorksheetWriter,
)
from openpyxl.writer.excel import ExcelWriter  # type: ignore[import-untyped]  # sin stubs

from app.application.listas.ports import ItemLista, ListaDetalle
from app.domain.common.enums import NivelRiesgo

COLUMNAS: tuple[str, ...] = (
    "Prioridad",
    "Nombre",
    "Celular",
    "Cédula",
    "Plan",
    "Fecha de vencimiento",
    "Dias para vencer",
    "Monto cobrado",
    "Score (indicador de prioridad)",
    "Nivel de riesgo",
    "Factores principales",
    "Estado de la gestion",
    "Campania asignada",
)
SIN_FACTORES = "Sin factores de riesgo destacados"
HOJA_CARTERA = "cartera_completa"
HOJA_RESUMEN = "resumen"
FORMATO_FECHA = "yyyy-mm-dd"
_PREFIJOS_FORMULA = ("=", "+", "-", "@")
_SEPARADOR_FACTORES = "; "


def neutralizar(texto: str) -> str:
    """Texto seguro para Excel: quita caracteres de control y desactiva formulas (RN-12.2)."""
    limpio: str = ILLEGAL_CHARACTERS_RE.sub("", texto)
    return "'" + limpio if limpio.startswith(_PREFIJOS_FORMULA) else limpio


def _utc_sin_zona(instante: datetime) -> datetime:
    return instante.astimezone(UTC).replace(tzinfo=None)


class _ZipDeterminista(zipfile.ZipFile):
    """Zip cuyas entradas llevan siempre la misma fecha (no la hora del sistema)."""

    def __init__(self, destino: io.BytesIO, fecha: datetime) -> None:
        super().__init__(destino, "w", zipfile.ZIP_DEFLATED, allowZip64=True)
        self._fecha = (fecha.year, fecha.month, fecha.day, fecha.hour, fecha.minute, fecha.second)

    def writestr(
        self,
        zinfo_or_arcname: str | zipfile.ZipInfo,
        data: Any,  # noqa: ANN401 - misma firma que ZipFile.writestr (bytes o str)
        compress_type: int | None = None,
        compresslevel: int | None = None,
    ) -> None:
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            info = zinfo_or_arcname
        else:
            info = zipfile.ZipInfo(zinfo_or_arcname, date_time=self._fecha)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
        super().writestr(info, data, compress_type, compresslevel)


class _EscritorEnMemoria(ExcelWriter):  # type: ignore[misc]  # base sin tipos (openpyxl)
    """``ExcelWriter`` que serializa cada hoja en memoria en lugar de un temporal."""

    def write_worksheet(self, ws: Any) -> None:  # noqa: ANN401 - Worksheet de openpyxl sin tipos
        ws._drawing = SpreadsheetDrawing()
        ws._drawing.charts = ws._charts
        ws._drawing.images = ws._images
        writer = WorksheetWriter(ws, out=io.BytesIO())
        writer.write()
        ws._rels = writer._rels
        self._archive.writestr(ws.path[1:], writer.read())
        self.manifest.append(ws)


class ExcelListaOpenpyxl:
    """Implementa ``ExportadorLista``."""

    def generar(self, lista: ListaDetalle) -> bytes:
        creada_en = _utc_sin_zona(lista.creada_en)
        libro = Workbook()
        libro.properties.created = creada_en
        libro.properties.modified = creada_en

        top = libro.active
        top.title = f"top_{lista.top_k}"
        self._escribir_items(top, lista, [i for i in lista.items if i.prioridad <= lista.top_k])
        self._escribir_items(libro.create_sheet(HOJA_CARTERA), lista, list(lista.items))
        self._escribir_resumen(libro.create_sheet(HOJA_RESUMEN), lista)

        destino = io.BytesIO()
        with _ZipDeterminista(destino, creada_en) as archivo:
            _EscritorEnMemoria(libro, archivo).write_data()
        return destino.getvalue()

    @staticmethod
    def _texto(hoja: Any, fila: int, columna: int, valor: str | None) -> None:  # noqa: ANN401 - Worksheet sin tipos
        celda = hoja.cell(row=fila, column=columna)
        if valor is not None:
            celda.value = neutralizar(valor)
            celda.data_type = "s"

    def _escribir_items(self, hoja: Any, lista: ListaDetalle, items: Sequence[ItemLista]) -> None:  # noqa: ANN401 - Worksheet sin tipos
        for columna, nombre in enumerate(COLUMNAS, start=1):
            hoja.cell(row=1, column=columna, value=nombre)
        for fila, item in enumerate(items, start=2):
            hoja.cell(row=fila, column=1, value=item.prioridad)
            self._texto(hoja, fila, 2, item.socio_nombre)
            self._texto(hoja, fila, 3, item.celular)
            self._texto(hoja, fila, 4, item.cedula)
            self._texto(hoja, fila, 5, item.plan.value)
            vence = hoja.cell(row=fila, column=6, value=item.fecha_vencimiento)
            vence.number_format = FORMATO_FECHA
            dias = (item.fecha_vencimiento - lista.fecha_generacion).days
            hoja.cell(row=fila, column=7, value=dias)
            hoja.cell(row=fila, column=8, value=item.monto_cobrado)
            hoja.cell(row=fila, column=9, value=item.score)
            self._texto(hoja, fila, 10, item.nivel_riesgo.value)
            factores = _SEPARADOR_FACTORES.join(item.factores_principales) or SIN_FACTORES
            self._texto(hoja, fila, 11, factores)
            # Estado de la gestion y campania: aun no hay gestiones (CU-08, otro dia).

    @staticmethod
    def _escribir_resumen(hoja: Any, lista: ListaDetalle) -> None:  # noqa: ANN401 - Worksheet sin tipos
        niveles = Counter(item.nivel_riesgo for item in lista.items)
        filas: list[tuple[str, object]] = [
            ("Fecha de generacion", lista.fecha_generacion),
            ("Horizonte (dias)", lista.horizonte_dias),
            ("Top K", lista.top_k),
            ("Version del modelo", f"v{lista.modelo_version}"),
            ("Umbral alto", lista.umbral_alto),
            ("Umbral medio", lista.umbral_medio),
            ("Total en cartera", len(lista.items)),
            ("Dentro del top K", sum(1 for i in lista.items if i.dentro_top_k)),
            *((f"Nivel {n.value}", niveles.get(n, 0)) for n in NivelRiesgo),
        ]
        for numero, (etiqueta, valor) in enumerate(filas, start=1):
            hoja.cell(row=numero, column=1, value=etiqueta)
            celda = hoja.cell(row=numero, column=2, value=valor)
            if numero == 1:
                celda.number_format = FORMATO_FECHA
