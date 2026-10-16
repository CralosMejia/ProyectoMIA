"""Script de verificacion de la lista frente al notebook M01 (libros sinteticos, sin BD).

Las referencias se inyectan o se escriben en ``tmp_path``: ninguna prueba lee ``salidas/``.
"""

import hashlib
import hmac
import io
import json
import re
import warnings
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from scripts import verificar_lista as script

from app.application.historial.procesar_historico import ProcesarHistorico
from app.domain.modelo.umbrales import UMBRAL_ALTO, UMBRAL_MEDIO
from app.domain.modelo.variables import CONJUNTO_MODELO
from app.infrastructure.historico.lector_libros import LectorLibrosExcel

pytestmark = pytest.mark.unit

DIR_HISTORICO = Path(__file__).resolve().parents[2] / "fixtures" / "historico"
FECHA = date(2026, 8, 31)
# Sal de prueba (no es la del notebook, que vive fuera del repositorio).
SAL_PRUEBA = b"sal-de-prueba-solo-para-tests"
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
    return script.ejecutar_en_memoria(rutas, FECHA, HORIZONTE, TOP_K, SAL_PRUEBA)


def _referencia(res: script.ResultadoApp) -> script.Referencia:
    """Referencia identica a lo que produce la app (punto de partida de cada prueba)."""
    return script.Referencia(
        conteos=dict(res.conteos),
        variables=res.variables,
        medianas=dict(res.medianas),
        referencia_factores=dict(res.referencia_factores),
        lista=tuple(
            script.FilaReferencia(f.codigo, f.score, f.nivel, f.factores) for f in res.filas
        ),
    )


def _ejecutar(referencia: script.Referencia, argv: list[str] | None = None) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = script.main(argv or ARGUMENTOS, referencia=referencia, sal=SAL_PRUEBA, salida=salida)
    return codigo, salida.getvalue()


def _fila_app(prioridad: int, codigo: str, score: str, nivel: str = "MEDIO") -> script.FilaApp:
    return script.FilaApp(prioridad, codigo, Decimal(score), nivel, (), prioridad <= 2)


def _fila_ref(codigo: str, score: str, nivel: str = "MEDIO") -> script.FilaReferencia:
    return script.FilaReferencia(codigo, Decimal(score), nivel, ())


# ---------------------------------------------------------------- utilidades


def test_codigo_anonimo_es_el_hmac_con_sal_del_notebook() -> None:
    esperado = (
        "MTB-" + hmac.new(SAL_PRUEBA, b"C:0102030405", hashlib.sha256).hexdigest()[:8].upper()
    )
    assert script.codigo_anonimo("C:0102030405", SAL_PRUEBA) == esperado


def test_codigo_anonimo_depende_de_la_sal_y_no_es_el_sha256_sin_sal() -> None:
    sin_sal = "MTB-" + hashlib.sha256(b"C:0102030405").hexdigest()[:8].upper()

    codigo = script.codigo_anonimo("C:0102030405", SAL_PRUEBA)

    assert codigo != sin_sal
    assert codigo != script.codigo_anonimo("C:0102030405", b"otra-sal")


def test_cargar_sal_prefiere_la_variable_de_entorno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / script.ARCHIVO_SAL).write_text("sal-del-archivo\n", encoding="utf-8")
    monkeypatch.setenv(script.VARIABLE_SAL, " sal-del-entorno ")

    assert script.cargar_sal(tmp_path) == b"sal-del-entorno"


def test_cargar_sal_sin_variable_lee_el_archivo_de_salidas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(script.VARIABLE_SAL, raising=False)
    (tmp_path / script.ARCHIVO_SAL).write_text("sal-del-archivo\n", encoding="utf-8")

    assert script.cargar_sal(tmp_path) == b"sal-del-archivo"


def test_cargar_sal_sin_variable_ni_archivo_lanza_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(script.VARIABLE_SAL, raising=False)

    with pytest.raises(script.SalNoDisponibleError):
        script.cargar_sal(tmp_path)


def test_a_ocho_decimales_redondea_como_la_app() -> None:
    assert script.a_ocho_decimales(0.7101997203343381) == Decimal("0.71019972")
    assert script.a_ocho_decimales(0.6435987253983281) == Decimal("0.64359873")


def test_separar_factores_del_texto_del_notebook() -> None:
    texto = "Plan: OTRO (+0,07); Monto actual (USD): 70 (+0,03)"

    assert script.separar_factores(texto) == (
        "Plan: OTRO (+0,07)",
        "Monto actual (USD): 70 (+0,03)",
    )
    assert script.separar_factores("Sin factores de riesgo destacados") == ()
    assert script.separar_factores("") == ()


