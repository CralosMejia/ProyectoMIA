"""Verificacion local del historico con los libros reales (T11, D2-BE-05). Fuera de la suite.

Uso (desde ``Backend/``, con el entorno virtual activo)::

    python scripts/verificar_historico.py <carpeta con los libros Control Gym>

Compone ``LectorLibrosExcel`` + ``ProcesarHistorico`` sobre los libros de la carpeta e imprime
una tabla "notebook vs obtenido" con las cifras de referencia del notebook MVP (secciones 3.6,
4.1, 4.3, 5.3 y 5.5). Sale con 0 si todo coincide o solo hay diferencias conocidas con su
delta exacto (``DIFERENCIAS_CONOCIDAS``), 1 si hay cualquier otra diferencia o un delta
conocido cambia, y 2 si la carpeta no tiene libros. Solo imprime conteos y fechas: nunca
nombres, cedulas, celulares, correos ni rutas (RN-03.5, RT-13). No escribe archivos.
"""

import argparse
import sys
import warnings
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TextIO

from app.application.historial.procesar_historico import InformeHistorico, ProcesarHistorico
from app.infrastructure.historico.lector_libros import LectorLibrosExcel

Cifra = int | date

# Cifras del notebook ``Notebookes/MVP.ipynb`` (salidas guardadas, ejecutado con pandas 3.x).
REFERENCIA_NOTEBOOK: dict[str, Cifra] = {
    "utiles": 2771,
    "con_identidad": 2748,
    "socios_distintos": 1410,
    "fecha_corte": date(2026, 8, 31),
    "evaluables": 1564,
    "motivo.SIN_VENCIMIENTO": 855,
    "motivo.VENCIMIENTO_POSTERIOR_AL_CORTE": 160,
    "motivo.VENTANA_INCOMPLETA": 96,
    "motivo.DURACION_IMPLAUSIBLE": 49,
    "motivo.PASE_DIARIO": 16,
    "motivo.FECHA_FUERA_DE_RANGO": 8,
    "no_renovo": 1098,
    "renovo": 466,
}

# Diferencias aceptadas: cifra -> (delta exacto obtenido - notebook, motivo en una linea).
DIFERENCIAS_CONOCIDAS: dict[str, tuple[int, str]] = {
    "motivo.SIN_VENCIMIENTO": (
        2,
        "2 celdas basura en fecha_fin que pandas 3 convierte en anio 1114 y anio 1; "
        "la app no las interpreta como fecha (ambos ciclos quedan excluidos igual)",
    ),
    "motivo.FECHA_FUERA_DE_RANGO": (
        -2,
        "las mismas 2 celdas basura de fecha_fin: el notebook las cuenta fuera de rango "
        "(anio 1114 y anio 1 de pandas 3); la app, sin vencimiento",
    ),
}

_PREFIJO_MOTIVO = "motivo."


def localizar_libros(carpeta: Path) -> list[Path]:
    """Libros ``*Control*Gym*.xlsx`` de la carpeta, ordenados; ignora bloqueos ``~$``."""
    return sorted(
        ruta
        for ruta in carpeta.glob("*.xlsx")
        if not ruta.name.startswith("~$")
        and "CONTROL" in ruta.name.upper()
        and "GYM" in ruta.name.upper()
    )


def _obtenido(informe: InformeHistorico, cifra: str) -> Cifra | None:
    if cifra.startswith(_PREFIJO_MOTIVO):
        return informe.ciclos_por_motivo.get(cifra.removeprefix(_PREFIJO_MOTIVO))
    valor = getattr(informe, cifra, None)
    return valor if isinstance(valor, int | date) else None


def _resultado(obtenido: Cifra | None, esperado: Cifra, conocida: tuple[int, str] | None) -> str:
    """``ok``, ``conocida`` (delta exacto de una diferencia documentada) o ``DIFIERE``."""
    if conocida is None:
        return "ok" if obtenido == esperado else "DIFIERE"
    delta_exacto = (
        isinstance(obtenido, int)
        and isinstance(esperado, int)
        and obtenido - esperado == conocida[0]
    )
    return "conocida" if delta_exacto else "DIFIERE"


def _tabla(
    informe: InformeHistorico,
    referencia: dict[str, Cifra],
    conocidas: dict[str, tuple[int, str]],
) -> tuple[list[str], int, int]:
    ancho = max(len(c) for c in referencia)
    lineas = [f"{'cifra':<{ancho}}  {'notebook':>10}  {'obtenido':>10}  resultado"]
    diferencias = aceptadas = 0
    notas: list[str] = []
    for cifra, esperado in referencia.items():
        obtenido = _obtenido(informe, cifra)
        conocida = conocidas.get(cifra)
        resultado = _resultado(obtenido, esperado, conocida)
        diferencias += resultado == "DIFIERE"
        aceptadas += resultado == "conocida"
        if resultado == "conocida" and conocida is not None:
            notas.append(f"  {cifra} ({conocida[0]:+d}): {conocida[1]}")
        lineas.append(f"{cifra:<{ancho}}  {esperado!s:>10}  {obtenido!s:>10}  {resultado}")
    if notas:
        lineas.extend(["diferencias conocidas:", *notas])
    return lineas, diferencias, aceptadas


def main(
    argv: Sequence[str] | None = None,
    *,
    referencia: dict[str, Cifra] = REFERENCIA_NOTEBOOK,
    conocidas: dict[str, tuple[int, str]] = DIFERENCIAS_CONOCIDAS,
    salida: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(description="Verifica el historico frente al notebook.")
    parser.add_argument("carpeta", type=Path, help="carpeta con los libros Control Gym")
    argumentos = parser.parse_args(argv)

    rutas = localizar_libros(argumentos.carpeta)
    if not rutas:
        print("No se encontraron libros Control Gym en la carpeta indicada.", file=salida)
        return 2

    # openpyxl avisa de celdas con formato de fecha y serial invalido citando el valor de la
    # celda (puede ser una cedula mal ubicada): se silencian para no filtrar datos personales.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        informe = ProcesarHistorico(LectorLibrosExcel()).ejecutar(rutas).informe

    lineas, diferencias, aceptadas = _tabla(informe, referencia, conocidas)
    print(f"libros: {informe.libros}  hojas mensuales: {informe.hojas_incluidas}", file=salida)
    for linea in lineas:
        print(linea, file=salida)
    total = len(referencia)
    print(
        f"coinciden {total - diferencias - aceptadas} de {total} cifras; "
        f"diferencias conocidas: {aceptadas}; otras diferencias: {diferencias}",
        file=salida,
    )
    return 0 if diferencias == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
