"""Verificacion local de la lista de septiembre con los libros reales (T19, D3-BE-05).

Fuera de la suite. Uso (desde ``Backend/``, con el entorno virtual activo)::

    python scripts/verificar_lista.py <carpeta con los libros Control Gym>
        [--fecha 2026-08-31] [--horizonte 30] [--top-k 25]

Compone **en memoria y sin base de datos** el mismo camino que la app: ``LectorLibrosExcel``
+ ``ProcesarHistorico`` -> ``EntrenarModeloInicial`` (``RandomForestPredictor``) -> las
membresias como las guarda la migracion -> ``GenerarLista`` sobre una unidad de trabajo en
memoria. Compara con la lista de septiembre del notebook ``Notebookes/MVP.ipynb`` (13.8):

- conteos (cartera, ya renovaron, a priorizar, socios, ciclos de entrenamiento);
- la probabilidad de cada codigo del top K a 3 decimales;
- el orden, con los empates (misma probabilidad a 3 decimales) comparados como conjunto;
- los factores (porcentaje de coincidencia, informativo: decision (a) de R-004) y los
  niveles (informativos: el notebook usa umbrales fijos 0,70/0,50 y la app percentiles).

Sale con 0 si conteos, probabilidades y orden coinciden; 1 si no; 2 si no hay libros. Solo
imprime codigos ``MTB-`` (``sha256`` de la identidad), conteos y cifras: nunca nombres,
cedulas, celulares, correos ni rutas (RN-03.5, RT-13). No escribe archivos.
"""

import argparse
import hashlib
import sys
import warnings
from collections import Counter, defaultdict
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import TextIO

import sklearn

from app.application.historial.ports import MembresiaParaPrediccion, NuevaMembresia
from app.application.historial.procesar_historico import ProcesarHistorico
from app.application.listas.dtos import GenerarListaDTO
from app.application.listas.generar_lista import GenerarLista
from app.application.listas.ports import (
    ItemLista,
    ListaDetalle,
    ListaResumen,
    NuevaLista,
    NuevaPrediccion,
)
from app.application.modelo.entrenar_modelo import EntrenarModeloInicial
from app.application.modelo.mapeo import ciclo_modelo_desde
from app.application.modelo.ports import EstadoSistema, ModeloGuardado, NuevoModelo
from app.domain.common.enums import EstadoMigracion
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.domain.historico.registro import RegistroHistorico
from app.domain.modelo.cartera import seleccionar_cartera, ya_renovo
from app.domain.modelo.variables import CicloModelo
from app.infrastructure.historico.lector_libros import LectorLibrosExcel
from app.infrastructure.ml.random_forest import RandomForestPredictor

FECHA_GENERACION = date(2026, 8, 31)
HORIZONTE_DIAS = 30
TOP_K = 25
_TRES_DECIMALES = Decimal("0.001")

# Las salidas guardadas del notebook se reproducen exactamente con scikit-learn 1.8.0; con
# la version fijada en la app (1.9.1) el propio notebook da las mismas cifras que la app,
# pero sus probabilidades se mueven hasta 0,016 respecto a las guardadas (ver T19).
SKLEARN_NOTEBOOK = "1.8.0"

# Notebook 13.8 (salidas guardadas): cartera y lista operativa de septiembre de 2026.
REFERENCIA_CONTEOS: dict[str, int] = {
    "cartera": 59,
    "ya_renovaron": 2,
    "a_priorizar": 57,
    "socios": 57,
    "ciclos_entrenamiento": 1564,
}


@dataclass(frozen=True, slots=True)
class FilaReferencia:
    """Una fila del top K del notebook: codigo anonimo, probabilidad a 3 decimales, nivel
    con los umbrales fijos del notebook y factores principales."""

    codigo: str
    probabilidad: Decimal
    nivel: str
    factores: tuple[str, ...]


def _ref(codigo: str, prob: str, nivel: str, *factores: str) -> FilaReferencia:
    return FilaReferencia(codigo, Decimal(prob), nivel, factores)


