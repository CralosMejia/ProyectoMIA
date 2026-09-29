"""Script de verificacion con los libros sinteticos de T8 y valores esperados inyectados."""

import io
import re
import shutil
from datetime import date
from pathlib import Path

import pytest
from scripts import verificar_historico as script

from tests.fixtures import esperado
from tests.fixtures import generar_fixtures as gen

pytestmark = pytest.mark.unit

DIR_HISTORICO = Path(__file__).resolve().parents[2] / "fixtures" / "historico"

REFERENCIA_SINTETICA: dict[str, int | date] = {
    "utiles": esperado.UTILES,
    "con_identidad": esperado.CON_IDENTIDAD,
    "socios_distintos": esperado.SOCIOS_DISTINTOS,
    "fecha_corte": esperado.FECHA_CORTE,
    "evaluables": esperado.EVALUABLES,
    **{f"motivo.{m}": n for m, n in esperado.CICLOS_POR_MOTIVO.items() if m != "EVALUABLE"},
    "no_renovo": esperado.NO_RENOVO,
    "renovo": esperado.RENOVO,
}


def _ejecutar(
    carpeta: Path,
    referencia: dict[str, int | date],
    conocidas: dict[str, tuple[int, str]] | None = None,
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = script.main(
        [str(carpeta)], referencia=referencia, conocidas=conocidas or {}, salida=salida
    )
    return codigo, salida.getvalue()


def _linea(texto: str, cifra: str) -> str:
    return next(linea for linea in texto.splitlines() if linea.startswith(cifra + " "))


def test_diferencias_conocidas_codifica_los_deltas_documentados() -> None:
    conocidas = script.DIFERENCIAS_CONOCIDAS
    assert set(conocidas) == {"motivo.SIN_VENCIMIENTO", "motivo.FECHA_FUERA_DE_RANGO"}
    assert conocidas["motivo.SIN_VENCIMIENTO"][0] == 2
    assert conocidas["motivo.FECHA_FUERA_DE_RANGO"][0] == -2
    assert all(motivo.strip() for _, motivo in conocidas.values())


def test_main_diferencia_conocida_con_el_delta_exacto_la_marca_y_sale_con_cero() -> None:
    referencia = {**REFERENCIA_SINTETICA, "evaluables": esperado.EVALUABLES - 3}
    conocidas = {"evaluables": (3, "motivo sintetico de la diferencia")}

    codigo, texto = _ejecutar(DIR_HISTORICO, referencia, conocidas)

    assert codigo == 0
    assert "conocida" in _linea(texto, "evaluables")
    assert "DIFIERE" not in texto
    assert "motivo sintetico de la diferencia" in texto


def test_main_diferencia_conocida_con_otro_delta_sale_con_uno() -> None:
    referencia = {**REFERENCIA_SINTETICA, "evaluables": esperado.EVALUABLES - 3}
    conocidas = {"evaluables": (2, "motivo sintetico de la diferencia")}

    codigo, texto = _ejecutar(DIR_HISTORICO, referencia, conocidas)

    assert codigo == 1
    assert "DIFIERE" in _linea(texto, "evaluables")


def test_main_diferencia_conocida_que_desaparece_sale_con_uno() -> None:
    conocidas = {"evaluables": (3, "motivo sintetico de la diferencia")}

    codigo, texto = _ejecutar(DIR_HISTORICO, REFERENCIA_SINTETICA, conocidas)

    assert codigo == 1
    assert "DIFIERE" in _linea(texto, "evaluables")


def test_referencia_notebook_codifica_las_cifras_del_plan() -> None:
    ref = script.REFERENCIA_NOTEBOOK
    assert ref["utiles"] == 2771
    assert ref["con_identidad"] == 2748
    assert ref["socios_distintos"] == 1410
    assert ref["fecha_corte"] == date(2026, 8, 31)
    assert ref["evaluables"] == 1564
    assert ref["motivo.SIN_VENCIMIENTO"] == 855
    assert ref["motivo.VENCIMIENTO_POSTERIOR_AL_CORTE"] == 160
    assert ref["motivo.VENTANA_INCOMPLETA"] == 96
    assert ref["motivo.DURACION_IMPLAUSIBLE"] == 49
    assert ref["motivo.PASE_DIARIO"] == 16
    assert ref["motivo.FECHA_FUERA_DE_RANGO"] == 8
    assert ref["no_renovo"] == 1098
    assert ref["renovo"] == 466


def test_localizar_libros_devuelve_solo_libros_control_gym_ordenados(tmp_path: Path) -> None:
    for nombre in (esperado.LIBRO_2026, esperado.LIBRO_2025):
        shutil.copy(DIR_HISTORICO / nombre, tmp_path / nombre)
    (tmp_path / "otro.xlsx").write_bytes(b"")
    (tmp_path / f"~${esperado.LIBRO_2025}").write_bytes(b"")

    libros = script.localizar_libros(tmp_path)

    assert [r.name for r in libros] == [esperado.LIBRO_2025, esperado.LIBRO_2026]


def test_main_con_valores_coincidentes_imprime_tabla_y_sale_con_cero() -> None:
    codigo, texto = _ejecutar(DIR_HISTORICO, REFERENCIA_SINTETICA)

    assert codigo == 0
    assert "notebook" in texto
    assert "obtenido" in texto
    for cifra in REFERENCIA_SINTETICA:
        assert cifra in texto
    assert "2026-08-31" in texto


def test_main_con_una_cifra_distinta_sale_con_uno_y_la_marca() -> None:
    referencia = {**REFERENCIA_SINTETICA, "evaluables": esperado.EVALUABLES + 1}

    codigo, texto = _ejecutar(DIR_HISTORICO, referencia)

    assert codigo == 1
    linea = next(linea for linea in texto.splitlines() if linea.startswith("evaluables"))
    assert "DIFIERE" in linea
    assert str(esperado.EVALUABLES + 1) in linea


def test_main_salida_no_contiene_nombres_ni_cedulas() -> None:
    _, texto = _ejecutar(DIR_HISTORICO, REFERENCIA_SINTETICA)

    texto_mayus = texto.upper()
    for nombre in gen.NOMBRES_FICTICIOS:
        for palabra in nombre.upper().split():
            if len(palabra) >= 4:
                assert palabra not in texto_mayus
    assert re.search(r"\d{9,}", texto) is None  # ninguna cedula ni celular
    assert "@" not in texto  # ningun correo


def test_main_carpeta_sin_libros_sale_con_dos_sin_rutas(tmp_path: Path) -> None:
    codigo, texto = _ejecutar(tmp_path, REFERENCIA_SINTETICA)

    assert codigo == 2
    assert str(tmp_path) not in texto


def test_main_no_escribe_archivos(tmp_path: Path) -> None:
    for nombre in (esperado.LIBRO_2025, esperado.LIBRO_2026):
        shutil.copy(DIR_HISTORICO / nombre, tmp_path / nombre)
    antes = sorted(p.name for p in tmp_path.iterdir())

    _ejecutar(tmp_path, REFERENCIA_SINTETICA)

    assert sorted(p.name for p in tmp_path.iterdir()) == antes
