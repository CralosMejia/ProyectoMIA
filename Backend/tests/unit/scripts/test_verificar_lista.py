"""Script de verificacion de la lista con los libros sinteticos y referencias inyectadas."""

import hashlib
import io
import itertools
import re
import warnings
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from scripts import verificar_lista as script

from app.application.historial.procesar_historico import ProcesarHistorico
from app.infrastructure.historico.lector_libros import LectorLibrosExcel

pytestmark = pytest.mark.unit

DIR_HISTORICO = Path(__file__).resolve().parents[2] / "fixtures" / "historico"
FECHA = date(2026, 8, 31)
HORIZONTE = 180
TOP_K = 3
ARGUMENTOS = [
    str(DIR_HISTORICO),
    "--fecha",
    FECHA.isoformat(),
    "--horizonte",
    str(HORIZONTE),
    "--top-k",
    str(TOP_K),
]


@pytest.fixture(scope="module")
def resultado() -> script.ResultadoApp:
    rutas = script.localizar_libros(DIR_HISTORICO)
    return script.ejecutar_en_memoria(rutas, FECHA, HORIZONTE, TOP_K)


def _referencia(res: script.ResultadoApp) -> list[script.FilaReferencia]:
    return [
        script.FilaReferencia(
            codigo=f.codigo,
            probabilidad=script.a_tres_decimales(f.score),
            nivel=f.nivel,
            factores=f.factores,
        )
        for f in res.filas[:TOP_K]
    ]