_DSD = "Días desde la membresía anterior: sin dato (+0,02)"
_TRI_01 = "Plan: TRIMESTRAL (+0,01)"
_DUR_123 = "Duración del plan (días): 123 (+0,01)"
_DATAFAST = ("Forma de pago: TARJETA_DATAFAST (+0,05)", "Plan: TRIMESTRAL (+0,04)", _DSD)
_OTRO_TRI = ("Forma de pago: OTRO (+0,05)", "Plan: TRIMESTRAL (+0,03)", _DSD)
_ANUAL = (
    "Duración del plan (días): 365 (+0,05)",
    "Plan: ANUAL (+0,04)",
    "Monto actual (USD): 225 (+0,04)",
)
_MENSUAL = (
    "Monto actual (USD): 30 (+0,04)",
    "Días desde la membresía anterior: sin dato (+0,04)",
    "Forma de pago: SIN_DATO (+0,01)",
)

REFERENCIA_TOP: tuple[FilaReferencia, ...] = (
    _ref(
        "MTB-7C5F302E",
        "0.702",
        "ALTO",
        "Forma de pago: EFECTIVO (+0,07)",
        "Plan: TRIMESTRAL (+0,04)",
        _DSD,
    ),
    _ref(
        "MTB-6381C1A6",
        "0.701",
        "ALTO",
        "Plan: OTRO (+0,07)",
        "Forma de pago: EFECTIVO (+0,06)",
        _DSD,
    ),
    _ref(
        "MTB-83546C29",
        "0.687",
        "MEDIO",
        "Forma de pago: TARJETA_DATAFAST (+0,05)",
        "Plan: TRIMESTRAL (+0,04)",
        "Monto actual (USD): 99 (+0,02)",
    ),
    _ref("MTB-43E410CA", "0.684", "MEDIO", *_DATAFAST),
    _ref("MTB-FE5AB968", "0.684", "MEDIO", *_DATAFAST),
    _ref("MTB-15BCA8EE", "0.684", "MEDIO", *_DATAFAST),
    _ref("MTB-F42F3203", "0.677", "MEDIO", *_OTRO_TRI),
    _ref("MTB-61C72731", "0.677", "MEDIO", *_OTRO_TRI),
    _ref("MTB-1E601477", "0.676", "MEDIO", *_ANUAL),
    _ref("MTB-82145874", "0.676", "MEDIO", *_ANUAL),
    _ref(
        "MTB-8BDB2331", "0.674", "MEDIO", "Plan: OTRO (+0,06)", "Forma de pago: OTRO (+0,03)", _DSD
    ),
    _ref(
        "MTB-6728CA79",
        "0.672",
        "MEDIO",
        "Fecha de inicio aproximada: sí (+0,03)",
        "Plan: ANUAL (+0,03)",
        "Duración del plan (días): 365 (+0,02)",
    ),
    _ref(
        "MTB-211C4E06",
        "0.667",
        "MEDIO",
        "Forma de pago: SIN_DATO (+0,04)",
        "Plan: TRIMESTRAL (+0,03)",
        _DSD,
    ),
    _ref(
        "MTB-174990BA",
        "0.660",
        "MEDIO",
        "Plan: OTRO (+0,06)",
        "Monto actual (USD): 70 (+0,03)",
        _DSD,
    ),
    _ref(
        "MTB-1471163D",
        "0.645",
        "MEDIO",
        "Plan: OTRO (+0,06)",
        _DSD,
        "Duración del plan (días): 62 (+0,01)",
    ),
    _ref("MTB-9FD6D81D", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-64E86617", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-F53DFDB0", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-401DB2F2", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-56E191F9", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-645EE448", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-56236E6D", "0.631", "MEDIO", _DSD, _TRI_01, _DUR_123),
    _ref("MTB-DC18D489", "0.610", "MEDIO", *_MENSUAL),
    _ref("MTB-78227D28", "0.610", "MEDIO", *_MENSUAL),
    _ref("MTB-043DE3C6", "0.605", "MEDIO", _DSD, _TRI_01),
)


def codigo_anonimo(identidad: str) -> str:
    """``id_anonimo`` del notebook: ``MTB-`` + 8 primeros hex en mayusculas de ``sha256``."""
    return "MTB-" + hashlib.sha256(identidad.encode("utf-8")).hexdigest()[:8].upper()


def a_tres_decimales(score: Decimal) -> Decimal:
    return score.quantize(_TRES_DECIMALES, rounding=ROUND_HALF_EVEN)


