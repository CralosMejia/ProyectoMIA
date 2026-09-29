"""ProcesarHistorico + LectorLibrosExcel sobre los libros sinteticos de T8 (sin base de datos)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.application.historial.procesar_historico import (
    ProcesarHistorico,
    ResultadoProcesamiento,
)
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from tests.fixtures import esperado
from tests.fixtures import generar_fixtures as gen

pytestmark = pytest.mark.integration

DIR_HISTORICO = Path(__file__).resolve().parents[2] / "fixtures" / "historico"
RUTAS = [DIR_HISTORICO / esperado.LIBRO_2025, DIR_HISTORICO / esperado.LIBRO_2026]


@pytest.fixture(scope="module")
def resultado() -> ResultadoProcesamiento:
    return ProcesarHistorico(LectorLibrosExcel()).ejecutar(RUTAS)


def test_ejecutar_fixtures_conteos_de_limpieza_igual_a_esperado(
    resultado: ResultadoProcesamiento,
) -> None:
    informe = resultado.informe
    assert informe.libros == 2
    assert informe.hojas_incluidas == sum(len(h) for h in esperado.HOJAS_INCLUIDAS.values())
    assert informe.hojas_omitidas == sum(len(h) for h in esperado.HOJAS_OMITIDAS.values())
    assert informe.filas_leidas == esperado.FILAS_LEIDAS
    assert informe.descartadas_no_utiles == esperado.DESCARTADAS_NO_UTILES
    assert informe.utiles == esperado.UTILES
    assert informe.sin_identidad == esperado.SIN_IDENTIDAD
    assert informe.con_identidad == esperado.CON_IDENTIDAD
    assert informe.socios_distintos == esperado.SOCIOS_DISTINTOS
    assert informe.socios_por_cedula == esperado.SOCIOS_POR_CEDULA
    assert informe.socios_por_nombre == esperado.SOCIOS_POR_NOMBRE
    assert informe.registros_por_cedula == esperado.REGISTROS_POR_CEDULA
    assert informe.registros_por_nombre == esperado.REGISTROS_POR_NOMBRE
    assert informe.inicio_aproximado == esperado.INICIO_APROXIMADO
    assert informe.montos_invalidos == esperado.MONTOS_INVALIDOS


def test_ejecutar_fixtures_ciclos_y_etiqueta_igual_a_esperado(
    resultado: ResultadoProcesamiento,
) -> None:
    informe = resultado.informe
    assert resultado.fecha_corte == informe.fecha_corte == esperado.FECHA_CORTE
    assert informe.ciclos_por_estado == esperado.CICLOS_POR_ESTADO
    assert informe.ciclos_por_motivo == esperado.CICLOS_POR_MOTIVO
    assert sum(informe.ciclos_por_estado.values()) == informe.con_identidad
    assert informe.evaluables == esperado.EVALUABLES
    assert informe.no_renovo == esperado.NO_RENOVO
    assert informe.renovo == esperado.RENOVO
    assert informe.prevalencia == esperado.PREVALENCIA
    assert isinstance(informe.prevalencia, Decimal)
    assert informe.rango_vencimientos == esperado.RANGO_VENCIMIENTOS
    assert informe.rango_vencimientos_evaluables == esperado.RANGO_VENCIMIENTOS_EVALUABLES


def test_ejecutar_fixtures_caso_del_tutor_queda_pendiente(
    resultado: ResultadoProcesamiento,
) -> None:
    tutor = esperado.CASO_TUTOR
    (ciclo,) = [
        c
        for c in resultado.ciclos
        if c.registro.referencia == (tutor["anio"], tutor["hoja"], tutor["fila"])
    ]
    assert ciclo.registro.fecha_vencimiento == tutor["fecha_vencimiento"]
    assert ciclo.estado.value == tutor["estado"]
    assert ciclo.motivo.value == tutor["motivo"]
    assert ciclo.no_renovo is None


def test_ejecutar_fixtures_renovaciones_conocidas(resultado: ResultadoProcesamiento) -> None:
    por_referencia = {c.registro.referencia: c for c in resultado.ciclos}
    for referencia in esperado.RENOVACIONES:
        ciclo = por_referencia[referencia]
        assert ciclo.no_renovo is False
        assert isinstance(ciclo.fecha_renovacion, date)


def test_ejecutar_fixtures_informe_sin_datos_personales(
    resultado: ResultadoProcesamiento,
) -> None:
    personales = set(gen.NOMBRES_FICTICIOS)
    for registro in resultado.registros:
        personales.add(registro.nombre)
        personales.add(registro.nombre_normalizado)
        if registro.cedula is not None:
            personales.add(registro.cedula)
    textos = (repr(resultado), repr(resultado.informe), str(resultado.informe.a_dict()))
    for texto in textos:
        assert not any(dato in texto for dato in personales)