# ---------------------------------------------------------------- salidas del notebook


def _escribir_salidas(carpeta: Path) -> None:
    (carpeta / "m01" / "despues").mkdir(parents=True)
    (carpeta / "mvp").mkdir()
    parametros = {
        "variables_numericas": ["ciclos_previos", "monto_actual"],
        "variables_categoricas": ["plan", "mes_vencimiento"],
        "ciclos_entrenamiento_operativo": 1564,
        "medianas_monto_operativo": {"por_plan": {"ANUAL": 237.5, "MENSUAL": 39.0}, "general": 39},
        "referencia_factores": {"ciclos_previos": 0.0, "plan": "MENSUAL"},
        "cartera_septiembre": {
            "Ciclos que vencen entre el 01-09-2026 y el 30-09-2026": 59,
            "ya registraron una membresía posterior (renovación anticipada)": 2,
            "Ciclos a priorizar": 57,
            "Socios distintos a priorizar": 57,
        },
    }
    (carpeta / script.ARCHIVO_PARAMETROS).write_text(
        json.dumps(parametros, ensure_ascii=False), encoding="utf-8"
    )
    libro = openpyxl.Workbook()
    hoja = libro.active
    assert hoja is not None
    hoja.title = "top_25"
    cartera = libro.create_sheet("cartera_completa")
    cartera.append(
        [
            "prioridad",
            "socio_anonimo",
            "vence",
            "probabilidad",
            "nivel_riesgo",
            "factores principales",
            "dentro_de_capacidad",
        ]
    )
    cartera.append(
        [1, "MTB-AAAAAAAA", "2026-09-01", 0.7101997203343381, "ALTO", "Plan: ANUAL (+0,04)", "Sí"]
    )
    cartera.append(
        [
            2,
            "MTB-BBBBBBBB",
            "2026-09-02",
            0.2414349801232785,
            "BAJO",
            "Sin factores de riesgo destacados",
            "Sí",
        ]
    )
    libro.save(carpeta / script.ARCHIVO_LISTA)


def test_cargar_referencia_lee_parametros_y_lista_completa(tmp_path: Path) -> None:
    _escribir_salidas(tmp_path)

    ref = script.cargar_referencia(tmp_path)

    assert ref.conteos == {
        "cartera": 59,
        "ya_renovaron": 2,
        "a_priorizar": 57,
        "socios": 57,
        "ciclos_entrenamiento": 1564,
    }
    assert ref.variables == (("ciclos_previos", "monto_actual"), ("plan", "mes_vencimiento"))
    assert ref.medianas == {
        "ANUAL": Decimal("237.5"),
        "MENSUAL": Decimal("39"),
        "general": Decimal("39"),
    }
    assert ref.referencia_factores == {"ciclos_previos": 0.0, "plan": "MENSUAL"}
    assert ref.lista == (
        script.FilaReferencia(
            "MTB-AAAAAAAA", Decimal("0.71019972"), "ALTO", ("Plan: ANUAL (+0,04)",)
        ),
        script.FilaReferencia("MTB-BBBBBBBB", Decimal("0.24143498"), "BAJO", ()),
    )


def test_cargar_referencia_sin_salidas_lanza_error(tmp_path: Path) -> None:
    with pytest.raises(script.ReferenciaNoDisponibleError):
        script.cargar_referencia(tmp_path)


def test_main_sin_salidas_del_notebook_sale_con_dos(tmp_path: Path) -> None:
    salida = io.StringIO()

    codigo = script.main([*ARGUMENTOS, "--referencia", str(tmp_path)], salida=salida)

    assert codigo == 2
    assert "salidas del notebook" in salida.getvalue()
    assert str(tmp_path) not in salida.getvalue()