def localizar_libros(carpeta: Path) -> list[Path]:
    """Libros ``*Control*Gym*.xlsx`` de la carpeta, ordenados; ignora bloqueos ``~$``."""
    return sorted(
        ruta
        for ruta in carpeta.glob("*.xlsx")
        if not ruta.name.startswith("~$")
        and "CONTROL" in ruta.name.upper()
        and "GYM" in ruta.name.upper()
    )


# ---------------------------------------------------------------- unidad de trabajo en memoria


class _RelojFijo:
    def __init__(self, instante: datetime) -> None:
        self._instante = instante

    def now(self) -> datetime:
        return self._instante


class _PredictorContador:
    """Delega en el adaptador real y cuenta las filas que ``GenerarLista`` manda a predecir."""

    def __init__(self, predictor: RandomForestPredictor) -> None:
        self._predictor = predictor
        self.filas_predichas = 0

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        return self._predictor.train(features, labels, numericas, categoricas, referencia)

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        self.filas_predichas += len(features)
        return self._predictor.predict(artefacto, features)


class _Membresias:
    def __init__(self, membresias: Sequence[MembresiaParaPrediccion]) -> None:
        self._membresias = list(membresias)

    def insertar_en_bloque(self, membresias: Sequence[NuevaMembresia]) -> int:
        raise NotImplementedError("La verificacion no inserta membresias.")

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        return list(self._membresias)


class _Modelos:
    def __init__(self, modelo: ModeloGuardado) -> None:
        self._modelo = modelo

    def crear(self, modelo: NuevoModelo) -> int:
        raise NotImplementedError("La verificacion no guarda modelos.")

    def obtener_vigente(self) -> ModeloGuardado | None:
        return self._modelo


class _Estado:
    def obtener(self) -> EstadoSistema:
        return EstadoSistema(EstadoMigracion.COMPLETADA, None)

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        raise NotImplementedError("La verificacion no cambia el estado.")

    def fijar_proxima_fecha(self, fecha: date) -> None:
        raise NotImplementedError("La verificacion no cambia el estado.")


class _Cargas:
    def ultima_fecha_carga_hasta(self, instante: datetime) -> datetime | None:
        return None


class _Listas:
    """Guarda la lista en memoria; los items no llevan nombre, celular ni cedula."""

    def __init__(
        self,
        modelo: ModeloGuardado,
        membresias: Sequence[MembresiaParaPrediccion],
        creada_en: datetime,
    ) -> None:
        self._modelo = modelo
        self._membresias = {m.membresia_id: m for m in membresias}
        self._creada_en = creada_en
        self.guardadas: list[tuple[NuevaLista, list[NuevaPrediccion]]] = []

    def crear(self, lista: NuevaLista, predicciones: Sequence[NuevaPrediccion]) -> int:
        self.guardadas.append((lista, list(predicciones)))
        return len(self.guardadas)

    def obtener(self, lista_id: int) -> ListaDetalle | None:
        if not 1 <= lista_id <= len(self.guardadas):
            return None
        lista, predicciones = self.guardadas[lista_id - 1]
        return ListaDetalle(
            id=lista_id,
            modelo_id=lista.modelo_id,
            modelo_version=self._modelo.version,
            fecha_generacion=lista.fecha_generacion,
            creada_en=self._creada_en,
            horizonte_dias=lista.horizonte_dias,
            top_k=lista.top_k,
            umbral_alto=self._modelo.umbral_alto,
            umbral_medio=self._modelo.umbral_medio,
            items=tuple(
                self._item(i, p)
                for i, p in enumerate(sorted(predicciones, key=lambda p: p.prioridad), 1)
            ),
            nombre=lista.nombre,
        )

    def _item(self, prediccion_id: int, p: NuevaPrediccion) -> ItemLista:
        m = self._membresias[p.membresia_id]
        if m.fecha_vencimiento is None:
            raise ValueError("Una membresia de la lista no tiene vencimiento.")
        return ItemLista(
            prediccion_id=prediccion_id,
            membresia_id=p.membresia_id,
            socio_id=p.socio_id,
            prioridad=p.prioridad,
            socio_nombre="",
            celular=None,
            cedula=None,
            plan=m.plan,
            fecha_vencimiento=m.fecha_vencimiento,
            monto_cobrado=m.monto_cobrado,
            score=p.score,
            nivel_riesgo=p.nivel_riesgo,
            factores_principales=list(p.factores_principales),
            dentro_top_k=p.dentro_top_k,
        )

    def ultima(self) -> ListaDetalle | None:
        return self.obtener(len(self.guardadas))

    def listar(self) -> list[ListaResumen]:
        return []


