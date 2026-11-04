"""Generador del dataset sintetico del demo (R-019/T1), con la canalizacion real y sin BD."""

import ast
import hashlib
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from scripts import generar_dataset_demo as script

from app.application.historial.procesar_historico import (
    ProcesarHistorico,
    ResultadoProcesamiento,
)
from app.application.modelo.entrenar_modelo import EntrenarModeloInicial, ModeloEntrenado
from app.application.modelo.mapeo import ciclo_modelo_desde
from app.domain.cargas.documento import cedula_valida
from app.domain.cargas.validacion import FilaValida, validar_fila
from app.domain.common.enums import EstadoCiclo, NivelRiesgo
from app.domain.common.predictor import FeatureRow
from app.domain.modelo.cartera import seleccionar_cartera, ya_renovo
from app.domain.modelo.umbrales import nivel_de
from app.domain.modelo.variables import CicloModelo, construir_variables
from app.infrastructure.cargas.lector_plantilla import MAX_FILAS_PLANTILLA, LectorPlantillaOpenpyxl
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from app.infrastructure.historico.localizador_libros import LocalizadorLibrosCarpeta
from app.infrastructure.ml.predictor_adoptado import PredictorAdoptado

pytestmark = pytest.mark.unit

BASE_COMMIT = date(2026, 11, 2)
BASE_REGENERADA = date(2028, 3, 15)
HORIZONTE = 31
PREFIJOS_MOVILES = frozenset({"096", "097", "098", "099"})
LIBRERIAS_PERMITIDAS = frozenset(
    {
        "__future__",
        "argparse",
        "calendar",
        "collections",
        "dataclasses",
        "datetime",
        "decimal",
        "hashlib",
        "io",
        "openpyxl",
        "pathlib",
        "re",
        "sys",
        "zipfile",
    }
)


def _generar(base: date, salida: Path) -> None:
    assert script.main(["--fecha-base", base.isoformat(), "--salida", str(salida)]) == 0


def _contenido(carpeta: Path) -> dict[str, bytes]:
    return {ruta.name: ruta.read_bytes() for ruta in sorted(carpeta.iterdir())}


def _vigencia(carpeta: Path) -> date:
    return date.fromisoformat((carpeta / "vigencia.txt").read_text(encoding="ascii").strip())


@dataclass(frozen=True, slots=True)
class Escenario:
    base: date
    carpeta: Path
    resultado: ResultadoProcesamiento
    modelo: ModeloEntrenado
    # Ciclos sin etiquetar, como los que la lista lee de las membresias guardadas.
    ciclos: tuple[CicloModelo, ...]

    def cartera_vigente(self, fecha: date) -> list[CicloModelo]:
        cartera = seleccionar_cartera(self.ciclos, fecha, HORIZONTE)
        return [c for c in cartera if not ya_renovo(c, self.ciclos)]

    def cedulas(self, cartera: list[CicloModelo]) -> set[str]:
        por_referencia: dict[object, str | None] = {
            r.referencia: r.cedula for r in self.resultado.registros
        }
        return {cedula for c in cartera if (cedula := por_referencia[c.ref]) is not None}


@pytest.fixture(scope="module", params=[BASE_COMMIT, BASE_REGENERADA], ids=["commit", "regenerada"])
def escenario(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Escenario]:
    base: date = request.param
    carpeta = tmp_path_factory.mktemp("demo")
    _generar(base, carpeta)
    resultado = ProcesarHistorico(LectorLibrosExcel()).ejecutar(
        LocalizadorLibrosCarpeta(carpeta).rutas()
    )
    modelo = EntrenarModeloInicial(PredictorAdoptado()).ejecutar(
        resultado.ciclos, resultado.fecha_corte
    )
    ciclos = tuple(
        replace(ciclo_modelo_desde(c), excluido=False, no_renovo=None) for c in resultado.ciclos
    )
    yield Escenario(base, carpeta, resultado, modelo, ciclos)


# ------------------------------------------------------------------ restricciones del script


def test_generador_importa_solo_estandar_y_openpyxl() -> None:
    arbol = ast.parse(Path(script.__file__).read_text(encoding="utf-8"))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {alias.name.split(".")[0] for alias in nodo.names}
        elif isinstance(nodo, ast.ImportFrom):
            importados.add((nodo.module or "").split(".")[0])
    assert importados <= LIBRERIAS_PERMITIDAS