def _ejecutar(
    conteos: dict[str, int], top: list[script.FilaReferencia], argv: list[str] | None = None
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = script.main(argv or ARGUMENTOS, conteos=conteos, top=top, salida=salida)
    return codigo, salida.getvalue()


def test_referencias_codifican_las_cifras_del_notebook() -> None:
    assert script.REFERENCIA_CONTEOS == {
        "cartera": 59,
        "ya_renovaron": 2,
        "a_priorizar": 57,
        "socios": 57,
        "ciclos_entrenamiento": 1564,
    }
    top = script.REFERENCIA_TOP
    assert len(top) == 25
    assert (top[0].codigo, top[0].probabilidad) == ("MTB-7C5F302E", Decimal("0.702"))
    assert (top[-1].codigo, top[-1].probabilidad) == ("MTB-043DE3C6", Decimal("0.605"))
    assert len({r.codigo for r in top}) == 25
    assert all(re.fullmatch(r"MTB-[0-9A-F]{8}", r.codigo) for r in top)
    assert all(a.probabilidad >= b.probabilidad for a, b in itertools.pairwise(top))


def test_codigo_anonimo_es_el_sha256_del_notebook() -> None:
    esperado = "MTB-" + hashlib.sha256(b"C:0102030405").hexdigest()[:8].upper()
    assert script.codigo_anonimo("C:0102030405") == esperado


def test_ejecutar_en_memoria_con_sinteticos_devuelve_conteos_y_lista(
    resultado: script.ResultadoApp,
) -> None:
    conteos = resultado.conteos
    assert conteos["ciclos_entrenamiento"] == 15
    assert conteos["cartera"] == conteos["ya_renovaron"] + conteos["a_priorizar"]
    assert conteos["socios"] == len(resultado.filas) > 0
    assert [f.prioridad for f in resultado.filas] == list(range(1, len(resultado.filas) + 1))
    assert all(re.fullmatch(r"MTB-[0-9A-F]{8}", f.codigo) for f in resultado.filas)


def test_main_con_referencias_coincidentes_sale_con_cero(resultado: script.ResultadoApp) -> None:
    codigo, texto = _ejecutar(dict(resultado.conteos), _referencia(resultado))

    assert codigo == 0
    assert "DIFIERE" not in texto
    assert "notebook" in texto
    assert f"factores iguales: {TOP_K} de {TOP_K}" in texto


def test_main_con_una_probabilidad_distinta_sale_con_uno(resultado: script.ResultadoApp) -> None:
    top = _referencia(resultado)
    top[0] = replace(top[0], probabilidad=top[0].probabilidad + Decimal("0.001"))

    codigo, texto = _ejecutar(dict(resultado.conteos), top)

    assert codigo == 1
    assert "DIFIERE" in texto


def test_main_con_un_conteo_distinto_sale_con_uno(resultado: script.ResultadoApp) -> None:
    conteos = {**resultado.conteos, "cartera": resultado.conteos["cartera"] + 1}

    codigo, texto = _ejecutar(conteos, _referencia(resultado))

    assert codigo == 1
    assert "DIFIERE" in texto


def test_main_empates_en_otro_orden_se_comparan_como_conjunto(
    resultado: script.ResultadoApp,
) -> None:
    top = _referencia(resultado)
    assert top[0].probabilidad == top[1].probabilidad  # los sinteticos empatan
    top[0], top[1] = top[1], top[0]

    codigo, _ = _ejecutar(dict(resultado.conteos), top)

    assert codigo == 0


def test_main_codigo_ausente_de_la_lista_sale_con_uno(resultado: script.ResultadoApp) -> None:
    top = _referencia(resultado)
    top[0] = replace(top[0], codigo="MTB-00000000")

    codigo, texto = _ejecutar(dict(resultado.conteos), top)

    assert codigo == 1
    assert "AUSENTE" in texto


def test_main_factores_y_niveles_distintos_son_informativos(
    resultado: script.ResultadoApp,
) -> None:
    top = [
        replace(r, factores=("Plan: OTRO (+0,50)",), nivel="BAJO") for r in _referencia(resultado)
    ]

    codigo, texto = _ejecutar(dict(resultado.conteos), top)

    assert codigo == 0
    assert f"factores iguales: 0 de {TOP_K}" in texto
    assert f"niveles iguales: 0 de {TOP_K}" in texto


def test_main_sin_libros_sale_con_dos(tmp_path: Path) -> None:
    codigo, texto = _ejecutar({}, [], [str(tmp_path)])

    assert codigo == 2
    assert "No se encontraron libros" in texto


def test_main_no_imprime_datos_personales(resultado: script.ResultadoApp) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        registros = (
            ProcesarHistorico(LectorLibrosExcel())
            .ejecutar(script.localizar_libros(DIR_HISTORICO))
            .registros
        )
    personales = {
        valor
        for r in registros
        for valor in (r.nombre, r.nombre_normalizado, r.cedula, r.celular, r.correo, r.identidad)
        if valor and len(valor) >= 5
    }
    assert personales

    _, texto = _ejecutar(dict(resultado.conteos), _referencia(resultado))

    assert not [p for p in personales if p in texto]
    assert not re.search(r"@|\b\d{9,10}\b", texto)
    assert str(DIR_HISTORICO) not in texto


def test_membresias_marca_a_todos_con_cedula_aunque_el_registro_no_la_tenga() -> None:
    # Decision (c) de R-005: el script compara con el notebook, que no excluye sin cedula.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        registros = (
            ProcesarHistorico(LectorLibrosExcel())
            .ejecutar(script.localizar_libros(DIR_HISTORICO))
            .registros
        )
    sin_cedula = [replace(r, cedula=None) for r in registros[:3]] + list(registros[3:])

    membresias = script._membresias(sin_cedula)

    assert len(membresias) == len(sin_cedula)
    assert all(m.socio_con_cedula for m in membresias)


def test_ejecutar_en_memoria_admite_horizonte_mayor_que_31() -> None:
    rutas = script.localizar_libros(DIR_HISTORICO)

    res = script.ejecutar_en_memoria(rutas, FECHA, 32, TOP_K)

    assert res.conteos["socios"] == len(res.filas)


@pytest.mark.parametrize(("horizonte", "top_k"), [(0, 3), (30, 0)])
def test_ejecutar_en_memoria_horizonte_o_k_no_positivo_lanza_value_error(
    horizonte: int, top_k: int
) -> None:
    rutas = script.localizar_libros(DIR_HISTORICO)

    with pytest.raises(ValueError, match="positivos"):
        script.ejecutar_en_memoria(rutas, FECHA, horizonte, top_k)