@dataclass(frozen=True, slots=True)
class _Contexto:
    listas: _Listas
    modelos: _Modelos
    estado: _Estado
    membresias: _Membresias
    cargas: _Cargas

    def commit(self) -> None:
        """Nada que confirmar: todo esta en memoria."""


# ---------------------------------------------------------------- ejecucion


@dataclass(frozen=True, slots=True)
class FilaApp:
    """Fila de la lista generada por la app, anonimizada."""

    prioridad: int
    codigo: str
    score: Decimal
    nivel: str
    factores: tuple[str, ...]
    dentro_top_k: bool


@dataclass(frozen=True, slots=True)
class ResultadoApp:
    conteos: dict[str, int]
    filas: tuple[FilaApp, ...]
    umbral_alto: Decimal
    umbral_medio: Decimal


def _membresias(registros: Sequence[RegistroHistorico]) -> list[MembresiaParaPrediccion]:
    """Membresias como las guarda la migracion: una por registro, ids en orden de lectura."""
    socio_de: dict[str, int] = {}
    for r in registros:
        socio_de.setdefault(r.identidad, len(socio_de) + 1)
    return [
        MembresiaParaPrediccion(
            membresia_id=i,
            socio_id=socio_de[r.identidad],
            plan=r.plan,
            forma_pago=r.forma_pago,
            fecha_inicio=r.fecha_inicio,
            fecha_vencimiento=r.fecha_vencimiento,
            fecha_actividad=r.fecha_actividad,
            monto_cobrado=r.monto_cobrado,
            inicio_aproximado=r.inicio_aproximado,
            # Decision (c) de R-005: todas "con cedula" para comparar con el notebook, que no
            # excluye a los socios sin cedula; la app si los excluye de la lista.
            socio_con_cedula=True,
        )
        for i, r in enumerate(registros, 1)
    ]


def _conteo_cartera(ciclos: Sequence[CicloModelo], fecha: date, horizonte: int) -> tuple[int, int]:
    """(ciclos en la cartera, ciclos de la cartera cuyo socio ya renovo)."""
    por_socio: defaultdict[str, list[CicloModelo]] = defaultdict(list)
    for c in ciclos:
        por_socio[c.clave_socio].append(c)
    cartera = seleccionar_cartera(ciclos, fecha, horizonte)
    return len(cartera), sum(ya_renovo(c, por_socio[c.clave_socio]) for c in cartera)