def test_generador_no_consulta_el_reloj_del_sistema() -> None:
    arbol = ast.parse(Path(script.__file__).read_text(encoding="utf-8"))
    atributos = {nodo.attr for nodo in ast.walk(arbol) if isinstance(nodo, ast.Attribute)}
    assert not atributos & {"today", "now", "utcnow", "time"}


def test_main_sin_fecha_base_falla(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as salida:
        script.main(["--salida", str(tmp_path)])
    assert salida.value.code != 0


def test_main_fecha_base_mal_formada_falla(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as salida:
        script.main(["--fecha-base", "20261102", "--salida", str(tmp_path)])
    assert salida.value.code != 0


def test_main_fecha_base_anterior_al_minimo_falla_sin_escribir(tmp_path: Path) -> None:
    salida_demo = tmp_path / "demo"
    with pytest.raises(SystemExit) as salida:
        script.main(["--fecha-base", "2026-01-01", "--salida", str(salida_demo)])
    assert salida.value.code != 0
    assert not salida_demo.exists()


def test_main_escribe_solo_en_la_salida(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    monkeypatch.chdir(trabajo)
    _generar(BASE_COMMIT, tmp_path / "nueva" / "salida")
    assert list(trabajo.iterdir()) == []
    assert sorted(ruta.name for ruta in (tmp_path / "nueva" / "salida").iterdir()) == [
        "Control Gym 2025 demo.xlsx",
        "Control Gym 2026 demo.xlsx",
        "vigencia.txt",
    ]


# ------------------------------------------------------------------ determinismo


def test_misma_fecha_base_produce_los_mismos_bytes(tmp_path: Path) -> None:
    _generar(BASE_COMMIT, tmp_path / "a")
    _generar(BASE_COMMIT, tmp_path / "b")
    assert _contenido(tmp_path / "a") == _contenido(tmp_path / "b")


def test_regenerar_conserva_las_hojas_ya_cerradas(tmp_path: Path) -> None:
    _generar(BASE_COMMIT, tmp_path / "a")
    _generar(date(2026, 12, 7), tmp_path / "b")

    def filas(carpeta: Path) -> list[tuple[object, ...]]:
        libro = openpyxl.load_workbook(carpeta / "Control Gym 2026 demo.xlsx", read_only=True)
        return list(libro["OCTUBRE"].iter_rows(values_only=True))

    assert filas(tmp_path / "a") == filas(tmp_path / "b")


def test_zip_y_metadatos_son_fijos_e_independientes_del_sistema(tmp_path: Path) -> None:
    _generar(BASE_COMMIT, tmp_path)
    ruta = tmp_path / "Control Gym 2026 demo.xlsx"
    with zipfile.ZipFile(ruta) as archivo:
        entradas = archivo.infolist()
        nucleo = archivo.read("docProps/core.xml").decode()
    assert {e.date_time for e in entradas} == {(2026, 1, 1, 0, 0, 0)}
    assert {e.create_system for e in entradas} == {3}  # no varia entre Windows y Linux
    assert "generar_dataset_demo" in nucleo
    assert nucleo.count("2026-01-01T00:00:00Z") == 2
    libro = openpyxl.load_workbook(ruta, read_only=True)
    assert libro.properties.creator == "generar_dataset_demo"


def test_vigencia_es_una_fecha_con_salto_de_linea_lf(tmp_path: Path) -> None:
    _generar(BASE_COMMIT, tmp_path)
    assert (tmp_path / "vigencia.txt").read_bytes() == b"2027-09-30\n"


def test_montos_son_decimales_exactos() -> None:
    assert all(isinstance(m.monto, Decimal) for m in script.simular(date(2026, 10, 31)))


# ------------------------------------------------------------------ libros


def test_localizador_encuentra_un_libro_por_anio(escenario: Escenario) -> None:
    rutas = LocalizadorLibrosCarpeta(escenario.carpeta).rutas()
    anios = range(2025, escenario.base.year + 1)
    assert [r.name for r in rutas] == [f"Control Gym {anio} demo.xlsx" for anio in anios]


def test_fecha_corte_es_el_fin_del_ultimo_mes_cerrado(escenario: Escenario) -> None:
    esperado = {BASE_COMMIT: date(2026, 10, 31), BASE_REGENERADA: date(2028, 2, 29)}
    assert escenario.resultado.fecha_corte == esperado[escenario.base]


def test_libros_empiezan_en_enero_2025_sin_huecos(escenario: Escenario) -> None:
    corte = escenario.resultado.fecha_corte
    meses = {
        (r.fecha_actividad.year, r.fecha_actividad.month) for r in escenario.resultado.registros
    }
    total = (corte.year - 2025) * 12 + corte.month
    assert len(meses) == total
    assert min(meses) == (2025, 1)
    assert max(meses) == (corte.year, corte.month)


def test_base_en_enero_no_crea_libro_del_anio_en_curso(tmp_path: Path) -> None:
    _generar(date(2027, 1, 10), tmp_path)
    assert [r.name for r in LocalizadorLibrosCarpeta(tmp_path).rutas()] == [
        "Control Gym 2025 demo.xlsx",
        "Control Gym 2026 demo.xlsx",
    ]


def test_ninguna_fila_se_descarta(escenario: Escenario) -> None:
    informe = escenario.resultado.informe
    assert informe.descartadas_no_utiles == 0
    assert informe.sin_identidad == 0
    assert informe.inicio_aproximado == 0
    assert informe.montos_invalidos == 0
    assert informe.registros_por_nombre == 0


def test_datos_personales_son_ficticios(escenario: Escenario) -> None:
    registros = escenario.resultado.registros
    assert all("Demo" in r.nombre for r in registros)
    assert all(r.cedula is not None and r.cedula.startswith("0999") for r in registros)
    assert all(r.correo is not None and r.correo.endswith("@example.com") for r in registros)
    assert all(
        r.celular is not None and len(r.celular) == 10 and r.celular[:3] not in PREFIJOS_MOVILES
        for r in registros
    )


def test_cada_cedula_corresponde_a_un_solo_socio(escenario: Escenario) -> None:
    nombres_por_cedula: dict[str | None, set[str]] = {}
    for registro in escenario.resultado.registros:
        nombres_por_cedula.setdefault(registro.cedula, set()).add(registro.nombre)
    assert all(len(nombres) == 1 for nombres in nombres_por_cedula.values())


# ------------------------------------------------------------------ entrenamiento y listas


def test_evaluables_y_prevalencia_permiten_entrenar(escenario: Escenario) -> None:
    informe = escenario.resultado.informe
    assert informe.evaluables >= 500
    assert informe.prevalencia is not None
    assert Decimal("0.40") <= informe.prevalencia <= Decimal("0.70")
    assert informe.ciclos_por_estado[EstadoCiclo.EVALUABLE.value] == informe.evaluables
    assert escenario.modelo.ciclos_entrenamiento == informe.evaluables
    assert escenario.modelo.metadata_tecnica["ciclos_referencia_factores"] != 0


def test_lista_de_la_fecha_base_tiene_socios_y_niveles_de_riesgo(escenario: Escenario) -> None:
    cartera = escenario.cartera_vigente(escenario.base)
    assert len(escenario.cedulas(cartera)) >= 20

    filas: list[FeatureRow] = [
        construir_variables(c, escenario.ciclos, escenario.modelo.medianas) for c in cartera
    ]
    predicciones = PredictorAdoptado().predict(escenario.modelo.artefacto, filas)
    niveles: set[NivelRiesgo] = {nivel_de(p.score, escenario.modelo.umbrales) for p in predicciones}
    assert len(niveles) >= 2


def test_lista_tiene_socios_cada_semana_hasta_la_vigencia(escenario: Escenario) -> None:
    vigencia = _vigencia(escenario.carpeta)
    assert vigencia > escenario.base
    fechas = [
        escenario.base + timedelta(days=7 * semana)
        for semana in range((vigencia - escenario.base).days // 7 + 1)
    ]
    conteos = {f: len(escenario.cedulas(escenario.cartera_vigente(f))) for f in [*fechas, vigencia]}
    assert min(conteos.values()) >= 10, min(conteos, key=lambda f: conteos[f])


@pytest.mark.parametrize("base", [date(2026, 11, 30), date(2027, 2, 28), date(2027, 1, 31)])
def test_lista_con_base_a_fin_de_mes_no_queda_corta(base: date, tmp_path: Path) -> None:
    _generar(base, tmp_path)
    resultado = ProcesarHistorico(LectorLibrosExcel()).ejecutar(
        LocalizadorLibrosCarpeta(tmp_path).rutas()
    )
    ciclos = [ciclo_modelo_desde(c) for c in resultado.ciclos]
    cartera = seleccionar_cartera(ciclos, base, HORIZONTE)
    assert len({c.clave_socio for c in cartera if not ya_renovo(c, ciclos)}) >= 20


# ------------------------------------------------------------------ perfil "grabacion" (R-022/T8)

BASE_GRABACION = date(2026, 11, 3)
# Hash de los archivos versionados en ``datos-demo/`` (``--fecha-base 2026-11-02``).
HASH_DATOS_DEMO = {
    "Control Gym 2025 demo.xlsx": (
        "b5cb685c46f9344a686439ea3c3154987bd341a7810313cf14eea50c5e817afd"
    ),
    "Control Gym 2026 demo.xlsx": (
        "abba8489479e854544d3c4f74b02cf54c13090090bd154256634e0b11b618f2f"
    ),
    "vigencia.txt": "c0b653a8ee8708701568dae5825746783a66fc85235db5525de38578e43ed0ae",
}
MESES_CERRADOS_VERIFICABLES = 4
VENCIMIENTOS_MINIMOS_POR_MES = 25
VENTANA_RENOVACION = 30


def _generar_grabacion(base: date, salida: Path) -> None:
    argumentos = ["--fecha-base", base.isoformat(), "--salida", str(salida)]
    assert script.main([*argumentos, "--perfil", "grabacion"]) == 0


def _hashes(carpeta: Path) -> dict[str, str]:
    return {
        nombre: hashlib.sha256(datos).hexdigest() for nombre, datos in _contenido(carpeta).items()
    }


@pytest.fixture(scope="module")
def grabacion(tmp_path_factory: pytest.TempPathFactory) -> Escenario:
    return _escenario_grabacion(BASE_GRABACION, tmp_path_factory.mktemp("grabacion"))


def _escenario_grabacion(base: date, carpeta: Path) -> Escenario:
    _generar_grabacion(base, carpeta)
    resultado = ProcesarHistorico(LectorLibrosExcel()).ejecutar(
        LocalizadorLibrosCarpeta(carpeta).rutas()
    )
    modelo = EntrenarModeloInicial(PredictorAdoptado()).ejecutar(
        resultado.ciclos, resultado.fecha_corte
    )
    ciclos = tuple(
        replace(ciclo_modelo_desde(c), excluido=False, no_renovo=None) for c in resultado.ciclos
    )
    return Escenario(base, carpeta, resultado, modelo, ciclos)


def test_perfil_demo_por_defecto_produce_los_bytes_de_datos_demo(tmp_path: Path) -> None:
    _generar(BASE_COMMIT, tmp_path / "defecto")
    argumentos = ["--fecha-base", BASE_COMMIT.isoformat(), "--salida", str(tmp_path / "demo")]
    assert script.main([*argumentos, "--perfil", "demo"]) == 0
    assert _hashes(tmp_path / "defecto") == HASH_DATOS_DEMO
    assert _hashes(tmp_path / "demo") == HASH_DATOS_DEMO


def test_main_perfil_desconocido_falla_sin_escribir(tmp_path: Path) -> None:
    destino = tmp_path / "salida"
    argumentos = ["--fecha-base", BASE_GRABACION.isoformat(), "--salida", str(destino)]
    with pytest.raises(SystemExit) as salida:
        script.main([*argumentos, "--perfil", "real"])
    assert salida.value.code != 0
    assert not destino.exists()


def test_grabacion_misma_fecha_produce_los_mismos_bytes(tmp_path: Path) -> None:
    _generar_grabacion(BASE_GRABACION, tmp_path / "a")
    _generar_grabacion(BASE_GRABACION, tmp_path / "b")
    assert _contenido(tmp_path / "a") == _contenido(tmp_path / "b")


def test_grabacion_usa_semilla_propia() -> None:
    corte = script.fecha_corte(BASE_GRABACION)
    demo = script.simular(corte)
    grabacion = script.simular(corte, script.PERFILES["grabacion"].reglas)
    assert script.PERFILES["grabacion"].reglas.semilla != script.SEMILLA
    assert demo != grabacion


def test_grabacion_libros_sin_marca_demo_y_plantillas_de_los_4_meses(
    grabacion: Escenario,
) -> None:
    nombres = sorted(ruta.name for ruta in grabacion.carpeta.iterdir())
    assert nombres == [
        "Carga 2026-07.xlsx",
        "Carga 2026-08.xlsx",
        "Carga 2026-09.xlsx",
        "Carga 2026-10.xlsx",
        "Control Gym 2025.xlsx",
        "Control Gym 2026.xlsx",
        "vigencia.txt",
    ]
    # La migracion inicial solo lee los libros; las plantillas se cargan despues (CU-01).
    assert [r.name for r in LocalizadorLibrosCarpeta(grabacion.carpeta).rutas()] == [
        "Control Gym 2025.xlsx",
        "Control Gym 2026.xlsx",
    ]
    libro = openpyxl.load_workbook(grabacion.carpeta / "Control Gym 2026.xlsx", read_only=True)
    assert "demo" not in (libro.properties.title or "").lower()


def test_grabacion_libros_llegan_al_mes_5_anterior(grabacion: Escenario) -> None:
    assert grabacion.resultado.fecha_corte == date(2026, 6, 30)
    assert script.corte_de_libros(BASE_GRABACION, script.PERFILES["grabacion"]) == date(2026, 6, 30)
    assert script.corte_de_libros(BASE_GRABACION, script.PERFILES["demo"]) == date(2026, 10, 31)


def _plantillas(carpeta: Path) -> dict[str, list[FilaValida]]:
    validas: dict[str, list[FilaValida]] = {}
    for ruta in sorted(carpeta.glob("Carga *.xlsx")):
        leida = LectorPlantillaOpenpyxl().leer(ruta.read_bytes())
        resultados = [validar_fila(fila) for fila in leida.filas]
        assert all(isinstance(r, FilaValida) for r in resultados), ruta.name
        validas[ruta.stem] = [r for r in resultados if isinstance(r, FilaValida)]
    return validas


def test_grabacion_plantillas_validas_con_las_membresias_de_su_mes(grabacion: Escenario) -> None:
    plantillas = _plantillas(grabacion.carpeta)
    assert sorted(plantillas) == [f"Carga 2026-{mes:02d}" for mes in (7, 8, 9, 10)]
    for nombre, filas in plantillas.items():
        anio, mes = (int(parte) for parte in nombre.removeprefix("Carga ").split("-"))
        assert 25 <= len(filas) <= MAX_FILAS_PLANTILLA, nombre
        assert all((f.fecha_inicio.year, f.fecha_inicio.month) == (anio, mes) for f in filas)
        assert all(f.documento.startswith("0999") and cedula_valida(f.documento) for f in filas)
        assert all(f.correo is not None and f.correo.endswith("@example.com") for f in filas)
        assert all(f.celular is not None and f.celular.startswith("0900") for f in filas)
        assert all("demo" not in f.nombre.lower() for f in filas)
    simuladas = script.simular(
        script.fecha_corte(BASE_GRABACION), script.PERFILES["grabacion"].reglas
    )
    en_plantillas = sum(len(filas) for filas in plantillas.values())
    assert en_plantillas == sum(1 for m in simuladas if m.inicio > date(2026, 6, 30))


def test_grabacion_socio_tiene_la_misma_identidad_en_libros_y_plantillas(
    grabacion: Escenario,
) -> None:
    nombre_por_cedula = {r.cedula: r.nombre for r in grabacion.resultado.registros}
    filas = [f for lista in _plantillas(grabacion.carpeta).values() for f in lista]
    comunes = [f for f in filas if f.documento in nombre_por_cedula]
    assert comunes  # hay renovaciones de socios que vienen de los libros
    assert all(nombre_por_cedula[f.documento] == f.nombre for f in comunes)


def test_grabacion_ninguna_fila_se_descarta(grabacion: Escenario) -> None:
    informe = grabacion.resultado.informe
    assert informe.descartadas_no_utiles == 0
    assert informe.sin_identidad == 0
    assert informe.inicio_aproximado == 0
    assert informe.montos_invalidos == 0
    assert informe.registros_por_nombre == 0


def test_grabacion_datos_personales_son_ficticios_y_realistas(grabacion: Escenario) -> None:
    registros = grabacion.resultado.registros
    assert all(
        "demo" not in r.nombre.lower() and "prueba" not in r.nombre.lower() for r in registros
    )
    assert all(len(r.nombre.split()) == 3 for r in registros)
    assert all(
        r.cedula is not None and r.cedula.startswith("0999") and cedula_valida(r.cedula)
        for r in registros
    )
    assert all(r.correo is not None and r.correo.endswith("@example.com") for r in registros)
    assert all(
        r.celular is not None and len(r.celular) == 10 and r.celular.startswith("0900")
        for r in registros
    )
    assert all(r.celular is not None and r.celular[:3] not in PREFIJOS_MOVILES for r in registros)


def test_grabacion_cada_socio_tiene_nombre_propio(grabacion: Escenario) -> None:
    cedulas_por_nombre: dict[str, set[str | None]] = {}
    nombres_por_cedula: dict[str | None, set[str]] = {}
    for registro in grabacion.resultado.registros:
        cedulas_por_nombre.setdefault(registro.nombre, set()).add(registro.cedula)
        nombres_por_cedula.setdefault(registro.cedula, set()).add(registro.nombre)
    assert all(len(cedulas) == 1 for cedulas in cedulas_por_nombre.values())
    assert all(len(nombres) == 1 for nombres in nombres_por_cedula.values())


def test_grabacion_transacciones_con_prefijo_grab(grabacion: Escenario) -> None:
    for ruta in LocalizadorLibrosCarpeta(grabacion.carpeta).rutas():
        libro = openpyxl.load_workbook(ruta, read_only=True)
        for hoja in libro.worksheets:
            filas = list(hoja.iter_rows(min_row=2, values_only=True))
            assert filas
            assert all(str(fila[11]).startswith("GRAB-") for fila in filas)
    for ruta in grabacion.carpeta.glob("Carga *.xlsx"):
        hoja = openpyxl.load_workbook(ruta, read_only=True)["Registros"]
        assert all(
            str(f[9]).startswith("GRAB-") for f in hoja.iter_rows(min_row=2, values_only=True)
        )


def test_grabacion_historial_variado() -> None:
    membresias = script.simular(
        script.fecha_corte(BASE_GRABACION), script.PERFILES["grabacion"].reglas
    )
    ciclos_por_socio: dict[int, int] = {}
    for membresia in membresias:
        ciclos_por_socio[membresia.numero_socio] = (
            ciclos_por_socio.get(membresia.numero_socio, 0) + 1
        )
    assert 1 in ciclos_por_socio.values()
    assert max(ciclos_por_socio.values()) >= 4
    assert {m.plan for m in membresias} == {"MENSUAL", "TRIMESTRAL", "SEMESTRAL", "ANUAL"}
    assert {m.estado for m in membresias} == {"NUEVO", "RENOVACION", "REINGRESO"}


def test_grabacion_meses_cerrados_permiten_verificar_a_t_mas_30() -> None:
    corte = script.fecha_corte(BASE_GRABACION)
    membresias = script.simular(corte, script.PERFILES["grabacion"].reglas)
    inicios: dict[int, list[date]] = {}
    for membresia in membresias:
        inicios.setdefault(membresia.numero_socio, []).append(membresia.inicio)

    mes = BASE_GRABACION.replace(day=1)
    for _ in range(MESES_CERRADOS_VERIFICABLES):
        mes = (mes - timedelta(days=1)).replace(day=1)
        vencen = [m for m in membresias if (m.fin.year, m.fin.month) == (mes.year, mes.month)]
        assert len(vencen) >= VENCIMIENTOS_MINIMOS_POR_MES, mes
        renovados = [
            m
            for m in vencen
            if any(
                m.fin <= inicio <= m.fin + timedelta(days=VENTANA_RENOVACION)
                for inicio in inicios[m.numero_socio]
            )
        ]
        assert renovados, mes
        assert len(renovados) < len(vencen), mes


# La lista de hoy con nivel ALTO se comprueba tras cargar las plantillas, con PostgreSQL real:
# tests/integration/scripts/test_sembrar_grabacion.py (R-022/T9).