def test_main_sin_sal_sale_con_dos(
    resultado: script.ResultadoApp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(script.VARIABLE_SAL, raising=False)
    salida = io.StringIO()

    codigo = script.main(
        [*ARGUMENTOS, "--referencia", str(tmp_path)],
        referencia=_referencia(resultado),
        salida=salida,
    )

    assert codigo == 2
    assert script.VARIABLE_SAL in salida.getvalue()
    assert str(tmp_path) not in salida.getvalue()


def test_main_lee_la_sal_de_salidas_y_no_la_imprime(
    resultado: script.ResultadoApp, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(script.VARIABLE_SAL, raising=False)
    (tmp_path / script.ARCHIVO_SAL).write_text(SAL_PRUEBA.decode(), encoding="utf-8")
    salida = io.StringIO()

    codigo = script.main(
        [*ARGUMENTOS, "--referencia", str(tmp_path)],
        referencia=_referencia(resultado),
        salida=salida,
    )

    assert codigo == 0
    assert SAL_PRUEBA.decode() not in salida.getvalue()


def test_main_error_no_controlado_imprime_solo_el_tipo_y_sale_con_dos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fallar(*_: object, **__: object) -> script.ResultadoApp:
        raise RuntimeError("cedula 0102030405 en una ruta privada")

    monkeypatch.setattr(script, "ejecutar_en_memoria", fallar)
    referencia = script.Referencia({}, ((), ()), {}, {}, ())

    codigo, texto = _ejecutar(referencia)

    assert codigo == 2
    assert "RuntimeError" in texto
    assert "0102030405" not in texto
    assert "ruta privada" not in texto
    assert "Traceback" not in texto


def test_main_sin_libros_sale_con_dos(tmp_path: Path) -> None:
    salida = io.StringIO()

    codigo = script.main([str(tmp_path)], salida=salida)

    assert codigo == 2
    assert "No se encontraron libros" in salida.getvalue()


# ---------------------------------------------------------------- ejecucion en memoria


def test_ejecutar_en_memoria_con_sinteticos_devuelve_conteos_lista_y_modelo(
    resultado: script.ResultadoApp,
) -> None:
    conteos = resultado.conteos
    assert conteos["ciclos_entrenamiento"] == 15
    assert conteos["cartera"] == conteos["ya_renovaron"] + conteos["a_priorizar"]
    assert conteos["socios"] == len(resultado.filas) > 0
    assert [f.prioridad for f in resultado.filas] == list(range(1, len(resultado.filas) + 1))
    assert all(re.fullmatch(r"MTB-[0-9A-F]{8}", f.codigo) for f in resultado.filas)
    # La app entrena con el conjunto elegido por el notebook y niveles con cortes fijos.
    assert resultado.variables == (CONJUNTO_MODELO.numericas, CONJUNTO_MODELO.categoricas)
    assert (resultado.umbral_alto, resultado.umbral_medio) == (UMBRAL_ALTO, UMBRAL_MEDIO)
    assert set(resultado.referencia_factores) == {"plan", *CONJUNTO_MODELO.numericas} | {
        "mes_vencimiento"
    }
    assert "general" in resultado.medianas


def test_ejecutar_en_memoria_admite_horizonte_mayor_que_31() -> None:
    rutas = script.localizar_libros(DIR_HISTORICO)

    res = script.ejecutar_en_memoria(rutas, FECHA, 32, TOP_K, SAL_PRUEBA)

    assert res.conteos["socios"] == len(res.filas)


@pytest.mark.parametrize(("horizonte", "top_k"), [(0, 3), (30, 0)])
def test_ejecutar_en_memoria_horizonte_o_k_no_positivo_lanza_value_error(
    horizonte: int, top_k: int
) -> None:
    rutas = script.localizar_libros(DIR_HISTORICO)

    with pytest.raises(ValueError, match="positivos"):
        script.ejecutar_en_memoria(rutas, FECHA, horizonte, top_k, SAL_PRUEBA)


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


# ---------------------------------------------------------------- conciliacion


def test_main_con_referencia_identica_sale_con_cero(resultado: script.ResultadoApp) -> None:
    codigo, texto = _ejecutar(_referencia(resultado))

    assert codigo == 0
    assert "DIFIERE" not in texto
    assert "total 0" in texto
    assert f"socios dentro del top {TOP_K}: los mismos que en el notebook" in texto


def test_main_con_un_conteo_distinto_sale_con_uno(resultado: script.ResultadoApp) -> None:
    ref = _referencia(resultado)
    ref = replace(ref, conteos={**ref.conteos, "cartera": ref.conteos["cartera"] + 1})

    codigo, texto = _ejecutar(ref)

    assert codigo == 1
    assert "DIFIERE" in texto
    assert "conteos 1" in texto


def test_main_con_una_probabilidad_distinta_sale_con_uno(resultado: script.ResultadoApp) -> None:
    ref = _referencia(resultado)
    primera = ref.lista[0]
    lista = (replace(primera, probabilidad=primera.probabilidad + Decimal("0.00000001")),)
    ref = replace(ref, lista=lista + ref.lista[1:])

    codigo, texto = _ejecutar(ref)

    assert codigo == 1
    assert "probabilidades 1" in texto


def test_main_con_nivel_o_factores_distintos_sale_con_uno(resultado: script.ResultadoApp) -> None:
    ref = _referencia(resultado)
    otra = replace(ref.lista[0], nivel="ALTO", factores=("Plan: OTRO (+0,50)",))
    ref = replace(ref, lista=(otra, *ref.lista[1:]))

    codigo, texto = _ejecutar(ref)

    assert codigo == 1
    assert "niveles 1" in texto
    assert "factores 1" in texto


@pytest.mark.parametrize("apartado", ["variables", "medianas", "referencia_factores"])
def test_main_con_el_modelo_distinto_sale_con_uno(
    resultado: script.ResultadoApp, apartado: str
) -> None:
    ref = _referencia(resultado)
    cambios: dict[str, object] = {
        "variables": {"variables": (ref.variables[0], ("plan", "forma_pago"))},
        "medianas": {"medianas": {**ref.medianas, "general": Decimal("999")}},
        "referencia_factores": {
            "referencia_factores": {**ref.referencia_factores, "plan": "ANUAL"}
        },
    }[apartado]
    assert isinstance(cambios, dict)

    codigo, texto = _ejecutar(replace(ref, **cambios))

    assert codigo == 1
    assert f"{apartado} 1" in texto


def test_main_socio_ausente_de_la_lista_sale_con_uno(resultado: script.ResultadoApp) -> None:
    ref = _referencia(resultado)
    ref = replace(ref, lista=(replace(ref.lista[0], codigo="MTB-00000000"), *ref.lista[1:]))

    codigo, texto = _ejecutar(ref)

    assert codigo == 1
    assert "ausentes 1" in texto
    assert "MTB-" not in texto


def test_main_empates_en_otro_orden_se_comparan_como_conjunto(
    resultado: script.ResultadoApp,
) -> None:
    ref = _referencia(resultado)
    assert ref.lista[0].probabilidad == ref.lista[1].probabilidad  # los sinteticos empatan
    ref = replace(ref, lista=(ref.lista[1], ref.lista[0], *ref.lista[2:]))

    codigo, _ = _ejecutar(ref)

    assert codigo == 0


def test_conciliar_lista_fuera_de_orden_sin_empate_cuenta_las_posiciones() -> None:
    lista = [_fila_ref("MTB-A", "0.9"), _fila_ref("MTB-B", "0.8"), _fila_ref("MTB-C", "0.7")]
    filas = [
        _fila_app(1, "MTB-B", "0.8"),
        _fila_app(2, "MTB-A", "0.9"),
        _fila_app(3, "MTB-C", "0.7"),
    ]
    conciliacion = script.Conciliacion()

    script._conciliar_lista(filas, lista, 2, conciliacion)

    assert conciliacion.diferencias["orden"] == 2
    assert conciliacion.diferencias["probabilidades"] == 0
    assert any("posiciones 1-1" in linea for linea in conciliacion.lineas)


def test_conciliar_lista_empate_en_el_corte_es_informativo() -> None:
    lista = [_fila_ref("MTB-A", "0.9"), _fila_ref("MTB-B", "0.6"), _fila_ref("MTB-C", "0.6")]
    filas = [
        _fila_app(1, "MTB-A", "0.9"),
        _fila_app(2, "MTB-C", "0.6"),
        _fila_app(3, "MTB-B", "0.6"),
    ]
    conciliacion = script.Conciliacion()

    script._conciliar_lista(filas, lista, 2, conciliacion)

    assert conciliacion.total == 0
    assert any("cruzan el corte del top 2: 1" in linea for linea in conciliacion.lineas)
    assert any("distintos (informativo)" in linea for linea in conciliacion.lineas)


def test_conciliar_lista_socio_sobrante_cuenta_como_diferencia() -> None:
    lista = [_fila_ref("MTB-A", "0.9")]
    filas = [_fila_app(1, "MTB-A", "0.9"), _fila_app(2, "MTB-Z", "0.1", "BAJO")]
    conciliacion = script.Conciliacion()

    script._conciliar_lista(filas, lista, 2, conciliacion)

    assert conciliacion.diferencias["filas"] == 1


def test_main_no_imprime_datos_personales_ni_codigos(resultado: script.ResultadoApp) -> None:
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
    ref = _referencia(resultado)
    # Con diferencias en todas las filas, para que se imprima el detalle.
    ref = replace(ref, lista=tuple(replace(r, nivel="BAJO") for r in ref.lista))

    _, texto = _ejecutar(ref)

    assert "posicion 1: nivel" in texto
    assert not [p for p in personales if p in texto]
    assert not re.search(r"@|\b\d{9,10}\b|MTB-", texto)
    assert str(DIR_HISTORICO) not in texto