def ejecutar_en_memoria(
    rutas: Sequence[Path], fecha: date, horizonte: int, top_k: int
) -> ResultadoApp:
    """Historico -> modelo v1 -> lista de ``fecha``, todo en memoria y sin base de datos."""
    # openpyxl avisa de celdas con formato de fecha y serial invalido citando el valor de la
    # celda (puede ser una cedula mal ubicada): se silencian para no filtrar datos personales.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        procesado = ProcesarHistorico(LectorLibrosExcel()).ejecutar(rutas)

    predictor = RandomForestPredictor()
    entrenado = EntrenarModeloInicial(predictor).ejecutar(procesado.ciclos, procesado.fecha_corte)
    instante = datetime(fecha.year, fecha.month, fecha.day, tzinfo=UTC)
    modelo = ModeloGuardado(
        id=1,
        version=1,
        fecha_entrenamiento=instante,
        ciclos_entrenamiento=entrenado.ciclos_entrenamiento,
        periodo_desde=entrenado.periodo_desde,
        periodo_hasta=entrenado.periodo_hasta,
        prevalencia=entrenado.prevalencia,
        umbral_alto=entrenado.umbrales.alto,
        umbral_medio=entrenado.umbrales.medio,
        porcentajes_umbral=entrenado.porcentajes_umbral,
        artefacto=entrenado.artefacto,
        metadata_tecnica=entrenado.metadata_tecnica,
    )
    registros = procesado.registros
    membresias = _membresias(registros)
    listas = _Listas(modelo, membresias, instante)
    contexto = _Contexto(listas, _Modelos(modelo), _Estado(), _Membresias(membresias), _Cargas())

    @contextmanager
    def uow() -> Iterator[_Contexto]:
        yield contexto

    contador = _PredictorContador(predictor)
    # Decision (c) de R-005: la verificacion sigue su propio camino. El tope de 31 dias es una
    # validacion de entrada de la API; aqui se admite cualquier horizonte (>= 1) para comparar
    # con el notebook, por eso el DTO se construye sin esa validacion.
    if horizonte < 1 or top_k < 1:
        raise ValueError("El horizonte y K deben ser positivos.")
    parametros = GenerarListaDTO.model_construct(
        fecha_referencia=fecha, horizonte_dias=horizonte, top_k=top_k
    )
    GenerarLista(uow, contador, _RelojFijo(instante)).ejecutar(parametros)
    _, predicciones = listas.guardadas[-1]

    ciclos = [replace(ciclo_modelo_desde(c), ref=i) for i, c in enumerate(procesado.ciclos, 1)]
    en_cartera, ya_renovaron = _conteo_cartera(ciclos, fecha, horizonte)
    filas = tuple(
        FilaApp(
            prioridad=p.prioridad,
            codigo=codigo_anonimo(registros[p.membresia_id - 1].identidad),
            score=p.score,
            nivel=p.nivel_riesgo.value,
            factores=p.factores_principales,
            dentro_top_k=p.dentro_top_k,
        )
        for p in sorted(predicciones, key=lambda p: p.prioridad)
    )
    return ResultadoApp(
        conteos={
            "cartera": en_cartera,
            "ya_renovaron": ya_renovaron,
            "a_priorizar": contador.filas_predichas,
            "socios": len(filas),
            "ciclos_entrenamiento": entrenado.ciclos_entrenamiento,
        },
        filas=filas,
        umbral_alto=modelo.umbral_alto,
        umbral_medio=modelo.umbral_medio,
    )


# ---------------------------------------------------------------- conciliacion


def _tabla_conteos(obtenidos: dict[str, int], referencia: dict[str, int]) -> tuple[list[str], int]:
    lineas = [f"{'conteo':<22}  {'notebook':>8}  {'app':>8}  resultado"]
    diferencias = 0
    for nombre, esperado in referencia.items():
        obtenido = obtenidos.get(nombre)
        resultado = "ok" if obtenido == esperado else "DIFIERE"
        diferencias += resultado == "DIFIERE"
        lineas.append(f"{nombre:<22}  {esperado:>8}  {obtenido!s:>8}  {resultado}")
    return lineas, diferencias


def _orden_ok(posicion: int, fila_app: FilaApp | None, top: Sequence[FilaReferencia]) -> bool:
    """La fila de la app en ``posicion`` pertenece al grupo de empate del notebook en ella.

    Grupo de empate: los codigos del notebook con la misma probabilidad a 3 decimales. Si
    el grupo llega al final del top, un codigo que el notebook no muestra tambien vale si
    empata a 3 decimales (el corte del notebook no fija un orden entre empates).
    """
    if fila_app is None:
        return False
    esperada = top[posicion]
    grupo = [r for r in top if r.probabilidad == esperada.probabilidad]
    if fila_app.codigo in {r.codigo for r in grupo}:
        return True
    llega_al_final = grupo[-1] is top[-1]
    en_top = fila_app.codigo in {r.codigo for r in top}
    return (
        llega_al_final and not en_top and a_tres_decimales(fila_app.score) == esperada.probabilidad
    )


