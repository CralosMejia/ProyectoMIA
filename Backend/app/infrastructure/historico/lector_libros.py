"""Lector de los libros historicos ``Control Gym <anio>.xlsx`` (notebook MVP, secciones 2.2-3.4).

Adapta ``buscar_archivo`` (anio en el nombre), ``clasificar_hojas`` (solo hojas cuyo nombre es
un mes), ``encontrar_fila_encabezado`` (primera de las 10 primeras filas con ``CEDULA`` y
``NOMBRE``), ``buscar_indice_columna`` y ``leer_hoja_mensual``. Entrega valores **crudos** de
celda: ``NaN``/``NaT`` -> ``None``, ``Timestamp`` -> ``datetime``, numeros tal cual; la
conversion a ``date``/``Decimal`` es del dominio. Se lee con ``header=None`` y
``dtype=object`` para que pandas no infiera tipos (una cedula nunca llega como ``float``).

No escribe en disco ni en logs; los errores solo nombran el libro y la hoja (RN-03.5). Los
``UserWarning`` de ``openpyxl`` citan coordenada y valor de celda: se silencian solo durante la
lectura de cada libro (T6-OBS-1).
"""

import math
import re
import warnings
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]  # pandas no publica tipos (sin pandas-stubs)

from app.application.historial.ports import LibroLeido, LibrosLeidos
from app.domain.historico.conversiones import normalizar_texto_encabezado
from app.domain.historico.errores import HojaSinEncabezadoError, LibroSinAnioError
from app.domain.historico.registro import FilaCruda
from app.infrastructure.historico.alias_columnas import ALIAS_COLUMNAS, MESES

MAX_FILAS_ENCABEZADO = 10
_ANIO = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


def anio_del_libro(ruta: Path) -> int:
    """Anio tomado del nombre del archivo (``buscar_archivo`` busca ``*Control*Gym*<anio>*``)."""
    hallado = _ANIO.search(ruta.stem)
    if hallado is None:
        raise LibroSinAnioError(ruta.name)
    return int(hallado.group(1))


def mes_de_hoja(hoja: str) -> int | None:
    """Numero de mes si el nombre recortado y en mayusculas es un mes (``clasificar_hojas``)."""
    return MESES.get(hoja.strip().upper())


def _crudo(valor: object) -> object:
    """Celda sin tipos de pandas/numpy: vacios -> ``None``, ``Timestamp`` -> ``datetime``."""
    if valor is None or valor is pd.NaT:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    if isinstance(valor, pd.Timestamp):
        convertido: datetime = valor.to_pydatetime()
        return convertido
    item = getattr(valor, "item", None)
    if callable(item) and not isinstance(valor, str | bytes):
        nativo: object = item()  # escalar de numpy -> tipo nativo
        return _crudo(nativo)
    return valor


def _cedula_cruda(valor: object) -> object:
    """Una cedula numerica entera nunca sale como ``float`` (``1712345678.0`` -> ``1712345678``)."""
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


def _fila_encabezado(filas: Sequence[Sequence[object]]) -> int | None:
    for i in range(min(MAX_FILAS_ENCABEZADO, len(filas))):
        texto_fila = " | ".join(normalizar_texto_encabezado(v) for v in filas[i])
        if "CEDULA" in texto_fila and "NOMBRE" in texto_fila:
            return i
    return None


def _indice_columna(encabezados: Sequence[str], aliases: Sequence[str]) -> int | None:
    """Primera columna cuyo titulo contiene alguno de los alias (``buscar_indice_columna``)."""
    for i, encabezado in enumerate(encabezados):
        for alias in aliases:
            if alias in encabezado:
                return i
    return None


def _tomar(fila: Sequence[object], indices: Mapping[str, int | None], campo: str) -> object:
    indice = indices[campo]
    return None if indice is None else fila[indice]


class LectorLibrosExcel:
    """Implementacion de ``LectorHistorico`` con pandas + openpyxl."""

    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        filas: list[FilaCruda] = []
        libros: list[LibroLeido] = []
        for ruta in rutas:
            libro, filas_libro = self._leer_libro(ruta)
            libros.append(libro)
            filas.extend(filas_libro)
        return LibrosLeidos(filas=tuple(filas), libros=tuple(libros))

    def _leer_libro(self, ruta: Path) -> tuple[LibroLeido, list[FilaCruda]]:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
            return self._leer_libro_sin_avisos(ruta)

    def _leer_libro_sin_avisos(self, ruta: Path) -> tuple[LibroLeido, list[FilaCruda]]:
        anio = anio_del_libro(ruta)
        incluidas: list[str] = []
        omitidas: list[str] = []
        filas: list[FilaCruda] = []
        with pd.ExcelFile(ruta, engine="openpyxl") as excel:
            for hoja in excel.sheet_names:
                mes = mes_de_hoja(hoja)
                if mes is None:
                    omitidas.append(hoja)
                    continue
                incluidas.append(hoja)
                tabla = excel.parse(hoja, header=None, dtype=object)
                valores = [
                    [_crudo(v) for v in fila] for fila in tabla.itertuples(index=False, name=None)
                ]
                filas.extend(self._leer_hoja(valores, ruta.name, hoja, anio, date(anio, mes, 1)))
        libro = LibroLeido(
            nombre=ruta.name,
            anio=anio,
            hojas_incluidas=tuple(incluidas),
            hojas_omitidas=tuple(omitidas),
        )
        return libro, filas

    @staticmethod
    def _leer_hoja(
        valores: Sequence[Sequence[object]], libro: str, hoja: str, anio: int, mes_hoja: date
    ) -> list[FilaCruda]:
        encabezado = _fila_encabezado(valores)
        if encabezado is None:
            raise HojaSinEncabezadoError(libro, hoja)
        titulos = [normalizar_texto_encabezado(v) for v in valores[encabezado]]
        indices = {
            campo: _indice_columna(titulos, aliases) for campo, aliases in ALIAS_COLUMNAS.items()
        }
        return [
            FilaCruda(
                anio=anio,
                hoja=hoja,
                fila=posicion + 1,  # fila visible en Excel (``datos.index + 1``)
                mes_hoja=mes_hoja,
                nombre=_tomar(fila, indices, "nombre"),
                cedula=_cedula_cruda(_tomar(fila, indices, "cedula")),
                celular=_tomar(fila, indices, "celular"),
                correo=_tomar(fila, indices, "correo"),
                plan=_tomar(fila, indices, "plan"),
                fecha_inicio=_tomar(fila, indices, "fecha_inicio"),
                fecha_fin=_tomar(fila, indices, "fecha_fin"),
                forma_pago=_tomar(fila, indices, "forma_pago"),
                monto_cobrado=_tomar(fila, indices, "monto_cobrado"),
            )
            for posicion, fila in enumerate(valores)
            if posicion > encabezado
        ]