def _tabla_top(
    filas: Sequence[FilaApp], top: Sequence[FilaReferencia]
) -> tuple[list[str], int, int, int, int]:
    """Lineas, diferencias de probabilidad, de orden, factores iguales y niveles iguales."""
    por_codigo = {f.codigo: f for f in filas}
    lineas = [
        f"{'pos':>3}  {'notebook':<12}  {'prob':>5}  {'app':<12}  {'prob':>5}  "
        "prob_codigo  orden    factores  nivel_nb  nivel_app"
    ]
    dif_prob = dif_orden = factores_iguales = niveles_iguales = 0
    for i, ref in enumerate(top):
        en_posicion = filas[i] if i < len(filas) else None
        del_codigo = por_codigo.get(ref.codigo)
        if del_codigo is None:
            prob = "AUSENTE"
        elif a_tres_decimales(del_codigo.score) == ref.probabilidad:
            prob = "ok"
        else:
            prob = f"DIFIERE({a_tres_decimales(del_codigo.score)})"
        dif_prob += prob != "ok"
        orden = "ok" if _orden_ok(i, en_posicion, top) else "DIFIERE"
        dif_orden += orden == "DIFIERE"
        factores = "igual" if del_codigo and del_codigo.factores == ref.factores else "distinto"
        factores_iguales += factores == "igual"
        nivel_app = del_codigo.nivel if del_codigo else "-"
        niveles_iguales += nivel_app == ref.nivel
        codigo_app = en_posicion.codigo if en_posicion else "-"
        prob_app = f"{a_tres_decimales(en_posicion.score)}" if en_posicion else "-"
        lineas.append(
            f"{i + 1:>3}  {ref.codigo:<12}  {ref.probabilidad:>5}  {codigo_app:<12}  "
            f"{prob_app:>5}  {prob:<11}  {orden:<7}  {factores:<8}  {ref.nivel:<8}  {nivel_app}"
        )
    return lineas, dif_prob, dif_orden, factores_iguales, niveles_iguales


def _porcentaje(parte: int, total: int) -> str:
    return f"{(100 * parte / total) if total else 0:.1f} %"


def main(
    argv: Sequence[str] | None = None,
    *,
    conteos: dict[str, int] = REFERENCIA_CONTEOS,
    top: Sequence[FilaReferencia] = REFERENCIA_TOP,
    salida: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(description="Verifica la lista frente al notebook.")
    parser.add_argument("carpeta", type=Path, help="carpeta con los libros Control Gym")
    parser.add_argument("--fecha", type=date.fromisoformat, default=FECHA_GENERACION)
    parser.add_argument("--horizonte", type=int, default=HORIZONTE_DIAS)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    argumentos = parser.parse_args(argv)

    rutas = localizar_libros(argumentos.carpeta)
    if not rutas:
        print("No se encontraron libros Control Gym en la carpeta indicada.", file=salida)
        return 2

    resultado = ejecutar_en_memoria(rutas, argumentos.fecha, argumentos.horizonte, argumentos.top_k)
    lineas_conteos, dif_conteos = _tabla_conteos(resultado.conteos, conteos)
    lineas_top, dif_prob, dif_orden, factores_iguales, niveles_iguales = _tabla_top(
        resultado.filas, top
    )
    niveles_app = Counter(f.nivel for f in resultado.filas)

    def imprimir(texto: str = "") -> None:
        print(texto, file=salida)

    imprimir(
        f"lista de {argumentos.fecha.isoformat()} | horizonte {argumentos.horizonte} dias | "
        f"top {argumentos.top_k} | libros: {len(rutas)}"
    )
    for linea in lineas_conteos:
        imprimir(linea)
    imprimir()
    imprimir(f"top {len(top)} del notebook frente a la app (probabilidad a 3 decimales):")
    for linea in lineas_top:
        imprimir(linea)
    imprimir()
    imprimir(
        f"umbrales de la app (P80/P50): alto {a_tres_decimales(resultado.umbral_alto)} | "
        f"medio {a_tres_decimales(resultado.umbral_medio)}; niveles en toda la lista: "
        + ", ".join(f"{n} {niveles_app.get(n, 0)}" for n in ("ALTO", "MEDIO", "BAJO"))
    )
    imprimir(
        f"factores iguales: {factores_iguales} de {len(top)} "
        f"({_porcentaje(factores_iguales, len(top))}, informativo, decision (a))"
    )
    imprimir(
        f"niveles iguales: {niveles_iguales} de {len(top)} "
        f"({_porcentaje(niveles_iguales, len(top))}, informativo: umbrales fijos 0,70/0,50 "
        "del notebook frente a percentiles 20/30/50 de la app)"
    )
    imprimir(
        f"conteos distintos: {dif_conteos} | probabilidades distintas: {dif_prob} | "
        f"posiciones fuera de orden: {dif_orden}"
    )
    if sklearn.__version__ != SKLEARN_NOTEBOOK:
        imprimir(
            f"aviso: scikit-learn {sklearn.__version__} instalado; las salidas guardadas del "
            f"notebook se generaron con {SKLEARN_NOTEBOOK} (el bosque cambia entre versiones)"
        )
    return 0 if dif_conteos == dif_prob == dif_orden == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
